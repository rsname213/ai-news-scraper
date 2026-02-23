from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class FeedSource:
    name: str
    url: str
    tier: int           # 1 = paywalled (headlines only), 2 = open (full content)
    paywall: bool
    skip_on_403: bool = False


@dataclass
class RawArticle:
    title: str
    url: str
    summary: str        # RSS description/summary (may be truncated for paywalled sources)
    source: str         # Feed name, e.g. "TechCrunch AI"
    pub_date: datetime
    content_available: bool  # False for Tier 1 paywalled items


@dataclass
class RelevanceResult:
    relevant: bool
    score: float        # 0.0–1.0
    reason: str


@dataclass
class ProcessedArticle:
    raw: RawArticle
    is_relevant: bool
    relevance_score: float
    one_liner: str
    why_it_matters: str
    section: str
    rejection_reason: Optional[str] = None
