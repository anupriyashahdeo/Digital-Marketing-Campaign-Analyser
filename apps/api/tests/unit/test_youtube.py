from datetime import UTC, datetime

import pytest

from ada.api.v1.youtube import video_ids_in
from ada.main import app
from ada.providers.registry import get_youtube
from ada.providers.youtube.client import (
    CommentsOff,
    YouTubeDataClient,
    YouTubeError,
    parse_duration,
)
from ada.spi.video_metadata import VideoComment, VideoMeta
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

    async def top_comments(self, video_id, n=10):
        self.calls.append(("comments", video_id, n))
        if self.fail:
            raise YouTubeError("Today's YouTube quota is used up.")
        if video_id == "offoffoff00":
            return None
        return [VideoComment(comment_id=f"c{k}", author=f"@fan{k}", text=f"Love it {k}", likes=9 - k,
                             replies=k, published_at=datetime(2026, 2, 1, tzinfo=UTC))
                for k in range(n)]


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


def comments(c, wid, **params):
    return c.get(f"/api/v1/workspaces/{wid}/youtube/comments", params=params)


def test_top_comments_for_each_listed_video(client, yt):
    c, _ = client
    signup(c)
    r = comments(c, ws_id(c), ids="aaaaaaaaaa1,bbbbbbbbbb2,aaaaaaaaaa1,offoffoff00")
    assert r.status_code == 200
    vids = r.json()["videos"]
    assert [v["video_id"] for v in vids] == ["aaaaaaaaaa1", "bbbbbbbbbb2", "offoffoff00"]
    assert len(vids[0]["comments"]) == 10 and vids[0]["comments_disabled"] is False
    assert vids[0]["comments"][0] == {"comment_id": "c0", "author": "@fan0", "text": "Love it 0",
                                      "likes": 9, "replies": 0,
                                      "published_at": "2026-02-01T00:00:00Z"}
    assert vids[2] == {"video_id": "offoffoff00", "comments_disabled": True, "comments": []}
    assert ("comments", "aaaaaaaaaa1", 10) in yt.calls


def test_comments_rejects_bad_ids(client, yt):
    c, _ = client
    signup(c)
    assert comments(c, ws_id(c), ids="not a video id").status_code == 422
    assert comments(c, ws_id(c), ids=",".join(f"{i:011d}" for i in range(51))).status_code == 422


def test_comments_quota_error_is_shown_to_user(client):
    c, _ = client
    app.dependency_overrides[get_youtube] = lambda: FakeYouTube(fail=True)
    try:
        signup(c)
        r = comments(c, ws_id(c), ids="aaaaaaaaaa1")
        assert r.status_code == 502 and "quota" in r.json()["detail"]
    finally:
        app.dependency_overrides.pop(get_youtube, None)


async def test_client_parses_comment_threads_and_handles_comments_off():
    yt = YouTubeDataClient("key")
    sent = []

    async def fake_get(path, **params):
        sent.append((path, params))
        if params["videoId"] == "offoffoff00":
            raise CommentsOff("commentsDisabled")
        return {"items": [{"snippet": {"totalReplyCount": 3, "topLevelComment": {
            "id": "Ugx1", "snippet": {"authorDisplayName": "@ana", "textOriginal": "Great ad",
                                      "likeCount": 12, "publishedAt": "2026-03-01T10:00:00Z"}}}}]}

    yt._get = fake_get
    [c] = await yt.top_comments("aaaaaaaaaa1")
    assert (c.author, c.text, c.likes, c.replies) == ("@ana", "Great ad", 12, 3)
    assert sent[0] == ("commentThreads", {"part": "snippet", "videoId": "aaaaaaaaaa1",
                                          "order": "relevance", "maxResults": 10,
                                          "textFormat": "plainText"})
    assert await yt.top_comments("offoffoff00") is None
    await yt.top_comments("aaaaaaaaaa1")
    assert len(sent) == 2                                       # second call served from cache
