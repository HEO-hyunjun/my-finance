import uuid
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import DateTime, ForeignKey, Enum, Numeric, Text, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class TransactionType(str, PyEnum):
    BUY = "buy"
    SELL = "sell"
    EXCHANGE = "exchange"
    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"


class CurrencyType(str, PyEnum):
    KRW = "KRW"
    USD = "USD"


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        Index("ix_transactions_user_transacted", "user_id", "transacted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("assets.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[TransactionType] = mapped_column(
        Enum(TransactionType, name="transaction_type_enum", native_enum=False), nullable=False
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[CurrencyType] = mapped_column(
        Enum(CurrencyType, name="currency_type_enum", native_enum=False), nullable=False
    )
    exchange_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4), nullable=True
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 4), default=Decimal("0"), nullable=False
    )
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    transacted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    asset: Mapped["Asset"] = relationship(
        "Asset", foreign_keys=[asset_id], back_populates="transactions"
    )
