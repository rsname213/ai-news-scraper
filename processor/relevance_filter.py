"""
Relevance filter — uses Claude Haiku (cheap/fast) to decide if an article
is relevant to the AI Pulse newsletter.
"""
import json
import logging

from processor.claude_client import ClaudeClient, MODEL_HAIKU, strip_markdown_fences
from scraper.models import RawArticle, RelevanceResult

logger = logging.getLogger(__name__)

_RELEVANCE_THRESHOLD = 0.6

_SYSTEM_PROMPT = """You are a strict editorial filter for "AI Pulse" — a weekly newsletter \
covering the AI industry for finance professionals and technology leaders.

Your job: decide if a news article is relevant to the AI industry.

RELEVANT topics (score 0.8–1.0):
- LLM releases, model benchmarks, AI research breakthroughs
- AI infrastructure, compute, chips (NVIDIA, TPUs, data centres)
- Enterprise AI adoption and deployments
- AI startups, VC funding rounds, acquisitions of AI companies
- AI regulation, government policy, international AI race
- AI disrupting SaaS companies — revenue impact, valuation compression, customer churn
- Public market reactions to AI: stock moves, analyst downgrades/upgrades driven by AI
- AI safety, alignment, ethics (major developments only)

RELEVANT topics (score 0.6–0.8):
- Software companies pivoting to or being disrupted by AI
- Earnings calls where AI is a primary driver of results
- Macro tech sector moves with a clear AI catalyst

NOT RELEVANT (score below 0.6):
- General tech news with no meaningful AI angle
- Cybersecurity unrelated to AI
- Pure finance/market stories with no AI connection
- Consumer electronics, gaming, social media (unless direct AI angle)
- Sports, entertainment, lifestyle

Respond ONLY with valid JSON, no markdown, no explanation:
{"relevant": true/false, "score": 0.0-1.0, "reason": "one sentence max"}"""


def _build_user_prompt(article: RawArticle) -> str:
    summary_snippet = article.summary[:400] if article.summary else "(no summary available)"
    return (
        f"Source: {article.source}\n"
        f"Title: {article.title}\n"
        f"Summary: {summary_snippet}"
    )


def _parse_result(raw: str, article_url: str) -> RelevanceResult:
    """Parse Claude's JSON response into a RelevanceResult. Handles malformed output."""
    try:
        data = json.loads(strip_markdown_fences(raw))
        return RelevanceResult(
            relevant=bool(data.get("relevant", False)),
            score=float(data.get("score", 0.0)),
            reason=str(data.get("reason", "")),
        )
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Could not parse relevance response for %s: %s | raw: %r", article_url, exc, raw[:200])
        # Conservative default: mark as not relevant if we can't parse
        return RelevanceResult(relevant=False, score=0.0, reason="parse error")


def filter_articles(
    articles: list[RawArticle],
    client: ClaudeClient,
) -> list[tuple[RawArticle, RelevanceResult]]:
    """
    Filter a list of articles for AI relevance using Claude Haiku.
    Returns only articles that pass the relevance threshold.
    """
    if not articles:
        return []

    # Build batch requests
    requests = [
        {
            "custom_id": article.url,
            "system": _SYSTEM_PROMPT,
            "user": _build_user_prompt(article),
        }
        for article in articles
    ]

    logger.info("Submitting %d articles for relevance filtering...", len(articles))
    raw_results = client.batch_complete(requests, model=MODEL_HAIKU, max_tokens=128)

    # Parse and filter
    passed: list[tuple[RawArticle, RelevanceResult]] = []
    for article in articles:
        raw = raw_results.get(article.url, "")
        result = _parse_result(raw, article.url)

        if result.relevant and result.score >= _RELEVANCE_THRESHOLD:
            passed.append((article, result))
        else:
            logger.debug("Filtered out: [%.2f] %s", result.score, article.title[:60])

    logger.info(
        "Relevance filter: %d/%d articles passed (threshold %.1f)",
        len(passed),
        len(articles),
        _RELEVANCE_THRESHOLD,
    )
    return passed
