from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger

from app.database import async_session
from app.models import BriefingSession
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


def setup_scheduler() -> AsyncIOScheduler:
    """Configure APScheduler: 2x/day to stay within Gemini free tier."""
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
        CronTrigger(hour=18, minute=0, timezone="Asia/Seoul"),
        args=[BriefingSession.EVENING],
        id="evening_wrapup",
        max_instances=1,
        replace_existing=True,
    )

    return scheduler
