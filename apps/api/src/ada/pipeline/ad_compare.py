"""Best ad vs worst ad: rank a set of YouTube ads on public numbers, then explain the gap.

Ranking is within the set, so a small brand's search isn't judged against Nike. Each ad scores
the average of its percentile rank on views per day and on engagement rate (0-100). Views per day
stops old ads winning just by being old; engagement stops a big media budget winning on reach alone.
Ads under MIN_AGE_DAYS old or with under MIN_VIEWS views aren't judged (their numbers are still
moving), unless that leaves fewer than 2 ads.

Public numbers can't prove paid performance (docs/scoring-methodology.md): this says which ad
viewers responded to, not which one made money.
"""
from datetime import UTC, datetime

from ada.spi.comparer import AdEvidence
from ada.spi.video_metadata import VideoMeta

MIN_AGE_DAYS = 3
MIN_VIEWS = 100


def _age_days(v: VideoMeta, now: datetime) -> float:
    return max((now - v.published_at).total_seconds() / 86400, 0.0)


def _percentiles(values: list[float]) -> list[float]:
    """0 for the lowest, 1 for the highest; ties share the average of their places."""
    n = len(values)
    if n < 2:
        return [0.5] * n
    return [(sum(x < v for x in values) + (sum(x == v for x in values) - 1) / 2) / (n - 1)
            for v in values]


def rank(videos: list[VideoMeta], now: datetime | None = None) -> tuple[list[AdEvidence], int]:
    """Judged ads, best first, and how many were left out as too new / too few views."""
    now = now or datetime.now(UTC)
    judged = [v for v in videos if _age_days(v, now) >= MIN_AGE_DAYS and v.views >= MIN_VIEWS]
    if len(judged) < 2:
        judged = list(videos)
    per_day = [v.views / max(_age_days(v, now), 1.0) for v in judged]
    engagement = [(v.likes + v.comments) / v.views if v.views else 0.0 for v in judged]
    ads = [AdEvidence(video=v, views_per_day=round(d, 1), engagement_rate=round(e, 4),
                      score=round(50 * (pd + pe)))
           for v, d, e, pd, pe in zip(judged, per_day, engagement, _percentiles(per_day),
                                      _percentiles(engagement), strict=True)]
    ads.sort(key=lambda a: (a.score, a.views_per_day), reverse=True)
    return ads, len(videos) - len(judged)
