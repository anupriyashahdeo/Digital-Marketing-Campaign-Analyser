from typing import Protocol


class Vision(Protocol):
    async def describe_frames(self, frame_paths: list[str]) -> str: ...
