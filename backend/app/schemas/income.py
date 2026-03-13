import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


# ── RecurringIncome (템플릿) ──

class RecurringIncomeCreate(BaseModel):
    type: str = Field(pattern=r"^(salary|side|investment|other)$")
    amount: Decimal = Field(gt=0)
    description: str = Field(max_length=200)
    recurring_day: int = Field(ge=1, le=31)
    target_asset_id: uuid.UUID | None = None


class RecurringIncomeUpdate(BaseModel):
    type: str | None = Field(default=None, pattern=r"^(salary|side|investment|other)$")
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=200)
    recurring_day: int | None = Field(default=None, ge=1, le=31)
    target_asset_id: uuid.UUID | None = None
    is_active: bool | None = None


class RecurringIncomeResponse(BaseModel):
    id: uuid.UUID
    type: str
    amount: float
    description: str
    recurring_day: int
    target_asset_id: uuid.UUID | None = None
    target_asset_name: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ── Income (실제 수입 기록) ──

class IncomeCreate(BaseModel):
    type: str = Field(pattern=r"^(salary|side|investment|other)$")
    amount: Decimal = Field(gt=0)
    description: str = Field(max_length=200)
    received_at: date
    target_asset_id: uuid.UUID | None = None


class IncomeUpdate(BaseModel):
    type: str | None = Field(default=None, pattern=r"^(salary|side|investment|other)$")
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=200)
    received_at: date | None = None
    target_asset_id: uuid.UUID | None = None


class IncomeResponse(BaseModel):
    id: uuid.UUID
    type: str
    amount: float
    description: str
    recurring_income_id: uuid.UUID | None = None
    target_asset_id: uuid.UUID | None = None
    target_asset_name: str | None = None
    received_at: date
    created_at: datetime


class IncomeListResponse(BaseModel):
    data: list[IncomeResponse]
    total: int
    page: int
    per_page: int


class IncomeSummaryResponse(BaseModel):
    total_monthly_income: float
    salary_income: float
    side_income: float
    investment_income: float
    other_income: float
    recurring_count: int
