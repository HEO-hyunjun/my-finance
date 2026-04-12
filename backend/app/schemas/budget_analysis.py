from datetime import date

from pydantic import BaseModel


class DailyBudgetResponse(BaseModel):
    daily_available: float
    remaining_budget: float
    remaining_days: int
    today_spent: float
    period_start: date
    period_end: date


class WeeklyAnalysisResponse(BaseModel):
    week_start: date
    week_end: date
    week_spent: float
    weekly_average_budget: float
    usage_rate: float  # percentage
    is_over_budget: bool


class CategorySpendingRate(BaseModel):
    category_id: str
    category_name: str
    category_icon: str | None = None
    category_color: str | None = None
    monthly_budget: float
    spent: float
    remaining: float
    usage_rate: float
    status: str  # "normal" | "warning" | "exceeded"


class FixedDeductionItem(BaseModel):
    name: str
    amount: float
    payment_day: int
    is_paid: bool  # whether payment_day has passed this month
    item_type: str  # "fixed" | "installment"


class FixedDeductionSummary(BaseModel):
    items: list[FixedDeductionItem]
    total_amount: float
    paid_amount: float
    remaining_amount: float


class CarryoverPrediction(BaseModel):
    category_id: str
    category_name: str
    predicted_remaining: float
    carryover_type: str | None
    predicted_carryover: float


class BudgetAnalysisResponse(BaseModel):
    daily_budget: DailyBudgetResponse
    weekly_analysis: WeeklyAnalysisResponse
    category_rates: list[CategorySpendingRate]
    fixed_deductions: FixedDeductionSummary
    carryover_predictions: list[CarryoverPrediction]
    alerts: list[str]
