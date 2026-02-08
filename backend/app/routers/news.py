import json
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import TopicSummary
from app.schemas import TopicSummaryResponse, TopicSummaryListResponse, SourceArticle

router = APIRouter(prefix="/api", tags=["news"])


def _build_topic_responses(summaries) -> list[TopicSummaryResponse]:
    """Convert TopicSummary ORM objects to response models."""
    items = []
    for s in summaries:
        sources = []
        if s.source_articles:
            try:
                sources = [SourceArticle(**a) for a in json.loads(s.source_articles)]
            except (json.JSONDecodeError, TypeError):
                pass

        items.append(TopicSummaryResponse(
            id=s.id,
            keyword_tag=s.keyword_tag,
            region=s.region,
            batch_id=s.batch_id,
            headline=s.headline,
            summary=s.summary,
            sentiment=s.sentiment,
            related_tickers=json.loads(s.related_tickers) if s.related_tickers else [],
            source_articles=sources,
            article_count=s.article_count,
            created_at=s.created_at,
        ))
    return items


@router.get("/topics", response_model=TopicSummaryListResponse)
async def list_topic_summaries(
    batch_id: str | None = None,
    days_offset: int = Query(default=0, ge=0),
    days_limit: int = Query(default=3, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """List consolidated topic summaries.

    - batch_id: return a specific batch (legacy mode)
    - days_offset + days_limit: date-range pagination (default: latest 3 days)
    """
    # Legacy mode: specific batch_id
    if batch_id:
        query = (
            select(TopicSummary)
            .where(TopicSummary.batch_id == batch_id)
            .order_by(desc(TopicSummary.created_at))
        )
        result = await db.execute(query)
        summaries = result.scalars().all()
        return TopicSummaryListResponse(
            items=_build_topic_responses(summaries),
            batch_id=batch_id,
        )

    # Date-range pagination mode
    now = datetime.now()
    range_end = now - timedelta(days=days_offset)
    range_start = range_end - timedelta(days=days_limit)

    query = (
        select(TopicSummary)
        .where(TopicSummary.created_at >= range_start)
        .where(TopicSummary.created_at <= range_end)
        .order_by(desc(TopicSummary.created_at))
    )
    result = await db.execute(query)
    summaries = result.scalars().all()

    # Check if older data exists
    older = await db.execute(
        select(func.count(TopicSummary.id))
        .where(TopicSummary.created_at < range_start)
    )
    has_more = (older.scalar() or 0) > 0

    # Determine batch_id for response (use latest batch in range, or empty)
    response_batch_id = summaries[0].batch_id if summaries else ""

    return TopicSummaryListResponse(
        items=_build_topic_responses(summaries),
        batch_id=response_batch_id,
        has_more=has_more,
    )


@router.get("/batches")
async def list_batches(db: AsyncSession = Depends(get_db)):
    """List available batch IDs for historical browsing."""
    result = await db.execute(
        select(TopicSummary.batch_id, func.count(TopicSummary.id), func.max(TopicSummary.created_at))
        .group_by(TopicSummary.batch_id)
        .order_by(desc(func.max(TopicSummary.created_at)))
        .limit(20)
    )
    return [
        {"batch_id": row[0], "topic_count": row[1], "created_at": row[2].isoformat() if row[2] else None}
        for row in result.all()
    ]
