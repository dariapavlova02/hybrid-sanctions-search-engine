"""
Comprehensive metrics collection system for performance trends and error rate monitoring.
Provides real-time metrics aggregation, storage, and analysis for the AI Service.
"""

import time
import asyncio
import threading
from typing import Dict, List, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum
import json
import statistics
import math
from datetime import datetime, timedelta
import weakref

from ..utils.enhanced_logging import get_logger_for_component, LogCategory


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"          # Monotonic increasing counter
    GAUGE = "gauge"              # Point-in-time value
    HISTOGRAM = "histogram"      # Distribution of values
    TIMER = "timer"              # Duration measurements
    RATE = "rate"               # Rate over time window
    PERCENTAGE = "percentage"    # Percentage values (0-100)


class AggregationType(Enum):
    """Types of aggregation for metrics."""
    SUM = "sum"
    AVERAGE = "avg"
    MIN = "min"
    MAX = "max"
    COUNT = "count"
    P50 = "p50"
    P95 = "p95"
    P99 = "p99"
    RATE_PER_SECOND = "rate_per_second"
    RATE_PER_MINUTE = "rate_per_minute"


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "value": self.value,
            "timestamp": self.timestamp,
            "tags": self.tags,
            "type": self.metric_type.value
        }


@dataclass
class HistogramData:
    """Histogram data with buckets and statistics."""
    buckets: Dict[float, int] = field(default_factory=dict)
    count: int = 0
    sum: float = 0.0
    min_value: float = float('inf')
    max_value: float = float('-inf')

    def add_value(self, value: float) -> None:
        """Add value to histogram."""
        self.count += 1
        self.sum += value
        self.min_value = min(self.min_value, value)
        self.max_value = max(self.max_value, value)

        # Add to appropriate bucket
        for bucket_limit in sorted(self.buckets.keys()):
            if value <= bucket_limit:
                self.buckets[bucket_limit] += 1

    def get_percentile(self, percentile: float, values: List[float]) -> float:
        """Calculate percentile from values."""
        if not values:
            return 0.0

        values = sorted(values)
        index = (percentile / 100.0) * (len(values) - 1)

        if index.is_integer():
            return values[int(index)]
        else:
            lower_index = int(math.floor(index))
            upper_index = int(math.ceil(index))
            weight = index - lower_index
            return values[lower_index] * (1 - weight) + values[upper_index] * weight


class MetricBuffer:
    """Thread-safe buffer for metric points with time-based windowing."""

    def __init__(self, max_size: int = 10000, max_age_seconds: float = 3600.0):
        self.max_size = max_size
        self.max_age_seconds = max_age_seconds
        self.points: deque = deque(maxlen=max_size)
        self._lock = threading.RLock()

    def add_point(self, point: MetricPoint) -> None:
        """Add metric point to buffer."""
        with self._lock:
            self.points.append(point)
            self._cleanup_old_points()

    def _cleanup_old_points(self) -> None:
        """Remove points older than max_age_seconds."""
        current_time = time.time()
        cutoff_time = current_time - self.max_age_seconds

        while self.points and self.points[0].timestamp < cutoff_time:
            self.points.popleft()

    def get_points(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        tags_filter: Optional[Dict[str, str]] = None
    ) -> List[MetricPoint]:
        """Get filtered points from buffer."""
        with self._lock:
            self._cleanup_old_points()

            current_time = time.time()
            start_time = start_time or (current_time - self.max_age_seconds)
            end_time = end_time or current_time

            filtered_points = []
            for point in self.points:
                # Time filter
                if not (start_time <= point.timestamp <= end_time):
                    continue

                # Tags filter
                if tags_filter:
                    if not all(point.tags.get(k) == v for k, v in tags_filter.items()):
                        continue

                filtered_points.append(point)

            return filtered_points

    def get_aggregated_stats(
        self,
        aggregation_types: List[AggregationType],
        time_window_seconds: float = 300.0
    ) -> Dict[str, float]:
        """Get aggregated statistics for the buffer."""
        current_time = time.time()
        start_time = current_time - time_window_seconds

        points = self.get_points(start_time=start_time)
        if not points:
            return {agg.value: 0.0 for agg in aggregation_types}

        values = [point.value for point in points]
        stats = {}

        for agg_type in aggregation_types:
            if agg_type == AggregationType.SUM:
                stats[agg_type.value] = sum(values)
            elif agg_type == AggregationType.AVERAGE:
                stats[agg_type.value] = statistics.mean(values)
            elif agg_type == AggregationType.MIN:
                stats[agg_type.value] = min(values)
            elif agg_type == AggregationType.MAX:
                stats[agg_type.value] = max(values)
            elif agg_type == AggregationType.COUNT:
                stats[agg_type.value] = len(values)
            elif agg_type == AggregationType.P50:
                stats[agg_type.value] = statistics.median(values)
            elif agg_type == AggregationType.P95:
                stats[agg_type.value] = self._percentile(values, 95)
            elif agg_type == AggregationType.P99:
                stats[agg_type.value] = self._percentile(values, 99)
            elif agg_type == AggregationType.RATE_PER_SECOND:
                stats[agg_type.value] = len(values) / time_window_seconds
            elif agg_type == AggregationType.RATE_PER_MINUTE:
                stats[agg_type.value] = len(values) / (time_window_seconds / 60.0)

        return stats

    def _percentile(self, values: List[float], percentile: float) -> float:
        """Calculate percentile from values."""
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (percentile / 100.0) * (len(sorted_values) - 1)

        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = int(math.floor(index))
            upper = int(math.ceil(index))
            weight = index - lower
            return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


