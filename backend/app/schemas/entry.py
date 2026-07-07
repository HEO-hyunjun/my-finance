from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EntryCreate(BaseModel):
    account_id: UUID
    type: Literal["income", "expense", "adjustment", "dividend", "fee"]
    amount: Decimal
    currency: str = "KRW"
    category_id: UUID | None = None
    security_id: UUID | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    exchange_rate: Decimal | None = None
    memo: str | None = Field(default=None, max_length=1000)
    transacted_at: datetime

    @model_validator(mode="after")
    def normalize_amount_sign(self):
        """지출·수수료는 음수, 수입·배당은 양수로 보정"""
        if self.type in ("expense", "fee") and self.amount > 0:
            self.amount = -self.amount
        elif self.type in ("income", "dividend") and self.amount < 0:
            self.amount = -self.amount
        return self


class EntryUpdate(BaseModel):
    amount: Decimal | None = None
    category_id: UUID | None = None
    memo: str | None = Field(default=None, max_length=1000)
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fee: Decimal | None = Field(default=None, ge=0)
    transacted_at: datetime | None = None


class EntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_id: UUID
    entry_group_id: UUID | None
    category_id: UUID | None
    security_id: UUID | None
    type: str
    amount: Decimal
    currency: str
    quantity: Decimal | None
    unit_price: Decimal | None
    fee: Decimal
    exchange_rate: Decimal | None
    memo: str | None
    recurring_schedule_id: UUID | None
    transacted_at: datetime
    created_at: datetime


class TransferRequest(BaseModel):
    source_account_id: UUID
    target_account_id: UUID
    amount: Decimal = Field(gt=0)
    currency: str = "KRW"
    target_amount: Decimal | None = Field(default=None, gt=0)
    exchange_rate: Decimal | None = None
    memo: str | None = Field(default=None, max_length=1000)
    transacted_at: datetime | None = None

    @model_validator(mode="after")
    def check_different_accounts(self):
        if self.source_account_id == self.target_account_id:
            raise ValueError("출금/입금 계좌가 같을 수 없습니다")
        return self


class EntryGroupUpdate(BaseModel):
    amount: Decimal | None = Field(default=None, gt=0)
    target_amount: Decimal | None = Field(default=None, gt=0)
    exchange_rate: Decimal | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, gt=0)
    fee: Decimal | None = Field(default=None, ge=0)
    memo: str | None = Field(default=None, max_length=1000)
    transacted_at: datetime | None = None


class EntryGroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    group_type: str
    description: str | None
    created_at: datetime
    entries: list[EntryResponse]


class TradeRequest(BaseModel):
    account_id: UUID
    security_id: UUID
    trade_type: Literal["buy", "sell"]
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(gt=0)
    currency: str = "KRW"
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    exchange_rate: Decimal | None = None
    memo: str | None = Field(default=None, max_length=1000)
    transacted_at: datetime | None = None


class EntryListResponse(BaseModel):
    data: list[EntryResponse]
    total: int
    page: int
    per_page: int
