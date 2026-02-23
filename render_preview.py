"""
render_preview.py — Generate a preview newsletter using sample data.

Usage:
    python render_preview.py
    # Then open data/preview.html in your browser
"""
from datetime import datetime, timezone
from pathlib import Path

from renderer.email_renderer import render, subject_line
from scraper.models import ProcessedArticle, RawArticle


def _make_article(title, url, source, section, one_liner, why, score=0.9):
    raw = RawArticle(
        title=title,
        url=url,
        summary="",
        source=source,
        pub_date=datetime.now(tz=timezone.utc),
        content_available=False,
    )
    return ProcessedArticle(
        raw=raw,
        is_relevant=True,
        relevance_score=score,
        one_liner=one_liner,
        why_it_matters=why,
        section=section,
    )


SAMPLE_ARTICLES = [
    _make_article(
        title="OpenAI Raises $40bn at $340bn Valuation in SoftBank-Led Round",
        url="https://www.wsj.com/tech/ai/openai-funding",
        source="Wall Street Journal",
        section="Startups & Funding",
        one_liner="OpenAI closed a $40bn funding round led by SoftBank, making it the most valuable private company in the world.",
        why="The round cements OpenAI's position at the top of the AI stack for at least another cycle. SoftBank's involvement is a reminder that the Vision Fund's appetite for outsized bets did not die with WeWork. For enterprise buyers, the valuation matters less than the signal: OpenAI is not running out of runway anytime soon.",
    ),
    _make_article(
        title="Google Acquires AI Startup Character.AI for $2.7bn",
        url="https://www.ft.com/content/google-character-ai",
        source="Financial Times",
        section="Startups & Funding",
        one_liner="Google agreed to acquire Character.AI for $2.7bn, adding a consumer AI platform with 20 million daily active users.",
        why="Consumer AI retention is the problem nobody has solved cleanly yet. Character.AI's numbers suggest emotional engagement drives stickiness in a way that productivity tools have not. For Microsoft and Apple this is a reminder that Google is willing to pay for distribution it cannot build organically.",
        score=0.88,
    ),
    _make_article(
        title="Anthropic Signs $3bn Enterprise Deal with Accenture",
        url="https://www.theinformation.com/articles/anthropic-accenture",
        source="The Information",
        section="Enterprise Adoption",
        one_liner="Anthropic signed a $3bn multi-year contract with Accenture to deploy Claude across the consulting firm's client base.",
        why="Professional services firms are the distribution layer for enterprise AI adoption in regulated industries. A $3bn commitment from Accenture is less about Accenture's own AI use and more about which model gets deployed at their clients in financial services, healthcare and government. This is a channel deal masquerading as a product deal.",
        score=0.92,
    ),
    _make_article(
        title="EU AI Act Fines Come Into Force: What Changes on August 2",
        url="https://www.ft.com/content/eu-ai-act-fines",
        source="Financial Times",
        section="Policy & Regulation",
        one_liner="The EU AI Act's enforcement provisions take effect in August, exposing companies to fines of up to 3% of global revenue for non-compliance.",
        why="The paperwork era of enterprise AI has officially begun. Companies with EU operations need risk classifications and documentation in place within weeks. The practical effect is a compliance advantage for firms that built audit trails from day one and a meaningful liability for those that did not.",
        score=0.85,
    ),
    _make_article(
        title="Nvidia's Market Cap Surpasses $4 Trillion as AI Chip Demand Accelerates",
        url="https://www.wsj.com/markets/nvidia-market-cap",
        source="Wall Street Journal",
        section="Software Impact on Markets",
        one_liner="Nvidia crossed a $4 trillion market cap as data center GPU orders for 2026 exceeded analyst estimates by roughly 30%.",
        why="At $4 trillion Nvidia is priced as infrastructure rather than a cyclical hardware company. That framing holds as long as model training continues to scale with compute. The risk is not competition from AMD or Intel but a shift in training architectures that reduces reliance on dense GPU clusters. Nothing in this week's order data suggests that shift is imminent.",
        score=0.95,
    ),
]

SAMPLE_DISRUPTION = (
    "The clearest disruption signal this week sits at the intersection of model distribution and consulting. "
    "Accenture's $3bn Anthropic commitment effectively turns professional services into a reseller layer for AI, "
    "squeezing the independent SaaS vendors who have relied on consulting firms as implementation partners. "
    "Meanwhile OpenAI's latest raise gives it the runway to undercut incumbents on price in legal, finance and HR "
    "automation before challengers can establish defensible positions."
)

html_body, _ = render(SAMPLE_ARTICLES, disruption_commentary=SAMPLE_DISRUPTION)
subject = subject_line()

out_path = Path("data/preview.html")
out_path.parent.mkdir(exist_ok=True)
out_path.write_text(html_body, encoding="utf-8")

print(f"\nPreview saved to: {out_path}")
print(f"Subject: {subject}")
print(f"Articles: {len(SAMPLE_ARTICLES)}\n")
