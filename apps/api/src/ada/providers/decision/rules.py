"""Rules-based fallback: works with no AI access. Low confidence by design."""
import re

from ada.spi.decision import Answer, QuestionSet


class RulesDecision:
    name = "rules"

    async def answer(self, text: str, questions: QuestionSet) -> list[Answer]:
        t = text.lower()
        out: list[Answer] = []
        for q in questions.questions:
            if q.id == "hook_type":
                first = t[:200]
                v, c = ("question", 0.7) if "?" in first else ("other", 0.3)
            elif q.id == "offer":
                m = re.search(r"(\d+%\s*off|free [a-z ]+|buy one get one)", t)
                v, c = (m.group(0), 0.8) if m else ("none", 0.4)
            elif q.id == "cta":
                m = re.search(r"(buy now|shop now|sign up|download|call now|learn more)", t)
                v, c = (m.group(0), 0.8) if m else ("unknown", 0.3)
            elif q.id == "stop_scroll_score":
                v, c = 5.0, 0.2
            else:
                v, c = "other", 0.3
            out.append(Answer(question_id=q.id, value=v, confidence=c,
                              evidence=text[:80], answered_by=self.name))
        return out
