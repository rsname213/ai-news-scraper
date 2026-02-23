import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    anthropic_api_key: str
    gmail_address: str
    gmail_app_password: str
    recipient_email: str
    lookback_days: int
    max_articles_per_section: int
    dry_run: bool
    theinformation_cookie: str | None

    @classmethod
    def from_env(cls) -> "Settings":
        missing = []
        for key in ("ANTHROPIC_API_KEY", "GMAIL_ADDRESS", "GMAIL_APP_PASSWORD", "RECIPIENT_EMAIL"):
            if not os.getenv(key):
                missing.append(key)
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Copy .env.example to .env and fill in your values."
            )

        return cls(
            anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
            gmail_address=os.environ["GMAIL_ADDRESS"],
            gmail_app_password=os.environ["GMAIL_APP_PASSWORD"],
            recipient_email=os.environ["RECIPIENT_EMAIL"],
            lookback_days=int(os.getenv("LOOKBACK_DAYS", "7")),
            max_articles_per_section=int(os.getenv("MAX_ARTICLES_PER_SECTION", "8")),
            dry_run=os.getenv("DRY_RUN", "false").lower() == "true",
            theinformation_cookie=os.getenv("THEINFORMATION_SESSION_COOKIE"),
        )
