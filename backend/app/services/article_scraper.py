import asyncio

import httpx
from bs4 import BeautifulSoup
from loguru import logger


async def extract_article_body(url: str, timeout: float = 10.0) -> str | None:
    """Extract main text content from an article URL."""
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            },
        ) as client:
            resp = await client.get(url)
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "lxml")

        # Remove non-content elements
        for tag in soup.find_all(["script", "style", "nav", "header", "footer", "aside", "iframe", "form"]):
            tag.decompose()

        # Try common article selectors
        article_el = (
            soup.find("article")
            or soup.find(attrs={"role": "article"})
            or soup.find(class_=lambda c: c and any(
                x in str(c).lower() for x in ["article-body", "story-body", "post-content", "entry-content"]
            ))
        )

        if article_el:
            paragraphs = article_el.find_all("p")
        else:
            # Fallback: collect all <p> tags from body
            paragraphs = soup.find_all("p")

        text_parts = []
        for p in paragraphs:
            text = p.get_text(strip=True)
            # Skip very short paragraphs (likely UI elements)
            if len(text) > 40:
                text_parts.append(text)

        body = "\n\n".join(text_parts)

        # Truncate to ~2000 chars to stay within token limits
        if len(body) > 2000:
            body = body[:2000] + "..."

        return body if len(body) > 100 else None

    except Exception as e:
        logger.debug(f"Failed to scrape {url}: {e}")
        return None
