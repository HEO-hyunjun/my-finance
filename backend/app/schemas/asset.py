import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.models.asset import AssetType


# --- Request ---


class AssetCreate(BaseModel):
    asset_type: AssetType
    symbol: str | None = None
    name: str = Field(max_length=100)
    # 예금/적금/파킹통장 전용
    interest_rate: Decimal | None = Field(default=None, gt=0, le=100)
    interest_type: str | None = None
    principal: Decimal | None = Field(default=None, ge=0)
    monthly_amount: Decimal | None = Field(default=None, gt=0)
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: Decimal | None = Field(default=Decimal("15.4"), ge=0, le=100)
    bank_name: str | None = Field(default=None, max_length=50)

    @model_validator(mode="after")
    def validate_by_asset_type(self):
        t = self.asset_type
        if t == AssetType.DEPOSIT:
            if not self.interest_rate:
                raise ValueError("예금은 연이율(interest_rate)이 필수입니다")
            if not self.principal:
                raise ValueError("예금은 원금(principal)이 필수입니다")
            if not self.start_date or not self.maturity_date:
                raise ValueError("예금은 가입일과 만기일이 필수입니다")
            if self.maturity_date <= self.start_date:
                raise ValueError("만기일은 가입일보다 이후여야 합니다")
            if not self.interest_type:
                self.interest_type = "simple"
        elif t == AssetType.SAVINGS:
            if not self.interest_rate:
                raise ValueError("적금은 연이율(interest_rate)이 필수입니다")
            if not self.monthly_amount:
                raise ValueError("적금은 월납입액(monthly_amount)이 필수입니다")
            if not self.start_date or not self.maturity_date:
                raise ValueError("적금은 가입일과 만기일이 필수입니다")
            if self.maturity_date <= self.start_date:
                raise ValueError("만기일은 가입일보다 이후여야 합니다")
        elif t == AssetType.PARKING:
            if not self.interest_rate:
                raise ValueError("파킹통장은 연이율(interest_rate)이 필수입니다")
            if self.principal is None:
                raise ValueError("파킹통장은 현재잔액(principal)이 필수입니다")
        return self


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=100)
    interest_rate: Decimal | None = Field(default=None, gt=0, le=100)
    interest_type: str | None = None
    principal: Decimal | None = Field(default=None, ge=0)
    monthly_amount: Decimal | None = Field(default=None, gt=0)
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: Decimal | None = Field(default=None, ge=0, le=100)
    bank_name: str | None = Field(default=None, max_length=50)


# --- Response ---


class AssetResponse(BaseModel):
    id: uuid.UUID
    asset_type: AssetType
    symbol: str | None
    name: str
    created_at: datetime
    # 예금/적금/파킹통장 전용
    interest_rate: float | None = None
    interest_type: str | None = None
    principal: float | None = None
    monthly_amount: float | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: float | None = None
    bank_name: str | None = None

    model_config = {"from_attributes": True}


class AssetHoldingResponse(BaseModel):
    """자산 상세 — 보유량, 평균단가, 현재가, 수익률 + 이자 정보"""

    id: uuid.UUID
    asset_type: AssetType
    symbol: str | None
    name: str
    quantity: float
    avg_price: float
    current_price: float
    exchange_rate: float | None
    total_value_krw: float
    total_invested_krw: float
    profit_loss: float
    profit_loss_rate: float
    created_at: datetime
    # 예금/적금/파킹통장 전용
    interest_rate: float | None = None
    interest_type: str | None = None
    bank_name: str | None = None
    principal: float | None = None
    monthly_amount: float | None = None
    start_date: date | None = None
    maturity_date: date | None = None
    tax_rate: float | None = None
    accrued_interest_pretax: float | None = None
    accrued_interest_aftertax: float | None = None
    maturity_amount: float | None = None
    daily_interest: float | None = None
    monthly_interest: float | None = None
    elapsed_months: int | None = None
    total_months: int | None = None
    paid_count: int | None = None
    price_cached: bool = True


class AssetSummaryResponse(BaseModel):
    """자산 요약 — 총자산, 유형별 소계"""

    total_value_krw: float
    total_invested_krw: float
    total_profit_loss: float
    total_profit_loss_rate: float
    breakdown: dict[str, float]
    holdings: list[AssetHoldingResponse]
