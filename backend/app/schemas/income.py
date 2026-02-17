import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class IncomeCreate(BaseModel):
    type: str = Field(pattern=r"^(salary|side|investment|other)$")
    amount: Decimal = Field(gt=0)
    description: str = Field(max_length=200)
    is_recurring: bool = False
    recurring_day: int | None = Field(default=None, ge=1, le=31)
    received_at: date


class IncomeUpdate(BaseModel):
    type: str | None = Field(default=None, pattern=r"^(salary|side|investment|other)$")
    amount: Decimal | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=200)
    is_recurring: bool | None = None
    recurring_day: int | None = Field(default=None, ge=1, le=31)
    received_at: date | None = None


class IncomeResponse(BaseModel):
    id: uuid.UUID
    type: str
    amount: float
    description: str
    is_recurring: bool
    recurring_day: int | None
    received_at: date
    created_at: datetime

    model_config = {"from_attributes": True}


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
