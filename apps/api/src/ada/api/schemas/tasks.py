"""Shapes for the task queue: what the browser sees, and what the model worker may send back.

The worker runs on another machine, so its output is treated as untrusted input: every field
is typed and bounded, unknown fields are dropped, and links are rebuilt here from the video id
(an uploaded CSV could otherwise smuggle a javascript: URL into a link the browser renders).
"""
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ada.api.schemas import UtcDatetime

VIDEO_ID = r"^[A-Za-z0-9_-]{11}$"
TaskStatus = Literal["queued", "processing", "done", "failed"]

Text = Annotated[str, StringConstraints(max_length=5000)]
Short = Annotated[str, StringConstraints(max_length=100)]
Count = Annotated[int, Field(ge=0, le=10**13)]
Pct = Annotated[int, Field(ge=0, le=100)]
Rate = Annotated[float, Field(ge=0, le=1000)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)


class AdInsightRow(_Strict):
    video_id: str = Field(pattern=VIDEO_ID)
    title: Annotated[str, StringConstraints(max_length=500)] = ""
    channel: Annotated[str, StringConstraints(max_length=200)] = ""
    url: str = ""
    views: Count
    duration_seconds: Count = 0
    engagement_rate: Rate = 0.0
    million_views: bool
    comments_read: Count
    positive_pct: Pct | None
    negative_pct: Pct | None
    reception: Literal["loved", "liked", "mixed", "disliked", "no comments"]
    best_comment: Text = ""
    worst_comment: Text = ""
    main_complaint: Short = ""
    age_group_guess: Short = "unknown"
    age_hints: Count = 0
    interested_comments: Count = 0
    interested_people: Count | None = None

    @model_validator(mode="after")
    def _safe_url(self):
        self.url = f"https://www.youtube.com/watch?v={self.video_id}"
        return self


class AdBrief(_Strict):
    video_id: str = Field(pattern=VIDEO_ID)
    title: Annotated[str, StringConstraints(max_length=500)] = ""
    views: Count
    engagement_rate: Rate
    reception: Literal["loved", "liked", "mixed", "disliked", "no comments"]


class LengthBucket(_Strict):
    ads: Count
    avg_engagement_rate: Rate


class InsightSummary(_Strict):
    videos: Count
    million_view_ads: Count
    best_ads: list[AdBrief] = Field(max_length=50)
    worst_received: list[AdBrief] = Field(max_length=50)
    top_complaints: dict[Short, Count] = Field(max_length=50)
    engagement_by_length: dict[Short, LengthBucket] = Field(max_length=20)
    age_groups_from_comments: dict[Short, Count] = Field(max_length=20)


class InsightReport(_Strict):
    """Exactly what ada.pipeline.youtube_insights.analyse_csv returns."""
    videos: list[AdInsightRow] = Field(max_length=500)
    summary: InsightSummary


class TaskResultIn(_Strict):
    """Worker -> API. Send `output`, or `error` (with retry=true for a temporary failure)."""
    lease_token: str = Field(min_length=20, max_length=64)
    output: InsightReport | None = None
    error: Annotated[str, StringConstraints(max_length=500)] | None = None
    retry: bool = False

    @model_validator(mode="after")
    def _one_of(self):
        if (self.output is None) == (self.error is None):
            raise ValueError("send exactly one of output or error")
        return self


class TaskClaimOut(BaseModel):
    """API -> worker: the next CSV to process."""
    task_id: str
    kind: str
    lease_token: str
    lease_seconds: int
    attempt: int
    task_input: str


class TaskCreatedOut(BaseModel):
    task_id: str
    status: TaskStatus
    poll_after_seconds: int


class TaskOut(BaseModel):
    """API -> browser."""
    task_id: str
    status: TaskStatus
    task_complete: int
    created_at: UtcDatetime
    completed_at: UtcDatetime | None
    error: str | None
    output: dict | None
