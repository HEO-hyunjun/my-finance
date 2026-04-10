import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey, Text, Enum, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from enum import Enum as PyEnum

from app.core.database import Base


class ApiServiceType(str, PyEnum):
    TAVILY = "tavily"
    SERPAPI = "serpapi"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MISTRAL = "mistral"
    CUSTOM_LLM = "custom_llm"


class ApiKey(Base):
    __tablename__ = "api_keys"
    __table_args__ = (
        UniqueConstraint("user_id", "service", name="uq_api_key_user_service"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    service: Mapped[ApiServiceType] = mapped_column(
        Enum(ApiServiceType), nullable=False,
    )
    encrypted_key: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class LlmSetting(Base):
    __tablename__ = "llm_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    default_model: Mapped[str] = mapped_column(
        String(100), default="gpt-4o", nullable=False
    )
    inference_model: Mapped[str] = mapped_column(
        String(100), default="gpt-4o", nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
