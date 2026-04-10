import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, Enum, Numeric, Uuid, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssetClass(str, PyEnum):
    EQUITY_KR = "equity_kr"
    EQUITY_US = "equity_us"
    COMMODITY = "commodity"
    CURRENCY_PAIR = "currency_pair"


class DataSource(str, PyEnum):
    YAHOO = "yahoo"
    MANUAL = "manual"


class Security(Base):
    __tablename__ = "securities"
    __table_args__ = (
        UniqueConstraint("symbol", "data_source", name="uq_security_symbol_source"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    asset_class: Mapped[AssetClass] = mapped_column(
        Enum(AssetClass, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False,
    )
    data_source: Mapped[DataSource] = mapped_column(
        Enum(DataSource, native_enum=False, values_callable=lambda x: [e.value for e in x]), nullable=False, default=DataSource.YAHOO,
    )
    exchange: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    prices: Mapped[list["SecurityPrice"]] = relationship(back_populates="security", cascade="all, delete-orphan")


class SecurityPrice(Base):
    __tablename__ = "security_prices"
    __table_args__ = (
        UniqueConstraint("security_id", "price_date", name="uq_price_security_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    security_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("securities.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    price_date: Mapped[date] = mapped_column(Date, nullable=False)
    close_price: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    security: Mapped["Security"] = relationship(back_populates="prices")
