"""YouTube data extraction: search by keyword, or paste video links, and get public stats."""
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ada.api.schemas import YouTubeSearchOut, YouTubeSummary, YouTubeVideoOut
from ada.db.models import Membership, Workspace
from ada.db.session import get_db
from ada.providers.registry import get_youtube
from ada.providers.youtube.client import YouTubeDataClient, YouTubeError
from ada.security.deps import workspace_member
from ada.spi.video_metadata import VideoMeta

router = APIRouter(prefix="/workspaces/{workspace_id}/youtube", tags=["youtube"])

_LINK_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})")
_BARE_ID = re.compile(r"[A-Za-z0-9_-]{11}")


def video_ids_in(text: str) -> list[str]:
    """IDs from pasted links / bare ids, in order, no repeats. [] means 'treat as keywords'."""
    tokens = re.split(r"[\s,]+", text.strip())
    ids = []
    for t in tokens:
        m = _LINK_ID.search(t)
        # bare ids are random (mixed case/digits); a lowercase word like 'iphone15pro' is a keyword
        bare = _BARE_ID.fullmatch(t) and not t.isalpha() and not t.islower()
        vid = m.group(1) if m else (t if bare else None)
        if not vid:
            return []                   # any plain word -> it's a keyword search
        if vid not in ids:
            ids.append(vid)
    return ids


def _out(v: VideoMeta) -> YouTubeVideoOut:
    rate = (v.likes + v.comments) / v.views if v.views else 0.0
    return YouTubeVideoOut(**v.model_dump(exclude={"description"}),
                           url=f"https://www.youtube.com/watch?v={v.video_id}",
                           engagement_rate=round(rate, 4))


def _summary(videos: list[YouTubeVideoOut]) -> YouTubeSummary:
    n = len(videos)
    total = sum(v.views for v in videos)
    return YouTubeSummary(
        count=n, total_views=total, avg_views=total // n if n else 0,
        avg_engagement_rate=round(sum(v.engagement_rate for v in videos) / n, 4) if n else 0.0,
        top_video_id=max(videos, key=lambda v: v.views).video_id if n else None,
    )


@router.get("/search", response_model=YouTubeSearchOut)
async def search(q: str = Query(min_length=2, max_length=500),
                 limit: int = Query(10, ge=1, le=50),
                 order: Literal["relevance", "viewCount", "date"] = "relevance",
                 language: Literal["en", "hi"] = "en",
                 m: Membership = Depends(workspace_member), db: Session = Depends(get_db),
                 yt: YouTubeDataClient | None = Depends(get_youtube)):
    if yt is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE,
                            "YouTube isn't set up yet. Add YOUTUBE_API_KEY to .env and restart "
                            "the API.")
    q = " ".join(q.split())
    ids = video_ids_in(q)
    try:
        if ids:
            metas = await yt.get_videos(ids[:50])
        else:
            region = db.get(Workspace, m.workspace_id).region
            metas = await yt.search(q, region=region, language=language, n=limit, order=order)
    except YouTubeError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    videos = [_out(v) for v in metas]
    return YouTubeSearchOut(query=q, mode="lookup" if ids else "search", videos=videos,
                            summary=_summary(videos))
