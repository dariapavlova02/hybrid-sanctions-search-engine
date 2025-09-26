"""
Cache utilities for deterministic key generation and metrics.
"""

from typing import Any, Dict, Tuple, Union
from functools import wraps
import threading
from collections import defaultdict


def make_policy_flags_tuple(flags: Union[Dict[str, Any], None]) -> Tuple[Tuple[str, Any], ...]:
    """
    Create a deterministic tuple from policy flags for cache key generation.
    
    Args:
        flags: Dictionary of policy flags or None
        
    Returns:
        Sorted tuple of (key, value) pairs for deterministic cache keys
    """
    if not flags:
        return tuple()
    
    # Sort items to ensure deterministic ordering
    return tuple(sorted(flags.items()))


def create_cache_key(lang: str, token: str, policy_flags: Union[Dict[str, Any], None] = None) -> Tuple[str, str, Tuple[Tuple[str, Any], ...]]:
    """
    Create a cache key from language, token, and policy flags.
    
    Args:
        lang: Language code
        token: Token to cache
        policy_flags: Optional policy flags dictionary
        
    Returns:
        Tuple suitable for use as cache key
    """
    return (lang, token, make_policy_flags_tuple(policy_flags))


class CacheMetrics:
    """Thread-safe cache metrics collector."""
    
    def __init__(self):
        self._lock = threading.RLock()
        self._hits = defaultdict(int)
        self._misses = defaultdict(int)
        self._sizes = defaultdict(int)
    
    def record_hit(self, cache_name: str):
        """Record a cache hit."""
        with self._lock:
            self._hits[cache_name] += 1
    
    def record_miss(self, cache_name: str):
        """Record a cache miss."""
        with self._lock:
            self._misses[cache_name] += 1
    
    def update_size(self, cache_name: str, size: int):
        """Update cache size."""
        with self._lock:
            self._sizes[cache_name] = size
    
    def get_hit_rate(self, cache_name: str) -> float:
        """Get cache hit rate for a specific cache."""
        with self._lock:
            hits = self._hits[cache_name]
            misses = self._misses[cache_name]
            total = hits + misses
            return hits / total if total > 0 else 0.0
    
    def get_size(self, cache_name: str) -> int:
        """Get current cache size."""
        with self._lock:
            return self._sizes[cache_name]
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Union[int, float]]]:
        """Get all metrics for all caches."""
        with self._lock:
            result = {}
            for cache_name in set(list(self._hits.keys()) + list(self._misses.keys()) + list(self._sizes.keys())):
                result[cache_name] = {
                    'hits': self._hits[cache_name],
                    'misses': self._misses[cache_name],
                    'hit_rate': self.get_hit_rate(cache_name),
                    'size': self._sizes[cache_name]
                }
            return result
    
    def reset(self, cache_name: str = None):
        """Reset metrics for a specific cache or all caches."""
        with self._lock:
            if cache_name:
                self._hits[cache_name] = 0
                self._misses[cache_name] = 0
                self._sizes[cache_name] = 0
            else:
                self._hits.clear()
                self._misses.clear()
                self._sizes.clear()


# Global cache metrics instance
cache_metrics = CacheMetrics()


def lru_cache_with_metrics(maxsize: int = 128, cache_name: str = "default"):
    """
    Decorator that adds LRU caching with metrics collection.
    
    Args:
        maxsize: Maximum cache size
        cache_name: Name for metrics collection
        
    Returns:
        Decorator function
    """
    def decorator(func):
        from functools import lru_cache
        
        # Create the LRU cache
        cached_func = lru_cache(maxsize=maxsize)(func)
        
        # Wrap with metrics collection
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Convert policy_flags dict to tuple for hashing
            if len(args) >= 4 and isinstance(args[3], dict):
                # Convert policy_flags dict to tuple
                policy_flags = args[3]
                policy_flags_tuple = make_policy_flags_tuple(policy_flags)
                # Replace dict with tuple in args
                args = args[:3] + (policy_flags_tuple,) + args[4:]
            
            # Check if result is in cache
            cache_info = cached_func.cache_info()
            initial_hits = getattr(cache_info, 'hits', cache_info.get('hits', 0) if isinstance(cache_info, dict) else 0)
            initial_misses = getattr(cache_info, 'misses', cache_info.get('misses', 0) if isinstance(cache_info, dict) else 0)
            
            # Call the cached function
            try:
                result = cached_func(*args, **kwargs)
            except TypeError as e:
                if "unhashable type" in str(e):
                    # Fallback: call original function without caching
                    result = func(*args, **kwargs)
                else:
                    raise
            
            # Update metrics
            new_cache_info = cached_func.cache_info()
            new_hits = getattr(new_cache_info, 'hits', new_cache_info.get('hits', 0) if isinstance(new_cache_info, dict) else 0)
            new_misses = getattr(new_cache_info, 'misses', new_cache_info.get('misses', 0) if isinstance(new_cache_info, dict) else 0)
            currsize = getattr(new_cache_info, 'currsize', new_cache_info.get('currsize', 0) if isinstance(new_cache_info, dict) else 0)

            if new_hits > initial_hits:
                cache_metrics.record_hit(cache_name)
            elif new_misses > initial_misses:
                cache_metrics.record_miss(cache_name)

            # Update cache size
            cache_metrics.update_size(cache_name, currsize)
            
            return result
        
        # Add cache management methods
        def cache_clear():
            cached_func.cache_clear()
            cache_metrics.update_size(cache_name, 0)
        
        wrapper.cache_clear = cache_clear
        wrapper.cache_info = cached_func.cache_info
        
        return wrapper
    
    return decorator
