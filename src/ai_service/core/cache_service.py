"""
Simple cache service implementation.
"""

from typing import Any, Optional
import threading
import time


class CacheService:
    """Simple in-memory cache service."""

    def __init__(self, default_ttl: int = 3600):
        """Initialize cache service.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache = {}
        self._ttl = {}
        self._default_ttl = default_ttl
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key in self._cache:
                # Check if expired
                if time.time() > self._ttl.get(key, 0):
                    del self._cache[key]
                    del self._ttl[key]
                    return None
                return self._cache[key]
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (optional)
        """
        with self._lock:
            self._cache[key] = value
            expire_time = time.time() + (ttl or self._default_ttl)
            self._ttl[key] = expire_time

    def delete(self, key: str) -> bool:
        """Delete key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._ttl[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            self._ttl.clear()

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists and not expired
        """
        return self.get(key) is not None

    def size(self) -> int:
        """Get number of items in cache."""
        with self._lock:
            # Clean expired items first
            current_time = time.time()
            expired_keys = [k for k, ttl in self._ttl.items() if current_time > ttl]
            for key in expired_keys:
                del self._cache[key]
                del self._ttl[key]
            return len(self._cache)