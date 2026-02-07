from datetime import datetime, date
from pydantic import BaseModel

from app.models import Region, Sentiment, BriefingSession


# --- Keywords ---

class KeywordCreate(BaseModel):
    topic: str
    region: Region


class KeywordUpdate(BaseModel):
    topic: str | None = None
    region: Region | None = None
    is_active: bool | None = None


class KeywordResponse(BaseModel):
    id: int
    topic: str
    region: Region
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Articles ---

class AISummary(BaseModel):
    headline: str = ""
    summary: str = ""


class ArticleResponse(BaseModel):
    id: int
    title: str
    link: str
    published_at: datetime | None
    source_name: str
    region: Region
    ai_headline: str | None = None
    ai_summary: str | None = None
    sentiment: Sentiment | None
    related_tickers: list[str] | None = None
    keyword_tag: str
    created_at: datetime

    model_config = {"from_attributes": True}


class NewsListResponse(BaseModel):
    items: list[ArticleResponse]
    total: int
    page: int
    page_size: int


# --- Topic Summaries ---

class SourceArticle(BaseModel):
    id: int
    title: str
    link: str
    source: str


class TopicSummaryResponse(BaseModel):
    id: int
    keyword_tag: str
    region: Region
    batch_id: str
    headline: str
    summary: str
    sentiment: Sentiment | None
    related_tickers: list[str] = []
    source_articles: list[SourceArticle] = []
    article_count: int
    created_at: datetime


class TopicSummaryListResponse(BaseModel):
    items: list[TopicSummaryResponse]
    batch_id: str


# --- Briefing ---

class MustRead(BaseModel):
    article_id: int
    title: str
    why_important: str
    impact_analysis: str


class OverallSentiment(BaseModel):
    bullish_pct: float
    bearish_pct: float
    neutral_pct: float
    summary: str


class BriefingResponse(BaseModel):
    id: int
    date: date
    session: BriefingSession
    overall_sentiment: OverallSentiment | None = None
    must_reads: list[MustRead] | None = None
    cross_market_themes: list[str] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Market Data ---

class IndexData(BaseModel):
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float


class MarketDataResponse(BaseModel):
    indices: list[IndexData]
    updated_at: datetime


# --- Refresh ---

class RefreshResponse(BaseModel):
    status: str
    articles_collected: int
    articles_processed: int
    message: str
