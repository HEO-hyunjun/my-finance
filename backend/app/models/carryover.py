import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class CarryoverType(str, PyEnum):
    EXPIRE = "expire"
    NEXT_MONTH = "next_month"
    SAVINGS = "savings"
    DEPOSIT = "deposit"
    TRANSFER = "transfer"


class CarryoverSetting(Base):
    __tablename__ = "carryover_settings"
    __table_args__ = (
        UniqueConstraint("user_id", "category_id", name="uq_carryover_setting_user_category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False,
    )
    carryover_type: Mapped[CarryoverType] = mapped_column(
        Enum(CarryoverType), nullable=False, default=CarryoverType.EXPIRE,
    )
    carryover_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True,
    )
    target_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True,
    )
    target_savings_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_annual_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 3), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class CarryoverLog(Base):
    __tablename__ = "carryover_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="CASCADE"), nullable=False,
    )
    budget_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    budget_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    carryover_type: Mapped[CarryoverType] = mapped_column(
        Enum(CarryoverType), nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    target_description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
