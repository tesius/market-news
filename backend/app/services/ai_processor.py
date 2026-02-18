import asyncio
import json
from datetime import datetime
from collections import defaultdict

from google import genai
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Article, TopicSummary, Sentiment

CONSOLIDATION_PROMPT = """You are a senior financial journalist writing a consolidated briefing for a Korean quant developer.

Topic keyword: {keyword} ({region})
Below are {count} news articles collected under this keyword:

{articles_text}

IMPORTANT: These articles share the same search keyword but may cover DIFFERENT stories.
Your first task is to cluster articles by actual topic similarity based on their titles and content.
- Articles about the same event/development should be grouped together.
- Articles about unrelated stories must be separated into different sections.
- If all articles genuinely cover the same story, return a single section.

For EACH cluster, write a separate section:
1. "headline": Korean headline (max 60 chars) capturing that cluster's key narrative.
2. "summary": Detailed Korean summary (6-10 sentences, magazine-style).
   - Split into 2-3 short paragraphs using "\\n\\n" between them.
   - Paragraph 1: Core facts and key developments.
   - Paragraph 2: Context, conflicting viewpoints, and why it matters.
   - Paragraph 3: Market outlook and investor implications.
   - Each paragraph should be 2-4 sentences.
3. "sentiment": "Bullish", "Bearish", or "Neutral" for that cluster.
4. "tickers": Relevant stock tickers mentioned in that cluster.
5. "article_indices": Which article numbers (from the list above) belong to this cluster.

Return ONLY valid JSON:
{{
  "sections": [
    {{
      "headline": "첫 번째 토픽 헤드라인",
      "summary": "첫 번째 문단.\\n\\n두 번째 문단.\\n\\n세 번째 문단.",
      "sentiment": "Bullish",
      "tickers": ["NVDA"],
      "article_indices": [1, 3, 5]
    }},
    {{
      "headline": "두 번째 토픽 헤드라인",
      "summary": "첫 번째 문단.\\n\\n두 번째 문단.\\n\\n세 번째 문단.",
      "sentiment": "Bearish",
      "tickers": ["AAPL"],
      "article_indices": [2, 4]
    }}
  ]
}}"""


class AIProcessor:
    """Process articles by keyword - consolidate multiple articles into one summary per topic."""

    def __init__(self):
        self.client = genai.Client(api_key=settings.gemini_api_key)

    async def process_keyword(self, db: AsyncSession, batch_id: str, keyword_tag: str) -> bool:
        """Generate consolidated summaries for a single keyword's unprocessed articles."""
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
        sections = await self._consolidate_articles(keyword_tag, region, articles)

        if not sections:
            return False

        for section in sections:
            # Map article_indices back to actual articles
            indices = section.get("article_indices", [])
            section_articles = [articles[i - 1] for i in indices if 1 <= i <= len(articles)]
            if not section_articles:
                section_articles = articles  # fallback: assign all

            source_refs = [
                {"id": a.id, "title": a.title, "link": a.link, "source": a.source_name}
                for a in section_articles
            ]

            topic_summary = TopicSummary(
                keyword_tag=keyword_tag,
                region=region,
                batch_id=batch_id,
                headline=section.get("headline", keyword_tag),
                summary=section["summary"],
                sentiment=Sentiment(section["sentiment"]),
                related_tickers=json.dumps(section.get("tickers", [])),
                source_articles=json.dumps(source_refs, ensure_ascii=False),
                article_count=len(section_articles),
            )
            db.add(topic_summary)

        for a in articles:
            a.ai_summary = "consolidated"

        await db.commit()
        logger.info(f"Consolidated {len(articles)} articles for '{keyword_tag}' -> {len(sections)} sections")
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
                sections = await self._consolidate_articles(keyword_tag, region, group_articles)

                if sections:
                    for section in sections:
                        # Map article_indices back to actual articles
                        indices = section.get("article_indices", [])
                        section_articles = [group_articles[i - 1] for i in indices if 1 <= i <= len(group_articles)]
                        if not section_articles:
                            section_articles = group_articles  # fallback: assign all

                        source_refs = [
                            {
                                "id": a.id,
                                "title": a.title,
                                "link": a.link,
                                "source": a.source_name,
                            }
                            for a in section_articles
                        ]

                        topic_summary = TopicSummary(
                            keyword_tag=keyword_tag,
                            region=region,
                            batch_id=batch_id,
                            headline=section.get("headline", keyword_tag),
                            summary=section["summary"],
                            sentiment=Sentiment(section["sentiment"]),
                            related_tickers=json.dumps(section.get("tickers", [])),
                            source_articles=json.dumps(source_refs, ensure_ascii=False),
                            article_count=len(section_articles),
                        )
                        db.add(topic_summary)

                    # Mark individual articles as processed
                    for a in group_articles:
                        a.ai_summary = "consolidated"

                    processed += len(sections)
                    logger.info(
                        f"Consolidated {len(group_articles)} articles for '{keyword_tag}' -> {len(sections)} sections"
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
    ) -> list[dict] | None:
        """Send all articles for a keyword to Gemini for consolidated analysis.

        Returns a list of section dicts, each with headline/summary/sentiment/tickers/article_indices.
        """
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

                sections = data.get("sections", [])
                if not isinstance(sections, list) or len(sections) == 0:
                    raise ValueError("No sections returned")

                # Validate each section
                for section in sections:
                    if not isinstance(section.get("summary"), str) or len(section["summary"]) < 30:
                        raise ValueError(f"Section summary too short: {section.get('headline', '?')}")
                    if section.get("sentiment") not in ("Bullish", "Bearish", "Neutral"):
                        raise ValueError(f"Invalid sentiment: {section.get('sentiment')}")

                return sections

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
