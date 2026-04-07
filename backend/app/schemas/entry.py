from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EntryCreate(BaseModel):
    account_id: UUID
    type: str
    amount: Decimal
    currency: str = "KRW"
    category_id: UUID | None = None
    security_id: UUID | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fee: Decimal = Decimal("0")
    exchange_rate: Decimal | None = None
    memo: str | None = None
    transacted_at: datetime


class EntryUpdate(BaseModel):
    amount: Decimal | None = None
    category_id: UUID | None = None
    memo: str | None = None
    quantity: Decimal | None = None
    unit_price: Decimal | None = None
    fee: Decimal | None = None
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
    amount: Decimal
    currency: str = "KRW"
    memo: str | None = None
    transacted_at: datetime | None = None


class TradeRequest(BaseModel):
    account_id: UUID
    security_id: UUID
    trade_type: str  # "buy" or "sell"
    quantity: Decimal
    unit_price: Decimal
    currency: str = "KRW"
    fee: Decimal = Decimal("0")
    exchange_rate: Decimal | None = None
    memo: str | None = None
    transacted_at: datetime | None = None


class EntryListResponse(BaseModel):
    data: list[EntryResponse]
    total: int
    page: int
    per_page: int
