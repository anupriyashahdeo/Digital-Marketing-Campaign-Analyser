from datetime import datetime
from typing import Protocol

from pydantic import BaseModel


class VideoMeta(BaseModel):
    video_id: str
    channel_id: str
    title: str
    description: str = ""
    published_at: datetime
    views: int = 0
    likes: int = 0
    comments: int = 0


class VideoMetadataSource(Protocol):
    async def get_videos(self, video_ids: list[str]) -> list[VideoMeta]: ...
    async def channel_recent(self, channel_id: str, n: int = 30) -> list[VideoMeta]: ...
