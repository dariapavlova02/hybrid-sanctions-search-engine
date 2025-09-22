"""
Cache management for search operations including embeddings, results, and queries.
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from ..contracts import Candidate


class SearchCacheManager:
    """Manages various caches for search operations."""

    def __init__(self, ttl_minutes: int = 60):
        """Initialize cache manager with TTL settings."""
        self.ttl = timedelta(minutes=ttl_minutes)

        # Embedding cache
        self._embedding_cache: Dict[str, Tuple[List[float], datetime]] = {}
        self._embedding_cache_lock = asyncio.Lock()

        # Search result cache
        self._search_cache: Dict[str, Tuple[List[Candidate], datetime]] = {}
        self._search_cache_lock = asyncio.Lock()

        # Query cache
        self._query_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._query_cache_lock = asyncio.Lock()

    # Embedding Cache Methods
    async def get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding vector for text."""
        async with self._embedding_cache_lock:
            if text in self._embedding_cache:
                vector, timestamp = self._embedding_cache[text]
                if datetime.now() - timestamp < self.ttl:
                    return vector
                else:
                    # Remove expired entry
                    del self._embedding_cache[text]
        return None

    async def cache_embedding(self, text: str, vector: List[float]) -> None:
        """Cache embedding vector for text."""
        async with self._embedding_cache_lock:
            self._embedding_cache[text] = (vector, datetime.now())

    async def clear_embedding_cache(self) -> None:
        """Clear all cached embeddings."""
        async with self._embedding_cache_lock:
            self._embedding_cache.clear()

    async def get_embedding_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        async with self._embedding_cache_lock:
            now = datetime.now()
            valid_entries = sum(
                1 for _, timestamp in self._embedding_cache.values()
                if now - timestamp < self.ttl
            )

            return {
                "total_entries": len(self._embedding_cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self._embedding_cache) - valid_entries,
                "cache_hit_rate": None,  # Would need tracking to calculate
                "memory_usage_mb": self._estimate_cache_size_mb(self._embedding_cache)
            }

    # Search Result Cache Methods
    async def get_cached_search_result(self, cache_key: str) -> Optional[List[Candidate]]:
        """Get cached search results."""
        async with self._search_cache_lock:
            if cache_key in self._search_cache:
                candidates, timestamp = self._search_cache[cache_key]
                if datetime.now() - timestamp < self.ttl:
                    return candidates
                else:
                    del self._search_cache[cache_key]
        return None

    async def cache_search_result(self, cache_key: str, candidates: List[Candidate]) -> None:
        """Cache search results."""
        async with self._search_cache_lock:
            self._search_cache[cache_key] = (candidates, datetime.now())

    def generate_search_cache_key(self, query: str, opts: Any) -> str:
        """Generate cache key for search results."""
        # Create a deterministic key based on query and options
        opts_dict = {}
        if hasattr(opts, '__dict__'):
            opts_dict = {k: v for k, v in opts.__dict__.items()
                        if not k.startswith('_')}

        key_data = {
            "query": query,
            "opts": opts_dict
        }

        return f"search:{hash(json.dumps(key_data, sort_keys=True))}"

    async def clear_search_cache(self) -> None:
        """Clear all cached search results."""
        async with self._search_cache_lock:
            self._search_cache.clear()

    async def invalidate_search_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate search cache entries matching pattern."""
        async with self._search_cache_lock:
            if pattern is None:
                count = len(self._search_cache)
                self._search_cache.clear()
                return count

            keys_to_remove = [
                key for key in self._search_cache.keys()
                if pattern in key
            ]

            for key in keys_to_remove:
                del self._search_cache[key]

            return len(keys_to_remove)

    async def get_search_cache_stats(self) -> Dict[str, Any]:
        """Get search cache statistics."""
        async with self._search_cache_lock:
            now = datetime.now()
            valid_entries = sum(
                1 for _, timestamp in self._search_cache.values()
                if now - timestamp < self.ttl
            )

            return {
                "total_entries": len(self._search_cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self._search_cache) - valid_entries,
                "memory_usage_mb": self._estimate_cache_size_mb(self._search_cache)
            }

    # Query Cache Methods
    async def get_cached_query(self, query_key: str) -> Optional[Dict[str, Any]]:
        """Get cached query data."""
        async with self._query_cache_lock:
            if query_key in self._query_cache:
                query_data, timestamp = self._query_cache[query_key]
                if datetime.now() - timestamp < self.ttl:
                    return query_data
                else:
                    del self._query_cache[query_key]
        return None

    async def cache_query(self, query_key: str, query_data: Dict[str, Any]) -> None:
        """Cache query data."""
        async with self._query_cache_lock:
            self._query_cache[query_key] = (query_data, datetime.now())

    def generate_query_cache_key(self, query: str, search_mode: str) -> str:
        """Generate cache key for query data."""
        return f"query:{search_mode}:{hash(query)}"

    async def clear_query_cache(self) -> None:
        """Clear all cached queries."""
        async with self._query_cache_lock:
            self._query_cache.clear()

    async def get_query_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        async with self._query_cache_lock:
            now = datetime.now()
            valid_entries = sum(
                1 for _, timestamp in self._query_cache.values()
                if now - timestamp < self.ttl
            )

            return {
                "total_entries": len(self._query_cache),
                "valid_entries": valid_entries,
                "expired_entries": len(self._query_cache) - valid_entries,
                "memory_usage_mb": self._estimate_cache_size_mb(self._query_cache)
            }

    # Cleanup Methods
    async def cleanup_expired_cache_entries(self) -> int:
        """Clean up expired entries from all caches."""
        now = datetime.now()
        total_removed = 0

        # Clean embedding cache
        async with self._embedding_cache_lock:
            expired_keys = [
                key for key, (_, timestamp) in self._embedding_cache.items()
                if now - timestamp >= self.ttl
            ]
            for key in expired_keys:
                del self._embedding_cache[key]
            total_removed += len(expired_keys)

        # Clean search cache
        async with self._search_cache_lock:
            expired_keys = [
                key for key, (_, timestamp) in self._search_cache.items()
                if now - timestamp >= self.ttl
            ]
            for key in expired_keys:
                del self._search_cache[key]
            total_removed += len(expired_keys)

        # Clean query cache
        async with self._query_cache_lock:
            expired_keys = [
                key for key, (_, timestamp) in self._query_cache.items()
                if now - timestamp >= self.ttl
            ]
            for key in expired_keys:
                del self._query_cache[key]
            total_removed += len(expired_keys)

        return total_removed

    def _estimate_cache_size_mb(self, cache: Dict[str, Any]) -> float:
        """Estimate memory usage of a cache in MB."""
        # Rough estimation - in production, would use more accurate methods
        try:
            import sys
            total_size = 0
            for key, value in cache.items():
                total_size += sys.getsizeof(key)
                total_size += sys.getsizeof(value)
            return total_size / (1024 * 1024)  # Convert to MB
        except Exception:
            return 0.0  # Fallback if estimation fails