from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db, async_session
from app.models import Keyword, TopicSummary
from app.schemas import KeywordCreate, KeywordUpdate, KeywordResponse
from app.services.news_collector import NewsCollector
from app.services.ai_processor import AIProcessor

router = APIRouter(prefix="/api/keywords", tags=["keywords"])


async def _collect_and_process(keyword_id: int):
    """Background task: collect news for a keyword and generate a topic summary."""
    async with async_session() as db:
        result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
        keyword = result.scalar_one_or_none()
        if not keyword:
            return

        try:
            # 1. Collect articles
            collector = NewsCollector(db)
            new_articles = await collector.collect_for_keyword(keyword)

            if not new_articles:
                logger.info(f"No articles found for new keyword '{keyword.topic}'")
                return

            # 2. Get latest batch_id or create new one
            latest = await db.execute(
                select(TopicSummary.batch_id)
                .order_by(desc(TopicSummary.created_at))
                .limit(1)
            )
            batch_id = latest.scalar_one_or_none()
            if not batch_id:
                batch_id = f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_manual"

            # 3. AI consolidation
            processor = AIProcessor()
            await processor.process_keyword(db, batch_id, keyword.topic)

            logger.info(f"Keyword '{keyword.topic}' collected and processed successfully")
        except Exception as e:
            logger.error(f"Background collect for '{keyword.topic}' failed: {e}")


@router.get("", response_model=list[KeywordResponse])
async def list_keywords(db: AsyncSession = Depends(get_db)):
    """List all keywords."""
    result = await db.execute(select(Keyword).order_by(Keyword.id))
    return result.scalars().all()


@router.post("", response_model=KeywordResponse, status_code=201)
async def create_keyword(
    data: KeywordCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Add a new keyword and start collecting articles for it."""
    keyword = Keyword(topic=data.topic, region=data.region)
    db.add(keyword)
    await db.commit()
    await db.refresh(keyword)

    # Trigger collection in background
    background_tasks.add_task(_collect_and_process, keyword.id)

    return keyword


@router.patch("/{keyword_id}", response_model=KeywordResponse)
async def update_keyword(
    keyword_id: int,
    data: KeywordUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a keyword (toggle is_active, change topic/region)."""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    if data.topic is not None:
        keyword.topic = data.topic
    if data.region is not None:
        keyword.region = data.region
    if data.is_active is not None:
        keyword.is_active = data.is_active

    await db.commit()
    await db.refresh(keyword)
    return keyword


@router.delete("/{keyword_id}", status_code=204)
async def delete_keyword(keyword_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a keyword."""
    result = await db.execute(select(Keyword).where(Keyword.id == keyword_id))
    keyword = result.scalar_one_or_none()

    if not keyword:
        raise HTTPException(status_code=404, detail="Keyword not found")

    await db.delete(keyword)
    await db.commit()
