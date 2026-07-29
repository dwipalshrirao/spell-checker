import time
from collections import OrderedDict

from config import settings


class CacheService:
    def __init__(self):
        self._store: OrderedDict[str, tuple[float, dict]] = OrderedDict()
        self._max_size = settings.cache_max_size
        self._ttl = settings.cache_ttl_seconds

    def _make_key(self, text: str, model: str) -> str:
        return f"{model}::{text.strip().lower()}"

    def get(self, text: str, model: str) -> dict | None:
        key = self._make_key(text, model)
        if key not in self._store:
            return None
        ts, value = self._store[key]
        if time.monotonic() - ts > self._ttl:
            del self._store[key]
            return None
        self._store.move_to_end(key)
        return value

    def set(self, text: str, model: str, value: dict):
        key = self._make_key(text, model)
        self._store[key] = (time.monotonic(), value)
        while len(self._store) > self._max_size:
            self._store.popitem(last=False)

    def clear(self):
        self._store.clear()

    @property
    def size(self) -> int:
        return len(self._store)
