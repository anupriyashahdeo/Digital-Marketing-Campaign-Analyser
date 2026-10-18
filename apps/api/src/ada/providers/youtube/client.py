"""YouTube Data API v3: public video metadata only (title, channel, views, likes, comments).
Never downloads video or audio. Quota: search = 100 units, videos.list = 1 unit, 10,000/day free.
"""
import re
import time
from datetime import datetime

import httpx

from ada.spi.video_metadata import VideoMeta

API = "https://www.googleapis.com/youtube/v3"
CACHE_SECONDS = 15 * 60          # same search within 15 min is free (saves quota)
_ISO_DURATION = re.compile(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?")


class YouTubeError(Exception):
    """Something the user should see (bad key, quota used up, YouTube down)."""


def parse_duration(iso: str) -> int:
    """'PT1M5S' -> 65 seconds."""
    m = _ISO_DURATION.fullmatch(iso or "")
    if not m:
        return 0
    d, h, mi, s = (int(x or 0) for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def _to_meta(item: dict) -> VideoMeta:
    sn, st = item.get("snippet", {}), item.get("statistics", {})
    thumbs = sn.get("thumbnails", {})
    thumb = (thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
    return VideoMeta(
        video_id=item["id"], channel_id=sn.get("channelId", ""), title=sn.get("title", ""),
        description=sn.get("description", ""),
        published_at=datetime.fromisoformat(sn["publishedAt"]),
        views=int(st.get("viewCount", 0)), likes=int(st.get("likeCount", 0)),
        comments=int(st.get("commentCount", 0)), channel_title=sn.get("channelTitle", ""),
        thumbnail_url=thumb,
        duration_seconds=parse_duration(item.get("contentDetails", {}).get("duration", "")),
    )


class YouTubeDataClient:
    def __init__(self, api_key: str, timeout: float = 10.0):
        self.key, self.timeout = api_key, timeout
        self._cache: dict[tuple, tuple[float, list[VideoMeta]]] = {}

    async def _get(self, path: str, **params) -> dict:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            try:
                r = await c.get(f"{API}/{path}", params={**params, "key": self.key})
            except httpx.HTTPError as e:
                raise YouTubeError("Couldn't reach YouTube. Try again in a minute.") from e
        if r.status_code == 403:
            reason = (r.json().get("error", {}).get("errors") or [{}])[0].get("reason", "")
            if "quota" in reason.lower():
                raise YouTubeError("Today's YouTube quota is used up. It resets at midnight "
                                   "Pacific time.")
            raise YouTubeError("YouTube rejected the API key. Check YOUTUBE_API_KEY.")
        if r.status_code == 400:
            raise YouTubeError("YouTube rejected the request. Check YOUTUBE_API_KEY.")
        if r.status_code >= 400:
            raise YouTubeError(f"YouTube returned an error ({r.status_code}).")
        return r.json()

    async def get_videos(self, video_ids: list[str]) -> list[VideoMeta]:
        if not video_ids:
            return []
        data = await self._get("videos", part="snippet,statistics,contentDetails",
                               id=",".join(video_ids[:50]))
        return [_to_meta(i) for i in data.get("items", [])]

    async def search(self, query: str, region: str, language: str, n: int = 10,
                     order: str = "relevance") -> list[VideoMeta]:
        key = (query.lower(), region, language, n, order)
        if (hit := self._cache.get(key)) and time.monotonic() - hit[0] < CACHE_SECONDS:
            return hit[1]
        data = await self._get("search", part="id", type="video", q=query, maxResults=n,
                               regionCode=region, relevanceLanguage=language, order=order)
        ids = [i["id"]["videoId"] for i in data.get("items", []) if i.get("id", {}).get("videoId")]
        videos = await self.get_videos(ids)
        self._cache[key] = (time.monotonic(), videos)
        return videos
