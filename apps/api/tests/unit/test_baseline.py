from datetime import datetime, timedelta

from ada.domain.scoring.baseline import VideoStats, engagement_z

NOW = datetime(2026, 10, 12)


def vs(views, age_days):
    return VideoStats(views, views // 20, views // 200, NOW - timedelta(days=age_days))


def test_big_old_video_is_not_automatically_above_baseline():
    history = [vs(2_000_000, 1400 + i) for i in range(10)]   # channel always gets ~2M
    z = engagement_z(vs(2_000_000, 1400), history, NOW)
    assert z is not None and abs(z) < 1


def test_too_little_history_makes_no_claim():
    assert engagement_z(vs(1000, 10), [vs(900, 10)], NOW) is None
