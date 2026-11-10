"""YouTube data extraction: search by keyword, or paste video links, and get public stats."""
import asyncio
import re
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ada.api.schemas import (
    ComparedAd,
    YouTubeCommentOut,
    YouTubeCommentsOut,
    YouTubeCompareOut,
    YouTubeSearchOut,
    YouTubeSummary,
    YouTubeVideoComments,
    YouTubeVideoOut,
)
from ada.db.models import Membership, Workspace, YouTubeInsight
from ada.db.session import get_db
from ada.pipeline.ad_compare import rank
from ada.providers.registry import get_comparer, get_youtube
from ada.providers.youtube.client import YouTubeDataClient, YouTubeError
from ada.security.deps import workspace_member
from ada.spi.comparer import AdEvidence
from ada.spi.video_metadata import VideoMeta

router = APIRouter(prefix="/workspaces/{workspace_id}/youtube", tags=["youtube"])

_LINK_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|embed/)([A-Za-z0-9_-]{11})")
_BARE_ID = re.compile(r"[A-Za-z0-9_-]{11}")
_NOT_SET_UP = "YouTube isn't set up yet. Add YOUTUBE_API_KEY to .env and restart the API."
MAX_CSV_BYTES = 2_000_000          # CSV uploads to the task queue (see tasks.py)



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


def _listed_ids(ids: str, least: int) -> list[str]:
    """'a,b,c' -> valid ids, no repeats; 422 unless there are `least` to 50 of them."""
    video_ids = list(dict.fromkeys(i for i in ids.split(",") if _BARE_ID.fullmatch(i)))
    if not least <= len(video_ids) <= 50:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Send {least} to 50 video ids.")
    return video_ids


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
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _NOT_SET_UP)
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


@router.get("/comments", response_model=YouTubeCommentsOut)
async def comments(ids: str = Query(min_length=11, max_length=2000,
                                    description="Comma-separated video ids (max 50)"),
                   limit: int = Query(10, ge=1, le=100),
                   m: Membership = Depends(workspace_member),
                   yt: YouTubeDataClient | None = Depends(get_youtube)):
    """Top comments (YouTube's 'Top comments' order) for each listed video. 1 quota unit each."""
    if yt is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _NOT_SET_UP)
    video_ids = _listed_ids(ids, least=1)
    try:
        results = await asyncio.gather(*(yt.top_comments(v, limit) for v in video_ids))
    except YouTubeError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    return YouTubeCommentsOut(videos=[
        YouTubeVideoComments(video_id=v, comments_disabled=found is None,
                             comments=[YouTubeCommentOut(**c.model_dump()) for c in found or []])
        for v, found in zip(video_ids, results, strict=True)
    ])


def _compared(a: AdEvidence) -> ComparedAd:
    return ComparedAd(video=_out(a.video), views_per_day=a.views_per_day, score=a.score,
                      comments_disabled=a.comments is None,
                      top_comments=[YouTubeCommentOut(**c.model_dump()) for c in a.comments or []])


@router.get("/compare", response_model=YouTubeCompareOut)
async def compare(ids: str = Query(min_length=23, max_length=2000,
                                   description="Comma-separated video ids from one search (2-50)"),
                  q: str = Query("", max_length=500, description="The search, for context"),
                  m: Membership = Depends(workspace_member),
                  yt: YouTubeDataClient | None = Depends(get_youtube),
                  comparer=Depends(get_comparer)):
    """Rank the listed ads, then show why the best beat the worst. Free: 3 YouTube quota units
    (stats + both ads' comments), no paid API."""
    if yt is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _NOT_SET_UP)
    video_ids = _listed_ids(ids, least=2)
    try:
        metas = await yt.get_videos(video_ids)    # fresh stats + descriptions for the prompt
        if len(metas) < 2:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                "Need at least 2 videos that still exist on YouTube.")
        ranked, too_new = rank(metas)
        best, worst = ranked[0], ranked[-1]
        best.comments, worst.comments = await asyncio.gather(
            yt.top_comments(best.video.video_id), yt.top_comments(worst.video.video_id))
    except YouTubeError as e:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(e)) from e
    analysis = await comparer.compare(best, worst, " ".join(q.split()))
    return YouTubeCompareOut(best=_compared(best), worst=_compared(worst), ads_judged=len(ranked),
                             ads_too_new=too_new, analysis=analysis)


def save_interest(db: Session, workspace_id: int, rows: list[dict]) -> None:
    """Keep this analysis for the dashboard, replacing the last one. Rows come from an uploaded
    CSV that other members will see, so bad ids are dropped and the link is built here."""
    videos = [{"title": r["title"][:200], "url": f"https://www.youtube.com/watch?v={r['video_id']}",
               "interested_people": r["interested_people"],
               "interested_comments": r["interested_comments"],
               "comments_read": r["comments_read"]}
              for r in rows
              if r["interested_people"] is not None and _BARE_ID.fullmatch(r["video_id"])]
    db.execute(delete(YouTubeInsight).where(YouTubeInsight.workspace_id == workspace_id))
    db.add(YouTubeInsight(workspace_id=workspace_id, videos=videos))
    db.commit()
