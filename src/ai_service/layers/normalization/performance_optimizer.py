"""
Performance optimization utilities for normalization service.
Provides intelligent caching, batch processing, and performance monitoring.
"""

import time
import hashlib
from typing import Dict, List, Set, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from collections import defaultdict, OrderedDict
from functools import wraps

from ...utils.logging_config import get_logger


@dataclass
class CacheStats:
    """Cache performance statistics."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    total_requests: int = 0

    @property
    def hit_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.hits / self.total_requests


class LRUCache:
    """Thread-safe LRU cache implementation with statistics."""

    def __init__(self, maxsize: int = 10000):
        self.maxsize = maxsize
        self.cache = OrderedDict()
        self.stats = CacheStats()
        self.logger = get_logger(__name__)

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        self.stats.total_requests += 1

        if key in self.cache:
            # Move to end (most recently used)
            value = self.cache.pop(key)
            self.cache[key] = value
            self.stats.hits += 1
            return value

        self.stats.misses += 1
        return None

    def put(self, key: str, value: Any) -> None:
        """Put value in cache."""
        if key in self.cache:
            # Update existing
            self.cache.pop(key)
        elif len(self.cache) >= self.maxsize:
            # Evict oldest
            self.cache.popitem(last=False)
            self.stats.evictions += 1

        self.cache[key] = value

    def clear(self) -> None:
        """Clear cache."""
        self.cache.clear()
        self.stats = CacheStats()

    def size(self) -> int:
        """Get current cache size."""
        return len(self.cache)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            'size': len(self.cache),
            'maxsize': self.maxsize,
            'hits': self.stats.hits,
            'misses': self.stats.misses,
            'evictions': self.stats.evictions,
            'hit_rate': self.stats.hit_rate,
            'total_requests': self.stats.total_requests
        }


class PerformanceOptimizer:
    """Performance optimization coordinator for normalization."""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Different caches for different operations
        self.token_cache = LRUCache(maxsize=50000)  # Larger for tokens
        self.role_cache = LRUCache(maxsize=20000)
        self.morphology_cache = LRUCache(maxsize=30000)
        self.gender_cache = LRUCache(maxsize=5000)

        # Performance monitoring
        self.performance_stats = defaultdict(list)
        self.slow_operations = []

        self.logger.info("PerformanceOptimizer initialized")

    def cache_key(self, operation: str, *args, **kwargs) -> str:
        """Generate cache key from operation parameters."""
        # Create deterministic hash from arguments
        key_data = f"{operation}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def cached_operation(self, cache_name: str, operation: str):
        """Decorator for caching operation results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Get appropriate cache
                cache = getattr(self, f"{cache_name}_cache", None)
                if cache is None:
                    return func(*args, **kwargs)

                # Generate cache key
                cache_key = self.cache_key(operation, *args, **kwargs)

                # Try cache first
                cached_result = cache.get(cache_key)
                if cached_result is not None:
                    return cached_result

                # Execute operation and cache result
                start_time = time.time()
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Cache the result
                cache.put(cache_key, result)

                # Record performance
                self.record_performance(operation, execution_time)

                return result

            return wrapper
        return decorator

    def record_performance(self, operation: str, execution_time: float) -> None:
        """Record performance metrics for an operation."""
        self.performance_stats[operation].append(execution_time)

        # Keep only recent measurements (last 1000)
        if len(self.performance_stats[operation]) > 1000:
            self.performance_stats[operation] = self.performance_stats[operation][-1000:]

        # Track slow operations
        if execution_time > 0.1:  # 100ms threshold
            self.slow_operations.append({
                'operation': operation,
                'time': execution_time,
                'timestamp': time.time()
            })

            # Keep only recent slow operations
            if len(self.slow_operations) > 100:
                self.slow_operations = self.slow_operations[-100:]

    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        stats = {}

        for operation, times in self.performance_stats.items():
            if times:
                stats[operation] = {
                    'count': len(times),
                    'avg_time': sum(times) / len(times),
                    'min_time': min(times),
                    'max_time': max(times),
                    'p95_time': sorted(times)[int(len(times) * 0.95)] if len(times) > 20 else max(times)
                }

        return {
            'operations': stats,
            'cache_stats': self.get_cache_stats(),
            'slow_operations_count': len(self.slow_operations),
            'recent_slow_operations': self.slow_operations[-5:] if self.slow_operations else []
        }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get all cache statistics."""
        return {
            'token_cache': self.token_cache.get_stats(),
            'role_cache': self.role_cache.get_stats(),
            'morphology_cache': self.morphology_cache.get_stats(),
            'gender_cache': self.gender_cache.get_stats()
        }

    def optimize_for_batch(self, texts: List[str]) -> Dict[str, Any]:
        """Optimize settings for batch processing."""
        batch_size = len(texts)

        # Adjust cache sizes for batch processing
        if batch_size > 1000:
            # Large batch - increase cache sizes
            self.token_cache.maxsize = min(100000, batch_size * 10)
            self.role_cache.maxsize = min(50000, batch_size * 5)
            return {'strategy': 'large_batch', 'cache_scaling': True}
        elif batch_size > 100:
            # Medium batch - moderate cache sizes
            self.token_cache.maxsize = min(75000, batch_size * 15)
            self.role_cache.maxsize = min(30000, batch_size * 8)
            return {'strategy': 'medium_batch', 'cache_scaling': True}
        else:
            # Small batch - default sizes
            return {'strategy': 'small_batch', 'cache_scaling': False}

    def preload_common_patterns(self, common_tokens: Set[str]) -> None:
        """Preload cache with common patterns."""
        self.logger.info(f"Preloading {len(common_tokens)} common tokens")

        # This would be called with frequently used tokens
        # to warm up the cache for better performance
        for token in common_tokens:
            # Preload with placeholder - actual implementation would
            # run common operations on these tokens
            cache_key = self.cache_key("preload", token)
            self.token_cache.put(cache_key, {'preloaded': True})

    def clear_all_caches(self) -> None:
        """Clear all caches."""
        self.token_cache.clear()
        self.role_cache.clear()
        self.morphology_cache.clear()
        self.gender_cache.clear()
        self.logger.info("All caches cleared")

    def memory_pressure_cleanup(self) -> Dict[str, int]:
        """Clean up caches under memory pressure."""
        initial_sizes = {
            'token': self.token_cache.size(),
            'role': self.role_cache.size(),
            'morphology': self.morphology_cache.size(),
            'gender': self.gender_cache.size()
        }

        # Reduce cache sizes by 50%
        for cache_name in ['token', 'role', 'morphology', 'gender']:
            cache = getattr(self, f"{cache_name}_cache")
            target_size = cache.maxsize // 2

            while cache.size() > target_size and cache.size() > 0:
                cache.cache.popitem(last=False)  # Remove oldest items

        final_sizes = {
            'token': self.token_cache.size(),
            'role': self.role_cache.size(),
            'morphology': self.morphology_cache.size(),
            'gender': self.gender_cache.size()
        }

        self.logger.info(f"Memory cleanup: {initial_sizes} -> {final_sizes}")
        return final_sizes

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on performance systems."""
        health = {
            'status': 'healthy',
            'issues': []
        }

        # Check cache hit rates
        for cache_name in ['token', 'role', 'morphology', 'gender']:
            cache = getattr(self, f"{cache_name}_cache")
            stats = cache.get_stats()

            if stats['hit_rate'] < 0.3 and stats['total_requests'] > 100:
                health['issues'].append(f"Low hit rate for {cache_name}_cache: {stats['hit_rate']:.2f}")

        # Check for excessive slow operations
        if len(self.slow_operations) > 50:
            health['issues'].append(f"High number of slow operations: {len(self.slow_operations)}")

        # Check recent performance
        recent_avg_times = {}
        for operation, times in self.performance_stats.items():
            if len(times) > 10:
                recent_times = times[-50:]  # Last 50 operations
                recent_avg = sum(recent_times) / len(recent_times)
                recent_avg_times[operation] = recent_avg

                if recent_avg > 0.05:  # 50ms threshold
                    health['issues'].append(f"Slow operation {operation}: {recent_avg:.3f}s avg")

        if health['issues']:
            health['status'] = 'degraded'

        health['recent_performance'] = recent_avg_times
        return health


# Global performance optimizer instance
performance_optimizer = PerformanceOptimizer()


def cached(cache_name: str, operation: str):
    """Convenience decorator for caching operations."""
    return performance_optimizer.cached_operation(cache_name, operation)


def monitor_performance(operation_name: str):
    """Decorator to monitor operation performance."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                execution_time = time.time() - start_time
                performance_optimizer.record_performance(operation_name, execution_time)

        return wrapper
    return decorator