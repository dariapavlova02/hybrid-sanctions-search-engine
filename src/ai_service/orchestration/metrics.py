"""
Performance metrics and monitoring system.
Single Responsibility: Collects, stores, and reports performance metrics.
"""

import statistics
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

# Import interfaces
try:
    from ..interfaces import MetricsInterface, ProcessingStage
except ImportError:
    # Fallback for when loaded via importlib
    import sys
    from pathlib import Path

    orchestration_path = Path(__file__).parent
    sys.path.insert(0, str(orchestration_path))

    from interfaces import MetricsInterface, ProcessingStage


@dataclass
class TimingMetric:
    """Timing metric with statistical analysis"""

    count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    recent_times: deque = field(default_factory=lambda: deque(maxlen=100))

    def add_timing(self, time_ms: float):
        """Add a timing measurement"""
        self.count += 1
        self.total_time_ms += time_ms
        self.min_time_ms = min(self.min_time_ms, time_ms)
        self.max_time_ms = max(self.max_time_ms, time_ms)
        self.recent_times.append(time_ms)

    @property
    def average_time_ms(self) -> float:
        """Calculate average time"""
        return self.total_time_ms / self.count if self.count > 0 else 0.0

    @property
    def median_time_ms(self) -> float:
        """Calculate median time from recent measurements"""
        if not self.recent_times:
            return 0.0
        return statistics.median(self.recent_times)

    @property
    def percentile_95_ms(self) -> float:
        """Calculate 95th percentile from recent measurements"""
        if not self.recent_times:
            return 0.0
        sorted_times = sorted(self.recent_times)
        index = int(len(sorted_times) * 0.95)
        return sorted_times[min(index, len(sorted_times) - 1)]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "count": self.count,
            "total_time_ms": self.total_time_ms,
            "average_time_ms": self.average_time_ms,
            "median_time_ms": self.median_time_ms,
            "min_time_ms": (
                self.min_time_ms if self.min_time_ms != float("inf") else 0.0
            ),
            "max_time_ms": self.max_time_ms,
            "percentile_95_ms": self.percentile_95_ms,
        }


@dataclass
class CounterMetric:
    """Counter metric with rate calculation"""

    count: int = 0
    last_reset: datetime = field(default_factory=datetime.now)
    recent_counts: deque = field(
        default_factory=lambda: deque(maxlen=60)
    )  # Last 60 seconds

    def increment(self, value: int = 1):
        """Increment counter"""
        self.count += value
        # Track per-second counts for rate calculation
        now = datetime.now()
        if not self.recent_counts or (now - self.last_reset).seconds >= 1:
            self.recent_counts.append(value)
            self.last_reset = now
        else:
            # Add to current second
            if self.recent_counts:
                self.recent_counts[-1] += value
            else:
                self.recent_counts.append(value)

    @property
    def rate_per_second(self) -> float:
        """Calculate average rate per second"""
        if not self.recent_counts:
            return 0.0
        return sum(self.recent_counts) / len(self.recent_counts)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {"count": self.count, "rate_per_second": self.rate_per_second}


