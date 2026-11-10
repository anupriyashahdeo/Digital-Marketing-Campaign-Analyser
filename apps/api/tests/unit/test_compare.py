from datetime import UTC, datetime, timedelta

import pytest

from ada.main import app
from ada.pipeline.ad_compare import rank
from ada.providers.compare.rules import RulesComparer
from ada.providers.registry import get_comparer
from ada.spi.comparer import Comparison
from ada.spi.video_metadata import VideoMeta
from tests.unit.test_auth import signup
from tests.unit.test_workspaces import ws_id
from tests.unit.test_youtube import yt  # noqa: F401  (fixture)

NOW = datetime(2026, 10, 31, tzinfo=UTC)


def ad(vid, views, likes, days_old, duration=30):
    return VideoMeta(video_id=vid, channel_id="UC1", channel_title="FitCo", title=f"Ad {vid}",
                     published_at=NOW - timedelta(days=days_old), views=views, likes=likes,
                     duration_seconds=duration)


def evidence(**kw):
    best = ad("a", 30_000, 900, 30, duration=15).model_copy(update={
        "title": "Tired of slow workouts?", "description": "Flat 50% off. Shop now https://fit.co"})
    worst = ad("b", 3_000, 9, 30, duration=60).model_copy(update={"title": "FitCo brand film"})
    ranked, _ = rank([best, worst], now=NOW)
    return ranked[0], ranked[-1]


async def test_free_comparer_reads_offer_cta_and_numbers():
    best, worst = evidence()
    c = await RulesComparer().compare(best, worst, "fitness")
    assert c.analysed_by == "rules" and c.notice == ""
    assert "10x the daily views" in c.headline
    rows = {d.aspect: d for d in c.differences}
    assert rows["Offer"].best == "Flat 50% off" and rows["Offer"].worst == "None found"
    assert rows["Call to action"].best == "Shop now"
    assert rows["Title"].best == "Asks a question"
    assert any("15s" in tip for tip in c.recommendations)
    assert any("link" in w for w in c.worst_weaknesses)
    assert "not the video itself" in c.caveat


class FakeComparer:
    def __init__(self):
        self.calls = []

    async def compare(self, best, worst, query):
        self.calls.append((best.video.video_id, worst.video.video_id, query))
        return Comparison(headline="Best ad opens with a question.", best_strengths=["Clear offer"],
                          worst_weaknesses=["Slow start"], differences=[], recommendations=["Hook"],
                          caveat="No spend data.", analysed_by="rules")


@pytest.fixture()
def comparer():
    fake = FakeComparer()
    app.dependency_overrides[get_comparer] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_comparer, None)


def compare(c, wid, ids, q="fitness ads"):
    return c.get(f"/api/v1/workspaces/{wid}/youtube/compare", params={"ids": ids, "q": q})


def test_compare_ranks_fetches_comments_and_explains(client, yt, comparer):  # noqa: F811
    c, _ = client
    signup(c)
    r = compare(c, ws_id(c), "aaaaaaaaaa1,bbbbbbbbbb2,offoffoff00")
    assert r.status_code == 200
    d = r.json()
    assert d["analysis"]["analysed_by"] == "rules"
    assert d["analysis"]["headline"] == "Best ad opens with a question."
    assert d["ads_judged"] == 3
    # FakeYouTube gives every video the same stats, so the order is stable but arbitrary;
    # what matters is that only the best and worst ads' comments were fetched
    comment_calls = [call[1] for call in yt.calls if call[0] == "comments"]
    assert comment_calls == [d["best"]["video"]["video_id"], d["worst"]["video"]["video_id"]]
    assert comparer.calls[0][2] == "fitness ads"


def test_compare_needs_two_videos(client, yt, comparer):  # noqa: F811
    c, _ = client
    signup(c)
    r = compare(c, ws_id(c), "aaaaaaaaaa1,aaaaaaaaaa1,bad")
    assert r.status_code == 422
