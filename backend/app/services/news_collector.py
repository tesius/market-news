import asyncio
from datetime import datetime, timedelta
from html import unescape
from typing import Any

import feedparser
import httpx
from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Article, Keyword, Region
from app.services.article_scraper import extract_article_body

MAX_PER_KEYWORD = 10


class NewsCollector:
    """Multi-source news collector with Finnhub (primary) + RSS (fallback) for US,
    and Naver Search API for KR news."""

    FINNHUB_BASE = "https://finnhub.io/api/v1"
    NAVER_BASE = "https://openapi.naver.com/v1/search/news.json"

    RSS_FEEDS = [
        {
            "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258",
            "source": "CNBC",
        },
        {
            "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10001147",
            "source": "CNBC Tech",
        },
    ]

    KEYWORD_ALIASES: dict[str, list[str]] = {
        "us stock market": ["s&p", "nasdaq", "dow jones", "wall street", "stock market", "equities"],
        "federal reserve": ["fed", "fomc", "interest rate", "powell", "monetary policy"],
        "semiconductor": ["chip", "nvidia", "tsmc", "intel", "hbm", "semiconductor"],
        "artificial intelligence": ["ai ", "openai", "chatgpt", "llm", "generative ai", "machine learning"],
    }

    def __init__(self, db: AsyncSession):
        self.db = db

    async def collect_for_keyword(self, keyword: Keyword) -> list[dict[str, Any]]:
        """Collect news for a single keyword, then scrape article bodies."""
        try:
            if keyword.region == Region.US:
                articles = await self._collect_us_news(keyword)
            else:
                articles = await self._collect_kr_news(keyword)

            new_articles = await self._deduplicate_and_save(articles)
            logger.info(
                f"Collected {len(new_articles)} new articles for '{keyword.topic}' ({keyword.region.value})"
            )

            if new_articles:
                await self._scrape_bodies()

            return new_articles
        except Exception as e:
            logger.error(f"Failed to collect news for '{keyword.topic}': {e}")
            return []

    async def collect_all(self) -> list[dict[str, Any]]:
        """Collect news for all active keywords, then scrape article bodies."""
        result = await self.db.execute(
            select(Keyword).where(Keyword.is_active.is_(True))
        )
        keywords = result.scalars().all()

        all_articles: list[dict[str, Any]] = []

        for keyword in keywords:
            try:
                if keyword.region == Region.US:
                    articles = await self._collect_us_news(keyword)
                else:
                    articles = await self._collect_kr_news(keyword)

                new_articles = await self._deduplicate_and_save(articles)
                all_articles.extend(new_articles)
                logger.info(
                    f"Collected {len(new_articles)} new articles for '{keyword.topic}' ({keyword.region.value})"
                )
            except Exception as e:
                logger.error(f"Failed to collect news for '{keyword.topic}': {e}")

        # Scrape article bodies for newly saved articles
        if all_articles:
            await self._scrape_bodies()

        return all_articles

    async def _scrape_bodies(self):
        """Scrape article bodies for articles that don't have one yet."""
        result = await self.db.execute(
            select(Article)
            .where(Article.raw_snippet.is_(None) | (Article.raw_snippet == ""))
            .order_by(Article.created_at.desc())
            .limit(MAX_PER_KEYWORD * 10)
        )
        no_body = result.scalars().all()

        # Also scrape articles with very short snippets
        result2 = await self.db.execute(
            select(Article)
            .where(
                Article.ai_summary.is_(None),
                Article.raw_snippet.isnot(None),
            )
            .order_by(Article.created_at.desc())
            .limit(MAX_PER_KEYWORD * 10)
        )
        short_snippet = result2.scalars().all()

        to_scrape = {a.id: a for a in list(no_body) + list(short_snippet)}
        if not to_scrape:
            return

        logger.info(f"Scraping bodies for {len(to_scrape)} articles...")
        updated = 0
        for article in to_scrape.values():
            body = await extract_article_body(article.link)
            if body:
                # Append body to existing snippet or replace
                if article.raw_snippet and len(article.raw_snippet) > 50:
                    article.raw_snippet = article.raw_snippet + "\n\n" + body
                else:
                    article.raw_snippet = body
                updated += 1
            # Small delay to avoid hammering
            await asyncio.sleep(0.5)

        if updated:
            await self.db.commit()
            logger.info(f"Scraped bodies for {updated} articles")

    def _get_search_terms(self, topic: str) -> list[str]:
        """Get expanded search terms for a keyword topic."""
        topic_lower = topic.lower()
        aliases = self.KEYWORD_ALIASES.get(topic_lower, [])
        return [topic_lower] + aliases

    async def _collect_us_news(self, keyword: Keyword) -> list[dict[str, Any]]:
        """Collect US news: try Finnhub first, fallback to RSS."""
        try:
            return await self._fetch_finnhub(keyword)
        except Exception as e:
            logger.warning(f"Finnhub failed for '{keyword.topic}': {e}, falling back to RSS")
            return await self._fetch_rss(keyword)

    async def _fetch_finnhub(self, keyword: Keyword) -> list[dict[str, Any]]:
        """Fetch news from Finnhub API."""
        if not settings.finnhub_api_key:
            raise ValueError("Finnhub API key not configured")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{self.FINNHUB_BASE}/news",
                params={
                    "category": "general",
                    "minId": 0,
                    "token": settings.finnhub_api_key,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        articles = []
        search_terms = self._get_search_terms(keyword.topic)

        for item in data:
            headline = item.get("headline", "")
            summary = item.get("summary", "")
            text_lower = f"{headline} {summary}".lower()

            if not any(term in text_lower for term in search_terms):
                continue

            articles.append({
                "title": headline,
                "link": item.get("url", ""),
                "published_at": datetime.fromtimestamp(item.get("datetime", 0)),
                "source_name": item.get("source", "Finnhub"),
                "region": Region.US,
                "raw_snippet": summary[:500] if summary else None,
                "keyword_tag": keyword.topic,
            })

        return articles[:MAX_PER_KEYWORD]

    async def _fetch_rss(self, keyword: Keyword) -> list[dict[str, Any]]:
        """Fetch news from RSS feeds as fallback."""
        articles = []

        for feed_info in self.RSS_FEEDS:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.get(feed_info["url"])
                    resp.raise_for_status()

                feed = feedparser.parse(resp.text)
                search_terms = self._get_search_terms(keyword.topic)

                for entry in feed.entries:
                    title = entry.get("title", "")
                    summary = entry.get("summary", "")
                    text_lower = f"{title} {summary}".lower()

                    if not any(term in text_lower for term in search_terms):
                        continue

                    published = None
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])

                    articles.append({
                        "title": unescape(title),
                        "link": entry.get("link", ""),
                        "published_at": published,
                        "source_name": feed_info["source"],
                        "region": Region.US,
                        "raw_snippet": unescape(summary)[:500] if summary else None,
                        "keyword_tag": keyword.topic,
                    })
            except Exception as e:
                logger.warning(f"RSS feed {feed_info['source']} failed: {e}")

        return articles[:MAX_PER_KEYWORD]

    async def _collect_kr_news(self, keyword: Keyword) -> list[dict[str, Any]]:
        """Collect KR news from Naver Search API."""
        if not settings.naver_client_id or not settings.naver_client_secret:
            logger.warning("Naver API credentials not configured, skipping KR news")
            return []

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                self.NAVER_BASE,
                params={
                    "query": keyword.topic,
                    "display": MAX_PER_KEYWORD,
                    "sort": "sim",
                },
                headers={
                    "X-Naver-Client-Id": settings.naver_client_id,
                    "X-Naver-Client-Secret": settings.naver_client_secret,
                },
            )
            resp.raise_for_status()
            data = resp.json()

        articles = []
        for item in data.get("items", []):
            title = unescape(item.get("title", "")).replace("<b>", "").replace("</b>", "")
            description = unescape(item.get("description", "")).replace("<b>", "").replace("</b>", "")

            pub_date = None
            if item.get("pubDate"):
                try:
                    pub_date = datetime.strptime(item["pubDate"], "%a, %d %b %Y %H:%M:%S %z")
                except ValueError:
                    pass

            articles.append({
                "title": title,
                "link": item.get("originallink") or item.get("link", ""),
                "published_at": pub_date,
                "source_name": self._extract_source(item.get("originallink", "")),
                "region": Region.KR,
                "raw_snippet": description[:500] if description else None,
                "keyword_tag": keyword.topic,
            })

        return articles

    async def _deduplicate_and_save(self, articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Save articles to DB, skipping duplicates by link."""
        new_articles = []

        for article_data in articles:
            link = article_data.get("link", "")
            if not link:
                continue

            existing = await self.db.execute(
                select(Article.id).where(Article.link == link)
            )
            if existing.scalar_one_or_none() is not None:
                continue

            article = Article(**article_data)
            self.db.add(article)
            new_articles.append(article_data)

        if new_articles:
            await self.db.commit()

        return new_articles

    @staticmethod
    def _extract_source(url: str) -> str:
        """Extract source name from URL domain."""
        try:
            from urllib.parse import urlparse
            domain = urlparse(url).netloc
            domain = domain.replace("www.", "")
            parts = domain.split(".")
            return parts[0].capitalize() if parts else "Unknown"
        except Exception:
            return "Unknown"
