import asyncio
import json
from datetime import datetime, date
from collections import defaultdict

from google import genai
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Article, TopicSummary, Sentiment

CONSOLIDATION_PROMPT = """You are a senior financial journalist writing a consolidated briefing for a Korean quant developer.

Topic: {keyword} ({region})
Below are {count} news articles on this topic from various sources:

{articles_text}

Write a consolidated analysis that merges all these articles into ONE coherent briefing.

Tasks:
1. Write a Korean headline (max 60 chars) capturing the key narrative.
2. Write a detailed Korean summary (6-10 sentences, magazine-style).
   - Split into 2-3 short paragraphs using "\n\n" between them.
   - Paragraph 1: Core facts and key developments.
   - Paragraph 2: Context, conflicting viewpoints, and why it matters.
   - Paragraph 3: Market outlook and investor implications.
   - Each paragraph should be 2-4 sentences.
3. Determine overall sentiment: "Bullish", "Bearish", or "Neutral".
4. Extract all relevant stock tickers mentioned.

Return ONLY valid JSON:
{{
  "headline": "핵심 내러티브를 담은 헤드라인",
  "summary": "첫 번째 문단.\n\n두 번째 문단.\n\n세 번째 문단.",
  "sentiment": "Bullish",
  "tickers": ["NVDA", "005930.KS"]
}}"""


class AIProcessor:
    """Process articles by keyword - consolidate multiple articles into one summary per topic."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def process_keyword(self, db: AsyncSession, batch_id: str, keyword_tag: str) -> bool:
        """Generate a consolidated summary for a single keyword's unprocessed articles."""
        result = await db.execute(
            select(Article)
            .where(Article.ai_summary.is_(None), Article.keyword_tag == keyword_tag)
            .order_by(Article.created_at.desc())
        )
        articles = result.scalars().all()

        if not articles:
            logger.info(f"No unprocessed articles for '{keyword_tag}'")
            return False

        region = articles[0].region
        summary_data = await self._consolidate_articles(keyword_tag, region, articles)

        if not summary_data:
            return False

        source_refs = [
            {"id": a.id, "title": a.title, "link": a.link, "source": a.source_name}
            for a in articles
        ]

        topic_summary = TopicSummary(
            keyword_tag=keyword_tag,
            region=region,
            batch_id=batch_id,
            headline=summary_data.get("headline", keyword_tag),
            summary=summary_data["summary"],
            sentiment=Sentiment(summary_data["sentiment"]),
            related_tickers=json.dumps(summary_data.get("tickers", [])),
            source_articles=json.dumps(source_refs, ensure_ascii=False),
            article_count=len(articles),
        )
        db.add(topic_summary)

        for a in articles:
            a.ai_summary = "consolidated"

        await db.commit()
        logger.info(f"Consolidated {len(articles)} articles for '{keyword_tag}' -> 1 summary")
        return True

    async def process_batch(self, db: AsyncSession, batch_id: str) -> int:
        """Group unprocessed articles by keyword and generate consolidated summaries."""
        # Get articles from this batch that don't have topic summaries yet
        result = await db.execute(
            select(Article)
            .where(Article.ai_summary.is_(None))
            .order_by(Article.created_at.desc())
        )
        articles = result.scalars().all()

        if not articles:
            logger.info("No unprocessed articles found")
            return 0

        # Group by keyword_tag
        groups: dict[str, list[Article]] = defaultdict(list)
        for article in articles:
            groups[article.keyword_tag].append(article)

        processed = 0
        for keyword_tag, group_articles in groups.items():
            try:
                region = group_articles[0].region
                summary_data = await self._consolidate_articles(keyword_tag, region, group_articles)

                if summary_data:
                    # Store source article references
                    source_refs = [
                        {
                            "id": a.id,
                            "title": a.title,
                            "link": a.link,
                            "source": a.source_name,
                        }
                        for a in group_articles
                    ]

                    topic_summary = TopicSummary(
                        keyword_tag=keyword_tag,
                        region=region,
                        batch_id=batch_id,
                        headline=summary_data.get("headline", keyword_tag),
                        summary=summary_data["summary"],
                        sentiment=Sentiment(summary_data["sentiment"]),
                        related_tickers=json.dumps(summary_data.get("tickers", [])),
                        source_articles=json.dumps(source_refs, ensure_ascii=False),
                        article_count=len(group_articles),
                    )
                    db.add(topic_summary)

                    # Mark individual articles as processed
                    for a in group_articles:
                        a.ai_summary = "consolidated"

                    processed += 1
                    logger.info(
                        f"Consolidated {len(group_articles)} articles for '{keyword_tag}' -> 1 summary"
                    )

                # Rate limiting
                await asyncio.sleep(settings.gemini_rpm_delay)

            except Exception as e:
                logger.error(f"Failed to consolidate '{keyword_tag}': {e}")

        if processed > 0:
            await db.commit()

        logger.info(f"Created {processed} topic summaries from {len(articles)} articles")
        return processed

    async def _consolidate_articles(
        self, keyword: str, region, articles: list[Article]
    ) -> dict | None:
        """Send all articles for a keyword to Gemini for consolidated analysis."""
        # Build articles text
        articles_parts = []
        for i, a in enumerate(articles, 1):
            snippet = a.raw_snippet or ""
            if len(snippet) > 500:
                snippet = snippet[:500] + "..."
            articles_parts.append(
                f"[{i}] {a.source_name}: {a.title}\n{snippet}"
            )

        articles_text = "\n\n".join(articles_parts)

        # Truncate if too long for token limits
        if len(articles_text) > 6000:
            articles_text = articles_text[:6000] + "\n\n[... additional articles truncated]"

        prompt = CONSOLIDATION_PROMPT.format(
            keyword=keyword,
            region=region.value,
            count=len(articles),
            articles_text=articles_text,
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
                data = json.loads(text)

                if not isinstance(data.get("summary"), str) or len(data["summary"]) < 30:
                    raise ValueError("Summary too short")
                if data.get("sentiment") not in ("Bullish", "Bearish", "Neutral"):
                    raise ValueError(f"Invalid sentiment: {data.get('sentiment')}")

                return data

            except json.JSONDecodeError as e:
                logger.warning(f"JSON parse error for '{keyword}' (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    return None
            except Exception as e:
                logger.warning(f"Consolidation error for '{keyword}' (attempt {attempt + 1}): {e}")
                if attempt == 2:
                    return None
                await asyncio.sleep(2)

        return None
