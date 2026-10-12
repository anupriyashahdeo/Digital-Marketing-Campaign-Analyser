from typing import Protocol


class Transcriber(Protocol):
    async def transcribe(self, audio_path: str, language: str) -> str: ...
