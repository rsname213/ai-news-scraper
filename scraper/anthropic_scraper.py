"""
Anthropic news scraper.
Anthropic doesn't publish an RSS feed, so we scrape their news listing page directly.
"""
import logging
from datetime import datetime, timezone

import requests
from bs4 import BeautifulSoup

from scraper.models import RawArticle

logger = logging.getLogger(__name__)

_URL = "https://www.anthropic.com/news"
_TIMEOUT = 15
_HEADERS = {
    "User-Agent": "AI-Pulse-Newsletter/1.0 (+https://github.com/ai-news-scraper)"
}


def fetch_anthropic_articles() -> list[RawArticle]:
    """
    Scrape the Anthropic news listing page and return RawArticle objects.
    Returns [] on any error — never crashes the pipeline.
    """
    try:
        resp = requests.get(_URL, headers=_HEADERS, timeout=_TIMEOUT)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        logger.warning("Could not fetch Anthropic news page: %s", exc)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles: list[RawArticle] = []

    # Anthropic's news page uses article cards — find all <a> tags that link to /news/
    seen_urls: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = link["href"]
        # Only grab links to individual news articles
        if not href.startswith("/news/") or href == "/news/":
            continue

        full_url = f"https://www.anthropic.com{href}"
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # Try to extract title from the link text or nearby heading
        title = link.get_text(strip=True)
        if not title or len(title) < 10:
            # Look for a heading inside or near the link
            heading = link.find(["h1", "h2", "h3", "h4"])
            if heading:
                title = heading.get_text(strip=True)

        if not title or len(title) < 10:
            continue

        # Look for a description paragraph near the link
        parent = link.parent
        summary = ""
        if parent:
            p_tags = parent.find_all("p")
            if p_tags:
                summary = " ".join(p.get_text(strip=True) for p in p_tags[:2])

        articles.append(
            RawArticle(
                title=title,
                url=full_url,
                summary=summary[:500],
                source="Anthropic",
                pub_date=datetime.now(tz=timezone.utc),  # Date not always available
                content_available=True,
            )
        )

    logger.info("Fetched %d articles from Anthropic", len(articles))
    return articles
