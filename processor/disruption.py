"""
Generates the "Where is the disruption this week?" closing commentary
for the TOG AI Pulse newsletter, focused on SaaS disruption trends.
"""
import logging

from processor.claude_client import ClaudeClient, MODEL_SONNET, strip_markdown_fences
from scraper.models import ProcessedArticle

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are the editor of "TOG AI Pulse". Write a short, sharp commentary \
paragraph for the "Where is the disruption this week?" section of the newsletter. \
Focus on which SaaS categories, business models or incumbents are being most visibly \
disrupted by the AI stories in this issue. Be specific and opinionated. \
Formal but not stuffy, witty but not glib. 3-4 sentences maximum. \
No em dashes. No Oxford commas. No markdown, no headers, plain text only."""


def generate_disruption_commentary(
    articles: list[ProcessedArticle],
    client: ClaudeClient,
) -> str:
    """
    Generate the weekly disruption commentary based on the issue's articles.
    Returns a plain-text paragraph.
    """
    if not articles:
        return ""

    article_summaries = "\n".join(
        f"- {a.raw.title} ({a.raw.source}): {a.one_liner}"
        for a in articles
    )

    user_prompt = (
        "This week's TOG AI Pulse articles:\n"
        f"{article_summaries}\n\n"
        "Based on these stories, write the 'Where is the disruption this week?' paragraph."
    )

    try:
        raw = client.complete(
            system=_SYSTEM_PROMPT,
            user=user_prompt,
            model=MODEL_SONNET,
            max_tokens=300,
        )
        return strip_markdown_fences(raw).strip()
    except Exception as exc:
        logger.error("Failed to generate disruption commentary: %s", exc)
        return ""
