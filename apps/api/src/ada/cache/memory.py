"""Cache key = hash(text + question-set version). Swap the dict for Redis in production."""
import hashlib


def cache_key(text: str, qs_version: str) -> str:
    return hashlib.sha256(f"{qs_version}\n{text}".encode()).hexdigest()


class MemoryCache:
    def __init__(self):
        self._d: dict = {}

    def get(self, k):
        return self._d.get(k)

    def set(self, k, v):
        self._d[k] = v
