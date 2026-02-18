import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, String, Text, DateTime, JSON, Uuid, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    default_currency: Mapped[str] = mapped_column(
        String(3), default="KRW", nullable=False
    )
    salary_day: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False, server_default="1"
    )
    salary_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("assets.id", ondelete="SET NULL"),
        nullable=True,
        default=None,
    )
    investment_prompt: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    notification_preferences: Mapped[dict | None] = mapped_column(
        JSON, nullable=True, default=None
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
