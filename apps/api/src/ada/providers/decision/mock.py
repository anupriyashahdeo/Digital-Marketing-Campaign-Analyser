from ada.spi.decision import Answer, QuestionSet


class MockDecision:
    """Deterministic provider for tests. `low` ids are answered with low confidence."""
    name = "mock"

    def __init__(self, low: set[str] | None = None):
        self.low = low or set()

    async def answer(self, text: str, questions: QuestionSet) -> list[Answer]:
        return [Answer(question_id=q.id, value="x", confidence=0.3 if q.id in self.low else 0.9,
                       evidence=text[:40], answered_by=self.name) for q in questions.questions]
