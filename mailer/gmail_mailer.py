"""
Gmail SMTP mailer using an App Password.

Setup:
  1. Enable 2-Step Verification on your Google account.
  2. Go to: Google Account → Security → 2-Step Verification → App Passwords
  3. Create an App Password for "Mail" / "Other (Custom name)"
  4. Use that 16-character password as GMAIL_APP_PASSWORD in your .env
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from mailer.base_mailer import BaseMailer

logger = logging.getLogger(__name__)

_SMTP_HOST = "smtp.gmail.com"
_SMTP_PORT = 465  # SSL


class GmailMailer(BaseMailer):
    def __init__(self, from_addr: str, app_password: str):
        self._from_addr = from_addr
        self._app_password = app_password

    def send(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"AI Pulse <{self._from_addr}>"
        msg["To"] = to
        msg["Reply-To"] = self._from_addr

        # Attach plain text first, HTML second (email clients prefer the last part)
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        with smtplib.SMTP_SSL(_SMTP_HOST, _SMTP_PORT) as server:
            server.login(self._from_addr, self._app_password)
            server.sendmail(self._from_addr, to, msg.as_string())

        logger.info("Email sent to %s via Gmail SMTP", to)
        return True
