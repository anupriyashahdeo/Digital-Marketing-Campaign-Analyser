"""Pick adapters by region + config. Add a country = add an adapter and register it here."""
from ada.config import settings
from ada.providers.decision.claude import ClaudeDecision
from ada.providers.decision.jev import JevDecision
from ada.providers.decision.rules import RulesDecision
from ada.providers.mail.console import ConsoleMailer
from ada.providers.mail.smtp import SmtpMailer
from ada.providers.reviewer.claude import ClaudeReviewer
from ada.providers.youtube.client import YouTubeDataClient


def get_decision():
    p = settings.decision_provider
    if p == "claude":
        return ClaudeDecision(settings.anthropic_api_key)
    if p == "jev":
        return JevDecision(settings.jev_api_key, settings.jev_base_url)
    return RulesDecision()


def get_reviewer():
    return ClaudeReviewer(settings.anthropic_api_key)


def get_mailer():
    if settings.mail_provider == "smtp":
        return SmtpMailer(settings.smtp_host, settings.smtp_port, settings.smtp_username,
                          settings.smtp_password, settings.mail_from)
    return ConsoleMailer()


_youtube: YouTubeDataClient | None = None


def get_youtube() -> YouTubeDataClient | None:
    """One shared client so its search cache is reused. None when no API key is set."""
    global _youtube
    if not settings.youtube_api_key:
        return None
    if _youtube is None or _youtube.key != settings.youtube_api_key:
        _youtube = YouTubeDataClient(settings.youtube_api_key)
    return _youtube