class PerformanceMetrics(MetricsInterface):
    """
    Comprehensive performance metrics system.
    Thread-safe and optimized for high-throughput scenarios.
    """

    def __init__(self, enable_detailed_metrics: bool = True):
        self.enable_detailed = enable_detailed_metrics
        self._lock = threading.RLock()

        # Timing metrics for each stage
        self.stage_timings: Dict[ProcessingStage, TimingMetric] = defaultdict(
            TimingMetric
        )

        # Counter metrics
        self.counters: Dict[str, CounterMetric] = defaultdict(CounterMetric)

        # System metrics
        self.start_time = datetime.now()
        self.last_reset_time = datetime.now()

        # Throughput tracking
        self.throughput_tracker: deque = deque(maxlen=1000)  # Last 1000 requests

        # Error tracking
        self.error_rates: Dict[str, CounterMetric] = defaultdict(CounterMetric)

        # Initialize standard counters
        self._init_standard_counters()

    def _init_standard_counters(self):
        """Initialize standard performance counters"""
        standard_counters = [
            "requests_processed",
            "successful_processing",
            "failed_processing",
            "cache_hits",
            "cache_misses",
            "pipeline_errors",
            "stage_errors",
            "recovery_attempts",
            "fallback_used",
        ]

        for counter in standard_counters:
            self.counters[counter] = CounterMetric()

    def record_processing_time(self, stage: ProcessingStage, time_ms: float) -> None:
        """Record processing time for a stage"""
        with self._lock:
            self.stage_timings[stage].add_timing(time_ms)

            # Track overall throughput
            self.throughput_tracker.append(datetime.now())

    def increment_counter(self, metric_name: str, value: int = 1) -> None:
        """Increment a counter metric"""
        with self._lock:
            self.counters[metric_name].increment(value)

    def record_error(self, error_type: str, stage: Optional[ProcessingStage] = None):
        """Record an error occurrence"""
        with self._lock:
            self.error_rates[error_type].increment()
            self.counters["stage_errors"].increment()

            if stage:
                stage_error_key = f"{stage.value}_errors"
                self.error_rates[stage_error_key].increment()

    def get_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics summary"""
        with self._lock:
            return {
                "system": self._get_system_metrics(),
                "stage_performance": self._get_stage_metrics(),
                "counters": self._get_counter_metrics(),
                "throughput": self._get_throughput_metrics(),
                "errors": self._get_error_metrics(),
                "summary": self._get_summary_metrics(),
            }

    def _get_system_metrics(self) -> Dict[str, Any]:
        """Get system-level metrics"""
        uptime = datetime.now() - self.start_time
        time_since_reset = datetime.now() - self.last_reset_time

        return {
            "uptime_seconds": uptime.total_seconds(),
            "time_since_reset_seconds": time_since_reset.total_seconds(),
            "start_time": self.start_time.isoformat(),
            "last_reset_time": self.last_reset_time.isoformat(),
        }

    def _get_stage_metrics(self) -> Dict[str, Any]:
        """Get per-stage performance metrics"""
        stage_metrics = {}

        for stage, timing in self.stage_timings.items():
            stage_metrics[stage.value] = timing.to_dict()

        return stage_metrics

    def _get_counter_metrics(self) -> Dict[str, Any]:
        """Get counter metrics"""
        counter_metrics = {}

        for name, counter in self.counters.items():
            counter_metrics[name] = counter.to_dict()

        return counter_metrics

    def _get_throughput_metrics(self) -> Dict[str, Any]:
        """Calculate throughput metrics"""
        if not self.throughput_tracker:
            return {
                "requests_per_second": 0.0,
                "requests_per_minute": 0.0,
                "recent_request_count": 0,
            }

        now = datetime.now()

        # Calculate requests in last second
        one_second_ago = now - timedelta(seconds=1)
        last_second_requests = sum(
            1 for ts in self.throughput_tracker if ts >= one_second_ago
        )

        # Calculate requests in last minute
        one_minute_ago = now - timedelta(minutes=1)
        last_minute_requests = sum(
            1 for ts in self.throughput_tracker if ts >= one_minute_ago
        )

        return {
            "requests_per_second": float(last_second_requests),
            "requests_per_minute": float(last_minute_requests),
            "recent_request_count": len(self.throughput_tracker),
        }

    def _get_error_metrics(self) -> Dict[str, Any]:
        """Get error metrics and rates"""
        error_metrics = {}

        for error_type, counter in self.error_rates.items():
            error_metrics[error_type] = counter.to_dict()

        # Calculate error rates
        total_requests = self.counters["requests_processed"].count
        total_errors = self.counters["stage_errors"].count

        error_rate = (
            (total_errors / total_requests * 100) if total_requests > 0 else 0.0
        )

        error_metrics["overall_error_rate_percent"] = error_rate

        return error_metrics

    def _get_summary_metrics(self) -> Dict[str, Any]:
        """Get high-level summary metrics"""
        total_requests = self.counters["requests_processed"].count
        successful_requests = self.counters["successful_processing"].count
        failed_requests = self.counters["failed_processing"].count

        success_rate = (
            (successful_requests / total_requests * 100) if total_requests > 0 else 0.0
        )

        # Calculate average processing time across all stages
        total_time = 0.0
        total_count = 0

        for timing in self.stage_timings.values():
            total_time += timing.total_time_ms
            total_count += timing.count

        avg_processing_time = total_time / total_count if total_count > 0 else 0.0

        return {
            "total_requests_processed": total_requests,
            "success_rate_percent": success_rate,
            "average_processing_time_ms": avg_processing_time,
            "cache_hit_rate_percent": self._calculate_cache_hit_rate(),
            "active_stages": len(self.stage_timings),
            "uptime_hours": (datetime.now() - self.start_time).total_seconds() / 3600,
        }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        hits = self.counters["cache_hits"].count
        misses = self.counters["cache_misses"].count
        total = hits + misses

        return (hits / total * 100) if total > 0 else 0.0

    def reset_metrics(self) -> None:
        """Reset all metrics"""
        with self._lock:
            self.stage_timings.clear()
            self.counters.clear()
            self.error_rates.clear()
            self.throughput_tracker.clear()

            self.last_reset_time = datetime.now()
            self._init_standard_counters()

    def get_top_slow_stages(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get stages with highest average processing time"""
        with self._lock:
            stage_times = [
                {
                    "stage": stage.value,
                    "average_time_ms": timing.average_time_ms,
                    "count": timing.count,
                }
                for stage, timing in self.stage_timings.items()
                if timing.count > 0
            ]

            # Sort by average time, descending
            stage_times.sort(key=lambda x: x["average_time_ms"], reverse=True)

            return stage_times[:limit]

    def get_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score"""
        with self._lock:
            # Calculate health score based on multiple factors
            success_rate = self._get_summary_metrics()["success_rate_percent"]
            error_rate = self._get_error_metrics()["overall_error_rate_percent"]
            cache_hit_rate = self._calculate_cache_hit_rate()

            # Health score factors (0-100)
            success_score = success_rate  # Higher is better
            error_score = max(0, 100 - error_rate)  # Lower error rate is better
            cache_score = min(cache_hit_rate, 100)  # Higher cache hit rate is better

            # Performance score based on average processing time
            avg_time = self._get_summary_metrics()["average_processing_time_ms"]
            performance_score = max(
                0, 100 - min(avg_time / 100, 100)
            )  # Lower time is better

            # Overall health score (weighted average)
            health_score = (
                success_score * 0.4
                + error_score * 0.3
                + performance_score * 0.2
                + cache_score * 0.1
            )

            return {
                "overall_health_score": round(health_score, 2),
                "success_rate_score": round(success_score, 2),
                "error_rate_score": round(error_score, 2),
                "performance_score": round(performance_score, 2),
                "cache_score": round(cache_score, 2),
                "health_status": self._get_health_status(health_score),
            }

    def _get_health_status(self, health_score: float) -> str:
        """Get health status based on score"""
        if health_score >= 90:
            return "excellent"
        elif health_score >= 80:
            return "good"
        elif health_score >= 70:
            return "fair"
        elif health_score >= 60:
            return "poor"
        else:
            return "critical"
