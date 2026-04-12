import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.account import Account
from app.models.budget_v2 import BudgetAllocation
from app.models.carryover import CarryoverLog, CarryoverSetting, CarryoverType
from app.models.category import Category
from app.models.entry import Entry, EntryGroup, EntryType, GroupType
from app.schemas.carryover import (
    CarryoverLogResponse,
    CarryoverPreviewResponse,
    CarryoverSettingCreate,
    CarryoverSettingResponse,
)
from app.services.budget_v2_service import (
    ensure_default_allocations,
    get_or_create_period,
    get_period_dates,
)


def _carryover_type_label(t: CarryoverType) -> str:
    return {
        CarryoverType.EXPIRE: "소멸",
        CarryoverType.NEXT_MONTH: "다음 달로 이월",
        CarryoverType.SAVINGS: "적금 이체",
        CarryoverType.DEPOSIT: "예금 이체",
        CarryoverType.TRANSFER: "계좌 이체",
    }[t]


async def _to_setting_response(
    db: AsyncSession, setting: CarryoverSetting,
) -> CarryoverSettingResponse:
    cat = await db.get(Category, setting.category_id)
    source_name = None
    if setting.source_asset_id:
        acc = await db.get(Account, setting.source_asset_id)
        if acc:
            source_name = acc.name

    return CarryoverSettingResponse(
        id=setting.id,
        category_id=setting.category_id,
        category_name=cat.name if cat else "(삭제된 카테고리)",
        carryover_type=setting.carryover_type.value,
        carryover_limit=float(setting.carryover_limit) if setting.carryover_limit is not None else None,
        source_asset_id=setting.source_asset_id,
        source_asset_name=source_name,
        target_asset_id=setting.target_asset_id,
        target_savings_name=setting.target_savings_name,
        target_annual_rate=(
            float(setting.target_annual_rate)
            if setting.target_annual_rate is not None else None
        ),
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )


async def _to_log_response(
    db: AsyncSession, log: CarryoverLog,
) -> CarryoverLogResponse:
    cat = await db.get(Category, log.category_id)
    return CarryoverLogResponse(
        id=log.id,
        category_id=log.category_id,
        category_name=cat.name if cat else "(삭제된 카테고리)",
        budget_period_start=log.budget_period_start,
        budget_period_end=log.budget_period_end,
        carryover_type=log.carryover_type.value,
        amount=float(log.amount),
        target_description=log.target_description,
        executed_at=log.executed_at,
        created_at=log.created_at,
    )


async def get_carryover_settings(
    db: AsyncSession, user_id: uuid.UUID,
) -> list[CarryoverSettingResponse]:
    stmt = select(CarryoverSetting).where(CarryoverSetting.user_id == user_id)
    settings = (await db.execute(stmt)).scalars().all()
    return [await _to_setting_response(db, s) for s in settings]


async def upsert_carryover_setting(
    db: AsyncSession,
    user_id: uuid.UUID,
    data: CarryoverSettingCreate,
) -> CarryoverSettingResponse:
    # 카테고리 소유권 확인
    cat = await db.get(Category, data.category_id)
    if not cat or cat.user_id != user_id:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        co_type = CarryoverType(data.carryover_type)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid carryover_type") from e

    stmt = select(CarryoverSetting).where(
        CarryoverSetting.user_id == user_id,
        CarryoverSetting.category_id == data.category_id,
    )
    setting = (await db.execute(stmt)).scalar_one_or_none()

    if setting:
        setting.carryover_type = co_type
        setting.carryover_limit = data.carryover_limit
        setting.source_asset_id = data.source_asset_id
        setting.target_asset_id = data.target_asset_id
        setting.target_savings_name = data.target_savings_name
        setting.target_annual_rate = data.target_annual_rate
    else:
        setting = CarryoverSetting(
            user_id=user_id,
            category_id=data.category_id,
            carryover_type=co_type,
            carryover_limit=data.carryover_limit,
            source_asset_id=data.source_asset_id,
            target_asset_id=data.target_asset_id,
            target_savings_name=data.target_savings_name,
            target_annual_rate=data.target_annual_rate,
        )
        db.add(setting)

    await db.commit()
    await db.refresh(setting)
    return await _to_setting_response(db, setting)


