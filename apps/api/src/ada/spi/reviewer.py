from typing import Protocol

from ada.spi.decision import Answer, Question


class Reviewer(Protocol):
    name: str

    async def review(self, text: str, question: Question, first: Answer) -> Answer: ...
