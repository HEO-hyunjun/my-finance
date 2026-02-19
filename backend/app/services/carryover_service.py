import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.budget import (
    BudgetCategory, Expense, BudgetCarryoverSetting, BudgetCarryoverLog, CarryoverType,
)
from app.schemas.carryover import (
    CarryoverSettingCreate, CarryoverSettingResponse,
    CarryoverLogResponse, CarryoverPreviewResponse,
)


async def get_carryover_settings(
    db: AsyncSession, user_id: uuid.UUID
) -> list[CarryoverSettingResponse]:
    result = await db.execute(
        select(BudgetCarryoverSetting, BudgetCategory.name)
        .join(BudgetCategory, BudgetCarryoverSetting.category_id == BudgetCategory.id)
        .where(BudgetCarryoverSetting.user_id == user_id)
        .order_by(BudgetCategory.sort_order)
    )
    rows = result.all()

    # source_asset_id → name 매핑
    source_ids = {s.source_asset_id for s, _ in rows if s.source_asset_id}
    source_name_map: dict[uuid.UUID, str] = {}
    if source_ids:
        asset_rows = (await db.execute(
            select(Asset.id, Asset.name).where(Asset.id.in_(source_ids))
        )).all()
        source_name_map = {r.id: r.name for r in asset_rows}

    return [
        CarryoverSettingResponse(
            id=setting.id,
            category_id=setting.category_id,
            category_name=cat_name,
            carryover_type=setting.carryover_type.value,
            carryover_limit=float(setting.carryover_limit) if setting.carryover_limit else None,
            source_asset_id=setting.source_asset_id,
            source_asset_name=source_name_map.get(setting.source_asset_id) if setting.source_asset_id else None,
            target_asset_id=setting.target_asset_id,
            target_savings_name=setting.target_savings_name,
            target_annual_rate=float(setting.target_annual_rate) if setting.target_annual_rate else None,
            created_at=setting.created_at,
            updated_at=setting.updated_at,
        )
        for setting, cat_name in rows
    ]


async def upsert_carryover_setting(
    db: AsyncSession, user_id: uuid.UUID, data: CarryoverSettingCreate
) -> CarryoverSettingResponse:
    result = await db.execute(
        select(BudgetCarryoverSetting).where(
            BudgetCarryoverSetting.user_id == user_id,
            BudgetCarryoverSetting.category_id == data.category_id,
        )
    )
    setting = result.scalar_one_or_none()

    if setting:
        setting.carryover_type = CarryoverType(data.carryover_type)
        setting.carryover_limit = data.carryover_limit
        setting.source_asset_id = data.source_asset_id
        setting.target_asset_id = data.target_asset_id
        setting.target_savings_name = data.target_savings_name
        setting.target_annual_rate = data.target_annual_rate
    else:
        setting = BudgetCarryoverSetting(
            user_id=user_id,
            category_id=data.category_id,
            carryover_type=CarryoverType(data.carryover_type),
            carryover_limit=data.carryover_limit,
            source_asset_id=data.source_asset_id,
            target_asset_id=data.target_asset_id,
            target_savings_name=data.target_savings_name,
            target_annual_rate=data.target_annual_rate,
        )
        db.add(setting)

    await db.commit()
    await db.refresh(setting)

    cat_result = await db.execute(
        select(BudgetCategory.name).where(BudgetCategory.id == setting.category_id)
    )
    cat_name = cat_result.scalar_one()

    source_asset_name = None
    if setting.source_asset_id:
        src_result = await db.execute(
            select(Asset.name).where(Asset.id == setting.source_asset_id)
        )
        source_asset_name = src_result.scalar_one_or_none()

    return CarryoverSettingResponse(
        id=setting.id,
        category_id=setting.category_id,
        category_name=cat_name,
        carryover_type=setting.carryover_type.value,
        carryover_limit=float(setting.carryover_limit) if setting.carryover_limit else None,
        source_asset_id=setting.source_asset_id,
        source_asset_name=source_asset_name,
        target_asset_id=setting.target_asset_id,
        target_savings_name=setting.target_savings_name,
        target_annual_rate=float(setting.target_annual_rate) if setting.target_annual_rate else None,
        created_at=setting.created_at,
        updated_at=setting.updated_at,
    )


