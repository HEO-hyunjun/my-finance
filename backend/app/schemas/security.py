import uuid
from datetime import datetime

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
