"""Performance monitoring utilities"""

import functools
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


def monitor_performance(func_name: str = None):
    """Decorator to monitor function performance"""

    def decorator(func: Callable) -> Callable:
        name = func_name or f"{func.__module__}.{func.__name__}"

        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # Log slow operations (> 100ms)
                if execution_time > 0.1:
                    logger.warning(f"Slow operation: {name} took {execution_time:.3f}s")
                else:
                    logger.debug(f"Performance: {name} took {execution_time:.3f}s")

                return result

            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Error in {name} after {execution_time:.3f}s: {e}")
                raise

        return wrapper

    return decorator


def monitor_memory_usage(func: Callable) -> Callable:
    """Decorator to monitor memory usage (basic version)"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        # Basic memory monitoring without psutil dependency
        # Just track large input sizes for now
        try:
            # Check if first argument is a string and monitor its size
            if args and isinstance(args[0], str) and len(args[0]) > 1000:
                logger.info(f"Processing large input: {len(args[0])} characters")

            return func(*args, **kwargs)

        except MemoryError as e:
            logger.error(f"Memory error in {func.__name__}: {e}")
            raise

        except Exception as e:
            # Re-raise other exceptions
            raise

    return wrapper


class PerformanceTracker:
    """Simple performance tracking class"""

    def __init__(self):
        self.stats = {}

    def track_operation(self, operation_name: str, execution_time: float):
        """Track operation performance"""
        if operation_name not in self.stats:
            self.stats[operation_name] = {
                "count": 0,
                "total_time": 0.0,
                "min_time": float("inf"),
                "max_time": 0.0,
            }

        stats = self.stats[operation_name]
        stats["count"] += 1
        stats["total_time"] += execution_time
        stats["min_time"] = min(stats["min_time"], execution_time)
        stats["max_time"] = max(stats["max_time"], execution_time)

    def get_stats(self) -> dict:
        """Get performance statistics"""
        result = {}
        for operation, stats in self.stats.items():
            if stats["count"] > 0:
                result[operation] = {
                    "count": stats["count"],
                    "total_time": stats["total_time"],
                    "avg_time": stats["total_time"] / stats["count"],
                    "min_time": stats["min_time"],
                    "max_time": stats["max_time"],
                }
        return result

    def reset_stats(self):
        """Reset all statistics"""
        self.stats.clear()


# Global performance tracker instance
performance_tracker = PerformanceTracker()
