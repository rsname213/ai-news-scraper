from scraper.models import FeedSource

# Sources: premium publications only (headlines + brief summary via RSS)

FEEDS: list[FeedSource] = [
    FeedSource(
        name="Wall Street Journal",
        url="https://feeds.content.dowjones.io/public/rss/RSSWSJD",
        tier=1,
        paywall=True,
    ),
    FeedSource(
        name="Financial Times",
        url="https://www.ft.com/?format=rss",
        tier=1,
        paywall=True,
        skip_on_403=True,
    ),
    FeedSource(
        name="The Information",
        url="https://www.theinformation.com/feed",
        tier=1,
        paywall=True,
        skip_on_403=True,
    ),
    FeedSource(
        name="TechCrunch",
        url="https://techcrunch.com/category/artificial-intelligence/feed/",
        tier=2,
        paywall=False,
    ),
]

# Ordered section names for the newsletter (determines display order)
SECTIONS = [
    "AI Models & Infrastructure",
    "Enterprise Adoption",
    "Startups & Funding",
    "Policy & Regulation",
    "AI Impact on SaaS in Public Markets",
]

# Section accent colours (Outlook-safe hex values)
SECTION_COLOURS = {
    "AI Models & Infrastructure":  "#E8640C",
    "Enterprise Adoption":        "#1E3A5F",
    "Startups & Funding":         "#E8640C",
    "Policy & Regulation":        "#1E3A5F",
    "AI Impact on SaaS in Public Markets": "#E8640C",
}
