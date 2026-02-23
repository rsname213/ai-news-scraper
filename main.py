"""
TOG AI Pulse — Main Pipeline

Fetches AI news from WSJ, Financial Times, The Information and TechCrunch, generates
editorial content with Claude, and delivers a 5-article weekly newsletter
every Monday morning.

Usage:
    python main.py              # Full run (send email if DRY_RUN=false)
    DRY_RUN=true python main.py # Generate newsletter but save to data/preview.html
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# ─── Logging setup (before any imports that log) ──────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("logs/run.log"),
    ],
)
logger = logging.getLogger("ai_pulse")

# ─── Pipeline imports ──────────────────────────────────────────────────────────
from config.feeds import FEEDS
from config.settings import Settings
from mailer import get_mailer
from processor.article_processor import process_articles
from processor.categoriser import categorise_articles
from processor.claude_client import ClaudeClient
from processor.disruption import generate_disruption_commentary
from processor.relevance_filter import filter_articles
from renderer.email_renderer import render, subject_line
from scraper.deduplicator import deduplicate
from scraper.feed_fetcher import fetch_all_feeds
from scraper.models import ProcessedArticle
from storage.seen_articles import load_seen, save_seen, url_hash

MAX_ARTICLES = 5  # Total articles in the newsletter


def run_pipeline(settings: Settings) -> int:
    """
    Execute the full TOG AI Pulse pipeline.
    Returns the number of articles included in the newsletter.
    """
    run_date = datetime.now(tz=timezone.utc)
    logger.info("━━━━ TOG AI Pulse run started: %s ━━━━", run_date.strftime("%Y-%m-%d %H:%M UTC"))

    # ── Step 1: Fetch RSS feeds ────────────────────────────────────────────────
    logger.info("Step 1: Fetching RSS feeds (WSJ, FT, The Information, TechCrunch)...")
    all_raw = fetch_all_feeds(FEEDS, theinformation_cookie=settings.theinformation_cookie)
    logger.info("Total raw articles: %d", len(all_raw))

    if not all_raw:
        logger.error("No articles fetched — all sources failed. Aborting.")
        return 0

    # ── Step 2: Deduplicate ────────────────────────────────────────────────────
    logger.info("Step 2: Deduplicating...")
    seen_hashes = load_seen()
    new_articles = deduplicate(all_raw, seen_hashes, lookback_days=settings.lookback_days)

    if not new_articles:
        logger.warning("No new articles after deduplication.")
        _send_quiet_week_notice(settings, run_date)
        return 0

    # ── Step 3: Relevance filter ───────────────────────────────────────────────
    logger.info("Step 3: Filtering for AI relevance via Claude...")
    client = ClaudeClient(api_key=settings.anthropic_api_key)
    relevant_pairs = filter_articles(new_articles, client)

    if not relevant_pairs:
        logger.warning("No articles passed relevance filter.")
        _send_quiet_week_notice(settings, run_date)
        return 0

    # Sort by relevance score and take top MAX_ARTICLES
    relevant_pairs.sort(key=lambda p: p[1].score, reverse=True)
    top_pairs = relevant_pairs[:MAX_ARTICLES]
    top_articles = [article for article, _ in top_pairs]
    relevance_results = {article.url: result for article, result in top_pairs}

    logger.info("Selected top %d articles from %d relevant", len(top_articles), len(relevant_pairs))

    # ── Step 4: Generate editorial content ────────────────────────────────────
    logger.info("Step 4: Writing editorial content via Claude Sonnet...")
    editorial_map = process_articles(top_articles, client)

    # ── Step 5: Categorise into sections ──────────────────────────────────────
    logger.info("Step 5: Categorising articles...")
    section_map = categorise_articles(top_articles, editorial_map, client)

    # ── Step 6: Build ProcessedArticle list ───────────────────────────────────
    processed: list[ProcessedArticle] = []
    for article in top_articles:
        one_liner, why = editorial_map.get(article.url, (article.title, ""))
        section = section_map.get(article.url, "AI Models & Infrastructure")
        rel = relevance_results.get(article.url)
        processed.append(
            ProcessedArticle(
                raw=article,
                is_relevant=True,
                relevance_score=rel.score if rel else 0.5,
                one_liner=one_liner,
                why_it_matters=why,
                section=section,
            )
        )

    # ── Step 7: Generate disruption commentary ────────────────────────────────
    logger.info("Step 7: Generating disruption commentary...")
    disruption_commentary = generate_disruption_commentary(processed, client)

    # ── Step 8: Render newsletter ──────────────────────────────────────────────
    logger.info("Step 8: Rendering newsletter...")
    html_body, text_body = render(processed, run_date=run_date, disruption_commentary=disruption_commentary)
    subject = subject_line(run_date=run_date)

    # ── Step 9: Send or preview ────────────────────────────────────────────────
    if settings.dry_run:
        preview_path = Path("data/preview.html")
        preview_path.write_text(html_body, encoding="utf-8")
        logger.info("DRY RUN — newsletter saved to %s", preview_path)
    else:
        logger.info("Step 9: Sending email to %s...", settings.recipient_email)
        mailer = get_mailer(settings)
        mailer.send(to=settings.recipient_email, subject=subject, html_body=html_body, text_body=text_body)
        logger.info("Email sent successfully")

    # ── Update seen articles ───────────────────────────────────────────────────
    new_hashes = {url_hash(a.url) for a in new_articles}
    save_seen(seen_hashes | new_hashes)

    logger.info("━━━━ Run complete: %d raw → %d relevant → %d in newsletter ━━━━",
                len(all_raw), len(relevant_pairs), len(processed))
    return len(processed)


def _send_quiet_week_notice(settings: Settings, run_date: datetime) -> None:
    if settings.dry_run:
        logger.info("DRY RUN — would send quiet week notice")
        return
    try:
        mailer = get_mailer(settings)
        date_str = run_date.strftime("%B %d, %Y")
        mailer.send(
            to=settings.recipient_email,
            subject=f"TOG AI Pulse — {date_str} (Quiet Week)",
            html_body=f'<html><body style="font-family: Aptos, Calibri, Arial, sans-serif; padding: 40px; color: #1a1a1a;"><p><strong>TOG AI Pulse — {date_str}</strong></p><p>No new AI stories surfaced from our sources this week.</p></body></html>',
            text_body=f"TOG AI Pulse — {date_str}\n\nNo new AI stories this week.",
        )
    except Exception as exc:
        logger.error("Could not send quiet week notice: %s", exc)


if __name__ == "__main__":
    try:
        settings = Settings.from_env()
        count = run_pipeline(settings)
        sys.exit(0 if count >= 0 else 1)
    except EnvironmentError as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.exception("Pipeline failed: %s", exc)
        try:
            settings = Settings.from_env()
            if not settings.dry_run:
                mailer = get_mailer(settings)
                mailer.send(
                    to=settings.recipient_email,
                    subject="TOG AI Pulse pipeline failure",
                    html_body=f"<p>The TOG AI Pulse pipeline failed this Monday.</p><p>Error: {exc}</p>",
                    text_body=f"TOG AI Pulse pipeline failure.\n\nError: {exc}",
                )
        except Exception:
            pass
        sys.exit(1)
