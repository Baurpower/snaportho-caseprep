"""Small thread-safe TTL + LRU caches for the CasePrep v1.1 web pipeline.

In-process only (single-instance deployment). Registry writes call
``invalidate_resolution_caches`` so alias/content edits take effect
immediately; TTLs are the fallback when the write path is bypassed.
"""

from __future__ import annotations

import os
import re
import threading
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, "") or default)
    except ValueError:
        return default


class TtlCache:
    """OrderedDict-backed LRU with per-entry TTL. Thread-safe."""

    def __init__(self, *, max_size: int, ttl_seconds: float, name: str = "") -> None:
        self.name = name
        self.max_size = max(1, int(max_size))
        self.ttl_seconds = float(ttl_seconds)
        self._lock = threading.Lock()
        self._entries: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        now = time.monotonic()
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            expires_at, value = entry
            if now >= expires_at:
                del self._entries[key]
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, *, ttl_seconds: Optional[float] = None) -> None:
        ttl = self.ttl_seconds if ttl_seconds is None else float(ttl_seconds)
        expires_at = time.monotonic() + ttl
        with self._lock:
            self._entries[key] = (expires_at, value)
            self._entries.move_to_end(key)
            while len(self._entries) > self.max_size:
                self._entries.popitem(last=False)

    def invalidate(self, key: str) -> None:
        with self._lock:
            self._entries.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def stats(self) -> dict:
        with self._lock:
            return {
                "name": self.name,
                "size": len(self._entries),
                "max_size": self.max_size,
                "ttl_seconds": self.ttl_seconds,
                "hits": self._hits,
                "misses": self._misses,
            }


def normalize_cache_key(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


# TTLs are env-tunable so production can shorten them without a deploy.
resolution_cache = TtlCache(
    max_size=512,
    ttl_seconds=_env_float("CASEPREP_V1_1_CACHE_TTL_RESOLUTION", 6 * 3600),
    name="resolution",
)
# Unresolved prompts get a short TTL so registry fixes surface quickly.
RESOLUTION_MISS_TTL_SECONDS = _env_float("CASEPREP_V1_1_CACHE_TTL_RESOLUTION_MISS", 60)

retrieval_cache = TtlCache(
    max_size=256,
    ttl_seconds=_env_float("CASEPREP_V1_1_CACHE_TTL_RETRIEVAL", 3600),
    name="retrieval",
)

enrichment_cache = TtlCache(
    max_size=256,
    ttl_seconds=_env_float("CASEPREP_V1_1_CACHE_TTL_ENRICHMENT", 24 * 3600),
    name="enrichment",
)


def invalidate_resolution_caches() -> None:
    """Called by registry writes: alias/content edits must take effect now."""
    resolution_cache.clear()
    retrieval_cache.clear()
    enrichment_cache.clear()


def cache_stats() -> dict:
    return {
        "resolution": resolution_cache.stats(),
        "retrieval": retrieval_cache.stats(),
        "enrichment": enrichment_cache.stats(),
    }