async def get_carryover_preview(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> list[CarryoverPreviewResponse]:
    """특정 기간의 카테고리별 잔여 예산 미리보기"""
    alloc_stmt = select(BudgetAllocation).where(
        BudgetAllocation.user_id == user_id,
        BudgetAllocation.period_start == period_start,
    )
    allocations = (await db.execute(alloc_stmt)).scalars().all()

    setting_stmt = select(CarryoverSetting).where(CarryoverSetting.user_id == user_id)
    settings = {
        s.category_id: s for s in (await db.execute(setting_stmt)).scalars().all()
    }

    period_end_exclusive = period_end + timedelta(days=1)

    results: list[CarryoverPreviewResponse] = []
    for alloc in allocations:
        spent_stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
            Entry.user_id == user_id,
            Entry.category_id == alloc.category_id,
            Entry.type == EntryType.EXPENSE,
            Entry.transacted_at >= period_start,
            Entry.transacted_at < period_end_exclusive,
        )
        spent = abs(Decimal(str((await db.execute(spent_stmt)).scalar())))
        remaining = alloc.amount - spent

        setting = settings.get(alloc.category_id)
        co_type = setting.carryover_type if setting else CarryoverType.EXPIRE

        # 이월 가능 금액: 잔여 - 한도(있으면 min)
        carryover_amount = max(remaining, Decimal("0"))
        if setting and setting.carryover_limit is not None:
            carryover_amount = min(carryover_amount, setting.carryover_limit)

        cat = await db.get(Category, alloc.category_id)
        results.append(CarryoverPreviewResponse(
            category_id=alloc.category_id,
            category_name=cat.name if cat else "(삭제된 카테고리)",
            carryover_type=co_type.value,
            budget=float(alloc.amount),
            spent=float(spent),
            remaining=float(remaining),
            carryover_amount=float(carryover_amount),
            target_description=_target_description(setting) if setting else None,
        ))

    return results


def _target_description(setting: CarryoverSetting) -> str | None:
    if setting.carryover_type == CarryoverType.NEXT_MONTH:
        return "다음 달 예산에 추가"
    if setting.carryover_type == CarryoverType.SAVINGS and setting.target_savings_name:
        return f"적금: {setting.target_savings_name}"
    if setting.carryover_type == CarryoverType.DEPOSIT and setting.target_savings_name:
        return f"예금: {setting.target_savings_name}"
    if setting.carryover_type in (
        CarryoverType.SAVINGS, CarryoverType.DEPOSIT, CarryoverType.TRANSFER,
    ):
        return "대상 계좌로 이체"
    return None


async def _apply_next_month(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    amount: Decimal,
    next_start: date,
    next_end: date,
) -> None:
    """잔여 예산을 다음 기간 allocation에 추가. 없으면 default_allocation 기반으로 생성 후 +."""
    # 먼저 다음 기간의 default 시드 보장
    await ensure_default_allocations(db, user_id, next_start, next_end)

    existing = (await db.execute(
        select(BudgetAllocation).where(
            BudgetAllocation.user_id == user_id,
            BudgetAllocation.category_id == category_id,
            BudgetAllocation.period_start == next_start,
        )
    )).scalar_one_or_none()

    if existing:
        existing.amount += amount
    else:
        db.add(BudgetAllocation(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            period_start=next_start,
            period_end=next_end,
        ))


