from abc import ABC, abstractmethod


class BaseMailer(ABC):
    @abstractmethod
    def send(self, to: str, subject: str, html_body: str, text_body: str) -> bool:
        """
        Send an email.

        Args:
            to: Recipient email address.
            subject: Email subject line.
            html_body: HTML version of the email body.
            text_body: Plain text version (fallback for clients that don't render HTML).

        Returns:
            True on success.

        Raises:
            Exception on delivery failure.
        """
        ...
