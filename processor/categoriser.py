"""
Categoriser — uses Claude Haiku to assign each article to one of the 5 newsletter sections.
"""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from config.feeds import SECTIONS
from processor.claude_client import ClaudeClient, MODEL_HAIKU
from scraper.models import RawArticle

logger = logging.getLogger(__name__)

_VALID_SECTIONS = set(SECTIONS)

_SYSTEM_PROMPT = f"""You are categorising articles for "AI Pulse" newsletter sections.
Assign each article to EXACTLY ONE of these sections:

{chr(10).join(f'- {s}' for s in SECTIONS)}

Section guidance:
- "AI Models & Infrastructure": New LLM releases, model benchmarks, research breakthroughs, \
training techniques, AI labs announcements, compute/chip news (NVIDIA, TPUs), AI infrastructure
- "Enterprise Adoption": Fortune 500 AI deployments, enterprise software with AI features, \
B2B AI tools, productivity and workflow automation
- "Startups & Funding": New AI companies, seed/Series rounds, VC activity, acqui-hires, \
exits, AI-native startup ecosystem
- "Policy & Regulation": Government AI policy, regulation bills, international AI treaties, \
AI safety bodies, ethics frameworks
- "AI Impact on SaaS in Public Markets": AI's effect on public SaaS company valuations, \
software sector disruption, commoditisation of software, analyst reports on AI market impact, \
public company earnings affected by AI, stock movements driven by AI disruption

Respond with ONLY the section name, exactly as written above. No punctuation, no explanation."""


def _categorise_one(
    article: RawArticle,
    why_it_matters: str,
    client: ClaudeClient,
) -> tuple[str, str]:
    """Returns (article.url, section_name)."""
    user_prompt = (
        f"Title: {article.title}\n"
        f"Source: {article.source}\n"
        f"Summary: {article.summary[:300]}\n"
        f"Why it matters: {why_it_matters[:200]}"
    )
    raw = client.complete(
        system=_SYSTEM_PROMPT,
        user=user_prompt,
        model=MODEL_HAIKU,
        max_tokens=32,
    )
    section = raw.strip()

    # Validate the response
    if section not in _VALID_SECTIONS:
        # Try to find a partial match
        for valid in SECTIONS:
            if valid.lower() in section.lower() or section.lower() in valid.lower():
                section = valid
                break
        else:
            logger.warning("Invalid section '%s' for '%s' — defaulting to Models & Capabilities", section, article.title[:50])
            section = SECTIONS[0]

    return article.url, section


def categorise_articles(
    articles: list[RawArticle],
    editorial_map: dict[str, tuple[str, str]],  # url → (one_liner, why_it_matters)
    client: ClaudeClient,
    max_workers: int = 5,
) -> dict[str, str]:
    """
    Categorise articles into newsletter sections.
    Returns dict mapping article.url → section_name.
    """
    if not articles:
        return {}

    logger.info("Categorising %d articles into sections...", len(articles))
    results: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(
                _categorise_one,
                article,
                editorial_map.get(article.url, ("", ""))[1],  # why_it_matters
                client,
            ): article.url
            for article in articles
        }
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                _, section = future.result()
                results[url] = section
            except Exception as exc:
                logger.error("Failed to categorise %s: %s", url, exc)
                results[url] = SECTIONS[0]  # Safe default

    logger.info("Categorisation complete")
    return results
