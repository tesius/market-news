from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import engine, get_db, Base, async_session
from app.models import Keyword, Region
from app.routers import news, keywords, briefing, market
from app.scheduler import setup_scheduler
from app.schemas import RefreshResponse
from app.services.news_collector import NewsCollector
from app.services.ai_processor import AIProcessor

DEFAULT_KEYWORDS = [
    {"topic": "US Stock Market", "region": Region.US},
    {"topic": "Federal Reserve", "region": Region.US},
    {"topic": "Semiconductor", "region": Region.US},
    {"topic": "Artificial Intelligence", "region": Region.US},
    {"topic": "한국 주식시장", "region": Region.KR},
    {"topic": "반도체", "region": Region.KR},
    {"topic": "인공지능", "region": Region.KR},
]


async def seed_default_keywords():
    async with async_session() as db:
        result = await db.execute(select(Keyword).limit(1))
        if result.scalar_one_or_none() is None:
            for kw in DEFAULT_KEYWORDS:
                db.add(Keyword(**kw))
            await db.commit()
            logger.info(f"Seeded {len(DEFAULT_KEYWORDS)} default keywords")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")

    await seed_default_keywords()

    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduler started (08:00, 18:00 KST)")

    yield

    scheduler.shutdown()
    logger.info("Scheduler stopped")


app = FastAPI(
    title="Market News API",
    description="Personal investment dashboard - news aggregation & AI analysis",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(news.router)
app.include_router(keywords.router)
app.include_router(briefing.router)
app.include_router(market.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok"}


@app.post("/api/refresh", response_model=RefreshResponse)
async def manual_refresh(db: AsyncSession = Depends(get_db)):
    """Manually trigger news collection and consolidated AI processing."""
    try:
        batch_id = f"{datetime.now().strftime('%Y-%m-%d_%H%M')}_manual"

        # 1. Collect news + scrape bodies
        collector = NewsCollector(db)
        new_articles = await collector.collect_all()

        # 2. Consolidated AI processing (per keyword)
        processor = AIProcessor()
        summaries = await processor.process_batch(db, batch_id)

        return RefreshResponse(
            status="success",
            articles_collected=len(new_articles),
            articles_processed=summaries,
            message=f"Collected {len(new_articles)} articles, created {summaries} topic summaries",
        )
    except Exception as e:
        logger.error(f"Manual refresh failed: {e}")
        return RefreshResponse(
            status="error",
            articles_collected=0,
            articles_processed=0,
            message=str(e),
        )
