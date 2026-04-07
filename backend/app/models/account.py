import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, Enum, Numeric, Uuid, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AccountType(str, PyEnum):
    CASH = "cash"
    DEPOSIT = "deposit"
    SAVINGS = "savings"
    PARKING = "parking"
    INVESTMENT = "investment"


class InterestType(str, PyEnum):
    SIMPLE = "simple"
    COMPOUND = "compound"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, native_enum=False), nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="KRW")
    institution: Mapped[str | None] = mapped_column(String(50), nullable=True)
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 3), nullable=True)
    interest_type: Mapped[InterestType | None] = mapped_column(
        Enum(InterestType, native_enum=False), nullable=True,
    )
    monthly_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    tax_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3), nullable=True, default=Decimal("15.400"),
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    entries: Mapped[list["Entry"]] = relationship(back_populates="account", cascade="all, delete-orphan")  # noqa: F821
