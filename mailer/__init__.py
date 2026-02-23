from mailer.base_mailer import BaseMailer
from mailer.gmail_mailer import GmailMailer


def get_mailer(settings) -> BaseMailer:
    """Factory — returns the configured mailer."""
    return GmailMailer(
        from_addr=settings.gmail_address,
        app_password=settings.gmail_app_password,
    )
