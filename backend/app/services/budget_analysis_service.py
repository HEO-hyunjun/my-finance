import uuid
from datetime import date, timedelta

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.budget import (
    BudgetCategory, Expense, FixedExpense, Installment,
    BudgetCarryoverSetting,
)
from app.models.income import Income
from app.schemas.budget_analysis import (
    BudgetAnalysisResponse,
    CarryoverPrediction,
    CategorySpendingRate,
    DailyBudgetResponse,
    FixedDeductionItem,
    FixedDeductionSummary,
    WeeklyAnalysisResponse,
)
from app.services.budget_period import get_budget_period


async def get_budget_analysis(
    db: AsyncSession,
    user_id: uuid.UUID,
    period_start: date | None = None,
    period_end: date | None = None,
    salary_day: int = 1,
) -> BudgetAnalysisResponse:
    today = date.today()
    if not period_start or not period_end:
        period_start, period_end = get_budget_period(today, salary_day)

    # Fetch categories
    cat_stmt = (
        select(BudgetCategory)
        .where(BudgetCategory.user_id == user_id, BudgetCategory.is_active.is_(True))
        .order_by(BudgetCategory.sort_order)
    )
    categories = (await db.execute(cat_stmt)).scalars().all()

    # Total budget and category spending
    total_budget = 0.0
    total_spent = 0.0
    category_rates: list[CategorySpendingRate] = []
    alerts: list[str] = []

    # 단일 GROUP BY 쿼리로 모든 카테고리의 지출 합계를 한번에 조회
    spent_stmt = (
        select(
            Expense.category_id,
            func.coalesce(func.sum(Expense.amount), 0).label("total"),
        )
        .where(
            Expense.user_id == user_id,
            Expense.category_id.in_([cat.id for cat in categories]),
            Expense.spent_at >= period_start,
            Expense.spent_at <= period_end,
        )
        .group_by(Expense.category_id)
    )
    spent_result = await db.execute(spent_stmt)
    spending_map = {row.category_id: float(row.total) for row in spent_result.all()}

    for cat in categories:
        spent = spending_map.get(cat.id, 0.0)
        budget = float(cat.monthly_budget)
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

    # Fixed expenses & installments
    fe_stmt = select(FixedExpense).where(
        FixedExpense.user_id == user_id, FixedExpense.is_active.is_(True)
    )
    fixed_expenses = (await db.execute(fe_stmt)).scalars().all()

    inst_stmt = select(Installment).where(
        Installment.user_id == user_id, Installment.is_active.is_(True)
    )
    installments = (await db.execute(inst_stmt)).scalars().all()

    deduction_items: list[FixedDeductionItem] = []
    total_fixed_amount = 0.0
    paid_fixed = 0.0

    for fe in fixed_expenses:
        is_paid = today.day >= fe.payment_day
        amount = float(fe.amount)
        deduction_items.append(FixedDeductionItem(
            name=fe.name,
            amount=amount,
            payment_day=fe.payment_day,
            is_paid=is_paid,
            item_type="fixed",
        ))
        total_fixed_amount += amount
        if is_paid:
            paid_fixed += amount

    for inst in installments:
        is_paid = today.day >= inst.payment_day
        amount = float(inst.monthly_amount)
        deduction_items.append(FixedDeductionItem(
            name=inst.name,
            amount=amount,
            payment_day=inst.payment_day,
            is_paid=is_paid,
            item_type="installment",
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

    # 고정비 자동 Expense 합계 (이중 차감 방지)
    auto_fixed_stmt = (
        select(func.coalesce(func.sum(Expense.amount), 0))
        .where(
            Expense.user_id == user_id,
            Expense.fixed_expense_id.isnot(None),
            Expense.spent_at >= period_start,
            Expense.spent_at <= period_end,
        )
    )
    total_auto_fixed_spent = float((await db.execute(auto_fixed_stmt)).scalar() or 0)

    # Variable budget
    variable_budget = total_budget - total_fixed_amount
    variable_spent = total_spent - total_auto_fixed_spent
    variable_remaining = variable_budget - variable_spent

    # Daily available
    remaining_days = max((period_end - today).days + 1, 1)
    daily_available = max(variable_remaining / remaining_days, 0)

    # Today's spending (고정비 자동 Expense 제외 — daily_available과 기준 일치)
    today_spent_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.user_id == user_id,
        Expense.spent_at == today,
        Expense.fixed_expense_id.is_(None),
    )
    today_spent = float((await db.execute(today_spent_stmt)).scalar() or 0)

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

    week_spent_stmt = select(func.coalesce(func.sum(Expense.amount), 0)).where(
        Expense.user_id == user_id,
        Expense.spent_at >= week_start,
        Expense.spent_at <= min(week_end, period_end),
        Expense.fixed_expense_id.is_(None),
    )
    week_spent = float((await db.execute(week_spent_stmt)).scalar() or 0)

    # Weekly average budget from income
    income_stmt = select(func.coalesce(func.sum(Income.amount), 0)).where(
        Income.user_id == user_id,
        Income.is_recurring.is_(True),
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

    # Carryover predictions
    carryover_predictions: list[CarryoverPrediction] = []
    if remaining_days > 0:
        days_elapsed = (today - period_start).days + 1
        total_days = (period_end - period_start).days + 1

        # 단일 IN 쿼리로 모든 carryover setting을 한번에 조회
        cat_ids = [uuid.UUID(r.category_id) for r in category_rates if r.monthly_budget > 0]
        carryover_map: dict[uuid.UUID, BudgetCarryoverSetting] = {}
        if cat_ids:
            cs_stmt = select(BudgetCarryoverSetting).where(
                BudgetCarryoverSetting.user_id == user_id,
                BudgetCarryoverSetting.category_id.in_(cat_ids),
            )
            cs_result = await db.execute(cs_stmt)
            carryover_map = {cs.category_id: cs for cs in cs_result.scalars().all()}

        for rate in category_rates:
            if rate.monthly_budget <= 0:
                continue
            daily_avg_spend = rate.spent / max(days_elapsed, 1)
            predicted_total = daily_avg_spend * total_days
            predicted_remaining = rate.monthly_budget - predicted_total

            # Check carryover setting
            cs = carryover_map.get(uuid.UUID(rate.category_id))
            carryover_type = cs.carryover_type.value if cs else None

            predicted_carryover = max(predicted_remaining, 0) if carryover_type and carryover_type != "expire" else 0

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