async def _apply_account_transfer(
    db: AsyncSession,
    user_id: uuid.UUID,
    setting: CarryoverSetting,
    amount: Decimal,
    when: datetime,
) -> str | None:
    """source_asset → target_asset 이체 Entry 생성. target_description 반환."""
    if not setting.source_asset_id or not setting.target_asset_id:
        return None

    src = await db.get(Account, setting.source_asset_id)
    tgt = await db.get(Account, setting.target_asset_id)
    if not src or not tgt or src.user_id != user_id or tgt.user_id != user_id:
        return None

    group = EntryGroup(
        user_id=user_id,
        group_type=GroupType.TRANSFER,
        description=f"예산 이월 이체: {src.name} → {tgt.name}",
    )
    db.add(group)
    await db.flush()

    db.add(Entry(
        user_id=user_id,
        account_id=src.id,
        entry_group_id=group.id,
        type=EntryType.TRANSFER_OUT,
        amount=-amount,
        currency=src.currency,
        memo="예산 이월 이체",
        transacted_at=when,
    ))
    db.add(Entry(
        user_id=user_id,
        account_id=tgt.id,
        entry_group_id=group.id,
        type=EntryType.TRANSFER_IN,
        amount=amount,
        currency=tgt.currency,
        memo="예산 이월 이체",
        transacted_at=when,
    ))

    return f"{src.name} → {tgt.name}"


async def execute_carryover(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> list[CarryoverLogResponse]:
    """지정한 기간의 잔여 예산을 각 카테고리 정책대로 이월 실행."""
    period = await get_or_create_period(db, user_id)
    # 다음 기간 계산
    next_day = period_end + timedelta(days=1)
    next_start, next_end = get_period_dates(period.period_start_day, next_day)

    preview = await get_carryover_preview(db, user_id, period_start, period_end)

    setting_stmt = select(CarryoverSetting).where(CarryoverSetting.user_id == user_id)
    settings_by_cat = {
        s.category_id: s for s in (await db.execute(setting_stmt)).scalars().all()
    }

    executed_at = datetime.now(timezone.utc)
    logs: list[CarryoverLog] = []

    for item in preview:
        cat_id = item.category_id
        amount = Decimal(str(item.carryover_amount))
        if amount <= 0:
            continue

        setting = settings_by_cat.get(cat_id)
        co_type = setting.carryover_type if setting else CarryoverType.EXPIRE
        target_desc: str | None = None

        if co_type == CarryoverType.EXPIRE:
            # 소멸: 로그만 남기고 끝
            target_desc = "소멸"
        elif co_type == CarryoverType.NEXT_MONTH:
            await _apply_next_month(db, user_id, cat_id, amount, next_start, next_end)
            target_desc = "다음 달 예산에 추가"
        elif co_type in (CarryoverType.SAVINGS, CarryoverType.DEPOSIT, CarryoverType.TRANSFER):
            if setting is None:
                continue
            target_desc = await _apply_account_transfer(
                db, user_id, setting, amount, executed_at,
            )
            if target_desc is None:
                # 계좌 미설정/오너 불일치 → 스킵
                continue
            if co_type == CarryoverType.DEPOSIT and setting.target_annual_rate is not None:
                tgt = await db.get(Account, setting.target_asset_id) if setting.target_asset_id else None
                if tgt and tgt.user_id == user_id:
                    tgt.interest_rate = setting.target_annual_rate
        else:
            continue

        log = CarryoverLog(
            user_id=user_id,
            category_id=cat_id,
            budget_period_start=period_start,
            budget_period_end=period_end,
            carryover_type=co_type,
            amount=amount,
            target_description=target_desc,
            executed_at=executed_at,
        )
        db.add(log)
        logs.append(log)

    await db.commit()
    for log in logs:
        await db.refresh(log)

    return [await _to_log_response(db, log) for log in logs]


async def get_carryover_logs(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
) -> list[CarryoverLogResponse]:
    stmt = select(CarryoverLog).where(CarryoverLog.user_id == user_id)
    if period_start is not None:
        stmt = stmt.where(CarryoverLog.budget_period_start == period_start)
    if period_end is not None:
        stmt = stmt.where(CarryoverLog.budget_period_end == period_end)
    stmt = stmt.order_by(CarryoverLog.executed_at.desc())
    logs = (await db.execute(stmt)).scalars().all()
    return [await _to_log_response(db, log) for log in logs]
