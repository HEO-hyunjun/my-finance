import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    String, Text, DateTime, Date, Numeric, Uuid, ForeignKey, Boolean,
    Integer, LargeBinary, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ImportBatch(Base):
    __tablename__ = "import_batches"
    __table_args__ = (
        UniqueConstraint("user_id", "file_hash", name="uq_import_batch_user_filehash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True,
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_bank: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # uploaded / parsing / review / committed / failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")
    period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    period_end: Mapped[date | None] = mapped_column(Date, nullable=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 원본 파일 바이트 — Celery 태스크가 파싱할 때 사용
    raw_file: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    staged_entries: Mapped[list["StagedEntry"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan",
    )


class StagedEntry(Base):
    __tablename__ = "staged_entries"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("import_batches.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    transacted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 4), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    balance_after: Mapped[Decimal | None] = mapped_column(Numeric(18, 4), nullable=True)
    suggested_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    suggested_category_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True,
    )
    # new / exact / probable
    dedup_status: Mapped[str] = mapped_column(String(20), nullable=False, default="new")
    matched_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("entries.id", ondelete="SET NULL"), nullable=True,
    )
    is_selected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    committed_entry_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("entries.id", ondelete="SET NULL"), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
    )

    batch: Mapped["ImportBatch"] = relationship(back_populates="staged_entries")
