from ada.spi.decision import Answer, Question


class MockReviewer:
    name = "mock-reviewer"

    async def review(self, text: str, question: Question, first: Answer) -> Answer:
        return Answer(question_id=question.id, value="reviewed", confidence=0.95,
                      evidence=first.evidence, answered_by=self.name)
