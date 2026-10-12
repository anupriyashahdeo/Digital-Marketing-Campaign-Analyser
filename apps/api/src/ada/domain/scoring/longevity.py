from datetime import date


def run_days(first: date | None, last: date | None) -> int | None:
    if not first or not last:
        return None
    return max((last - first).days, 0) + 1
