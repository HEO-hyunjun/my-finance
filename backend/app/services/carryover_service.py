import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget_v2 import BudgetAllocation
from app.models.entry import Entry, EntryType
from app.services.budget_v2_service import get_period_dates, get_or_create_period


async def get_carryover_preview(db: AsyncSession, user_id: uuid.UUID, today: date) -> list[dict]:
    """현재 기간의 카테고리별 잔여 예산 (이월 가능 금액)"""
    period = await get_or_create_period(db, user_id)
    period_start, period_end = get_period_dates(period.period_start_day, today)

    alloc_stmt = select(BudgetAllocation).where(
        BudgetAllocation.user_id == user_id,
        BudgetAllocation.period_start == period_start,
    )
    allocations = (await db.execute(alloc_stmt)).scalars().all()

    # period_end 당일까지 포함하기 위해 다음날을 exclusive upper bound로 사용
    period_end_exclusive = period_end + timedelta(days=1)

    results = []
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

        results.append({
            "category_id": str(alloc.category_id),
            "allocated": alloc.amount,
            "spent": spent,
            "remaining": remaining,
            "carryover_amount": max(remaining, Decimal("0")),
        })

    return results


async def execute_carryover(db: AsyncSession, user_id: uuid.UUID, today: date) -> dict:
    """현재 기간 잔여 예산을 다음 기간으로 이월"""
    preview = await get_carryover_preview(db, user_id, today)
    period = await get_or_create_period(db, user_id)
    _, current_end = get_period_dates(period.period_start_day, today)

    # 다음 기간 계산
    next_day = current_end + timedelta(days=1)
    next_start, next_end = get_period_dates(period.period_start_day, next_day)

    carried = 0
    for item in preview:
        if item["carryover_amount"] <= 0:
            continue

        cat_id = uuid.UUID(item["category_id"])

        # 다음 기간 allocation 조회/생성
        existing = (await db.execute(
            select(BudgetAllocation).where(
                BudgetAllocation.user_id == user_id,
                BudgetAllocation.category_id == cat_id,
                BudgetAllocation.period_start == next_start,
            )
        )).scalar_one_or_none()

        if existing:
            existing.amount += item["carryover_amount"]
        else:
            db.add(BudgetAllocation(
                user_id=user_id,
                category_id=cat_id,
                amount=item["carryover_amount"],
                period_start=next_start,
                period_end=next_end,
            ))
        carried += 1

    await db.commit()
    return {"carried_categories": carried}
