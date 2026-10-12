"""Steps 3+4: ask fixed questions, escalate low-confidence answers to the reviewer."""
from ada.cache.memory import MemoryCache, cache_key
from ada.config import settings
from ada.spi.decision import Answer, DecisionProvider, QuestionSet
from ada.spi.reviewer import Reviewer


async def analyse_ad(text: str, qs: QuestionSet, decider: DecisionProvider, reviewer: Reviewer,
                     cache: MemoryCache | None = None,
                     threshold: float | None = None) -> list[Answer]:
    threshold = settings.escalation_threshold if threshold is None else threshold
    key = cache_key(text, qs.version)
    if cache and (hit := cache.get(key)):
        return hit
    answers = await decider.answer(text, qs)
    by_id = {q.id: q for q in qs.questions}
    final: list[Answer] = []
    for a in answers:
        if a.confidence < threshold:
            a = await reviewer.review(text, by_id[a.question_id], a)
        final.append(a)
    if cache:
        cache.set(key, final)
    return final
