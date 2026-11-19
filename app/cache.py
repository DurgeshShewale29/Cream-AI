"""In-memory thread-safe response cache for ScholarSetu queries."""

from __future__ import annotations

import threading
import time
from typing import Any


class SimpleCache:
    """Thread-safe in-memory LRU / TTL response cache for ScholarSetu queries."""

    def __init__(self, max_size: int = 1000, ttl_seconds: int = 3600) -> None:
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    @staticmethod
    def normalize_key(key: str) -> str:
        """Strip whitespace, collapse repeated spaces, and lowercase the key."""
        return " ".join(key.strip().lower().split())

    def get(self, key: str) -> Any | None:
        """Return the cached value if present and unexpired; otherwise None."""
        norm_key = self.normalize_key(key)
        with self._lock:
            entry = self._cache.get(norm_key)
            if entry is None:
                self._misses += 1
                return None
            if time.time() > entry["expires_at"]:
                del self._cache[norm_key]
                self._misses += 1
                return None
            self._hits += 1
            # Re-insert to mark as recently used
            self._cache[norm_key] = entry
            return entry["value"]

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store a value in the cache with an optional custom TTL in seconds."""
        norm_key = self.normalize_key(key)
        ttl_val = self.ttl_seconds if ttl is None else ttl
        expires_at = time.time() + ttl_val
        with self._lock:
            if len(self._cache) >= self.max_size and norm_key not in self._cache:
                # Evict oldest entry (first inserted key in dict)
                oldest = next(iter(self._cache))
                del self._cache[oldest]
            self._cache[norm_key] = {"value": value, "expires_at": expires_at}

    def clear(self) -> None:
        """Clear all entries and reset hit/miss counters."""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def stats(self) -> dict[str, Any]:
        """Return cache performance statistics."""
        with self._lock:
            total = self._hits + self._misses
            ratio = (self._hits / total) if total > 0 else 0.0
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_ratio": round(ratio, 4),
            }


# Global shared cache instance for RAG answers and queries
query_cache = SimpleCache(max_size=1000, ttl_seconds=3600)
