import uuid
from datetime import date, datetime, timezone as tz
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tz import today as tz_today
from app.models.asset import Asset, AssetType
from app.models.income import Income, IncomeType, RecurringIncome
from app.models.transaction import Transaction, TransactionType, CurrencyType
from app.models.user import User
from app.services.budget_period import get_budget_period
from app.schemas.income import (
    IncomeCreate, IncomeUpdate, IncomeResponse,
    IncomeListResponse, IncomeSummaryResponse,
    RecurringIncomeCreate, RecurringIncomeUpdate, RecurringIncomeResponse,
)

ALLOWED_TARGET_TYPES = {AssetType.CASH_KRW, AssetType.DEPOSIT, AssetType.PARKING}


# ── 공통 헬퍼 ──

async def _validate_target_asset(
    db: AsyncSession, user_id: uuid.UUID, asset_id: uuid.UUID
) -> Asset:
    asset = await db.get(Asset, asset_id)
    if not asset or asset.user_id != user_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    if asset.asset_type not in ALLOWED_TARGET_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Asset type '{asset.asset_type.value}' is not allowed for income linking",
        )
    return asset


async def _adjust_asset_principal(asset: Asset, delta: Decimal) -> None:
    current = Decimal(str(asset.principal)) if asset.principal else Decimal("0")
    new_val = current + delta
    if new_val < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient balance: {asset.name} (current: {current}, required: {abs(delta)})",
        )
    asset.principal = new_val


def _income_to_response(income: Income, target_asset_name: str | None = None) -> IncomeResponse:
    return IncomeResponse(
        id=income.id,
        type=income.type.value,
        amount=float(income.amount),
        description=income.description,
        recurring_income_id=income.recurring_income_id,
        target_asset_id=income.target_asset_id,
        target_asset_name=target_asset_name,
        received_at=income.received_at,
        created_at=income.created_at,
    )


# ── RecurringIncome (템플릿) CRUD ──

def _recurring_to_response(
    ri: RecurringIncome, target_asset_name: str | None = None,
) -> RecurringIncomeResponse:
    return RecurringIncomeResponse(
        id=ri.id,
        type=ri.type.value,
        amount=float(ri.amount),
        description=ri.description,
        recurring_day=ri.recurring_day,
        target_asset_id=ri.target_asset_id,
        target_asset_name=target_asset_name,
        is_active=ri.is_active,
        created_at=ri.created_at,
        updated_at=ri.updated_at,
    )


async def _get_target_asset_name(
    db: AsyncSession, asset_id: uuid.UUID | None,
) -> str | None:
    if not asset_id:
        return None
    asset = await db.get(Asset, asset_id)
    return asset.name if asset else None


async def get_recurring_incomes(
    db: AsyncSession, user_id: uuid.UUID,
) -> list[RecurringIncomeResponse]:
    stmt = (
        select(RecurringIncome)
        .where(RecurringIncome.user_id == user_id)
        .order_by(RecurringIncome.recurring_day)
    )
    items = (await db.execute(stmt)).scalars().all()

    asset_ids = {ri.target_asset_id for ri in items if ri.target_asset_id}
    asset_cache: dict[uuid.UUID, str] = {}
    if asset_ids:
        asset_stmt = select(Asset.id, Asset.name).where(Asset.id.in_(asset_ids))
        asset_rows = (await db.execute(asset_stmt)).all()
        asset_cache = {row.id: row.name for row in asset_rows}

    return [
        _recurring_to_response(
            ri, asset_cache.get(ri.target_asset_id) if ri.target_asset_id else None
        )
        for ri in items
    ]


