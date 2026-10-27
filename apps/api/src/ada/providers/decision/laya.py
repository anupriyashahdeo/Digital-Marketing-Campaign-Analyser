"""Laya (convaiinnovations/laya-typed-decisions): a small local model that answers choice,
score and yes/no questions in one forward pass. No API key, no per-call cost, runs on CPU.
Install with `pip install -e .[laya]`; the first load downloads the weights into HF_HOME.
Laya picks from options, it can't write text, so free-text questions go to the rules provider."""
import asyncio
import os
from functools import lru_cache

from ada.config import settings
from ada.providers.decision.rules import RulesDecision
from ada.spi.decision import Answer, Question, QuestionSet


@lru_cache(maxsize=1)
def get_agent():
    """Load once per process (a few seconds, ~0.5 GB RAM). ImportError if laya isn't installed."""
    if settings.hf_home:
        os.environ.setdefault("HF_HOME", settings.hf_home)
    import laya  # heavy (torch); imported only when Laya is actually used

    return laya.load(settings.laya_model)


def to_laya(q: Question) -> dict | None:
    """Our question -> Laya's schema. None for kinds Laya can't answer (free text, lists)."""
    if q.kind == "choice":
        return {"type": "choice", "instructions": q.prompt, "criteria": {c: c for c in q.choices}}
    if q.kind == "number":      # our numbers are 0-10 scores; Laya's score = expected level index
        return {"type": "score", "instructions": q.prompt,
                "criteria": [str(i) for i in range(11)]}
    return None


class LayaDecision:
    name = "laya"

    async def answer(self, text: str, questions: QuestionSet) -> list[Answer]:
        asked = {q.id: spec for q in questions.questions if (spec := to_laya(q))}
        result = await asyncio.to_thread(get_agent().predict, text, asked) if asked else {}
        answers = result.get("answers", {})
        rest = QuestionSet(version=questions.version,
                           questions=[q for q in questions.questions if q.id not in asked])
        by_rules = {a.question_id: a for a in await RulesDecision().answer(text, rest)}
        out: list[Answer] = []
        for q in questions.questions:
            if q.id not in asked:
                out.append(by_rules[q.id])
                continue
            a = answers[q.id]
            value = a["choice"] if a["type"] == "choice" else round(a["score"], 1)
            out.append(Answer(question_id=q.id, value=value, confidence=a["answer_confidence"],
                              evidence=text[:80], answered_by=self.name))
        return out
