"""
Search system monitoring, metrics collection, and error handling.
Provides comprehensive monitoring for the hybrid search system.
"""

from __future__ import annotations

import asyncio
import time
import json
from typing import Dict, Any, List, Optional, Callable, NamedTuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict, deque
import threading
from datetime import datetime, timedelta

from ...utils.logging_config import get_logger
from .search_trace_validator import SearchTraceValidator, ValidationReport
from ...contracts.trace_models import SearchTrace


class MetricType(Enum):
    """Types of metrics collected by the monitoring system."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class MetricPoint:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    tags: Dict[str, str] = field(default_factory=dict)
    metric_type: MetricType = MetricType.GAUGE


@dataclass
class Alert:
    """System alert for monitoring issues."""
    name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)
    resolved: bool = False
    resolved_timestamp: Optional[float] = None


class PerformanceWindow:
    """Sliding window for performance metrics."""

    def __init__(self, window_size: int = 100, window_duration: float = 300.0):
        self.window_size = window_size
        self.window_duration = window_duration
        self.data_points: deque = deque(maxlen=window_size)
        self._lock = threading.Lock()

    def add_point(self, value: float, timestamp: Optional[float] = None) -> None:
        """Add data point to window."""
        if timestamp is None:
            timestamp = time.time()

        with self._lock:
            self.data_points.append((timestamp, value))
            self._cleanup_old_points(timestamp)

    def _cleanup_old_points(self, current_time: float) -> None:
        """Remove points older than window duration."""
        cutoff_time = current_time - self.window_duration
        while self.data_points and self.data_points[0][0] < cutoff_time:
            self.data_points.popleft()

    def get_statistics(self) -> Dict[str, Any]:
        """Calculate statistics for current window."""
        with self._lock:
            if not self.data_points:
                return {
                    "count": 0,
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "p50": 0,
                    "p95": 0,
                    "p99": 0
                }

            values = [point[1] for point in self.data_points]
            values.sort()

            count = len(values)
            return {
                "count": count,
                "min": values[0],
                "max": values[-1],
                "avg": sum(values) / count,
                "p50": values[count // 2],
                "p95": values[int(count * 0.95)] if count > 20 else values[-1],
                "p99": values[int(count * 0.99)] if count > 100 else values[-1]
            }


class SearchSystemMonitor:
    """Comprehensive monitoring system for search operations."""

    def __init__(self, enable_alerts: bool = True, alert_callback: Optional[Callable] = None):
        self.logger = get_logger(__name__)
        self.enable_alerts = enable_alerts
        self.alert_callback = alert_callback

        # Metrics storage
        self.metrics: Dict[str, List[MetricPoint]] = defaultdict(list)
        self.performance_windows: Dict[str, PerformanceWindow] = {}
        self.alerts: List[Alert] = []
        self.active_alerts: Dict[str, Alert] = {}

        # Search trace validator
        self.trace_validator = SearchTraceValidator()

        # Performance thresholds
        self.thresholds = {
            "search_latency_p95_ms": 200.0,
            "search_latency_p99_ms": 500.0,
            "elasticsearch_health_check_ms": 1000.0,
            "error_rate_percent": 5.0,
            "trace_validation_error_rate_percent": 10.0,
            "concurrent_searches": 50,
            "memory_usage_mb": 500.0
        }

        # Counters
        self.counters = defaultdict(int)
        self._lock = threading.Lock()

        # Initialize performance windows
        self._init_performance_windows()

    def _init_performance_windows(self) -> None:
        """Initialize performance monitoring windows."""
        windows = [
            "search_latency_ms",
            "elasticsearch_response_time_ms",
            "trace_validation_time_ms",
            "search_result_count",
            "concurrent_searches",
            "memory_usage_mb"
        ]

        for window_name in windows:
            self.performance_windows[window_name] = PerformanceWindow()

    def record_metric(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]] = None,
        metric_type: MetricType = MetricType.GAUGE
    ) -> None:
        """Record a metric data point."""
        metric_point = MetricPoint(
            name=name,
            value=value,
            timestamp=time.time(),
            tags=tags or {},
            metric_type=metric_type
        )

        with self._lock:
            self.metrics[name].append(metric_point)

            # Keep only last 1000 points per metric
            if len(self.metrics[name]) > 1000:
                self.metrics[name] = self.metrics[name][-1000:]

        # Add to performance window if applicable
        if name in self.performance_windows:
            self.performance_windows[name].add_point(value)

        # Check for threshold violations
        self._check_thresholds(name, value, tags or {})

    def increment_counter(self, name: str, tags: Optional[Dict[str, str]] = None) -> None:
        """Increment a counter metric."""
        with self._lock:
            counter_key = f"{name}:{json.dumps(tags or {}, sort_keys=True)}"
            self.counters[counter_key] += 1

        self.record_metric(name, self.counters[counter_key], tags, MetricType.COUNTER)

    def record_search_operation(
        self,
        query_text: str,
        strategy: str,
        latency_ms: float,
        result_count: int,
        success: bool,
        search_trace: Optional[SearchTrace] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record comprehensive search operation metrics."""
        tags = {
            "strategy": strategy,
            "success": str(success).lower()
        }

        # Record basic metrics
        self.record_metric("search_latency_ms", latency_ms, tags, MetricType.TIMER)
        self.record_metric("search_result_count", result_count, tags)

        # Increment counters
        self.increment_counter("search_requests_total", tags)

        if success:
            self.increment_counter("search_requests_successful", tags)
        else:
            self.increment_counter("search_requests_failed", tags)
            if error:
                error_tags = {**tags, "error_type": self._classify_error(error)}
                self.increment_counter("search_errors_by_type", error_tags)

        # Validate and analyze search trace
        trace_analysis = {}
        if search_trace:
            try:
                validation_start = time.time()
                validation_report = self.trace_validator.validate_trace(search_trace)
                validation_time = (time.time() - validation_start) * 1000

                self.record_metric("trace_validation_time_ms", validation_time)

                trace_analysis = {
                    "is_valid": validation_report.is_valid,
                    "total_steps": validation_report.total_steps,
                    "issues_count": len(validation_report.issues),
                    "errors_count": len(validation_report.get_issues_by_severity(
                        ValidationSeverity.ERROR
                    )),
                    "coverage_percentage": validation_report.coverage_analysis.get("coverage_percentage", 0)
                }

                # Record trace metrics
                trace_tags = {**tags, "trace_valid": str(validation_report.is_valid).lower()}
                self.record_metric("trace_coverage_percentage",
                                 trace_analysis["coverage_percentage"], trace_tags)

                if not validation_report.is_valid:
                    self.increment_counter("trace_validation_failures", tags)

            except Exception as e:
                self.logger.error(f"Failed to validate search trace: {e}")
                self.increment_counter("trace_validation_errors")

        # Create operation summary
        operation_summary = {
            "timestamp": time.time(),
            "query_text_length": len(query_text),
            "strategy": strategy,
            "latency_ms": latency_ms,
            "result_count": result_count,
            "success": success,
            "error": error,
            "trace_analysis": trace_analysis
        }

        return operation_summary

    def record_elasticsearch_operation(
        self,
        operation: str,
        host: str,
        latency_ms: float,
        success: bool,
        status_code: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Record Elasticsearch operation metrics."""
        tags = {
            "operation": operation,
            "host": host,
            "success": str(success).lower()
        }

        if status_code:
            tags["status_code"] = str(status_code)

        # Record metrics
        self.record_metric("elasticsearch_response_time_ms", latency_ms, tags, MetricType.TIMER)
        self.increment_counter("elasticsearch_requests_total", tags)

        if success:
            self.increment_counter("elasticsearch_requests_successful", tags)
        else:
            self.increment_counter("elasticsearch_requests_failed", tags)
            if error:
                error_tags = {**tags, "error_type": self._classify_error(error)}
                self.increment_counter("elasticsearch_errors_by_type", error_tags)

    def _classify_error(self, error_message: str) -> str:
        """Classify error into categories."""
        error_lower = error_message.lower()

        if "timeout" in error_lower or "time" in error_lower:
            return "timeout"
        elif "connection" in error_lower or "network" in error_lower:
            return "connection"
        elif "404" in error_lower or "not found" in error_lower:
            return "not_found"
        elif "401" in error_lower or "403" in error_lower or "unauthorized" in error_lower:
            return "auth"
        elif "500" in error_lower or "server" in error_lower:
            return "server_error"
        elif "parse" in error_lower or "invalid" in error_lower:
            return "validation"
        else:
            return "unknown"

    def _check_thresholds(self, metric_name: str, value: float, tags: Dict[str, str]) -> None:
        """Check metric against configured thresholds."""
        if not self.enable_alerts:
            return

        # Map metric names to threshold names
        threshold_mapping = {
            "search_latency_ms": "search_latency_p95_ms",
            "elasticsearch_response_time_ms": "elasticsearch_health_check_ms",
            "memory_usage_mb": "memory_usage_mb"
        }

        threshold_key = threshold_mapping.get(metric_name)
        if not threshold_key or threshold_key not in self.thresholds:
            return

        threshold_value = self.thresholds[threshold_key]

        # For latency metrics, check against percentiles
        if "latency" in metric_name or "response_time" in metric_name:
            window = self.performance_windows.get(metric_name)
            if window:
                stats = window.get_statistics()
                p95_value = stats.get("p95", 0)

                if p95_value > threshold_value:
                    self._trigger_alert(
                        name=f"high_{metric_name}_p95",
                        severity=AlertSeverity.WARNING,
                        message=f"High {metric_name} P95: {p95_value:.1f}ms > {threshold_value}ms",
                        details={
                            "metric_name": metric_name,
                            "p95_value": p95_value,
                            "threshold": threshold_value,
                            "tags": tags,
                            "stats": stats
                        }
                    )
        else:
            # Direct value comparison
            if value > threshold_value:
                self._trigger_alert(
                    name=f"high_{metric_name}",
                    severity=AlertSeverity.WARNING if value < threshold_value * 1.5 else AlertSeverity.CRITICAL,
                    message=f"High {metric_name}: {value} > {threshold_value}",
                    details={
                        "metric_name": metric_name,
                        "value": value,
                        "threshold": threshold_value,
                        "tags": tags
                    }
                )

    def _trigger_alert(
        self,
        name: str,
        severity: AlertSeverity,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Trigger system alert."""
        alert = Alert(
            name=name,
            severity=severity,
            message=message,
            timestamp=time.time(),
            details=details or {}
        )

        # Add to alerts list
        self.alerts.append(alert)

        # Update active alerts
        self.active_alerts[name] = alert

        # Log alert
        log_level = "error" if severity == AlertSeverity.CRITICAL else "warning"
        getattr(self.logger, log_level)(f"ALERT [{severity.value.upper()}] {name}: {message}")

        # Call alert callback if configured
        if self.alert_callback:
            try:
                self.alert_callback(alert)
            except Exception as e:
                self.logger.error(f"Alert callback failed: {e}")

        # Keep only last 1000 alerts
        if len(self.alerts) > 1000:
            self.alerts = self.alerts[-1000:]

    def resolve_alert(self, name: str) -> bool:
        """Mark alert as resolved."""
        if name in self.active_alerts:
            alert = self.active_alerts[name]
            alert.resolved = True
            alert.resolved_timestamp = time.time()
            del self.active_alerts[name]
            self.logger.info(f"Alert resolved: {name}")
            return True
        return False

    def get_system_health(self) -> Dict[str, Any]:
        """Get comprehensive system health report."""
        current_time = time.time()

        # Calculate error rates
        total_searches = self.counters.get("search_requests_total:{}", 0)
        failed_searches = self.counters.get("search_requests_failed:{}", 0)
        error_rate = (failed_searches / total_searches * 100) if total_searches > 0 else 0

        # Get performance statistics
        performance_stats = {}
        for window_name, window in self.performance_windows.items():
            performance_stats[window_name] = window.get_statistics()

        # Active alerts summary
        alerts_by_severity = defaultdict(list)
        for alert in self.active_alerts.values():
            alerts_by_severity[alert.severity.value].append(alert.name)

        health_status = "healthy"
        if len(alerts_by_severity.get("critical", [])) > 0:
            health_status = "critical"
        elif len(alerts_by_severity.get("warning", [])) > 0:
            health_status = "degraded"

        return {
            "status": health_status,
            "timestamp": current_time,
            "uptime_hours": (current_time - self._get_start_time()) / 3600,
            "performance": performance_stats,
            "error_rates": {
                "search_error_rate_percent": round(error_rate, 2),
                "total_searches": total_searches,
                "failed_searches": failed_searches
            },
            "alerts": {
                "active_count": len(self.active_alerts),
                "by_severity": dict(alerts_by_severity),
                "recent_alerts": [
                    {
                        "name": alert.name,
                        "severity": alert.severity.value,
                        "message": alert.message,
                        "age_minutes": (current_time - alert.timestamp) / 60
                    }
                    for alert in sorted(self.alerts[-10:], key=lambda a: a.timestamp, reverse=True)
                ]
            },
            "thresholds": dict(self.thresholds)
        }

    def get_metrics_summary(self, time_window_seconds: float = 3600.0) -> Dict[str, Any]:
        """Get metrics summary for specified time window."""
        current_time = time.time()
        cutoff_time = current_time - time_window_seconds

        # Filter metrics by time window
        windowed_metrics = {}
        for metric_name, points in self.metrics.items():
            recent_points = [p for p in points if p.timestamp >= cutoff_time]
            if recent_points:
                windowed_metrics[metric_name] = {
                    "count": len(recent_points),
                    "latest_value": recent_points[-1].value,
                    "avg_value": sum(p.value for p in recent_points) / len(recent_points),
                    "min_value": min(p.value for p in recent_points),
                    "max_value": max(p.value for p in recent_points),
                    "latest_timestamp": recent_points[-1].timestamp
                }

        return {
            "time_window_seconds": time_window_seconds,
            "metrics": windowed_metrics,
            "counters": dict(self.counters),
            "generated_at": current_time
        }

    def _get_start_time(self) -> float:
        """Get monitoring start time (approximated from first metric)."""
        if not self.metrics:
            return time.time()

        first_timestamps = []
        for points in self.metrics.values():
            if points:
                first_timestamps.append(points[0].timestamp)

        return min(first_timestamps) if first_timestamps else time.time()

    def reset_metrics(self) -> None:
        """Reset all metrics and alerts (for testing)."""
        with self._lock:
            self.metrics.clear()
            self.counters.clear()
            self.alerts.clear()
            self.active_alerts.clear()

        for window in self.performance_windows.values():
            window.data_points.clear()

        self.logger.info("All metrics and alerts have been reset")

    def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        current_time = time.time()

        # Export counters
        for counter_key, value in self.counters.items():
            if ":" in counter_key:
                name, tags_json = counter_key.split(":", 1)
                try:
                    tags_dict = json.loads(tags_json)
                    tags_str = ",".join([f'{k}="{v}"' for k, v in tags_dict.items()])
                    lines.append(f'search_{name}{{{tags_str}}} {value}')
                except json.JSONDecodeError:
                    lines.append(f'search_{name} {value}')
            else:
                lines.append(f'search_{counter_key} {value}')

        # Export latest gauge values
        for metric_name, points in self.metrics.items():
            if points and points[-1].metric_type == MetricType.GAUGE:
                latest_point = points[-1]
                if latest_point.tags:
                    tags_str = ",".join([f'{k}="{v}"' for k, v in latest_point.tags.items()])
                    lines.append(f'search_{metric_name}{{{tags_str}}} {latest_point.value}')
                else:
                    lines.append(f'search_{metric_name} {latest_point.value}')

        # Export performance window statistics
        for window_name, window in self.performance_windows.items():
            stats = window.get_statistics()
            for stat_name, stat_value in stats.items():
                lines.append(f'search_{window_name}_{stat_name} {stat_value}')

        # Add timestamp
        lines.append(f'# Generated at {current_time}')

        return "\n".join(lines)

    async def start_background_monitoring(self, interval_seconds: float = 30.0) -> None:
        """Start background monitoring tasks."""
        self.logger.info("Starting background monitoring tasks")

        async def monitoring_loop():
            while True:
                try:
                    # Health check and alerting
                    health = self.get_system_health()

                    # Auto-resolve old alerts (24 hours)
                    current_time = time.time()
                    old_alerts = [
                        name for name, alert in self.active_alerts.items()
                        if current_time - alert.timestamp > 86400  # 24 hours
                    ]

                    for alert_name in old_alerts:
                        self.resolve_alert(alert_name)

                    # Log health status
                    if health["status"] != "healthy":
                        self.logger.warning(f"System health: {health['status']}")

                except Exception as e:
                    self.logger.error(f"Background monitoring error: {e}")

                await asyncio.sleep(interval_seconds)

        # Start monitoring task
        asyncio.create_task(monitoring_loop())


# Global monitor instance
_global_monitor: Optional[SearchSystemMonitor] = None


def get_search_monitor() -> SearchSystemMonitor:
    """Get global search system monitor instance."""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SearchSystemMonitor()
    return _global_monitor


def configure_search_monitoring(
    enable_alerts: bool = True,
    alert_callback: Optional[Callable] = None,
    thresholds: Optional[Dict[str, float]] = None
) -> SearchSystemMonitor:
    """Configure global search monitoring."""
    global _global_monitor
    _global_monitor = SearchSystemMonitor(enable_alerts=enable_alerts, alert_callback=alert_callback)

    if thresholds:
        _global_monitor.thresholds.update(thresholds)

    return _global_monitor


# Decorator for monitoring search operations
def monitor_search_operation(strategy: str = "unknown"):
    """Decorator to automatically monitor search operations."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            monitor = get_search_monitor()
            start_time = time.time()
            error = None
            result = None

            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                error = str(e)
                raise
            finally:
                latency_ms = (time.time() - start_time) * 1000
                success = error is None

                # Extract query information if available
                query_text = "unknown"
                if args and hasattr(args[0], 'text'):
                    query_text = args[0].text
                elif 'query' in kwargs and hasattr(kwargs['query'], 'text'):
                    query_text = kwargs['query'].text

                result_count = 0
                if result and isinstance(result, (list, tuple)):
                    result_count = len(result)

                # Record operation
                monitor.record_search_operation(
                    query_text=query_text,
                    strategy=strategy,
                    latency_ms=latency_ms,
                    result_count=result_count,
                    success=success,
                    error=error
                )

        return wrapper
    return decorator