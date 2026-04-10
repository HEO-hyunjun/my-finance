from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AccountCreate(BaseModel):
    account_type: str
    name: str
    currency: str = "KRW"
    institution: str | None = None
    interest_rate: Decimal | None = None
    interest_type: str | None = None
    monthly_amount: Decimal | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: Decimal | None = None


class AccountUpdate(BaseModel):
    name: str | None = None
    institution: str | None = None
    interest_rate: Decimal | None = None
    interest_type: str | None = None
    monthly_amount: Decimal | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: Decimal | None = None
    is_active: bool | None = None


class AccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_type: str
    name: str
    currency: str
    institution: str | None
    interest_rate: Decimal | None
    interest_type: str | None
    monthly_amount: Decimal | None
    start_date: date | None
    maturity_date: date | None
    tax_rate: Decimal | None
    is_active: bool
    created_at: datetime


class AccountSummary(BaseModel):
    id: str
    name: str
    account_type: str
    currency: str
    balance: Decimal
    cash_balance: Decimal | None = None
    holdings: list[dict] | None = None


class AdjustBalanceRequest(BaseModel):
    target_balance: Decimal
    currency: str = "KRW"
    memo: str | None = None
    security_id: UUID | None = None
    target_quantity: Decimal | None = None
    unit_price: Decimal | None = None
