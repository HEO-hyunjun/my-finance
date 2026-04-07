import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import (
    String, Text, DateTime, Enum, Numeric, Uuid, ForeignKey, Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EntryType(str, PyEnum):
    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    BUY = "buy"
    SELL = "sell"
    DIVIDEND = "dividend"
    INTEREST = "interest"
    FEE = "fee"
    ADJUSTMENT = "adjustment"


class GroupType(str, PyEnum):
    TRANSFER = "transfer"
    TRADE = "trade"
    ADJUSTMENT = "adjustment"


class EntryGroup(Base):
    __tablename__ = "entry_groups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    group_type: Mapped[GroupType] = mapped_column(
        Enum(GroupType, native_enum=False), nullable=False,
    )
    description: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    entries: Mapped[list["Entry"]] = relationship(back_populates="entry_group")


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (
        Index("ix_entries_user_transacted", "user_id", "transacted_at"),
        Index("ix_entries_account_transacted", "account_id", "transacted_at"),
        Index("ix_entries_account_security", "account_id", "security_id"),
        Index("ix_entries_user_category_transacted", "user_id", "category_id", "transacted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False,
    )
    entry_group_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("entry_groups.id", ondelete="SET NULL"), nullable=True,
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True,
    )
    security_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("securities.id", ondelete="SET NULL"), nullable=True,
    )
    type: Mapped[EntryType] = mapped_column(
        Enum(EntryType, native_enum=False), nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(18, 8), nullable=True)
    unit_price: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    fee: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False, default=Decimal("0"))
    exchange_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    recurring_schedule_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, nullable=True,
    )
    transacted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    account: Mapped["Account"] = relationship(back_populates="entries")  # noqa: F821
    entry_group: Mapped["EntryGroup | None"] = relationship(back_populates="entries")
    category: Mapped["Category | None"] = relationship()  # noqa: F821
    security: Mapped["Security | None"] = relationship()  # noqa: F821
