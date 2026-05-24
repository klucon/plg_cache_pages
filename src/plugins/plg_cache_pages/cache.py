from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class _Entry:
    value: object
    expires_at: float


class PageCache:
    """Thread-safe in-memory TTL cache with a hard cap on entry count."""

    def __init__(self, default_ttl: int = 300, max_entries: int = 500) -> None:
        self.default_ttl = default_ttl
        self.max_entries = max_entries
        self._store: dict[str, _Entry] = {}
        self._lock = Lock()
        self.hits = 0
        self.misses = 0

    # ------------------------------------------------------------------

    def get(self, key: str) -> object | None:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                self.misses += 1
                return None
            if entry.expires_at < time.monotonic():
                del self._store[key]
                self.misses += 1
                return None
            self.hits += 1
            return entry.value

    def set(self, key: str, value: object, ttl: int | None = None) -> None:
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.monotonic() + effective_ttl
        with self._lock:
            if key not in self._store and len(self._store) >= self.max_entries:
                self._evict_one()
            self._store[key] = _Entry(value=value, expires_at=expires_at)

    def invalidate(self, key: str) -> bool:
        with self._lock:
            return self._store.pop(key, None) is not None

    def invalidate_prefix(self, prefix: str) -> int:
        with self._lock:
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)

    def clear(self) -> int:
        with self._lock:
            count = len(self._store)
            self._store.clear()
            self.hits = 0
            self.misses = 0
            return count

    def stats(self) -> dict:
        with self._lock:
            self._purge_expired()
            return {
                "entries": len(self._store),
                "max_entries": self.max_entries,
                "default_ttl": self.default_ttl,
                "hits": self.hits,
                "misses": self.misses,
            }

    # ------------------------------------------------------------------

    def _evict_one(self) -> None:
        """Evict the entry closest to expiry (called with lock held)."""
        if not self._store:
            return
        oldest = min(self._store, key=lambda k: self._store[k].expires_at)
        del self._store[oldest]

    def _purge_expired(self) -> None:
        now = time.monotonic()
        expired = [k for k, e in self._store.items() if e.expires_at < now]
        for k in expired:
            del self._store[k]

    def reconfigure(self, *, default_ttl: int, max_entries: int) -> None:
        with self._lock:
            self.default_ttl = default_ttl
            self.max_entries = max_entries


# Module-level singleton — importable by other extensions
page_cache: PageCache = PageCache()
