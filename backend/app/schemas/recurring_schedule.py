from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ScheduleCreate(BaseModel):
    type: str  # "income" / "expense" / "transfer"
    name: str
    amount: Decimal
    currency: str = "KRW"
    schedule_day: int
    start_date: date
    end_date: date | None = None
    total_count: int | None = None
    source_account_id: UUID | None = None
    target_account_id: UUID | None = None
    category_id: UUID | None = None
    memo: str | None = None


class ScheduleUpdate(BaseModel):
    name: str | None = None
    amount: Decimal | None = None
    schedule_day: int | None = None
    end_date: date | None = None
    source_account_id: UUID | None = None
    target_account_id: UUID | None = None
    category_id: UUID | None = None
    memo: str | None = None
    is_active: bool | None = None


class ScheduleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str
    name: str
    amount: Decimal
    currency: str
    schedule_day: int
    start_date: date
    end_date: date | None
    total_count: int | None
    executed_count: int
    source_account_id: UUID | None
    target_account_id: UUID | None
    category_id: UUID | None
    memo: str | None
    is_active: bool
    created_at: datetime
