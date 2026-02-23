"""
run_local.py — Test the scraper pipeline without spending Claude credits.

Usage:
    python run_local.py

Prints a table of fetched articles by source. Useful for validating
RSS feeds are working before running the full pipeline.
"""
import logging
import sys

from config.feeds import FEEDS
from config.settings import Settings
from scraper.anthropic_scraper import fetch_anthropic_articles
from scraper.deduplicator import deduplicate
from scraper.feed_fetcher import fetch_all_feeds
from storage.seen_articles import load_seen

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    stream=sys.stdout,
)

try:
    settings = Settings.from_env()
except EnvironmentError:
    # For local scraper testing, we only need optional env vars
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {
        "ANTHROPIC_API_KEY": "test",
        "GMAIL_ADDRESS": "test@test.com",
        "GMAIL_APP_PASSWORD": "test",
        "RECIPIENT_EMAIL": "test@test.com",
    }):
        settings = Settings.from_env()

print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print(" AI PULSE ► Scraper Test")
print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

# Fetch all RSS feeds
print("Fetching RSS feeds...")
rss_articles = fetch_all_feeds(
    FEEDS,
    theinformation_cookie=settings.theinformation_cookie,
)

# Fetch Anthropic separately (no RSS)
print("Fetching Anthropic blog...")
anthropic_articles = fetch_anthropic_articles()

all_articles = rss_articles + anthropic_articles

# Deduplicate
seen = load_seen()
new_articles = deduplicate(all_articles, seen, lookback_days=settings.lookback_days)

# Print results by source
from collections import Counter
source_counts_raw = Counter(a.source for a in all_articles)
source_counts_new = Counter(a.source for a in new_articles)

print(f"\n{'SOURCE':<30} {'RAW':>5} {'NEW':>5}")
print("─" * 42)
for source in sorted(source_counts_raw):
    raw = source_counts_raw[source]
    new = source_counts_new.get(source, 0)
    print(f"{source:<30} {raw:>5} {new:>5}")

print("─" * 42)
print(f"{'TOTAL':<30} {len(all_articles):>5} {len(new_articles):>5}")

print(f"\n✓ {len(new_articles)} new articles ready for processing")

# Print a sample of new articles
if new_articles:
    print("\nSample articles (first 10):\n")
    for i, a in enumerate(new_articles[:10], 1):
        date_str = a.pub_date.strftime("%b %d")
        title_short = a.title[:70] + "…" if len(a.title) > 70 else a.title
        print(f"  {i:>2}. [{date_str}] {a.source}: {title_short}")
