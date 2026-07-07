from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, model_validator


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

    @model_validator(mode="after")
    def check_type_fields(self):
        """monthly_amount(월 납입액)는 적금(savings) 계좌에만 허용"""
        if self.monthly_amount is not None and self.account_type != "savings":
            raise ValueError("monthly_amount는 적금(savings) 계좌에만 설정할 수 있습니다")
        return self


class AccountUpdate(BaseModel):
    account_type: str | None = None
    name: str | None = None
    institution: str | None = None
    interest_rate: Decimal | None = None
    interest_type: str | None = None
    monthly_amount: Decimal | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: Decimal | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def check_type_fields(self):
        """account_type이 함께 오면 monthly_amount는 적금에만 허용"""
        if (
            self.monthly_amount is not None
            and self.account_type is not None
            and self.account_type != "savings"
        ):
            raise ValueError("monthly_amount는 적금(savings) 계좌에만 설정할 수 있습니다")
        return self


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
