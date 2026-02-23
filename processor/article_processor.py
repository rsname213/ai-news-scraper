"""
Article processor — uses Claude Sonnet to write the editorial content for each article:
  - one_liner: a sharp, declarative 1-sentence summary
  - why_it_matters: 2-3 sentences of witty, insightful commentary
"""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from processor.claude_client import ClaudeClient, MODEL_SONNET, strip_markdown_fences
from scraper.models import RawArticle, RelevanceResult

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the editor of "TOG AI Pulse" — a weekly newsletter read by finance \
professionals and technology executives. Your voice: formal but not stuffy, witty but not \
glib, insightful but concise.

Style rules you must follow without exception:
- No em dashes. Use a comma or a new sentence instead.
- No Oxford commas.
- Write dollar amounts as $Xm (millions) or $Xbn (billions). Example: $500m, $1.2bn.
- Do not use the word "delve" or "crucial" or "game-changing".
- Respond with valid JSON ONLY. No markdown code fences, no text outside the JSON.

{
  "one_liner": "A single declarative sentence, maximum 25 words. \
Written for someone who already knows the AI industry. No hedging. State what happened.",
  "why_it_matters": "2-3 sentences on why this story matters. \
One dry observation is welcome. End with a specific implication for investors or practitioners."
}"""


def _build_user_prompt(article: RawArticle) -> str:
    summary = article.summary[:600] if article.summary else "(headline only — no summary available)"
    date_str = article.pub_date.strftime("%B %d, %Y")
    return (
        f"Source: {article.source}\n"
        f"Title: {article.title}\n"
        f"Published: {date_str}\n"
        f"Summary: {summary}"
    )


def _parse_result(raw: str, title: str) -> tuple[str, str]:
    """Parse Claude's JSON response. Returns (one_liner, why_it_matters) with fallbacks."""
    try:
        data = json.loads(strip_markdown_fences(raw))
        one_liner = str(data.get("one_liner", "")).strip()
        why = str(data.get("why_it_matters", "")).strip()
        if one_liner and why:
            return one_liner, why
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Could not parse article processor response for '%s': %s", title[:50], exc)

    # Fallback: use a safe placeholder rather than crashing
    return (
        f"{title}",
        "Editorial commentary could not be generated for this article.",
    )


def _process_one(
    article: RawArticle,
    client: ClaudeClient,
) -> tuple[RawArticle, str, str]:
    """Process a single article. Returns (article, one_liner, why_it_matters)."""
    raw = client.complete(
        system=_SYSTEM_PROMPT,
        user=_build_user_prompt(article),
        model=MODEL_SONNET,
        max_tokens=400,
    )
    one_liner, why = _parse_result(raw, article.title)
    return article, one_liner, why


def process_articles(
    articles: list[RawArticle],
    client: ClaudeClient,
    max_workers: int = 5,
) -> dict[str, tuple[str, str]]:
    """
    Generate editorial content for a list of articles in parallel.
    Returns dict mapping article.url → (one_liner, why_it_matters).
    """
    if not articles:
        return {}

    logger.info("Generating editorial content for %d articles...", len(articles))
    results: dict[str, tuple[str, str]] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_article = {
            executor.submit(_process_one, article, client): article
            for article in articles
        }
        for future in as_completed(future_to_article):
            article = future_to_article[future]
            try:
                _, one_liner, why = future.result()
                results[article.url] = (one_liner, why)
                logger.debug("Processed: %s", article.title[:60])
            except Exception as exc:
                logger.error("Failed to process '%s': %s", article.title[:50], exc)
                results[article.url] = (article.title, "Editorial commentary unavailable.")

    logger.info("Editorial generation complete: %d/%d articles", len(results), len(articles))
    return results
