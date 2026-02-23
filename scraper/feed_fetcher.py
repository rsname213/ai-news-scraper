import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from typing import Optional

import feedparser
import requests

from scraper.models import FeedSource, RawArticle

logger = logging.getLogger(__name__)

# feedparser uses its own HTTP — patch User-Agent to avoid bot blocks
feedparser.USER_AGENT = (
    "AI-Pulse-Newsletter/1.0 (+https://github.com/ai-news-scraper)"
)

_TIMEOUT = 15  # seconds per feed request


def _parse_date(entry) -> datetime:
    """Extract a timezone-aware datetime from a feedparser entry."""
    for attr in ("published_parsed", "updated_parsed", "created_parsed"):
        t = getattr(entry, attr, None)
        if t:
            import time
            ts = time.mktime(t)
            return datetime.fromtimestamp(ts, tz=timezone.utc)
    return datetime.now(tz=timezone.utc)


def _fetch_feed(source: FeedSource, cookie: Optional[str] = None) -> list[RawArticle]:
    """Fetch and parse a single RSS feed. Returns [] on any error."""
    headers = {"User-Agent": feedparser.USER_AGENT}
    if cookie and "theinformation" in source.url:
        headers["Cookie"] = f"session={cookie}"

    try:
        # Use requests first to get the raw response so we can check status codes
        resp = requests.get(source.url, headers=headers, timeout=_TIMEOUT)

        if resp.status_code == 403 and source.skip_on_403:
            logger.warning("Skipping %s — 403 Forbidden (paywall)", source.name)
            return []

        if resp.status_code == 404:
            logger.warning("Skipping %s — 404 Not Found", source.name)
            return []

        if not resp.ok:
            logger.warning("Skipping %s — HTTP %d", source.name, resp.status_code)
            return []

        feed = feedparser.parse(resp.content)

    except requests.exceptions.Timeout:
        logger.warning("Timeout fetching %s", source.name)
        return []
    except requests.exceptions.RequestException as exc:
        logger.warning("Error fetching %s: %s", source.name, exc)
        return []

    articles: list[RawArticle] = []
    for entry in feed.entries:
        title = getattr(entry, "title", "").strip()
        url = getattr(entry, "link", "").strip()
        if not title or not url:
            continue

        # Prefer content > summary > description for article text
        summary = ""
        if hasattr(entry, "content") and entry.content:
            summary = entry.content[0].get("value", "")
        if not summary:
            summary = getattr(entry, "summary", "") or getattr(entry, "description", "")

        # Strip HTML tags from summary
        summary = _strip_html(summary)[:1000]  # cap at 1000 chars

        articles.append(
            RawArticle(
                title=title,
                url=url,
                summary=summary,
                source=source.name,
                pub_date=_parse_date(entry),
                content_available=not source.paywall,
            )
        )

    logger.info("Fetched %d articles from %s", len(articles), source.name)
    return articles


def _strip_html(text: str) -> str:
    """Remove HTML tags from a string."""
    import re
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean


def fetch_all_feeds(
    sources: list[FeedSource],
    theinformation_cookie: Optional[str] = None,
    max_workers: int = 8,
) -> list[RawArticle]:
    """
    Fetch all feeds in parallel. Returns a combined flat list of RawArticles.
    Errors on individual feeds are logged and skipped — never crashes the pipeline.
    """
    all_articles: list[RawArticle] = []

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_source = {
            executor.submit(_fetch_feed, source, theinformation_cookie): source
            for source in sources
        }
        for future in as_completed(future_to_source):
            source = future_to_source[future]
            try:
                articles = future.result()
                all_articles.extend(articles)
            except Exception as exc:
                logger.error("Unexpected error fetching %s: %s", source.name, exc)

    logger.info("Total raw articles fetched: %d", len(all_articles))
    return all_articles
