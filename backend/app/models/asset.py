import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, ForeignKey, Enum, Numeric, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssetType(str, PyEnum):
    STOCK_KR = "stock_kr"
    STOCK_US = "stock_us"
    GOLD = "gold"
    CASH_KRW = "cash_krw"
    CASH_USD = "cash_usd"
    DEPOSIT = "deposit"
    SAVINGS = "savings"
    PARKING = "parking"


class InterestType(str, PyEnum):
    SIMPLE = "simple"
    COMPOUND = "compound"


class Asset(Base):
    __tablename__ = "assets"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    asset_type: Mapped[AssetType] = mapped_column(
        Enum(AssetType, name="asset_type_enum", native_enum=False), nullable=False
    )
    symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # --- 예금/적금/파킹통장 전용 필드 (nullable) ---
    interest_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3), nullable=True
    )
    interest_type: Mapped[InterestType | None] = mapped_column(
        Enum(InterestType, name="interest_type_enum", native_enum=False), nullable=True
    )
    principal: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 0), nullable=True
    )
    monthly_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 0), nullable=True
    )
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3), nullable=True, default=Decimal("15.400")
    )
    bank_name: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    transactions: Mapped[list["Transaction"]] = relationship(
        "Transaction", back_populates="asset", cascade="all, delete-orphan"
    )
