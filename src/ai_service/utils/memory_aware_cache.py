"""
Memory-aware cache system with pressure handling and automatic cleanup.
"""

import gc
import logging
import threading
import time

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
from functools import lru_cache, wraps
from typing import Any, Callable, Dict, Optional, Union
from weakref import WeakSet

logger = logging.getLogger(__name__)

class MemoryPressureMonitor:
    """Monitor system memory pressure and manage cache cleanup."""

    def __init__(self,
                 warning_threshold: float = 0.80,
                 critical_threshold: float = 0.90,
                 check_interval: float = 30.0):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.check_interval = check_interval
        self.registered_caches: WeakSet = WeakSet()
        self._monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def register_cache(self, cache_obj: Any) -> None:
        """Register a cache object for memory pressure cleanup."""
        with self._lock:
            self.registered_caches.add(cache_obj)
            if not self._monitoring:
                self._start_monitoring()

    def _start_monitoring(self) -> None:
        """Start memory pressure monitoring thread."""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._monitoring = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_memory,
            daemon=True,
            name="MemoryPressureMonitor"
        )
        self._monitor_thread.start()
        logger.info("Started memory pressure monitoring")

    def _monitor_memory(self) -> None:
        """Monitor memory usage and cleanup caches when needed."""
        if not HAS_PSUTIL:
            logger.warning("psutil not available, memory monitoring disabled")
            return

        while self._monitoring:
            try:
                memory_percent = psutil.virtual_memory().percent / 100.0

                if memory_percent >= self.critical_threshold:
                    logger.warning(f"Critical memory pressure: {memory_percent:.1%}")
                    self._cleanup_caches(aggressive=True)
                elif memory_percent >= self.warning_threshold:
                    logger.info(f"Memory pressure warning: {memory_percent:.1%}")
                    self._cleanup_caches(aggressive=False)

                time.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"Memory monitoring error: {e}")
                time.sleep(self.check_interval * 2)  # Back off on errors

    def _cleanup_caches(self, aggressive: bool = False) -> None:
        """Cleanup registered caches based on memory pressure."""
        cleaned_count = 0

        with self._lock:
            # Create a list to avoid iteration issues with WeakSet
            caches_to_clean = list(self.registered_caches)

        for cache_obj in caches_to_clean:
            try:
                if hasattr(cache_obj, 'memory_pressure_cleanup'):
                    cache_obj.memory_pressure_cleanup(aggressive)
                    cleaned_count += 1
                elif hasattr(cache_obj, 'cache_clear'):
                    cache_obj.cache_clear()
                    cleaned_count += 1
                elif hasattr(cache_obj, 'clear'):
                    cache_obj.clear()
                    cleaned_count += 1
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")

        if cleaned_count > 0:
            # Force garbage collection after cache cleanup
            gc.collect()
            logger.info(f"Cleaned {cleaned_count} caches, forced GC")

    def stop_monitoring(self) -> None:
        """Stop memory pressure monitoring."""
        self._monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=5.0)

# Global memory monitor instance
_memory_monitor = MemoryPressureMonitor()

class MemoryAwareLRUCache:
    """LRU Cache with memory pressure awareness and automatic cleanup."""

    def __init__(self, maxsize: int = 128, typed: bool = False):
        self.maxsize = maxsize
        self.typed = typed
        self._cache: Dict[Any, Any] = {}
        self._access_order: list = []
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0

        # Register with memory monitor
        _memory_monitor.register_cache(self)

    def __call__(self, func: Callable) -> Callable:
        """Decorator to create memory-aware cached function."""

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create cache key
            key = self._make_key(args, kwargs)

            with self._lock:
                # Check if in cache
                if key in self._cache:
                    self._hits += 1
                    # Move to end (most recently used)
                    self._access_order.remove(key)
                    self._access_order.append(key)
                    return self._cache[key]

                # Not in cache - compute value
                self._misses += 1
                result = func(*args, **kwargs)

                # Add to cache
                self._cache[key] = result
                self._access_order.append(key)

                # Enforce size limit (handle None maxsize for unlimited)
                while self.maxsize is not None and len(self._cache) > self.maxsize:
                    oldest_key = self._access_order.pop(0)
                    del self._cache[oldest_key]

                return result

        # Add cache management methods
        wrapper.cache_info = self.cache_info
        wrapper.cache_clear = self.cache_clear
        wrapper.memory_pressure_cleanup = self.memory_pressure_cleanup

        return wrapper

    def _make_key(self, args: tuple, kwargs: dict) -> tuple:
        """Create cache key from arguments."""
        key = args
        if kwargs:
            key += tuple(sorted(kwargs.items()))
        if self.typed:
            key += tuple(type(arg) for arg in args)
            if kwargs:
                key += tuple(type(v) for v in kwargs.values())
        return key

    def cache_info(self) -> Dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            return {
                'hits': self._hits,
                'misses': self._misses,
                'maxsize': self.maxsize,
                'currsize': len(self._cache),
                'hit_rate': self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0.0
            }

    def cache_clear(self) -> None:
        """Clear the entire cache."""
        with self._lock:
            self._cache.clear()
            self._access_order.clear()

    def memory_pressure_cleanup(self, aggressive: bool = False) -> None:
        """Cleanup cache entries based on memory pressure."""
        with self._lock:
            if not self._cache:
                return

            if aggressive:
                # Clear everything in aggressive mode
                self.cache_clear()
                logger.debug("Aggressive cache cleanup: cleared all entries")
            else:
                # Clear oldest half of entries
                entries_to_remove = len(self._cache) // 2
                for _ in range(entries_to_remove):
                    if self._access_order:
                        oldest_key = self._access_order.pop(0)
                        if oldest_key in self._cache:
                            del self._cache[oldest_key]

                logger.debug(f"Memory pressure cleanup: removed {entries_to_remove} cache entries")

def memory_aware_lru_cache(maxsize=128, typed=False):
    """
    Memory-aware LRU cache decorator that automatically manages memory pressure.

    This is a drop-in replacement for functools.lru_cache that includes:
    - Automatic cleanup during memory pressure
    - Memory usage monitoring
    - Statistics and introspection

    Args:
        maxsize: Maximum number of cached entries or function (if used without parentheses)
        typed: Whether to cache based on argument types

    Returns:
        Decorator function or decorated function (Pydantic-compatible)
    """
    # Support both @memory_aware_lru_cache and @memory_aware_lru_cache() syntax
    # This is needed for Pydantic compatibility
    def decorator(func: Callable) -> Callable:
        cache = MemoryAwareLRUCache(maxsize=maxsize, typed=typed)
        return cache(func)

    # If called without parentheses, maxsize is actually the function
    if callable(maxsize):
        func = maxsize
        cache = MemoryAwareLRUCache(maxsize=128, typed=False)  # default values
        return cache(func)

    return decorator

# Legacy compatibility wrapper
def enhanced_lru_cache(maxsize: int = 128) -> Callable:
    """Enhanced LRU cache with memory pressure handling (legacy alias)."""
    return memory_aware_lru_cache(maxsize=maxsize)

# Function to patch existing lru_cache usage
def patch_lru_cache_with_memory_awareness():
    """
    Monkey patch to replace existing lru_cache with memory-aware version.

    This can be called at startup to automatically upgrade all lru_cache usage.
    """

    import functools

    # Store original for fallback
    functools._original_lru_cache = functools.lru_cache

    # Replace lru_cache with our memory-aware version
    # This now supports both @lru_cache and @lru_cache() syntax
    functools.lru_cache = memory_aware_lru_cache
    logger.info("Patched functools.lru_cache with memory-aware version")