import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Article, TopicSummary, Region, Sentiment
from app.schemas import TopicSummaryResponse, TopicSummaryListResponse, SourceArticle

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/topics", response_model=TopicSummaryListResponse)
async def list_topic_summaries(
    batch_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """List consolidated topic summaries. Returns latest batch by default."""
    if batch_id:
        query = (
            select(TopicSummary)
            .where(TopicSummary.batch_id == batch_id)
            .order_by(desc(TopicSummary.created_at))
        )
    else:
        # Get the latest batch_id
        latest = await db.execute(
            select(TopicSummary.batch_id)
            .order_by(desc(TopicSummary.created_at))
            .limit(1)
        )
        latest_batch = latest.scalar_one_or_none()
        if not latest_batch:
            return TopicSummaryListResponse(items=[], batch_id="")

        query = (
            select(TopicSummary)
            .where(TopicSummary.batch_id == latest_batch)
            .order_by(desc(TopicSummary.created_at))
        )
        batch_id = latest_batch

    result = await db.execute(query)
    summaries = result.scalars().all()

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

    return TopicSummaryListResponse(items=items, batch_id=batch_id)


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
