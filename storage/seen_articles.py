import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

_STORE_PATH = Path("data/seen_articles.json")


def url_hash(url: str) -> str:
    """Return a short SHA-256 hash of the URL for compact storage."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def load_seen() -> set[str]:
    """Load the set of seen article URL hashes from disk."""
    if not _STORE_PATH.exists():
        logger.info("No seen_articles.json found — starting fresh")
        return set()
    try:
        data = json.loads(_STORE_PATH.read_text())
        return set(data.get("urls", []))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Could not load seen_articles.json: %s — starting fresh", exc)
        return set()


def save_seen(seen: set[str]) -> None:
    """Persist the set of seen URL hashes to disk."""
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(
        json.dumps({"urls": sorted(seen)}, indent=2) + "\n"
    )
    logger.info("Saved %d seen article hashes", len(seen))
