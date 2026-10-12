"""Jev adapter. [Verify] request format, auth and availability with TypeSafe/OpenRouter docs
before use. Implemented as a stub so the rest of the system never depends on it."""
from ada.spi.decision import Answer, QuestionSet


class JevDecision:
    name = "jev"

    def __init__(self, api_key: str, base_url: str):
        self.api_key, self.base_url = api_key, base_url

    async def answer(self, text: str, questions: QuestionSet) -> list[Answer]:
        raise NotImplementedError("Confirm Jev API contract, then implement (batching + retries).")
