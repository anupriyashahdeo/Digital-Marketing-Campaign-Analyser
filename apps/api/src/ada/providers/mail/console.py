import logging

log = logging.getLogger("ada.mail")


class ConsoleMailer:
    """Dev mailer: prints the email to the log. Replace with SES/SendGrid in production."""

    def send(self, to: str, subject: str, body: str) -> None:
        log.info("EMAIL to=%s subject=%s body=%s", to, subject, body)
