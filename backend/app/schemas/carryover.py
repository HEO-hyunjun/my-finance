import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CarryoverSettingCreate(BaseModel):
    category_id: uuid.UUID
    carryover_type: str = Field(pattern=r"^(expire|next_month|savings|transfer|deposit)$")
    carryover_limit: Decimal | None = Field(default=None, ge=0)
    source_asset_id: uuid.UUID | None = None
    target_asset_id: uuid.UUID | None = None
    target_savings_name: str | None = Field(default=None, max_length=100)
    target_annual_rate: Decimal | None = Field(default=None, ge=0, le=100)


class CarryoverSettingUpdate(BaseModel):
    carryover_type: str | None = Field(default=None, pattern=r"^(expire|next_month|savings|transfer|deposit)$")
    carryover_limit: Decimal | None = Field(default=None, ge=0)
    source_asset_id: uuid.UUID | None = None
    target_asset_id: uuid.UUID | None = None
    target_savings_name: str | None = Field(default=None, max_length=100)
    target_annual_rate: Decimal | None = Field(default=None, ge=0, le=100)


class CarryoverSettingResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    carryover_type: str
    carryover_limit: float | None
    source_asset_id: uuid.UUID | None
    source_asset_name: str | None
    target_asset_id: uuid.UUID | None
    target_savings_name: str | None
    target_annual_rate: float | None
    created_at: datetime
    updated_at: datetime


class CarryoverLogResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    budget_period_start: date
    budget_period_end: date
    carryover_type: str
    amount: float
    target_description: str | None
    executed_at: datetime
    created_at: datetime


class CarryoverExecuteRequest(BaseModel):
    period_start: date
    period_end: date


class CarryoverPreviewResponse(BaseModel):
    category_id: uuid.UUID
    category_name: str
    carryover_type: str
    budget: float
    spent: float
    remaining: float
    carryover_amount: float
    target_description: str | None
