import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.security import AssetClass, DataSource


class SecurityCreate(BaseModel):
    symbol: str = Field(..., max_length=20)
    name: str = Field(..., max_length=100)
    currency: str = Field("KRW", max_length=3)
    asset_class: AssetClass
    data_source: DataSource = DataSource.MANUAL
    exchange: str | None = Field(None, max_length=20)


class SecurityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    name: str
    currency: str
    asset_class: AssetClass
    data_source: DataSource
    exchange: str | None
    created_at: datetime


class SecuritySearchResult(BaseModel):
    """yfinance 검색 결과 한 줄. id가 null이면 DB에 아직 등록되지 않은 종목."""

    symbol: str
    name: str
    currency: str
    exchange: str | None
    asset_class: AssetClass
    id: uuid.UUID | None


class SecurityEnsureRequest(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)


class SecurityEnsureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    symbol: str
    name: str
    currency: str
    asset_class: AssetClass
    exchange: str | None
    current_price: Decimal | None
