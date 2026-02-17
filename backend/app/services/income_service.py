import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.income import Income, IncomeType
from app.schemas.income import (
    IncomeCreate, IncomeUpdate, IncomeResponse,
    IncomeListResponse, IncomeSummaryResponse,
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

    return IncomeListResponse(
        data=[IncomeResponse.model_validate(i) for i in incomes],
        total=total,
        page=page,
        per_page=per_page,
    )


async def create_income(
    db: AsyncSession, user_id: uuid.UUID, data: IncomeCreate
) -> IncomeResponse:
    income = Income(
        user_id=user_id,
        type=IncomeType(data.type),
        amount=data.amount,
        description=data.description,
        is_recurring=data.is_recurring,
        recurring_day=data.recurring_day,
        received_at=data.received_at,
    )
    db.add(income)
    await db.commit()
    await db.refresh(income)
    return IncomeResponse.model_validate(income)


async def update_income(
    db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID, data: IncomeUpdate
) -> IncomeResponse:
    result = await db.execute(
        select(Income).where(Income.id == income_id, Income.user_id == user_id)
    )
    income = result.scalar_one_or_none()
    if not income:
        raise ValueError("Income not found")

    update_data = data.model_dump(exclude_unset=True)
    if "type" in update_data:
        update_data["type"] = IncomeType(update_data["type"])
    for key, value in update_data.items():
        setattr(income, key, value)

    await db.commit()
    await db.refresh(income)
    return IncomeResponse.model_validate(income)


async def delete_income(
    db: AsyncSession, user_id: uuid.UUID, income_id: uuid.UUID
) -> None:
    result = await db.execute(
        select(Income).where(Income.id == income_id, Income.user_id == user_id)
    )
    income = result.scalar_one_or_none()
    if not income:
        raise ValueError("Income not found")
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
