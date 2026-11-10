from datetime import UTC, datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, Field, PlainSerializer, field_validator

from ada.config import settings
from ada.spi.comparer import Comparison

# Regions with a working ad-source adapter. Add a country here only when its adapter exists.
SUPPORTED_REGIONS = {settings.region}
SUPPORTED_LANGUAGES = {"en", "hi"}
MAX_KEYWORDS, MAX_KEYWORD_LEN = 10, 60


def _as_utc(d: datetime | None) -> str | None:
    """The DB stores naive UTC; send it with an explicit Z so browsers don't read it as local time."""
    if d is None:
        return None
    return (d if d.tzinfo else d.replace(tzinfo=UTC)).isoformat().replace("+00:00", "Z")


UtcDatetime = Annotated[datetime, PlainSerializer(_as_utc, return_type=str)]


def _clean_text(v: str) -> str:
    v = " ".join(v.split())   # collapse whitespace, drop newlines/tabs
    if any(ord(c) < 32 or ord(c) == 127 for c in v):
        raise ValueError("contains invalid characters")
    return v


CleanStr = Annotated[str, AfterValidator(_clean_text)]


class RunIn(BaseModel):
    category: CleanStr = Field(min_length=2, max_length=120)
    keywords: list[str] = Field(default_factory=list, max_length=MAX_KEYWORDS)
    region: str = settings.region
    language: str = settings.language

    @field_validator("category")
    @classmethod
    def _category_not_blank(cls, v: str) -> str:
        if len(v) < 2:
            raise ValueError("must be at least 2 characters")
        return v

    @field_validator("keywords")
    @classmethod
    def _keywords(cls, v: list[str]) -> list[str]:
        seen, out = set(), []
        for k in v:
            k = _clean_text(k)
            if not k:
                continue
            if len(k) > MAX_KEYWORD_LEN:
                raise ValueError(f"each keyword must be at most {MAX_KEYWORD_LEN} characters")
            if k.lower() not in seen:
                seen.add(k.lower())
                out.append(k)
        return out

    @field_validator("region")
    @classmethod
    def _region(cls, v: str) -> str:
        v = v.upper()
        if v not in SUPPORTED_REGIONS:
            raise ValueError(f"region must be one of {sorted(SUPPORTED_REGIONS)}")
        return v

    @field_validator("language")
    @classmethod
    def _language(cls, v: str) -> str:
        if v not in SUPPORTED_LANGUAGES:
            raise ValueError(f"language must be one of {sorted(SUPPORTED_LANGUAGES)}")
        return v


class RunOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    category: str
    keywords: list[str]
    region: str
    language: str
    status: str
    ad_count: int
    spent_usd: float
    error: str | None
    created_at: UtcDatetime
    finished_at: UtcDatetime | None


class RunPage(BaseModel):
    items: list[RunOut]
    total: int
    limit: int
    offset: int


class WorkspaceOut(BaseModel):
    id: int
    name: str
    region: str
    role: str


class DashboardStats(BaseModel):
    total_runs: int
    active_runs: int
    completed_runs: int
    ads_analysed: int
    spent_this_month_usd: float
    run_spend_cap_usd: float


class InterestedVideo(BaseModel):
    title: str
    url: str
    interested_people: int
    interested_comments: int
    comments_read: int


class ViewerInterest(BaseModel):
    analysed_at: UtcDatetime
    video_count: int
    interested_people: int          # across all videos in the analysis
    top_videos: list[InterestedVideo]


class DashboardOut(BaseModel):
    workspace: WorkspaceOut
    stats: DashboardStats
    recent_runs: list[RunOut]
    can_edit: bool
    viewer_interest: ViewerInterest | None  # None until a Laya analysis has read some comments


class YouTubeVideoOut(BaseModel):
    video_id: str
    url: str
    title: str
    channel_id: str
    channel_title: str
    thumbnail_url: str
    published_at: UtcDatetime
    duration_seconds: int
    views: int
    likes: int
    comments: int
    engagement_rate: float          # (likes + comments) / views, 0 when no views


class YouTubeSummary(BaseModel):
    count: int
    total_views: int
    avg_views: int
    avg_engagement_rate: float
    top_video_id: str | None


class YouTubeCommentOut(BaseModel):
    comment_id: str
    author: str
    text: str
    likes: int
    replies: int
    published_at: UtcDatetime


class YouTubeVideoComments(BaseModel):
    video_id: str
    comments_disabled: bool         # True: the video has comments turned off, list is empty
    comments: list[YouTubeCommentOut]


class YouTubeCommentsOut(BaseModel):
    videos: list[YouTubeVideoComments]


class ComparedAd(BaseModel):
    video: YouTubeVideoOut
    views_per_day: float
    score: int                      # 0-100, rank within the compared set
    comments_disabled: bool
    top_comments: list[YouTubeCommentOut]


class YouTubeCompareOut(BaseModel):
    best: ComparedAd
    worst: ComparedAd
    ads_judged: int
    ads_too_new: int                # left out: under 3 days old or under 100 views
    analysis: Comparison


class YouTubeSearchOut(BaseModel):
    query: str
    mode: str                       # "search" (keywords) | "lookup" (pasted links / ids)
    videos: list[YouTubeVideoOut]
    summary: YouTubeSummary
