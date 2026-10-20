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
    channel_title: str = ""
    thumbnail_url: str = ""
    duration_seconds: int = 0


class VideoComment(BaseModel):
    comment_id: str
    author: str
    text: str
    likes: int = 0
    replies: int = 0
    published_at: datetime


class VideoMetadataSource(Protocol):
    async def get_videos(self, video_ids: list[str]) -> list[VideoMeta]: ...
    async def search(self, query: str, region: str, language: str, n: int = 10,
                     order: str = "relevance") -> list[VideoMeta]: ...
    async def top_comments(self, video_id: str, n: int = 10) -> list[VideoComment] | None: ...
