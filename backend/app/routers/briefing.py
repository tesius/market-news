import json
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Briefing
from app.schemas import BriefingResponse, OverallSentiment, MustRead

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


def _parse_briefing(briefing: Briefing) -> BriefingResponse:
    """Parse a Briefing model into BriefingResponse."""
    overall = None
    if briefing.overall_sentiment:
        try:
            data = json.loads(briefing.overall_sentiment)
            overall = OverallSentiment(**data)
        except (json.JSONDecodeError, TypeError):
            pass

    must_reads = None
    cross_market_themes = None
    if briefing.must_read_summary:
        try:
            data = json.loads(briefing.must_read_summary)
            must_reads = [MustRead(**mr) for mr in data.get("must_reads", [])]
            cross_market_themes = data.get("cross_market_themes", [])
        except (json.JSONDecodeError, TypeError):
            pass

    return BriefingResponse(
        id=briefing.id,
        date=briefing.date,
        session=briefing.session,
        overall_sentiment=overall,
        must_reads=must_reads,
        cross_market_themes=cross_market_themes,
        created_at=briefing.created_at,
    )


@router.get("", response_model=BriefingResponse | None)
async def get_latest_briefing(db: AsyncSession = Depends(get_db)):
    """Get the latest briefing (today's most recent session)."""
    result = await db.execute(
        select(Briefing).order_by(desc(Briefing.created_at)).limit(1)
    )
    briefing = result.scalar_one_or_none()

    if not briefing:
        return None

    return _parse_briefing(briefing)


@router.get("/history", response_model=list[BriefingResponse])
async def get_briefing_history(
    days: int = Query(7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
):
    """Get briefing history for the past N days."""
    from datetime import timedelta

    start_date = date.today() - timedelta(days=days)

    result = await db.execute(
        select(Briefing)
        .where(Briefing.date >= start_date)
        .order_by(desc(Briefing.created_at))
    )
    briefings = result.scalars().all()

    return [_parse_briefing(b) for b in briefings]
