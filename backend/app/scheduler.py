from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
from sqlalchemy import delete

from app.database import async_session
from app.models import BriefingSession, Article, TopicSummary, Briefing
from app.services.news_collector import NewsCollector
from app.services.ai_processor import AIProcessor
from app.services.briefing_generator import BriefingGenerator


def _make_batch_id(session_type: BriefingSession) -> str:
    return f"{datetime.now().strftime('%Y-%m-%d')}_{session_type.value}"


async def scheduled_job(session_type: BriefingSession):
    """Run the full collection -> consolidation -> briefing pipeline."""
    batch_id = _make_batch_id(session_type)
    logger.info(f"Starting scheduled job: {batch_id}")

    async with async_session() as db:
        try:
            # 1. Collect news + scrape bodies
            collector = NewsCollector(db)
            new_articles = await collector.collect_all()
            logger.info(f"Collected {len(new_articles)} new articles")

            # 2. Consolidated AI analysis (per keyword, not per article)
            processor = AIProcessor()
            summaries = await processor.process_batch(db, batch_id)
            logger.info(f"Created {summaries} consolidated topic summaries")

            # 3. Generate daily briefing
            generator = BriefingGenerator()
            briefing = await generator.generate(db, session_type)
            if briefing:
                logger.info(f"Briefing generated: {briefing.id}")

        except Exception as e:
            logger.error(f"Scheduled job failed: {e}")


async def cleanup_old_data(days: int = 30):
    """Delete data older than the specified number of days."""
    cutoff = datetime.now() - timedelta(days=days)
    logger.info(f"Cleaning up data older than {cutoff.isoformat()}")

    async with async_session() as db:
        try:
            r1 = await db.execute(delete(TopicSummary).where(TopicSummary.created_at < cutoff))
            r2 = await db.execute(delete(Article).where(Article.created_at < cutoff))
            r3 = await db.execute(delete(Briefing).where(Briefing.created_at < cutoff))
            await db.commit()
            logger.info(
                f"Cleanup done: {r1.rowcount} summaries, {r2.rowcount} articles, {r3.rowcount} briefings deleted"
            )
        except Exception as e:
            await db.rollback()
            logger.error(f"Cleanup failed: {e}")


def setup_scheduler() -> AsyncIOScheduler:
    """Configure APScheduler: 3x/day (08:00, 13:00, 18:00 KST)."""
    scheduler = AsyncIOScheduler(timezone="Asia/Seoul")

    scheduler.add_job(
        scheduled_job,
        CronTrigger(hour=8, minute=0, timezone="Asia/Seoul"),
        args=[BriefingSession.MORNING],
        id="morning_briefing",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        scheduled_job,
        CronTrigger(hour=13, minute=0, timezone="Asia/Seoul"),
        args=[BriefingSession.MIDDAY],
        id="midday_check",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        scheduled_job,
        CronTrigger(hour=18, minute=0, timezone="Asia/Seoul"),
        args=[BriefingSession.EVENING],
        id="evening_wrapup",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.add_job(
        cleanup_old_data,
        CronTrigger(hour=3, minute=0, timezone="Asia/Seoul"),
        id="daily_cleanup",
        max_instances=1,
        replace_existing=True,
    )

    return scheduler
