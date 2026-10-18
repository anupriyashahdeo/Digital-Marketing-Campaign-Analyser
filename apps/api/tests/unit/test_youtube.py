from datetime import UTC, datetime

import pytest

from ada.api.v1.youtube import video_ids_in
from ada.main import app
from ada.providers.registry import get_youtube
from ada.providers.youtube.client import YouTubeError, parse_duration
from ada.spi.video_metadata import VideoMeta
from tests.unit.test_auth import signup
from tests.unit.test_workspaces import ws_id


def meta(vid, views, likes=0, comments=0):
    return VideoMeta(video_id=vid, channel_id="UC1", channel_title="Nike", title=f"Ad {vid}",
                     published_at=datetime(2026, 1, 1, tzinfo=UTC), views=views, likes=likes,
                     comments=comments, duration_seconds=30)


class FakeYouTube:
    def __init__(self, fail=False):
        self.fail, self.calls = fail, []

    async def search(self, query, region, language, n=10, order="relevance"):
        self.calls.append(("search", query, region, n, order))
        if self.fail:
            raise YouTubeError("Today's YouTube quota is used up.")
        return [meta("aaaaaaaaaa1", 1000, 40, 10), meta("bbbbbbbbbb2", 3000, 30, 0)]

    async def get_videos(self, ids):
        self.calls.append(("videos", ids))
        return [meta(i, 500, 5, 0) for i in ids]


@pytest.fixture()
def yt():
    fake = FakeYouTube()
    app.dependency_overrides[get_youtube] = lambda: fake
    yield fake
    app.dependency_overrides.pop(get_youtube, None)


def search(c, wid, **params):
    return c.get(f"/api/v1/workspaces/{wid}/youtube/search", params=params)


def test_keyword_search_returns_stats_and_summary(client, yt):
    c, _ = client
    signup(c)
    r = search(c, ws_id(c), q="  running   shoes ", limit=5, order="viewCount")
    assert r.status_code == 200
    d = r.json()
    assert d["mode"] == "search" and d["query"] == "running shoes"
    assert yt.calls == [("search", "running shoes", "IN", 5, "viewCount")]
    assert d["videos"][0]["engagement_rate"] == 0.05            # (40+10)/1000
    assert d["videos"][0]["url"].endswith("v=aaaaaaaaaa1")
    assert d["summary"] == {"count": 2, "total_views": 4000, "avg_views": 2000,
                            "avg_engagement_rate": 0.03, "top_video_id": "bbbbbbbbbb2"}


def test_pasted_links_are_looked_up_not_searched(client, yt):
    c, _ = client
    signup(c)
    q = "https://www.youtube.com/watch?v=dQw4w9WgXcQ, https://youtu.be/dQw4w9WgXcQ 9bZkp7q19f0"
    d = search(c, ws_id(c), q=q).json()
    assert d["mode"] == "lookup"
    assert yt.calls == [("videos", ["dQw4w9WgXcQ", "9bZkp7q19f0"])]


def test_quota_error_is_shown_to_user(client):
    c, _ = client
    app.dependency_overrides[get_youtube] = lambda: FakeYouTube(fail=True)
    try:
        signup(c)
        r = search(c, ws_id(c), q="shoes")
        assert r.status_code == 502 and "quota" in r.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_youtube, None)


def test_missing_api_key_gives_setup_message(client):
    c, _ = client
    app.dependency_overrides[get_youtube] = lambda: None
    try:
        signup(c)
        r = search(c, ws_id(c), q="shoes")
        assert r.status_code == 503 and "YOUTUBE_API_KEY" in r.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_youtube, None)


def test_requires_sign_in_and_membership(client, yt):
    c, _ = client
    assert search(c, 1, q="shoes").status_code == 401
    signup(c)
    assert search(c, ws_id(c) + 999, q="shoes").status_code == 404


def test_video_id_parsing():
    assert video_ids_in("youtube.com/shorts/dQw4w9WgXcQ") == ["dQw4w9WgXcQ"]
    assert video_ids_in("running shoes") == []
    assert video_ids_in("smartphones") == []                   # 11 letters, still a keyword
    assert video_ids_in("iphone15pro") == []
    assert video_ids_in("dQw4w9WgXcQ shoes") == []             # any word -> keyword search


def test_parse_duration():
    assert parse_duration("PT1M5S") == 65
    assert parse_duration("PT2H") == 7200
    assert parse_duration("") == 0
