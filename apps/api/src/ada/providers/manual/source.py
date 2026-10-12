"""Manual import: one video URL/ID per CSV row. Safest source; always available."""
import csv
import io
import re

from ada.spi.ad_source import AdRecord

_ID = re.compile(r"(?:v=|youtu\.be/|shorts/)([A-Za-z0-9_-]{11})")


def parse_csv(content: str, region: str = "IN") -> list[AdRecord]:
    out = []
    for row in csv.DictReader(io.StringIO(content)):
        url = (row.get("url") or "").strip()
        m = _ID.search(url) or (re.fullmatch(r"[A-Za-z0-9_-]{11}", url) and None)
        vid = m.group(1) if m else (url if re.fullmatch(r"[A-Za-z0-9_-]{11}", url) else None)
        if vid:
            out.append(AdRecord(video_id=vid, advertiser=row.get("advertiser", ""), region=region))
    return out
