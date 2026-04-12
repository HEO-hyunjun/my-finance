from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    direction: str  # "income" or "expense"
    name: str
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0
    default_allocation: Decimal | None = Field(default=None, ge=0)


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None
    default_allocation: Decimal | None = Field(default=None, ge=0)
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    direction: str
    name: str
    icon: str | None
    color: str | None
    sort_order: int
    default_allocation: Decimal | None
    is_active: bool
    created_at: datetime
