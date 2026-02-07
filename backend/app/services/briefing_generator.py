import asyncio
import json
from datetime import date, datetime, timedelta

from google import genai
from loguru import logger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Article, Briefing, BriefingSession, Sentiment

BRIEFING_PROMPT = """You are a senior market analyst creating a briefing for a quant developer.

Here are today's collected news articles (already analyzed):
{articles_json}

Tasks:
1. Select the 3 most impactful articles from the list. For each, explain why it matters for an investor (in Korean).
2. Provide an overall market sentiment breakdown (in Korean).
3. Identify cross-market themes between US and KR markets (in Korean).

Return ONLY valid JSON matching this schema:
{{
  "overall_sentiment": {{
    "bullish_pct": 60,
    "bearish_pct": 25,
    "neutral_pct": 15,
    "summary": "Korean summary of overall market mood"
  }},
  "must_reads": [
    {{
      "article_id": 1,
      "title": "article title",
      "why_important": "Korean explanation of importance",
      "impact_analysis": "Korean analysis of market impact"
    }}
  ],
  "cross_market_themes": ["theme1 in Korean", "theme2 in Korean"]
}}"""


class BriefingGenerator:
    """Generate daily market briefings using Gemini AI."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def generate(self, db: AsyncSession, session: BriefingSession) -> Briefing | None:
        """Generate a briefing for the given session."""
        today = date.today()

        # Check if briefing already exists for this session today
        existing = await db.execute(
            select(Briefing).where(
                Briefing.date == today,
                Briefing.session == session,
            )
        )
        if existing.scalar_one_or_none():
            logger.info(f"Briefing for {session.value} on {today} already exists")
            return None

        # Get today's analyzed articles
        articles = await self._get_todays_articles(db)
        if not articles:
            logger.warning("No analyzed articles found for briefing generation")
            return None

        # Prepare articles data for prompt
        articles_data = []
        for a in articles:
            articles_data.append({
                "id": a.id,
                "title": a.title,
                "source": a.source_name,
                "region": a.region.value,
                "sentiment": a.sentiment.value if a.sentiment else "Unknown",
                "summary": json.loads(a.ai_summary) if a.ai_summary else [],
                "tickers": json.loads(a.related_tickers) if a.related_tickers else [],
            })

        # Generate briefing with Gemini
        briefing_data = await self._generate_briefing(articles_data)
        if not briefing_data:
            # Fallback: compute basic sentiment stats
            briefing_data = self._compute_basic_stats(articles)

        briefing = Briefing(
            date=today,
            session=session,
            overall_sentiment=json.dumps(briefing_data.get("overall_sentiment", {}), ensure_ascii=False),
            must_read_summary=json.dumps({
                "must_reads": briefing_data.get("must_reads", []),
                "cross_market_themes": briefing_data.get("cross_market_themes", []),
            }, ensure_ascii=False),
        )

        db.add(briefing)
        await db.commit()
        await db.refresh(briefing)

        logger.info(f"Generated {session.value} briefing for {today}")
        return briefing

    async def _get_todays_articles(self, db: AsyncSession) -> list[Article]:
        """Get today's articles that have been analyzed."""
        today_start = datetime.combine(date.today(), datetime.min.time())

        result = await db.execute(
            select(Article)
            .where(
                Article.created_at >= today_start,
                Article.ai_summary.isnot(None),
            )
            .order_by(Article.created_at.desc())
        )
        return list(result.scalars().all())

    async def _generate_briefing(self, articles_data: list[dict]) -> dict | None:
        """Generate briefing content with Gemini."""
        prompt = BRIEFING_PROMPT.format(
            articles_json=json.dumps(articles_data, ensure_ascii=False, indent=2)
        )

        for attempt in range(3):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=settings.gemini_model,
                    contents=prompt,
                    config={
                        "temperature": 0.3,
                        "response_mime_type": "application/json",
                    },
                )

                text = response.text.strip()
                return json.loads(text)

            except json.JSONDecodeError as e:
                logger.warning(f"Briefing JSON parse error (attempt {attempt + 1}): {e}")
            except Exception as e:
                logger.warning(f"Briefing generation error (attempt {attempt + 1}): {e}")
                if attempt < 2:
                    await asyncio.sleep(2)

        return None

    @staticmethod
    def _compute_basic_stats(articles: list[Article]) -> dict:
        """Compute basic sentiment stats as fallback."""
        total = len(articles)
        if total == 0:
            return {
                "overall_sentiment": {"bullish_pct": 0, "bearish_pct": 0, "neutral_pct": 100, "summary": "데이터 없음"},
                "must_reads": [],
                "cross_market_themes": [],
            }

        bullish = sum(1 for a in articles if a.sentiment == Sentiment.BULLISH)
        bearish = sum(1 for a in articles if a.sentiment == Sentiment.BEARISH)
        neutral = total - bullish - bearish

        # Pick top 3 by most recent with non-neutral sentiment
        sorted_articles = sorted(
            [a for a in articles if a.sentiment in (Sentiment.BULLISH, Sentiment.BEARISH)],
            key=lambda a: a.created_at,
            reverse=True,
        )[:3]

        must_reads = [
            {
                "article_id": a.id,
                "title": a.title,
                "why_important": json.loads(a.ai_summary)[0] if a.ai_summary else a.title,
                "impact_analysis": f"감성: {a.sentiment.value}" if a.sentiment else "",
            }
            for a in sorted_articles
        ]

        return {
            "overall_sentiment": {
                "bullish_pct": round(bullish / total * 100),
                "bearish_pct": round(bearish / total * 100),
                "neutral_pct": round(neutral / total * 100),
                "summary": f"오늘 수집된 {total}건 중 긍정 {bullish}건, 부정 {bearish}건, 중립 {neutral}건",
            },
            "must_reads": must_reads,
            "cross_market_themes": [],
        }
