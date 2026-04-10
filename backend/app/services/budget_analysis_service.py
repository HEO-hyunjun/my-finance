"""예산 분석 서비스.

신규 스키마 기반으로 재작성:
- Entry (type=expense) 대신 구 Expense
- Category 대신 구 BudgetCategory
- RecurringSchedule (type=expense/income) 대신 구 FixedExpense/Installment/RecurringIncome
- BudgetAllocation 대신 구 BudgetCarryoverSetting
"""

import uuid
from datetime import date, timedelta

from app.core.tz import today as tz_today

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget_v2 import BudgetAllocation
from app.models.category import Category, CategoryDirection
from app.models.entry import Entry, EntryType
from app.models.recurring_schedule import RecurringSchedule, ScheduleType
from app.schemas.budget_analysis import (
    BudgetAnalysisResponse,
    CarryoverPrediction,
    CategorySpendingRate,
    DailyBudgetResponse,
    FixedDeductionItem,
    FixedDeductionSummary,
    WeeklyAnalysisResponse,
)
from app.services.budget_v2_service import get_or_create_period, get_period_dates


async def get_budget_analysis(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    salary_day: int | None = None,
) -> BudgetAnalysisResponse:
    today = tz_today()

    # BudgetPeriod에서 기간 계산 (salary_day 파라미터는 하위 호환용, 무시)
    budget_period = await get_or_create_period(db, user_id)
    if not period_start or not period_end:
        period_start, period_end = get_period_dates(budget_period.period_start_day, today)

    # Fetch expense categories
    cat_stmt = (
        select(Category)
        .where(
            Category.user_id == user_id,
            Category.direction == CategoryDirection.EXPENSE,
            Category.is_active.is_(True),
        )
        .order_by(Category.sort_order)
    )
    categories = (await db.execute(cat_stmt)).scalars().all()

    # period_end 당일까지 포함 (Entry.transacted_at은 DateTime)
    period_end_exclusive = period_end + timedelta(days=1)

    # 카테고리별 예산 배분 (BudgetAllocation) 조회
    alloc_stmt = select(BudgetAllocation).where(
        BudgetAllocation.user_id == user_id,
        BudgetAllocation.period_start == period_start,
    )
    allocations = (await db.execute(alloc_stmt)).scalars().all()
    alloc_map = {a.category_id: float(a.amount) for a in allocations}

    # 단일 GROUP BY 쿼리로 모든 카테고리의 지출 합계를 한번에 조회
    total_budget = 0.0
    total_spent = 0.0
    category_rates: list[CategorySpendingRate] = []
    alerts: list[str] = []

    cat_ids = [cat.id for cat in categories]
    spending_map: dict[uuid.UUID, float] = {}
    if cat_ids:
        spent_stmt = (
            select(
                Entry.category_id,
                func.coalesce(func.sum(Entry.amount), 0).label("total"),
            )
            .where(
                Entry.user_id == user_id,
                Entry.category_id.in_(cat_ids),
                Entry.type == EntryType.EXPENSE,
                Entry.transacted_at >= period_start,
                Entry.transacted_at < period_end_exclusive,
            )
            .group_by(Entry.category_id)
        )
        spent_result = await db.execute(spent_stmt)
        spending_map = {row.category_id: abs(float(row.total)) for row in spent_result.all()}

    for cat in categories:
        spent = spending_map.get(cat.id, 0.0)
        budget = alloc_map.get(cat.id, 0.0)
        remaining = budget - spent
        usage_rate = (spent / budget * 100) if budget > 0 else 0.0

        status = "normal"
        if budget > 0:
            if usage_rate >= 100:
                status = "exceeded"
                alerts.append(f"'{cat.name}' 카테고리 예산을 초과했습니다. ({usage_rate:.0f}%)")
            elif usage_rate >= 80:
                status = "warning"
                alerts.append(f"'{cat.name}' 카테고리 예산의 {usage_rate:.0f}%를 사용했습니다.")

        category_rates.append(CategorySpendingRate(
            category_id=str(cat.id),
            category_name=cat.name,
            category_icon=cat.icon,
            category_color=cat.color,
            monthly_budget=budget,
            spent=spent,
            remaining=remaining,
            usage_rate=round(usage_rate, 1),
            status=status,
        ))

        total_budget += budget
        total_spent += spent

    # Fixed expenses (RecurringSchedule type=expense) & installments (total_count 있는 것)
    fe_stmt = select(RecurringSchedule).where(
        RecurringSchedule.user_id == user_id,
        RecurringSchedule.type == ScheduleType.EXPENSE,
        RecurringSchedule.is_active.is_(True),
    )
    fixed_schedules = (await db.execute(fe_stmt)).scalars().all()

    deduction_items: list[FixedDeductionItem] = []
    total_fixed_amount = 0.0
    paid_fixed = 0.0

    for fs in fixed_schedules:
        is_paid = today.day >= fs.schedule_day
        amount = abs(float(fs.amount))
        item_type = "installment" if fs.total_count else "fixed"
        deduction_items.append(FixedDeductionItem(
            name=fs.name,
            amount=amount,
            payment_day=fs.schedule_day,
            is_paid=is_paid,
            item_type=item_type,
        ))
        total_fixed_amount += amount
        if is_paid:
            paid_fixed += amount

    deduction_items.sort(key=lambda x: x.payment_day)

    fixed_deductions = FixedDeductionSummary(
        items=deduction_items,
        total_amount=total_fixed_amount,
        paid_amount=paid_fixed,
        remaining_amount=total_fixed_amount - paid_fixed,
    )

    # 고정비 자동 Entry 합계 (recurring_schedule_id가 있는 expense 엔트리)
    auto_fixed_stmt = (
        select(func.coalesce(func.sum(Entry.amount), 0))
        .where(
            Entry.user_id == user_id,
            Entry.type == EntryType.EXPENSE,
            Entry.recurring_schedule_id.isnot(None),
            Entry.transacted_at >= period_start,
            Entry.transacted_at < period_end_exclusive,
        )
    )
    total_auto_fixed_spent = abs(float((await db.execute(auto_fixed_stmt)).scalar() or 0))

    # Variable budget
    variable_budget = total_budget - total_fixed_amount
    variable_spent = total_spent - total_auto_fixed_spent
    variable_remaining = variable_budget - variable_spent

    # Daily available
    remaining_days = max((period_end - today).days + 1, 1)
    daily_available = max(variable_remaining / remaining_days, 0)

    # Today's spending (고정비 자동 Entry 제외)
    today_start = today
    tomorrow = today + timedelta(days=1)
    today_spent_stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.user_id == user_id,
        Entry.type == EntryType.EXPENSE,
        Entry.transacted_at >= today_start,
        Entry.transacted_at < tomorrow,
        Entry.recurring_schedule_id.is_(None),
    )
    today_spent = abs(float((await db.execute(today_spent_stmt)).scalar() or 0))

    daily_budget = DailyBudgetResponse(
        daily_available=round(daily_available, 0),
        remaining_budget=round(variable_remaining, 0),
        remaining_days=remaining_days,
        today_spent=today_spent,
        period_start=period_start,
        period_end=period_end,
    )

    # Weekly analysis
    week_start = today - timedelta(days=today.weekday())  # Monday
    week_end = week_start + timedelta(days=6)
    week_end_exclusive = min(week_end, period_end) + timedelta(days=1)

    week_spent_stmt = select(func.coalesce(func.sum(Entry.amount), 0)).where(
        Entry.user_id == user_id,
        Entry.type == EntryType.EXPENSE,
        Entry.transacted_at >= week_start,
        Entry.transacted_at < week_end_exclusive,
        Entry.recurring_schedule_id.is_(None),
    )
    week_spent = abs(float((await db.execute(week_spent_stmt)).scalar() or 0))

    # Weekly average budget from recurring income schedules
    income_stmt = select(func.coalesce(func.sum(RecurringSchedule.amount), 0)).where(
        RecurringSchedule.user_id == user_id,
        RecurringSchedule.type == ScheduleType.INCOME,
        RecurringSchedule.is_active.is_(True),
    )
    monthly_income = float((await db.execute(income_stmt)).scalar() or 0)
    if monthly_income == 0:
        monthly_income = total_budget  # fallback to total budget

    weekly_avg_budget = max((monthly_income - total_fixed_amount) / 4.33, 0)
    weekly_usage = (week_spent / weekly_avg_budget * 100) if weekly_avg_budget > 0 else 0

    weekly_analysis = WeeklyAnalysisResponse(
        week_start=week_start,
        week_end=week_end,
        week_spent=week_spent,
        weekly_average_budget=round(weekly_avg_budget, 0),
        usage_rate=round(weekly_usage, 1),
        is_over_budget=weekly_usage > 100,
    )

    # Carryover predictions (BudgetAllocation 기반)
    carryover_predictions: list[CarryoverPrediction] = []
    if remaining_days > 0:
        days_elapsed = (today - period_start).days + 1
        total_days = (period_end - period_start).days + 1

        for rate in category_rates:
            if rate.monthly_budget <= 0:
                continue
            daily_avg_spend = rate.spent / max(days_elapsed, 1)
            predicted_total = daily_avg_spend * total_days
            predicted_remaining = rate.monthly_budget - predicted_total

            # v2 스키마에서는 별도 carryover_type 설정이 없으므로 None
            carryover_type = None
            predicted_carryover = 0.0

            carryover_predictions.append(CarryoverPrediction(
                category_id=rate.category_id,
                category_name=rate.category_name,
                predicted_remaining=round(predicted_remaining, 0),
                carryover_type=carryover_type,
                predicted_carryover=round(predicted_carryover, 0),
            ))

    return BudgetAnalysisResponse(
        daily_budget=daily_budget,
        weekly_analysis=weekly_analysis,
        category_rates=category_rates,
        fixed_deductions=fixed_deductions,
        carryover_predictions=carryover_predictions,
        alerts=alerts,
    )