async def get_carryover_preview(
    db: AsyncSession, user_id: uuid.UUID, period_start: date, period_end: date
) -> list[CarryoverPreviewResponse]:
    # Get categories with their settings
    cat_result = await db.execute(
        select(BudgetCategory).where(
            BudgetCategory.user_id == user_id,
            BudgetCategory.is_active.is_(True),
        )
    )
    categories = cat_result.scalars().all()

    # Get carryover settings
    settings_result = await db.execute(
        select(BudgetCarryoverSetting).where(
            BudgetCarryoverSetting.user_id == user_id
        )
    )
    settings_map = {s.category_id: s for s in settings_result.scalars().all()}

    previews = []
    for cat in categories:
        # Calculate spent for this category in the period
        spent_result = await db.execute(
            select(func.coalesce(func.sum(Expense.amount), 0)).where(
                Expense.user_id == user_id,
                Expense.category_id == cat.id,
                Expense.spent_at >= period_start,
                Expense.spent_at <= period_end,
            )
        )
        spent = float(spent_result.scalar())
        budget = float(cat.monthly_budget)
        remaining = max(0, budget - spent)

        setting = settings_map.get(cat.id)
        carryover_type = setting.carryover_type.value if setting else "expire"

        # Calculate carryover amount based on type and limit
        carryover_amount = remaining
        if setting and setting.carryover_limit and remaining > float(setting.carryover_limit):
            carryover_amount = float(setting.carryover_limit)

        target_desc = None
        if setting:
            if setting.carryover_type == CarryoverType.SAVINGS:
                target_desc = setting.target_savings_name or "저축"
            elif setting.carryover_type == CarryoverType.TRANSFER:
                target_desc = setting.target_savings_name or "이체 대상"
            elif setting.carryover_type == CarryoverType.DEPOSIT:
                rate = float(setting.target_annual_rate) if setting.target_annual_rate else 0
                target_desc = f"{setting.target_savings_name or '예금'} (연 {rate}%)"

        if carryover_type == "expire":
            carryover_amount = 0

        previews.append(CarryoverPreviewResponse(
            category_id=cat.id,
            category_name=cat.name,
            carryover_type=carryover_type,
            budget=budget,
            spent=spent,
            remaining=remaining,
            carryover_amount=carryover_amount,
            target_description=target_desc,
        ))

    return previews


async def execute_carryover(
    db: AsyncSession, user_id: uuid.UUID, period_start: date, period_end: date
) -> list[CarryoverLogResponse]:
    previews = await get_carryover_preview(db, user_id, period_start, period_end)
    logs = []

    for preview in previews:
        if preview.carryover_amount <= 0 or preview.carryover_type == "expire":
            continue

        log = BudgetCarryoverLog(
            user_id=user_id,
            category_id=preview.category_id,
            budget_period_start=period_start,
            budget_period_end=period_end,
            carryover_type=CarryoverType(preview.carryover_type),
            amount=Decimal(str(preview.carryover_amount)),
            target_description=preview.target_description,
        )
        db.add(log)
        logs.append(log)

    if logs:
        await db.commit()
        for log in logs:
            await db.refresh(log)

    cat_result = await db.execute(
        select(BudgetCategory).where(BudgetCategory.user_id == user_id)
    )
    cat_map = {c.id: c.name for c in cat_result.scalars().all()}

    return [
        CarryoverLogResponse(
            id=log.id,
            category_id=log.category_id,
            category_name=cat_map.get(log.category_id, ""),
            budget_period_start=log.budget_period_start,
            budget_period_end=log.budget_period_end,
            carryover_type=log.carryover_type.value,
            amount=float(log.amount),
            target_description=log.target_description,
            executed_at=log.executed_at,
            created_at=log.created_at,
        )
        for log in logs
    ]


async def get_carryover_logs(
    db: AsyncSession, user_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
) -> list[CarryoverLogResponse]:
    query = (
        select(BudgetCarryoverLog, BudgetCategory.name)
        .join(BudgetCategory, BudgetCarryoverLog.category_id == BudgetCategory.id)
        .where(BudgetCarryoverLog.user_id == user_id)
    )
    if period_start:
        query = query.where(BudgetCarryoverLog.budget_period_start >= period_start)
    if period_end:
        query = query.where(BudgetCarryoverLog.budget_period_end <= period_end)

    query = query.order_by(BudgetCarryoverLog.executed_at.desc())
    result = await db.execute(query)
    rows = result.all()

    return [
        CarryoverLogResponse(
            id=log.id,
            category_id=log.category_id,
            category_name=cat_name,
            budget_period_start=log.budget_period_start,
            budget_period_end=log.budget_period_end,
            carryover_type=log.carryover_type.value,
            amount=float(log.amount),
            target_description=log.target_description,
            executed_at=log.executed_at,
            created_at=log.created_at,
        )
        for log, cat_name in rows
    ]
