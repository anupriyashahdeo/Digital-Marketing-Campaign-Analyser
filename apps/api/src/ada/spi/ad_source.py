from datetime import date
from typing import Protocol

from pydantic import BaseModel


class AdRecord(BaseModel):
    video_id: str
    advertiser: str
    region: str
    first_shown: date | None = None
    last_shown: date | None = None
    variants: int = 1
    paid_confirmed: bool = False
    transcript: str | None = None


class AdSource(Protocol):
    name: str
    regions: set[str]

    async def find_ads(self, keywords: list[str], region: str) -> list[AdRecord]: ...
