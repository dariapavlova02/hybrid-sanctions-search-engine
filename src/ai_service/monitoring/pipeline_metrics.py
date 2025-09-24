"""
Pipeline metrics collection for performance monitoring.

Provides lightweight metrics collection for each processing step.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from contextlib import contextmanager
import threading


@dataclass
class StepMetrics:
    """Metrics for a single processing step."""
    name: str
    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float('inf')
    max_time_ms: float = 0.0
    last_time_ms: float = 0.0
    errors: int = 0

    @property
    def avg_time_ms(self) -> float:
        """Calculate average processing time."""
        return self.total_time_ms / self.count if self.count > 0 else 0.0

    def record(self, time_ms: float, error: bool = False):
        """Record a single measurement."""
        self.count += 1
        self.total_time_ms += time_ms
        self.last_time_ms = time_ms
        self.min_time_ms = min(self.min_time_ms, time_ms)
        self.max_time_ms = max(self.max_time_ms, time_ms)
        if error:
            self.errors += 1

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'name': self.name,
            'count': self.count,
            'total_time_ms': self.total_time_ms,
            'avg_time_ms': self.avg_time_ms,
            'min_time_ms': self.min_time_ms if self.min_time_ms != float('inf') else 0.0,
            'max_time_ms': self.max_time_ms,
            'last_time_ms': self.last_time_ms,
            'errors': self.errors,
            'error_rate': self.errors / self.count if self.count > 0 else 0.0
        }


class PipelineMetrics:
    """Centralized metrics collection for the processing pipeline."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for global metrics."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize metrics storage."""
        if not self._initialized:
            self.steps: Dict[str, StepMetrics] = {}
            self._lock = threading.Lock()
            self._enabled = True
            self._cache_hits = {}
            self._cache_misses = {}
            self._initialized = True

    def enable(self):
        """Enable metrics collection."""
        self._enabled = True

    def disable(self):
        """Disable metrics collection."""
        self._enabled = False

    @contextmanager
    def measure(self, step_name: str):
        """Context manager for measuring step execution time."""
        if not self._enabled:
            yield
            return

        start_time = time.perf_counter()
        error_occurred = False

        try:
            yield
        except Exception as e:
            error_occurred = True
            raise
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.record_step(step_name, elapsed_ms, error_occurred)

    def record_step(self, step_name: str, time_ms: float, error: bool = False):
        """Record metrics for a processing step."""
        if not self._enabled:
            return

        with self._lock:
            if step_name not in self.steps:
                self.steps[step_name] = StepMetrics(name=step_name)
            self.steps[step_name].record(time_ms, error)

    def record_cache_hit(self, cache_name: str):
        """Record a cache hit."""
        if not self._enabled:
            return

        with self._lock:
            self._cache_hits[cache_name] = self._cache_hits.get(cache_name, 0) + 1

    def record_cache_miss(self, cache_name: str):
        """Record a cache miss."""
        if not self._enabled:
            return

        with self._lock:
            self._cache_misses[cache_name] = self._cache_misses.get(cache_name, 0) + 1

    def get_cache_stats(self, cache_name: str) -> Dict[str, Any]:
        """Get cache statistics."""
        hits = self._cache_hits.get(cache_name, 0)
        misses = self._cache_misses.get(cache_name, 0)
        total = hits + misses

        return {
            'hits': hits,
            'misses': misses,
            'total': total,
            'hit_rate': (hits / total * 100) if total > 0 else 0.0
        }

    def get_step_metrics(self, step_name: str) -> Optional[StepMetrics]:
        """Get metrics for a specific step."""
        return self.steps.get(step_name)

    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all collected metrics."""
        with self._lock:
            step_metrics = {name: metrics.to_dict() for name, metrics in self.steps.items()}

            # Calculate total pipeline metrics
            total_time = sum(m.total_time_ms for m in self.steps.values())
            total_count = max(m.count for m in self.steps.values()) if self.steps else 0

            # Find bottlenecks (steps taking >30% of time)
            bottlenecks = []
            for name, metrics in self.steps.items():
                percent = (metrics.total_time_ms / total_time * 100) if total_time > 0 else 0
                if percent > 30:
                    bottlenecks.append({
                        'step': name,
                        'percent': percent,
                        'avg_ms': metrics.avg_time_ms
                    })

            # Cache statistics
            cache_stats = {}
            for cache_name in set(list(self._cache_hits.keys()) + list(self._cache_misses.keys())):
                cache_stats[cache_name] = self.get_cache_stats(cache_name)

            return {
                'steps': step_metrics,
                'total_time_ms': total_time,
                'total_requests': total_count,
                'avg_total_time_ms': total_time / total_count if total_count > 0 else 0,
                'bottlenecks': sorted(bottlenecks, key=lambda x: x['percent'], reverse=True),
                'cache_stats': cache_stats,
                'enabled': self._enabled
            }

    def reset(self):
        """Reset all metrics."""
        with self._lock:
            self.steps.clear()
            self._cache_hits.clear()
            self._cache_misses.clear()

    def get_summary(self) -> str:
        """Get a human-readable summary of metrics."""
        metrics = self.get_all_metrics()

        lines = [
            "Pipeline Metrics Summary",
            "=" * 40,
            f"Total requests: {metrics['total_requests']}",
            f"Avg total time: {metrics['avg_total_time_ms']:.2f}ms",
            ""
        ]

        # Step breakdown
        if metrics['steps']:
            lines.append("Step Breakdown:")
            for step_name, step_data in sorted(metrics['steps'].items(),
                                              key=lambda x: x[1]['total_time_ms'],
                                              reverse=True):
                percent = (step_data['total_time_ms'] / metrics['total_time_ms'] * 100) if metrics['total_time_ms'] > 0 else 0
                lines.append(f"  {step_name:30} {step_data['avg_time_ms']:7.2f}ms ({percent:5.1f}%)")

        # Bottlenecks
        if metrics['bottlenecks']:
            lines.append("\nBottlenecks (>30% of time):")
            for bottleneck in metrics['bottlenecks']:
                lines.append(f"  • {bottleneck['step']}: {bottleneck['percent']:.1f}% ({bottleneck['avg_ms']:.2f}ms)")

        # Cache stats
        if metrics['cache_stats']:
            lines.append("\nCache Performance:")
            for cache_name, stats in metrics['cache_stats'].items():
                lines.append(f"  {cache_name}: {stats['hit_rate']:.1f}% hit rate ({stats['hits']}/{stats['total']})")

        return "\n".join(lines)


# Global metrics instance
metrics = PipelineMetrics()


def get_pipeline_metrics() -> PipelineMetrics:
    """Get the global pipeline metrics instance."""
    return metrics