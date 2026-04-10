import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, JSON, Uuid
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

    # --- Personal API Key ---
    api_key_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None, index=True
    )
    api_key_encrypted: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )
    api_key_prefix: Mapped[str | None] = mapped_column(
        String(12), nullable=True, default=None
    )
    api_key_created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
