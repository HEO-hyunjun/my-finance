import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, ForeignKey, Enum, Numeric, Integer, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IncomeType(str, PyEnum):
    SALARY = "salary"
    SIDE = "side"
    INVESTMENT = "investment"
    OTHER = "other"


class RecurringIncome(Base):
    __tablename__ = "recurring_incomes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[IncomeType] = mapped_column(
        Enum(IncomeType, name="income_type_enum", native_enum=False), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    recurring_day: Mapped[int] = mapped_column(Integer, nullable=False)
    target_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    target_asset: Mapped["Asset | None"] = relationship(  # noqa: F821
        "Asset", foreign_keys=[target_asset_id]
    )


class Income(Base):
    __tablename__ = "incomes"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[IncomeType] = mapped_column(
        Enum(IncomeType, name="income_type_enum", native_enum=False), nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    recurring_income_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("recurring_incomes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    target_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    received_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    recurring_income: Mapped["RecurringIncome | None"] = relationship(
        "RecurringIncome", foreign_keys=[recurring_income_id]
    )
    target_asset: Mapped["Asset | None"] = relationship(  # noqa: F821
        "Asset", foreign_keys=[target_asset_id]
    )