async def _upsert_auto_income_for_recurring(
    db: AsyncSession, ri: RecurringIncome, today: date,
) -> None:
    """현재 달에 해당하는 자동 수입이 없으면 생성, 있으면 갱신."""
    stmt = select(Income).where(
        Income.recurring_income_id == ri.id,
        extract("year", Income.received_at) == today.year,
        extract("month", Income.received_at) == today.month,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()

    import calendar
    _, last_day = calendar.monthrange(today.year, today.month)
    recv_day = min(ri.recurring_day, last_day)
    received_at = date(today.year, today.month, recv_day)

    if existing:
        existing.type = ri.type
        existing.amount = ri.amount
        existing.description = ri.description
        existing.target_asset_id = ri.target_asset_id
        existing.received_at = received_at
    else:
        income = Income(
            user_id=ri.user_id,
            type=ri.type,
            amount=ri.amount,
            description=ri.description,
            recurring_income_id=ri.id,
            target_asset_id=ri.target_asset_id,
            received_at=received_at,
        )
        db.add(income)


async def _delete_auto_income_for_recurring(
    db: AsyncSession, ri_id: uuid.UUID, today: date,
) -> None:
    """현재 달의 자동 수입을 삭제."""
    stmt = select(Income).where(
        Income.recurring_income_id == ri_id,
        extract("year", Income.received_at) == today.year,
        extract("month", Income.received_at) == today.month,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        await db.delete(existing)


async def create_recurring_income(
    db: AsyncSession, user_id: uuid.UUID, data: RecurringIncomeCreate,
) -> RecurringIncomeResponse:
    if data.target_asset_id:
        await _validate_target_asset(db, user_id, data.target_asset_id)

    ri = RecurringIncome(
        user_id=user_id,
        type=IncomeType(data.type),
        amount=data.amount,
        description=data.description,
        recurring_day=data.recurring_day,
        target_asset_id=data.target_asset_id,
    )
    db.add(ri)
    await db.flush()

    # 현재 달에 자동 수입 생성
    today = tz_today()
    await _upsert_auto_income_for_recurring(db, ri, today)

    await db.commit()
    await db.refresh(ri)
    asset_name = await _get_target_asset_name(db, ri.target_asset_id)
    return _recurring_to_response(ri, asset_name)


async def update_recurring_income(
    db: AsyncSession, user_id: uuid.UUID, ri_id: uuid.UUID, data: RecurringIncomeUpdate,
) -> RecurringIncomeResponse:
    stmt = select(RecurringIncome).where(
        RecurringIncome.id == ri_id, RecurringIncome.user_id == user_id
    )
    ri = (await db.execute(stmt)).scalar_one_or_none()
    if not ri:
        raise HTTPException(status_code=404, detail="Recurring income not found")

    update_data = data.model_dump(exclude_unset=True)
    if "type" in update_data:
        update_data["type"] = IncomeType(update_data["type"])
    if "target_asset_id" in update_data and update_data["target_asset_id"]:
        await _validate_target_asset(db, user_id, update_data["target_asset_id"])

    for field, value in update_data.items():
        setattr(ri, field, value)

    # 활성이면 현재 달 자동 수입 동기화
    today = tz_today()
    if ri.is_active:
        await _upsert_auto_income_for_recurring(db, ri, today)
    else:
        await _delete_auto_income_for_recurring(db, ri.id, today)

    await db.commit()
    await db.refresh(ri)
    asset_name = await _get_target_asset_name(db, ri.target_asset_id)
    return _recurring_to_response(ri, asset_name)


async def delete_recurring_income(
    db: AsyncSession, user_id: uuid.UUID, ri_id: uuid.UUID,
) -> None:
    stmt = select(RecurringIncome).where(
        RecurringIncome.id == ri_id, RecurringIncome.user_id == user_id
    )
    ri = (await db.execute(stmt)).scalar_one_or_none()
    if not ri:
        raise HTTPException(status_code=404, detail="Recurring income not found")

    # 현재 달 자동 수입 삭제
    today = tz_today()
    await _delete_auto_income_for_recurring(db, ri.id, today)

    await db.delete(ri)
    await db.commit()


async def toggle_recurring_income(
    db: AsyncSession, user_id: uuid.UUID, ri_id: uuid.UUID,
) -> RecurringIncomeResponse:
    stmt = select(RecurringIncome).where(
        RecurringIncome.id == ri_id, RecurringIncome.user_id == user_id
    )
    ri = (await db.execute(stmt)).scalar_one_or_none()
    if not ri:
        raise HTTPException(status_code=404, detail="Recurring income not found")

    ri.is_active = not ri.is_active

    today = tz_today()
    if ri.is_active:
        await _upsert_auto_income_for_recurring(db, ri, today)
    else:
        await _delete_auto_income_for_recurring(db, ri.id, today)

    await db.commit()
    await db.refresh(ri)
    asset_name = await _get_target_asset_name(db, ri.target_asset_id)
    return _recurring_to_response(ri, asset_name)


# ── Income (실제 수입 기록) CRUD ──

async def get_incomes(
    db: AsyncSession,
    user_id: uuid.UUID,
    income_type: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    page: int = 1,
    per_page: int = 20,
) -> IncomeListResponse:
    query = select(Income).where(Income.user_id == user_id)

    if income_type:
        query = query.where(Income.type == income_type)
    if start_date:
        query = query.where(Income.received_at >= start_date)
    if end_date:
        query = query.where(Income.received_at <= end_date)

    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(Income.received_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    incomes = result.scalars().all()

    # 자산 이름 조회
    asset_ids = {i.target_asset_id for i in incomes if i.target_asset_id}
    asset_cache: dict[uuid.UUID, str] = {}
    if asset_ids:
        asset_stmt = select(Asset.id, Asset.name).where(Asset.id.in_(asset_ids))
        asset_rows = (await db.execute(asset_stmt)).all()
        asset_cache = {row.id: row.name for row in asset_rows}

    return IncomeListResponse(
        data=[
            _income_to_response(
                i, asset_cache.get(i.target_asset_id) if i.target_asset_id else None
            )
            for i in incomes
        ],
        total=total,
        page=page,
        per_page=per_page,
    )


async def create_income(
    db: AsyncSession, user_id: uuid.UUID, data: IncomeCreate
) -> IncomeResponse:
    target_asset_name: str | None = None
    if data.target_asset_id:
        asset = await _validate_target_asset(db, user_id, data.target_asset_id)
        await _adjust_asset_principal(asset, data.amount)
        target_asset_name = asset.name

        tx = Transaction(
            user_id=user_id,
            asset_id=data.target_asset_id,
            type=TransactionType.DEPOSIT,
            quantity=Decimal("1"),
            unit_price=data.amount,
            currency=CurrencyType.KRW,
            memo=f"[수입] {data.description}",
            transacted_at=datetime.combine(data.received_at, datetime.min.time(), tzinfo=tz.utc),
        )
        db.add(tx)

    income = Income(
        user_id=user_id,
        type=IncomeType(data.type),
        amount=data.amount,
        description=data.description,
        target_asset_id=data.target_asset_id,
        received_at=data.received_at,
    )
    db.add(income)
    await db.commit()
    await db.refresh(income)
    return _income_to_response(income, target_asset_name)


async def update_income(
    db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID, data: IncomeUpdate
) -> IncomeResponse:
    result = await db.execute(
        select(Income).where(Income.id == income_id, Income.user_id == user_id)
    )
    income = result.scalar_one_or_none()
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")

    update_data = data.model_dump(exclude_unset=True)
    if "type" in update_data:
        update_data["type"] = IncomeType(update_data["type"])

    # 자산 연동 처리
    old_asset_id = income.target_asset_id
    new_asset_id = update_data.get("target_asset_id", old_asset_id)
    old_amount = income.amount
    new_amount = update_data.get("amount", old_amount)

    # 기존 자산 차감 (복원)
    if old_asset_id:
        old_asset = await db.get(Asset, old_asset_id)
        if old_asset:
            await _adjust_asset_principal(old_asset, -Decimal(str(old_amount)))

    # 새 자산 증가
    if new_asset_id:
        new_asset = await _validate_target_asset(db, user_id, new_asset_id)
        await _adjust_asset_principal(new_asset, Decimal(str(new_amount)))

    for key, value in update_data.items():
        setattr(income, key, value)

    await db.commit()
    await db.refresh(income)
    target_asset_name = None
    if income.target_asset_id:
        ta = await db.get(Asset, income.target_asset_id)
        target_asset_name = ta.name if ta else None
    return _income_to_response(income, target_asset_name)


async def delete_income(
    db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Income).where(Income.id == income_id, Income.user_id == user_id)
    )
    income = result.scalar_one_or_none()
    if not income:
        raise HTTPException(status_code=404, detail="Income not found")

    # 자산 잔액 차감 (복원)
    if income.target_asset_id:
        asset = await db.get(Asset, income.target_asset_id)
        if asset:
            await _adjust_asset_principal(asset, -Decimal(str(income.amount)))

        # 연관 거래내역 삭제
        tx_stmt = select(Transaction).where(
            Transaction.user_id == user_id,
            Transaction.asset_id == income.target_asset_id,
            Transaction.type == TransactionType.DEPOSIT,
            Transaction.memo == f"[수입] {income.description}",
        )
        tx = (await db.execute(tx_stmt)).scalar_one_or_none()
        if tx:
            await db.delete(tx)

    await db.delete(income)
    await db.commit()


async def get_income_summary(
    db: AsyncSession, user_id: uuid.UUID, period_start: date, period_end: date
) -> IncomeSummaryResponse:
    result = await db.execute(
        select(Income).where(
            Income.user_id == user_id,
            Income.received_at >= period_start,
            Income.received_at <= period_end,
        )
    )
    incomes = result.scalars().all()

    salary = sum(float(i.amount) for i in incomes if i.type == IncomeType.SALARY)
    side = sum(float(i.amount) for i in incomes if i.type == IncomeType.SIDE)
    investment = sum(float(i.amount) for i in incomes if i.type == IncomeType.INVESTMENT)
    other = sum(float(i.amount) for i in incomes if i.type == IncomeType.OTHER)
    recurring_count = sum(1 for i in incomes if i.recurring_income_id is not None)

    return IncomeSummaryResponse(
        total_monthly_income=salary + side + investment + other,
        salary_income=salary,
        side_income=side,
        investment_income=investment,
        other_income=other,
        recurring_count=recurring_count,
    )
