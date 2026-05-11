import time
import hashlib
from collections import OrderedDict
from typing import Optional, Dict, Any
from core.logging import logger


class ExplanationCache:
    def __init__(self, max_size: int = 10000, ttl_seconds: int = 3600):
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._cache: OrderedDict[str, tuple[Dict[str, Any], float]] = OrderedDict()

    def _make_key(self, feature_hash: str, symbol: str, class_idx: int) -> str:
        raw = f"{feature_hash}:{symbol}:{class_idx}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]

    def get(self, feature_hash: str, symbol: str, class_idx: int) -> Optional[Dict[str, Any]]:
        key = self._make_key(feature_hash, symbol, class_idx)
        entry = self._cache.get(key)
        if entry is None:
            return None
        data, ts = entry
        if (time.monotonic() - ts) > self._ttl:
            del self._cache[key]
            return None
        self._cache.move_to_end(key)
        return data

    def set(self, feature_hash: str, symbol: str, class_idx: int, explanation: Dict[str, Any]):
        key = self._make_key(feature_hash, symbol, class_idx)
        self._cache[key] = (explanation, time.monotonic())
        self._cache.move_to_end(key)
        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def clear(self):
        self._cache.clear()

    def stats(self) -> dict:
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "ttl_seconds": self._ttl,
        }
