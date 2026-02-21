import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Float, Integer, Text, Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NewsArticleDB(Base):
    __tablename__ = "news_articles"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    external_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_icon: Mapped[str | None] = mapped_column(String(500), nullable=True)
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(String(500), nullable=True)
    published_at: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    related_asset: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # LLM-generated fields
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(20), nullable=True)  # positive, negative, neutral
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)  # -1.0 ~ 1.0
    keywords: Mapped[str | None] = mapped_column(Text, nullable=True)  # comma-separated

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_news_category_created", "category", "created_at"),
        Index("ix_news_external_id", "external_id"),
    )


class NewsCluster(Base):
    __tablename__ = "news_clusters"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    sentiment: Mapped[str] = mapped_column(
        String(20), nullable=False, default="neutral"
    )
    avg_sentiment_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )
    article_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    article_ids: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # comma-separated external_ids
    keywords: Mapped[str] = mapped_column(Text, nullable=False)  # top keywords
    importance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0
    )  # 0~1
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_clusters_created", "created_at"),
        Index("ix_clusters_category", "category"),
    )
