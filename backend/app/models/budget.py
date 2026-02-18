import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from enum import Enum as PyEnum

from sqlalchemy import String, DateTime, Date, ForeignKey, Enum, Index, Numeric, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentMethod(str, PyEnum):
    CASH = "cash"
    CARD = "card"
    TRANSFER = "transfer"


class CarryoverType(str, PyEnum):
    EXPIRE = "expire"
    NEXT_MONTH = "next_month"
    SAVINGS = "savings"
    INVESTMENT = "investment"
    DEPOSIT = "deposit"


class BudgetCategory(Base):
    __tablename__ = "budget_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(10), nullable=True)
    color: Mapped[str | None] = mapped_column(String(7), nullable=True)
    monthly_budget: Mapped[Decimal] = mapped_column(
        Numeric(18, 0), default=Decimal("0"), nullable=False
    )
    sort_order: Mapped[int] = mapped_column(default=0, nullable=False)
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
    expenses: Mapped[list["Expense"]] = relationship(
        "Expense", back_populates="category", cascade="all, delete-orphan"
    )


class Expense(Base):
    __tablename__ = "expenses"
    __table_args__ = (
        Index("ix_expenses_user_spent", "user_id", "spent_at"),
        Index("ix_expenses_user_category_spent", "user_id", "category_id", "spent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fixed_expense_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("fixed_expenses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    spent_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    category: Mapped["BudgetCategory"] = relationship(
        "BudgetCategory", back_populates="expenses"
    )
    fixed_expense: Mapped["FixedExpense | None"] = relationship(
        "FixedExpense", foreign_keys=[fixed_expense_id]
    )
    source_asset: Mapped["Asset | None"] = relationship(
        "Asset", foreign_keys=[source_asset_id]
    )


class FixedExpense(Base):
    __tablename__ = "fixed_expenses"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    payment_day: Mapped[int] = mapped_column(nullable=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", native_enum=False),
        nullable=True,
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
    category: Mapped["BudgetCategory"] = relationship(
        "BudgetCategory", foreign_keys=[category_id]
    )


class Installment(Base):
    __tablename__ = "installments"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    monthly_amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    payment_day: Mapped[int] = mapped_column(nullable=False)
    total_installments: Mapped[int] = mapped_column(nullable=False)
    paid_installments: Mapped[int] = mapped_column(default=0, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        Enum(PaymentMethod, name="payment_method_enum", native_enum=False),
        nullable=True,
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
    category: Mapped["BudgetCategory"] = relationship(
        "BudgetCategory", foreign_keys=[category_id]
    )


class BudgetCarryoverSetting(Base):
    __tablename__ = "budget_carryover_settings"
    __table_args__ = (
        Index("uq_carryover_user_category", "user_id", "category_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    carryover_type: Mapped[CarryoverType] = mapped_column(
        Enum(CarryoverType, name="carryover_type_enum", native_enum=False),
        default=CarryoverType.EXPIRE,
        nullable=False,
    )
    carryover_limit: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 0), nullable=True
    )
    target_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
    )
    target_savings_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    target_annual_rate: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 3), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    category_rel: Mapped["BudgetCategory"] = relationship(
        "BudgetCategory", foreign_keys=[category_id]
    )


class BudgetCarryoverLog(Base):
    __tablename__ = "budget_carryover_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("budget_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    budget_period_start: Mapped[date] = mapped_column(Date, nullable=False)
    budget_period_end: Mapped[date] = mapped_column(Date, nullable=False)
    carryover_type: Mapped[CarryoverType] = mapped_column(
        Enum(CarryoverType, name="carryover_type_enum", native_enum=False),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 0), nullable=False)
    target_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    category_rel: Mapped["BudgetCategory"] = relationship(
        "BudgetCategory", foreign_keys=[category_id]
    )
