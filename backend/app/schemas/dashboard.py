from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel


class DashboardAssetSummary(BaseModel):
    total_value_krw: float
    total_invested_krw: float
    total_profit_loss: float
    total_profit_loss_rate: float
    breakdown: dict[str, float]


class DashboardBudgetCategory(BaseModel):
    name: str
    icon: str | None = None
    color: str | None = None
    budget: float
    spent: float
    usage_rate: float


class DashboardBudgetSummary(BaseModel):
    total_budget: float
    total_spent: float
    total_remaining: float
    total_usage_rate: float
    total_fixed_expenses: float
    total_installments: float
    daily_available: float = 0.0
    today_spent: float = 0.0
    remaining_days: int = 0
    top_categories: list[DashboardBudgetCategory]


class DashboardTransaction(BaseModel):
    id: str
    asset_name: str
    asset_type: str
    type: str
    quantity: float
    unit_price: float
    currency: str
    transacted_at: datetime


class DashboardMarketItem(BaseModel):
    symbol: str
    name: str | None = None
    price: float
    currency: str
    change: float | None = None
    change_percent: float | None = None


class DashboardMarketInfo(BaseModel):
    exchange_rate: DashboardMarketItem
    gold_price: DashboardMarketItem | None = None


class DashboardPayment(BaseModel):
    name: str
    amount: float
    payment_day: int
    type: str
    remaining: str | None = None
    category_name: str | None = None
    category_color: str | None = None


class DashboardMaturityAlert(BaseModel):
    name: str
    asset_type: str
    maturity_date: date
    principal: float
    maturity_amount: float | None = None
    days_remaining: int
    bank_name: str | None = None


class DashboardSummaryResponse(BaseModel):
    asset_summary: DashboardAssetSummary
    budget_summary: DashboardBudgetSummary
    recent_transactions: list[DashboardTransaction]
    market_info: DashboardMarketInfo
    upcoming_payments: list[DashboardPayment]
    maturity_alerts: list[DashboardMaturityAlert]


# ── AI Insights ──

class AIInsight(BaseModel):
    type: str  # spending, budget, investment, saving, alert
    title: str
    description: str
    severity: str  # info, warning, success


class AIInsightsResponse(BaseModel):
    insights: list[AIInsight]
