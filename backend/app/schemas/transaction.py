import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.transaction import TransactionType, CurrencyType


# --- Request ---


class TransactionCreate(BaseModel):
    asset_id: uuid.UUID
    type: TransactionType
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    currency: CurrencyType
    exchange_rate: Decimal | None = None
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    memo: str | None = Field(default=None, max_length=500)
    transacted_at: datetime
    source_asset_id: uuid.UUID | None = None


class TransactionUpdate(BaseModel):
    type: TransactionType | None = None
    quantity: Decimal | None = Field(default=None, gt=0)
    unit_price: Decimal | None = Field(default=None, ge=0)
    currency: CurrencyType | None = None
    exchange_rate: Decimal | None = None
    fee: Decimal | None = Field(default=None, ge=0)
    memo: str | None = Field(default=None, max_length=500)
    transacted_at: datetime | None = None


# --- Response ---


class TransactionResponse(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    asset_name: str
    asset_type: str
    type: TransactionType
    quantity: float
    unit_price: float
    currency: CurrencyType
    exchange_rate: float | None
    fee: float
    memo: str | None
    source_asset_id: uuid.UUID | None = None
    source_asset_name: str | None = None
    transacted_at: datetime
    created_at: datetime


class TransactionListResponse(BaseModel):
    data: list[TransactionResponse]
    total: int
    page: int
    per_page: int
