"""
Renders the TOG AI Pulse newsletter into HTML and plain-text strings
using Jinja2 templates.
"""
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from config.feeds import SECTIONS, SECTION_COLOURS
from scraper.models import ProcessedArticle

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _build_context(
    articles: list[ProcessedArticle],
    run_date: datetime | None = None,
    disruption_commentary: str = "",
) -> dict:
    """Build the Jinja2 template context from processed articles."""
    if run_date is None:
        run_date = datetime.now(tz=timezone.utc)

    week_start = run_date - timedelta(days=7)

    edition_date = run_date.strftime("%B %d, %Y")
    week_range = f"{week_start.strftime('%b %d')} – {run_date.strftime('%b %d, %Y')}"

    # Group articles by section (maintaining SECTIONS order)
    section_map: dict[str, list[dict]] = {s: [] for s in SECTIONS}

    for article in articles:
        section = article.section
        if section not in section_map:
            section = SECTIONS[0]  # Safe fallback

        section_map[section].append({
            "title": article.raw.title,
            "url": article.raw.url,
            "source": article.raw.source,
            "pub_date": article.raw.pub_date.strftime("%b %d"),
            "one_liner": article.one_liner,
            "why_it_matters": article.why_it_matters,
        })

    # Sort within each section by relevance score (best first)
    article_score_map = {a.raw.url: a.relevance_score for a in articles}
    for section_articles in section_map.values():
        section_articles.sort(
            key=lambda a: article_score_map.get(a["url"], 0.0),
            reverse=True,
        )

    sections = [
        {
            "name": name,
            "colour": SECTION_COLOURS[name],
            "articles": section_map[name],
        }
        for name in SECTIONS
    ]

    return {
        "edition_date": edition_date,
        "week_range": week_range,
        "total_articles": len(articles),
        "sections": sections,
        "disruption_commentary": disruption_commentary,
    }


def render(
    articles: list[ProcessedArticle],
    run_date: datetime | None = None,
    disruption_commentary: str = "",
) -> tuple[str, str]:
    """
    Render the newsletter.

    Returns (html_body, text_body) as strings.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html"]),
    )

    context = _build_context(articles, run_date, disruption_commentary)

    html_template = env.get_template("newsletter.html.j2")
    # Plain text doesn't need autoescape
    txt_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))
    txt_template = txt_env.get_template("newsletter.txt.j2")

    html_body = html_template.render(**context)
    text_body = txt_template.render(**context)

    logger.info(
        "Rendered newsletter: %d articles, %d sections with content",
        len(articles),
        sum(1 for s in context["sections"] if s["articles"]),
    )

    return html_body, text_body


def subject_line(run_date: datetime | None = None) -> str:
    """Generate the email subject line."""
    if run_date is None:
        run_date = datetime.now(tz=timezone.utc)
    return f"TOG AI Pulse — {run_date.strftime('%B %d, %Y')}"
