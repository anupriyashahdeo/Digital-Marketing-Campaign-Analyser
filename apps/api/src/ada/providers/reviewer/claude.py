from ada.spi.decision import Answer, Question


class ClaudeReviewer:
    name = "claude"

    def __init__(self, api_key: str):
        self.api_key = api_key

    async def review(self, text: str, question: Question, first: Answer) -> Answer:
        raise NotImplementedError("Second opinion via Anthropic API.")
