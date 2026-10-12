from typing import Protocol

from pydantic import BaseModel, Field


class Question(BaseModel):
    id: str
    prompt: str
    kind: str = "text"            # text | choice | number | list
    choices: list[str] = []


class QuestionSet(BaseModel):
    version: str
    questions: list[Question]


class Answer(BaseModel):
    question_id: str
    value: str | float | list[str]
    confidence: float = Field(ge=0, le=1)
    evidence: str = ""            # quote/span from the ad text
    answered_by: str = ""


class DecisionProvider(Protocol):
    name: str

    async def answer(self, text: str, questions: QuestionSet) -> list[Answer]: ...
