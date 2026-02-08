import enum
from datetime import datetime, date

from sqlalchemy import String, Text, Boolean, Enum, DateTime, Date, Integer, Index, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Region(str, enum.Enum):
    US = "US"
    KR = "KR"


class Sentiment(str, enum.Enum):
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


class BriefingSession(str, enum.Enum):
    MORNING = "morning"
    MIDDAY = "midday"
    EVENING = "evening"


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[Region] = mapped_column(Enum(Region), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Article(Base):
    __tablename__ = "articles"
    __table_args__ = (
        Index("ix_articles_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    link: Mapped[str] = mapped_column(String(1000), unique=True, nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    source_name: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[Region] = mapped_column(Enum(Region), nullable=False)
    raw_snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment: Mapped[Sentiment | None] = mapped_column(Enum(Sentiment), nullable=True)
    related_tickers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    keyword_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class TopicSummary(Base):
    """Consolidated AI summary per keyword per batch."""
    __tablename__ = "topic_summaries"
    __table_args__ = (
        Index("ix_topic_summaries_created_at", "created_at"),
        Index("ix_topic_summaries_batch_id", "batch_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword_tag: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[Region] = mapped_column(Enum(Region), nullable=False)
    batch_id: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "2026-02-07_morning"
    headline: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sentiment: Mapped[Sentiment | None] = mapped_column(Enum(Sentiment), nullable=True)
    related_tickers: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON
    source_articles: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON: [{id, title, link, source}]
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Briefing(Base):
    __tablename__ = "briefings"
    __table_args__ = (
        Index("ix_briefings_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    session: Mapped[BriefingSession] = mapped_column(Enum(BriefingSession), nullable=False)
    overall_sentiment: Mapped[str | None] = mapped_column(Text, nullable=True)
    must_read_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
