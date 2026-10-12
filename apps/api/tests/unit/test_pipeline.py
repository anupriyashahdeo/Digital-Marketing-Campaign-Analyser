import pytest

from ada.cache.memory import MemoryCache
from ada.cost.ledger import CostLedger, SpendCapExceeded
from ada.domain.questions.registry import load
from ada.pipeline.analyse import analyse_ad
from ada.providers.decision.mock import MockDecision
from ada.providers.decision.rules import RulesDecision
from ada.providers.manual.source import parse_csv
from ada.providers.reviewer.mock import MockReviewer


async def test_low_confidence_goes_to_reviewer():
    out = await analyse_ad("some ad text", load(), MockDecision(low={"cta"}), MockReviewer(), threshold=0.6)
    by = {a.question_id: a for a in out}
    assert by["cta"].answered_by == "mock-reviewer"
    assert by["offer"].answered_by == "mock"


async def test_cache_avoids_second_call():
    cache, calls = MemoryCache(), []

    class Counting(MockDecision):
        async def answer(self, text, qs):
            calls.append(1)
            return await super().answer(text, qs)

    for _ in range(2):
        await analyse_ad("same text", load(), Counting(), MockReviewer(), cache=cache)
    assert len(calls) == 1


async def test_rules_fallback_runs_without_ai():
    out = await RulesDecision().answer("Get 50% off. Shop now!", load())
    assert {a.question_id for a in out} == {q.id for q in load().questions}


def test_manual_csv_parses_urls():
    rows = "url,advertiser\nhttps://www.youtube.com/watch?v=dQw4w9WgXcQ,Acme\nbad,x\n"
    assert [a.video_id for a in parse_csv(rows)] == ["dQw4w9WgXcQ"]


def test_spend_cap():
    led = CostLedger(1.0)
    led.charge("stt", 0.9)
    with pytest.raises(SpendCapExceeded):
        led.charge("llm", 0.2)
