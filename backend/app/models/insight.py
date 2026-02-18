import uuid
from datetime import date, datetime, timezone

from sqlalchemy import String, DateTime, Date, ForeignKey, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AIInsightRecord(Base):
    __tablename__ = "ai_insights"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)
    generated_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_ai_insights_user_date", "user_id", "generated_date"),
    )
