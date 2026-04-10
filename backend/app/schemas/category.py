from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CategoryCreate(BaseModel):
    direction: str  # "income" or "expense"
    name: str
    icon: str | None = None
    color: str | None = None
    sort_order: int = 0


class CategoryUpdate(BaseModel):
    name: str | None = None
    icon: str | None = None
    color: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    direction: str
    name: str
    icon: str | None
    color: str | None
    sort_order: int
    is_active: bool
    created_at: datetime
