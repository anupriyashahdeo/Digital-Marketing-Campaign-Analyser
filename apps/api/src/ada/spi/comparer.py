from typing import Protocol

from pydantic import BaseModel

from ada.spi.video_metadata import VideoComment, VideoMeta


class AdEvidence(BaseModel):
    """One ad as the comparer sees it: public stats, its rank in the set, and its top comments."""
    video: VideoMeta
    views_per_day: float
    engagement_rate: float          # (likes + comments) / views
    score: int                      # 0-100, rank within the compared set (see pipeline.ad_compare)
    comments: list[VideoComment] | None = None   # None: comments turned off


class Difference(BaseModel):
    aspect: str                     # e.g. "Offer", "Length", "Viewer reaction"
    best: str
    worst: str
    why_it_matters: str


class Comparison(BaseModel):
    headline: str                   # one sentence: how far the best ad beat the worst
    best_strengths: list[str]
    worst_weaknesses: list[str]
    differences: list[Difference]
    recommendations: list[str]      # what to do in the advertiser's next ad
    caveat: str                     # what this comparison can't tell you
    analysed_by: str = "rules"      # "rules" (text + numbers) | "laya" (also read the comments)
    notice: str = ""                # why Laya wasn't used, when it was expected


class Comparer(Protocol):
    async def compare(self, best: AdEvidence, worst: AdEvidence, query: str) -> Comparison: ...
