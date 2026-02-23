import logging
from datetime import datetime, timedelta, timezone

from scraper.models import RawArticle
from storage.seen_articles import url_hash

logger = logging.getLogger(__name__)


def deduplicate(
    articles: list[RawArticle],
    seen_hashes: set[str],
    lookback_days: int = 7,
) -> list[RawArticle]:
    """
    Filter articles to only include:
    - Articles not already in seen_hashes
    - Articles published within the lookback window

    Returns the filtered list. Does NOT mutate seen_hashes — caller handles that.
    """
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=lookback_days)
    new_articles: list[RawArticle] = []
    skipped_seen = 0
    skipped_old = 0

    for article in articles:
        h = url_hash(article.url)
        if h in seen_hashes:
            skipped_seen += 1
            continue
        if article.pub_date < cutoff:
            skipped_old += 1
            continue
        new_articles.append(article)

    logger.info(
        "Deduplication: %d new | %d already seen | %d too old",
        len(new_articles),
        skipped_seen,
        skipped_old,
    )
    return new_articles
