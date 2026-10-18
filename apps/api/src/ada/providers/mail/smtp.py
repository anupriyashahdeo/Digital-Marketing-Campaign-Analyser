import logging
import smtplib
import ssl
from email.message import EmailMessage

log = logging.getLogger("ada.mail")


class SmtpMailer:
    """Sends real email through any SMTP server (Gmail, Outlook, Brevo, SES SMTP, ...).
    Port 465 uses implicit TLS; any other port (usually 587) uses STARTTLS."""

    def __init__(self, host: str, port: int, username: str, password: str, sender: str):
        self.host, self.port = host, port
        # Google shows App Passwords as "abcd efgh ijkl mnop"; the spaces are not part of it
        self.username, self.password = username, password.replace(" ", "")
        self.sender = sender or username

    def send(self, to: str, subject: str, body: str) -> None:
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = self.sender, to, subject
        msg.set_content(body)
        ctx = ssl.create_default_context()
        try:
            if self.port == 465:
                with smtplib.SMTP_SSL(self.host, self.port, context=ctx, timeout=15) as s:
                    self._deliver(s, msg)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=15) as s:
                    s.starttls(context=ctx)
                    self._deliver(s, msg)
            log.info("EMAIL sent to=%s subject=%s", to, subject)
        except (smtplib.SMTPAuthenticationError, smtplib.SMTPServerDisconnected) as e:
            log.error("EMAIL failed to=%s: SMTP login rejected by %s (%s). For Gmail, SMTP_PASSWORD "
                      "must be a 16-letter App Password, not your account password.", to, self.host, e)
        except Exception:
            # Never let a mail failure surface to the caller (it would reveal the account exists)
            log.exception("EMAIL failed to=%s via %s:%s", to, self.host, self.port)

    def _deliver(self, s: smtplib.SMTP, msg: EmailMessage) -> None:
        if self.username:
            s.login(self.username, self.password)
        s.send_message(msg)