class MetricsCollector:
    """Main metrics collection and management system."""

    def __init__(self):
        self.logger = get_logger_for_component("metrics", LogCategory.MONITORING)

        # Metric storage
        self.metric_buffers: Dict[str, MetricBuffer] = {}
        self.counters: Dict[str, float] = defaultdict(float)
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, HistogramData] = {}
        self.timers: Dict[str, List[float]] = defaultdict(list)

        # Configuration
        self.default_histogram_buckets = [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        self.max_timer_values = 1000

        # Thread safety
        self._lock = threading.RLock()

        # Callbacks for metric events
        self.metric_callbacks: List[Callable[[MetricPoint], None]] = []

        # Performance tracking
        self.collection_stats = {
            "total_metrics_collected": 0,
            "collection_errors": 0,
            "last_collection_time": 0,
            "collection_duration_ms": 0
        }

    def add_metric_callback(self, callback: Callable[[MetricPoint], None]) -> None:
        """Add callback to be called when metrics are collected."""
        self.metric_callbacks.append(callback)

    def remove_metric_callback(self, callback: Callable[[MetricPoint], None]) -> None:
        """Remove metric callback."""
        if callback in self.metric_callbacks:
            self.metric_callbacks.remove(callback)

    def _get_metric_buffer(self, metric_name: str) -> MetricBuffer:
        """Get or create metric buffer for metric name."""
        if metric_name not in self.metric_buffers:
            self.metric_buffers[metric_name] = MetricBuffer()
        return self.metric_buffers[metric_name]

    def _emit_metric(self, point: MetricPoint) -> None:
        """Emit metric point to storage and callbacks."""
        with self._lock:
            # Store in buffer
            buffer = self._get_metric_buffer(point.name)
            buffer.add_point(point)

            # Update collection stats
            self.collection_stats["total_metrics_collected"] += 1

            # Call callbacks
            for callback in self.metric_callbacks:
                try:
                    callback(point)
                except Exception as e:
                    self.logger.error(f"Metric callback error: {e}", error=e)
                    self.collection_stats["collection_errors"] += 1

    def record_counter(
        self,
        name: str,
        value: float = 1.0,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record counter metric."""
        metric_key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"

        with self._lock:
            self.counters[metric_key] += value

        # Emit metric point
        point = MetricPoint(
            name=name,
            value=self.counters[metric_key],
            timestamp=time.time(),
            tags=tags or {},
            metric_type=MetricType.COUNTER
        )
        self._emit_metric(point)

    def record_gauge(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record gauge metric."""
        metric_key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"

        with self._lock:
            self.gauges[metric_key] = value

        # Emit metric point
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            metric_type=MetricType.GAUGE
        )
        self._emit_metric(point)

    def record_histogram(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        buckets: Optional[List[float]] = None
    ) -> None:
        """Record histogram metric."""
        metric_key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
        buckets = buckets or self.default_histogram_buckets

        with self._lock:
            if metric_key not in self.histograms:
                self.histograms[metric_key] = HistogramData()
                # Initialize buckets
                for bucket_limit in buckets:
                    self.histograms[metric_key].buckets[bucket_limit] = 0

            self.histograms[metric_key].add_value(value)

        # Emit metric point
        point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            metric_type=MetricType.HISTOGRAM
        )
        self._emit_metric(point)

    def record_timer(
        self,
        name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """Record timer metric."""
        metric_key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"

        with self._lock:
            self.timers[metric_key].append(duration_ms)
            # Keep only recent timer values
            if len(self.timers[metric_key]) > self.max_timer_values:
                self.timers[metric_key] = self.timers[metric_key][-self.max_timer_values:]

        # Also record as histogram for percentile calculations
        self.record_histogram(name, duration_ms, tags)

        # Emit metric point
        point = MetricPoint(
            name=name,
            value=duration_ms,
            timestamp=time.time(),
            tags=tags or {},
            metric_type=MetricType.TIMER
        )
        self._emit_metric(point)

    def increment(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment counter by 1."""
        self.record_counter(name, 1.0, tags)

    def decrement(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Decrement counter by 1."""
        self.record_counter(name, -1.0, tags)

    def time_function(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Decorator to time function execution."""
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_timer(name, duration_ms, tags)
            return wrapper
        return decorator

    async def time_async_function(self, name: str, tags: Optional[Dict[str, str]] = None):
        """Decorator to time async function execution."""
        def decorator(func):
            async def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = await func(*args, **kwargs)
                    return result
                finally:
                    duration_ms = (time.time() - start_time) * 1000
                    self.record_timer(name, duration_ms, tags)
            return wrapper
        return decorator

    def get_metric_stats(
        self,
        metric_name: str,
        aggregations: List[AggregationType],
        time_window_seconds: float = 300.0,
        tags_filter: Optional[Dict[str, str]] = None
    ) -> Dict[str, float]:
        """Get aggregated statistics for a metric."""
        buffer = self._get_metric_buffer(metric_name)
        return buffer.get_aggregated_stats(aggregations, time_window_seconds)

    def get_histogram_stats(self, name: str, tags: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Get histogram statistics."""
        metric_key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"

        with self._lock:
            if metric_key not in self.histograms:
                return {}

            histogram = self.histograms[metric_key]

            # Get recent values for percentile calculation
            buffer = self._get_metric_buffer(name)
            recent_points = buffer.get_points(
                start_time=time.time() - 300,  # Last 5 minutes
                tags_filter=tags
            )
            recent_values = [p.value for p in recent_points]

            stats = {
                "count": histogram.count,
                "sum": histogram.sum,
                "min": histogram.min_value if histogram.min_value != float('inf') else 0,
                "max": histogram.max_value if histogram.max_value != float('-inf') else 0,
                "avg": histogram.sum / histogram.count if histogram.count > 0 else 0,
                "buckets": dict(histogram.buckets)
            }

            # Calculate percentiles from recent values
            if recent_values:
                stats.update({
                    "p50": buffer._percentile(recent_values, 50),
                    "p95": buffer._percentile(recent_values, 95),
                    "p99": buffer._percentile(recent_values, 99)
                })

            return stats

    def get_all_metrics_summary(self, time_window_seconds: float = 300.0) -> Dict[str, Any]:
        """Get summary of all collected metrics."""
        current_time = time.time()
        summary = {
            "timestamp": current_time,
            "time_window_seconds": time_window_seconds,
            "collection_stats": dict(self.collection_stats),
            "metrics": {}
        }

        # Counter metrics
        for metric_key, value in self.counters.items():
            name = metric_key.split(':')[0]
            if name not in summary["metrics"]:
                summary["metrics"][name] = {"type": "counter", "values": []}
            summary["metrics"][name]["values"].append({
                "key": metric_key,
                "value": value
            })

        # Gauge metrics
        for metric_key, value in self.gauges.items():
            name = metric_key.split(':')[0]
            if name not in summary["metrics"]:
                summary["metrics"][name] = {"type": "gauge", "values": []}
            summary["metrics"][name]["values"].append({
                "key": metric_key,
                "value": value
            })

        # Histogram metrics
        for metric_key in self.histograms.keys():
            name = metric_key.split(':')[0]
            tags_str = metric_key.split(':', 1)[1] if ':' in metric_key else '{}'
            try:
                tags = json.loads(tags_str)
            except:
                tags = {}

            histogram_stats = self.get_histogram_stats(name, tags)
            if histogram_stats:
                if name not in summary["metrics"]:
                    summary["metrics"][name] = {"type": "histogram", "values": []}
                summary["metrics"][name]["values"].append({
                    "key": metric_key,
                    "stats": histogram_stats
                })

        return summary

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics for key operations."""
        metrics = {}

        # Common performance metrics
        performance_metric_names = [
            "api_request_duration",
            "search_operation_duration",
            "elasticsearch_response_time",
            "normalization_duration",
            "validation_duration"
        ]

        for metric_name in performance_metric_names:
            stats = self.get_metric_stats(
                metric_name,
                [AggregationType.AVERAGE, AggregationType.P95, AggregationType.P99, AggregationType.COUNT],
                time_window_seconds=300  # 5 minutes
            )
            if stats.get("count", 0) > 0:
                metrics[metric_name] = stats

        return metrics

    def get_error_rate_metrics(self) -> Dict[str, Any]:
        """Get error rate metrics."""
        error_metrics = {}

        # Calculate error rates for different operations
        operations = ["api_requests", "search_operations", "elasticsearch_requests"]

        for operation in operations:
            total_metric = f"{operation}_total"
            failed_metric = f"{operation}_failed"

            total_stats = self.get_metric_stats(total_metric, [AggregationType.SUM], 300)
            failed_stats = self.get_metric_stats(failed_metric, [AggregationType.SUM], 300)

            total_count = total_stats.get("sum", 0)
            failed_count = failed_stats.get("sum", 0)

            if total_count > 0:
                error_rate = (failed_count / total_count) * 100
                error_metrics[f"{operation}_error_rate_percent"] = round(error_rate, 2)
                error_metrics[f"{operation}_total"] = total_count
                error_metrics[f"{operation}_failed"] = failed_count
            else:
                error_metrics[f"{operation}_error_rate_percent"] = 0.0

        return error_metrics

    def reset_metrics(self) -> None:
        """Reset all metrics (useful for testing)."""
        with self._lock:
            self.metric_buffers.clear()
            self.counters.clear()
            self.gauges.clear()
            self.histograms.clear()
            self.timers.clear()

            self.collection_stats = {
                "total_metrics_collected": 0,
                "collection_errors": 0,
                "last_collection_time": 0,
                "collection_duration_ms": 0
            }

        self.logger.info("All metrics have been reset")

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        current_time = time.time()

        # Export counters
        for metric_key, value in self.counters.items():
            name = metric_key.split(':')[0]
            tags_str = metric_key.split(':', 1)[1] if ':' in metric_key else '{}'

            try:
                tags = json.loads(tags_str)
                if tags:
                    tags_str = ','.join([f'{k}="{v}"' for k, v in tags.items()])
                    lines.append(f'ai_service_{name}{{{tags_str}}} {value}')
                else:
                    lines.append(f'ai_service_{name} {value}')
            except:
                lines.append(f'ai_service_{name} {value}')

        # Export gauges
        for metric_key, value in self.gauges.items():
            name = metric_key.split(':')[0]
            tags_str = metric_key.split(':', 1)[1] if ':' in metric_key else '{}'

            try:
                tags = json.loads(tags_str)
                if tags:
                    tags_str = ','.join([f'{k}="{v}"' for k, v in tags.items()])
                    lines.append(f'ai_service_{name}{{{tags_str}}} {value}')
                else:
                    lines.append(f'ai_service_{name} {value}')
            except:
                lines.append(f'ai_service_{name} {value}')

        # Export histogram percentiles
        for metric_key in self.histograms.keys():
            name = metric_key.split(':')[0]
            tags_str = metric_key.split(':', 1)[1] if ':' in metric_key else '{}'

            try:
                tags = json.loads(tags_str)
                histogram_stats = self.get_histogram_stats(name, tags)

                if histogram_stats:
                    base_tags = ','.join([f'{k}="{v}"' for k, v in tags.items()]) if tags else ''

                    # Export histogram statistics
                    lines.append(f'ai_service_{name}_count{{{base_tags}}} {histogram_stats["count"]}')
                    lines.append(f'ai_service_{name}_sum{{{base_tags}}} {histogram_stats["sum"]}')

                    if 'p50' in histogram_stats:
                        lines.append(f'ai_service_{name}_p50{{{base_tags}}} {histogram_stats["p50"]}')
                    if 'p95' in histogram_stats:
                        lines.append(f'ai_service_{name}_p95{{{base_tags}}} {histogram_stats["p95"]}')
                    if 'p99' in histogram_stats:
                        lines.append(f'ai_service_{name}_p99{{{base_tags}}} {histogram_stats["p99"]}')

            except Exception as e:
                self.logger.error(f"Error exporting histogram {metric_key}: {e}")

        # Add metadata
        lines.append(f'# AI Service Metrics Export')
        lines.append(f'# Timestamp: {current_time}')
        lines.append(f'# Total metrics: {self.collection_stats["total_metrics_collected"]}')

        return '\n'.join(lines)

    async def start_background_collection(self, interval_seconds: float = 30.0) -> None:
        """Start background metrics collection and cleanup."""
        self.logger.info("Starting background metrics collection")

        async def collection_loop():
            while True:
                try:
                    collection_start = time.time()

                    # Cleanup old data
                    self._cleanup_old_data()

                    # Update collection stats
                    collection_duration = (time.time() - collection_start) * 1000
                    self.collection_stats.update({
                        "last_collection_time": collection_start,
                        "collection_duration_ms": collection_duration
                    })

                    self.logger.debug(f"Metrics collection completed in {collection_duration:.2f}ms")

                except Exception as e:
                    self.logger.error(f"Background metrics collection error: {e}", error=e)
                    self.collection_stats["collection_errors"] += 1

                await asyncio.sleep(interval_seconds)

        # Start collection task
        asyncio.create_task(collection_loop())

    def _cleanup_old_data(self) -> None:
        """Clean up old metric data to prevent memory leaks."""
        # Cleanup happens automatically in MetricBuffer
        # This method is for additional cleanup if needed

        # Clean up timer data
        current_time = time.time()
        cutoff_time = current_time - 3600  # Keep 1 hour of timer data

        for metric_key in list(self.timers.keys()):
            # For simplicity, just limit the size of timer arrays
            if len(self.timers[metric_key]) > self.max_timer_values:
                self.timers[metric_key] = self.timers[metric_key][-self.max_timer_values:]


# Global metrics collector
_global_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _global_collector
    if _global_collector is None:
        _global_collector = MetricsCollector()
    return _global_collector


def reset_global_metrics() -> None:
    """Reset global metrics collector (for testing)."""
    global _global_collector
    if _global_collector:
        _global_collector.reset_metrics()


# Convenience functions for common metrics
def record_api_request(
    method: str,
    endpoint: str,
    status_code: int,
    duration_ms: float
) -> None:
    """Record API request metrics."""
    collector = get_metrics_collector()

    tags = {
        "method": method,
        "endpoint": endpoint,
        "status_code": str(status_code),
        "success": str(200 <= status_code < 400).lower()
    }

    collector.increment("api_requests_total", tags)
    collector.record_timer("api_request_duration", duration_ms, tags)

    if status_code >= 400:
        collector.increment("api_requests_failed", tags)


def record_search_operation(
    strategy: str,
    query_length: int,
    result_count: int,
    duration_ms: float,
    success: bool = True
) -> None:
    """Record search operation metrics."""
    collector = get_metrics_collector()

    tags = {
        "strategy": strategy,
        "success": str(success).lower()
    }

    collector.increment("search_operations_total", tags)
    collector.record_timer("search_operation_duration", duration_ms, tags)
    collector.record_gauge("search_query_length", query_length, tags)
    collector.record_gauge("search_result_count", result_count, tags)

    if not success:
        collector.increment("search_operations_failed", tags)


def record_elasticsearch_operation(
    operation: str,
    host: str,
    duration_ms: float,
    success: bool = True,
    status_code: Optional[int] = None
) -> None:
    """Record Elasticsearch operation metrics."""
    collector = get_metrics_collector()

    tags = {
        "operation": operation,
        "host": host,
        "success": str(success).lower()
    }

    if status_code:
        tags["status_code"] = str(status_code)

    collector.increment("elasticsearch_requests_total", tags)
    collector.record_timer("elasticsearch_response_time", duration_ms, tags)

    if not success:
        collector.increment("elasticsearch_requests_failed", tags)