from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ScheduleCreate(BaseModel):
    type: Literal["income", "expense", "transfer"]
    name: str = Field(min_length=1, max_length=100)
    amount: Decimal = Field(gt=0)
    currency: str = "KRW"
    schedule_day: int = Field(ge=0, le=31)  # 0 = 월말
    start_date: date
    end_date: date | None = None
    total_count: int | None = Field(default=None, ge=1)
    source_account_id: UUID | None = None
    target_account_id: UUID | None = None
    category_id: UUID | None = None
    memo: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def validate_transfer(self):
        if self.type == "transfer":
            if not self.source_account_id or not self.target_account_id:
                raise ValueError("이체에는 출금/입금 계좌가 모두 필요합니다")
            if self.source_account_id == self.target_account_id:
                raise ValueError("출금/입금 계좌가 같을 수 없습니다")
        return self


class ScheduleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0)
    schedule_day: int | None = Field(default=None, ge=0, le=31)
    end_date: date | None = None
    source_account_id: UUID | None = None
    target_account_id: UUID | None = None
    category_id: UUID | None = None
    memo: str | None = Field(default=None, max_length=500)
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
