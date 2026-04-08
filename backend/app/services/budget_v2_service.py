import uuid
import calendar
from datetime import date, timedelta
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget_v2 import BudgetPeriod, BudgetAllocation
from app.models.entry import Entry, EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType


def get_period_dates(period_start_day: int, today: date) -> tuple[date, date]:
    """기간 시작일 기준 현재 예산 기간 계산.

    period_start_day=10이고 today=4/15이면 → (4/10, 5/9)
    period_start_day=10이고 today=4/5이면 → (3/10, 4/9)
    period_start_day=1이면 → 표준 월 (4/1, 4/30)
    """
    if period_start_day == 1:
        _, last_day = calendar.monthrange(today.year, today.month)
        return date(today.year, today.month, 1), date(today.year, today.month, last_day)

    if today.day >= period_start_day:
        start = today.replace(day=period_start_day)
        # 다음달 period_start_day - 1
        if today.month == 12:
            end_month, end_year = 1, today.year + 1
        else:
            end_month, end_year = today.month + 1, today.year
        _, last = calendar.monthrange(end_year, end_month)
        end_day = min(period_start_day - 1, last)
        end = date(end_year, end_month, end_day)
    else:
        # 이전달 period_start_day ~ 이번달 period_start_day - 1
        if today.month == 1:
            start_month, start_year = 12, today.year - 1
        else:
            start_month, start_year = today.month - 1, today.year
        _, last = calendar.monthrange(start_year, start_month)
        start_day = min(period_start_day, last)
        start = date(start_year, start_month, start_day)
        end = today.replace(day=period_start_day - 1)

    return start, end


async def get_or_create_period(db: AsyncSession, user_id: uuid.UUID) -> BudgetPeriod:
    stmt = select(BudgetPeriod).where(BudgetPeriod.user_id == user_id)
    period = (await db.execute(stmt)).scalar_one_or_none()
    if not period:
        period = BudgetPeriod(user_id=user_id, period_start_day=1)
        db.add(period)
        await db.flush()
    return period


async def update_period_start_day(
    db: AsyncSession, user_id: uuid.UUID, day: int,
) -> BudgetPeriod:
    if not (1 <= day <= 28):
        raise HTTPException(status_code=400, detail="period_start_day must be 1-28")
    period = await get_or_create_period(db, user_id)
    period.period_start_day = day
    await db.commit()
    await db.refresh(period)
    return period


async def get_budget_overview(
    db: AsyncSession, user_id: uuid.UUID, today: date,
) -> dict:
    """Top-down 예산 개요"""
    period = await get_or_create_period(db, user_id)
    period_start, period_end = get_period_dates(period.period_start_day, today)

    # 월 수입 합계 (활성 income 스케줄)
    income_stmt = select(
        func.coalesce(func.sum(RecurringSchedule.amount), 0),
    ).where(
        RecurringSchedule.user_id == user_id,
        RecurringSchedule.type == ScheduleType.INCOME,
        RecurringSchedule.is_active.is_(True),
    )
    total_income = Decimal(str((await db.execute(income_stmt)).scalar()))

    # 고정 지출 합계 (활성 expense 스케줄)
    expense_stmt = select(
        func.coalesce(func.sum(RecurringSchedule.amount), 0),
    ).where(
        RecurringSchedule.user_id == user_id,
        RecurringSchedule.type == ScheduleType.EXPENSE,
        RecurringSchedule.is_active.is_(True),
    )
    total_fixed = Decimal(str((await db.execute(expense_stmt)).scalar()))

    # 자동이체 합계 (활성 transfer 스케줄)
    transfer_stmt = select(
        func.coalesce(func.sum(RecurringSchedule.amount), 0),
    ).where(
        RecurringSchedule.user_id == user_id,
        RecurringSchedule.type == ScheduleType.TRANSFER,
        RecurringSchedule.is_active.is_(True),
    )
    total_transfer = Decimal(str((await db.execute(transfer_stmt)).scalar()))

    available = total_income - total_fixed - total_transfer

    # 카테고리 배분 합계
    alloc_stmt = select(
        func.coalesce(func.sum(BudgetAllocation.amount), 0),
    ).where(
        BudgetAllocation.user_id == user_id,
        BudgetAllocation.period_start == period_start,
    )
    total_allocated = Decimal(str((await db.execute(alloc_stmt)).scalar()))

    unallocated = available - total_allocated

    return {
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "period_start_day": period.period_start_day,
        "total_income": total_income,
        "total_fixed_expense": total_fixed,
        "total_transfer": total_transfer,
        "available_budget": available,
        "total_allocated": total_allocated,
        "unallocated": unallocated,
    }


async def get_category_budgets(
    db: AsyncSession, user_id: uuid.UUID, today: date,
) -> list[dict]:
    """카테고리별 배분 + 실제 지출 + 잔여"""
    period = await get_or_create_period(db, user_id)
    period_start, period_end = get_period_dates(period.period_start_day, today)

    # 이번 기간 allocations
    alloc_stmt = select(BudgetAllocation).where(
        BudgetAllocation.user_id == user_id,
        BudgetAllocation.period_start == period_start,
    )
    allocations = (await db.execute(alloc_stmt)).scalars().all()

    # period_end 당일까지 포함하기 위해 다음날을 exclusive upper bound로 사용
    period_end_exclusive = period_end + timedelta(days=1)

    results = []
    for alloc in allocations:
        # 해당 카테고리의 이번 기간 실제 지출
        # Entry.transacted_at은 DateTime이므로 date 기반 범위로 비교
        spent_stmt = select(
            func.coalesce(func.sum(Entry.amount), 0),
        ).where(
            Entry.user_id == user_id,
            Entry.category_id == alloc.category_id,
            Entry.type == EntryType.EXPENSE,
            Entry.transacted_at >= period_start,
            Entry.transacted_at < period_end_exclusive,
        )
        spent = abs(Decimal(str((await db.execute(spent_stmt)).scalar())))

        results.append({
            "allocation_id": str(alloc.id),
            "category_id": str(alloc.category_id),
            "allocated": alloc.amount,
            "spent": spent,
            "remaining": alloc.amount - spent,
        })

    return results


async def create_or_update_allocation(
    db: AsyncSession,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    amount: Decimal,
    today: date,
) -> BudgetAllocation:
    """예산 배분 생성/수정"""
    period = await get_or_create_period(db, user_id)
    period_start, period_end = get_period_dates(period.period_start_day, today)

    stmt = select(BudgetAllocation).where(
        BudgetAllocation.user_id == user_id,
        BudgetAllocation.category_id == category_id,
        BudgetAllocation.period_start == period_start,
    )
    alloc = (await db.execute(stmt)).scalar_one_or_none()

    if alloc:
        alloc.amount = amount
    else:
        alloc = BudgetAllocation(
            user_id=user_id,
            category_id=category_id,
            amount=amount,
            period_start=period_start,
            period_end=period_end,
        )
        db.add(alloc)

    await db.commit()
    await db.refresh(alloc)
    return alloc


async def delete_allocation(
    db: AsyncSession, user_id: uuid.UUID, allocation_id: uuid.UUID,
) -> None:
    stmt = select(BudgetAllocation).where(
        BudgetAllocation.id == allocation_id,
        BudgetAllocation.user_id == user_id,
    )
    alloc = (await db.execute(stmt)).scalar_one_or_none()
    if not alloc:
        raise HTTPException(status_code=404, detail="Allocation not found")
    await db.delete(alloc)
    await db.commit()
