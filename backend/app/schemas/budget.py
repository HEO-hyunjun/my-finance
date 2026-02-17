import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# --- BudgetCategory Request ---


class BudgetCategoryCreate(BaseModel):
    name: str = Field(max_length=50)
    icon: str | None = Field(default=None, max_length=10)
    color: str | None = Field(default=None, max_length=7)
    monthly_budget: Decimal = Field(default=Decimal("0"), ge=0)
    sort_order: int = Field(default=0, ge=0)


class BudgetCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    icon: str | None = None
    color: str | None = None
    monthly_budget: Decimal | None = Field(default=None, ge=0)
    sort_order: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


# --- BudgetCategory Response ---


class BudgetCategoryResponse(BaseModel):
    id: uuid.UUID
    name: str
    icon: str | None
    color: str | None
    monthly_budget: float
    sort_order: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Expense Request ---


class ExpenseCreate(BaseModel):
    category_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    memo: str | None = Field(default=None, max_length=500)
    payment_method: str | None = None
    tags: str | None = Field(default=None, max_length=200)
    spent_at: date


class ExpenseUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    amount: Decimal | None = Field(default=None, gt=0)
    memo: str | None = Field(default=None, max_length=500)
    payment_method: str | None = None
    tags: str | None = None
    spent_at: date | None = None


# --- Expense Response ---


class ExpenseResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_color: str | None
    amount: float
    memo: str | None
    payment_method: str | None
    tags: str | None
    spent_at: date
    created_at: datetime


class ExpenseListResponse(BaseModel):
    data: list[ExpenseResponse]
    total: int
    page: int
    per_page: int


# --- Budget Summary ---


class CategoryBudgetSummary(BaseModel):
    category_id: uuid.UUID
    category_name: str
    category_icon: str | None
    category_color: str | None
    monthly_budget: float
    spent: float
    remaining: float
    usage_rate: float


class BudgetSummaryResponse(BaseModel):
    period_start: date
    period_end: date
    total_budget: float
    total_spent: float
    total_remaining: float
    total_usage_rate: float
    categories: list[CategoryBudgetSummary]
    # Phase 2
    total_fixed_expenses: float = 0.0
    total_installments: float = 0.0
    variable_budget: float = 0.0
    variable_spent: float = 0.0
    variable_remaining: float = 0.0


# --- FixedExpense Request ---


class FixedExpenseCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(max_length=100)
    amount: Decimal = Field(gt=0)
    payment_day: int = Field(ge=1, le=31)
    payment_method: str | None = None


class FixedExpenseUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0)
    payment_day: int | None = Field(default=None, ge=1, le=31)
    payment_method: str | None = None
    is_active: bool | None = None


# --- FixedExpense Response ---


class FixedExpenseResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_color: str | None
    name: str
    amount: float
    payment_day: int
    payment_method: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# --- Installment Request ---


class InstallmentCreate(BaseModel):
    category_id: uuid.UUID
    name: str = Field(max_length=100)
    total_amount: Decimal = Field(gt=0)
    monthly_amount: Decimal = Field(gt=0)
    payment_day: int = Field(ge=1, le=31)
    total_installments: int = Field(gt=0)
    start_date: date
    end_date: date
    payment_method: str | None = None


class InstallmentUpdate(BaseModel):
    category_id: uuid.UUID | None = None
    name: str | None = Field(default=None, max_length=100)
    monthly_amount: Decimal | None = Field(default=None, gt=0)
    payment_day: int | None = Field(default=None, ge=1, le=31)
    payment_method: str | None = None
    is_active: bool | None = None


# --- Installment Response ---


class InstallmentResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    category_color: str | None
    name: str
    total_amount: float
    monthly_amount: float
    payment_day: int
    total_installments: int
    paid_installments: int
    remaining_installments: int
    remaining_amount: float
    progress_rate: float
    start_date: date
    end_date: date
    payment_method: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
