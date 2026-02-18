import uuid
from datetime import date
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset, AssetType
from app.models.income import Income, IncomeType
from app.models.transaction import Transaction, TransactionType, CurrencyType
from app.schemas.income import (
    IncomeCreate, IncomeUpdate, IncomeResponse,
    IncomeListResponse, IncomeSummaryResponse,
)

ALLOWED_TARGET_TYPES = {AssetType.CASH_KRW, AssetType.DEPOSIT, AssetType.PARKING}


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
    current = asset.principal or Decimal("0")
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
        is_recurring=income.is_recurring,
        recurring_day=income.recurring_day,
        target_asset_id=income.target_asset_id,
        target_asset_name=target_asset_name,
        received_at=income.received_at,
        created_at=income.created_at,
    )


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

        # 거래내역에도 입금 기록 생성
        from datetime import datetime, timezone as tz
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
        is_recurring=data.is_recurring,
        recurring_day=data.recurring_day,
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
    recurring_count = sum(1 for i in incomes if i.is_recurring)

    return IncomeSummaryResponse(
        total_monthly_income=salary + side + investment + other,
        salary_income=salary,
        side_income=side,
        investment_income=investment,
        other_income=other,
        recurring_count=recurring_count,
    )
