"""Pick adapters by region + config. Add a country = add an adapter and register it here."""
from ada.config import settings
from ada.providers.decision.claude import ClaudeDecision
from ada.providers.decision.jev import JevDecision
from ada.providers.decision.rules import RulesDecision
from ada.providers.reviewer.claude import ClaudeReviewer


def get_decision():
    p = settings.decision_provider
    if p == "claude":
        return ClaudeDecision(settings.anthropic_api_key)
    if p == "jev":
        return JevDecision(settings.jev_api_key, settings.jev_base_url)
    return RulesDecision()


def get_reviewer():
    return ClaudeReviewer(settings.anthropic_api_key)
