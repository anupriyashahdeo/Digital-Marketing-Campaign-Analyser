"""Channel-relative engagement: compare a video to the SAME channel's recent videos."""
from dataclasses import dataclass
from datetime import datetime
from statistics import mean, pstdev


@dataclass
class VideoStats:
    views: int
    likes: int
    comments: int
    published_at: datetime


def views_per_day(v: VideoStats, now: datetime) -> float:
    days = max((now - v.published_at).days, 1)
    return v.views / days


def engagement_rate(v: VideoStats) -> float:
    return (v.likes + 2 * v.comments) / max(v.views, 1)


def zscore(value: float, sample: list[float]) -> float | None:
    if len(sample) < 5:           # too little history -> no claim
        return None
    sd = pstdev(sample)
    if sd == 0:
        return 0.0
    return (value - mean(sample)) / sd


def engagement_z(video: VideoStats, channel_history: list[VideoStats], now: datetime) -> float | None:
    """Average of z(views/day) and z(engagement rate) vs channel's own history."""
    zs = [
        zscore(views_per_day(video, now), [views_per_day(h, now) for h in channel_history]),
        zscore(engagement_rate(video), [engagement_rate(h) for h in channel_history]),
    ]
    zs = [z for z in zs if z is not None]
    return sum(zs) / len(zs) if zs else None
