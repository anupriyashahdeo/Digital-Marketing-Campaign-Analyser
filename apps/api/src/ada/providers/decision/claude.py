"""Claude decision provider. Fill in with the Anthropic SDK; return the same Answer schema."""
from ada.spi.decision import Answer, QuestionSet


class ClaudeDecision:
    name = "claude"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def answer(self, text: str, questions: QuestionSet) -> list[Answer]:
        raise NotImplementedError("Call Anthropic API with JSON-only prompt; validate with Answer.")
