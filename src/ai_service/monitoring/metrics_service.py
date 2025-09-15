"""
Comprehensive Metrics Service for AI Service Monitoring
"""

import asyncio
import time
import threading
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from enum import Enum
import json
import logging

from ..utils.logging_config import get_logger


class MetricType(Enum):
    """Types of metrics"""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricValue:
    """Individual metric value"""
    value: Union[int, float]
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MetricDefinition:
    """Metric definition"""
    name: str
    metric_type: MetricType
    description: str
    unit: Optional[str] = None
    labels: Set[str] = field(default_factory=set)


@dataclass
class Alert:
    """Alert definition"""
    name: str
    severity: AlertSeverity
    message: str
    timestamp: float
    metric_name: str
    metric_value: Union[int, float]
    threshold: Union[int, float]
    labels: Dict[str, str] = field(default_factory=dict)


class MetricsService:
    """Comprehensive metrics collection and monitoring service"""

    def __init__(
        self,
        max_metric_history: int = 10000,
        alert_cooldown_seconds: int = 300,  # 5 minutes
        enable_auto_cleanup: bool = True,
        cleanup_interval_hours: int = 24,
    ):
        """
        Initialize metrics service

        Args:
            max_metric_history: Maximum number of metric values to keep per metric
            alert_cooldown_seconds: Minimum time between identical alerts
            enable_auto_cleanup: Enable automatic cleanup of old metrics
            cleanup_interval_hours: Hours between automatic cleanup
        """
        self.logger = get_logger(__name__)

        # Configuration
        self.max_metric_history = max_metric_history
        self.alert_cooldown_seconds = alert_cooldown_seconds
        self.enable_auto_cleanup = enable_auto_cleanup
        self.cleanup_interval_hours = cleanup_interval_hours

        # Thread safety
        self.metrics_lock = threading.RLock()
        self.alerts_lock = threading.RLock()

        # Storage
        self.metric_definitions: Dict[str, MetricDefinition] = {}
        self.metric_values: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_metric_history))
        self.alert_rules: Dict[str, Dict[str, Any]] = {}
        self.active_alerts: List[Alert] = []
        self.alert_history: deque = deque(maxlen=1000)

        # Alert cooldown tracking
        self.alert_last_triggered: Dict[str, float] = {}

        # Performance tracking
        self.service_start_time = time.time()
        self.last_cleanup_time = time.time()

        # Background tasks
        self.cleanup_task: Optional[asyncio.Task] = None

        # Initialize core metrics
        self._initialize_core_metrics()

        self.logger.info("MetricsService initialized")

    @property
    def metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get current metric values as a dictionary"""
        result = {}
        with self.metrics_lock:
            for name, values in self.metric_values.items():
                if values:
                    latest = values[-1]
                    metric_def = self.metric_definitions.get(name)
                    result[name] = {
                        "value": latest.value,
                        "type": metric_def.metric_type.value if metric_def else "unknown",
                        "timestamp": latest.timestamp,
                        "labels": latest.labels,
                        "count": len(values)
                    }
        return result

    def _initialize_core_metrics(self):
        """Initialize core system metrics"""
        core_metrics = [
            # Performance metrics
            MetricDefinition("request_count", MetricType.COUNTER, "Total requests processed"),
            MetricDefinition("request_duration", MetricType.HISTOGRAM, "Request processing time", "seconds"),
            MetricDefinition("error_count", MetricType.COUNTER, "Total errors occurred"),
            MetricDefinition("cache_hit_rate", MetricType.GAUGE, "Cache hit rate", "percent"),

            # Service-specific metrics
            MetricDefinition("embeddings_generated", MetricType.COUNTER, "Total embeddings generated"),
            MetricDefinition("similarity_searches", MetricType.COUNTER, "Total similarity searches"),
            MetricDefinition("pattern_matches", MetricType.COUNTER, "Total pattern matches"),
            MetricDefinition("decisions_made", MetricType.COUNTER, "Total decisions made"),

            # Resource metrics
            MetricDefinition("memory_usage", MetricType.GAUGE, "Memory usage", "bytes"),
            MetricDefinition("cpu_usage", MetricType.GAUGE, "CPU usage", "percent"),
            MetricDefinition("active_threads", MetricType.GAUGE, "Active thread count"),

            # Quality metrics
            MetricDefinition("confidence_score", MetricType.HISTOGRAM, "Confidence scores"),
            MetricDefinition("processing_accuracy", MetricType.GAUGE, "Processing accuracy", "percent"),
            MetricDefinition("false_positive_rate", MetricType.GAUGE, "False positive rate", "percent"),
        ]

        for metric_def in core_metrics:
            self.register_metric(metric_def)

    def register_metric(self, metric_def: MetricDefinition):
        """Register a new metric definition"""
        with self.metrics_lock:
            self.metric_definitions[metric_def.name] = metric_def
            self.logger.debug(f"Registered metric: {metric_def.name}")

    def increment_counter(self, name: str, value: Union[int, float] = 1, labels: Optional[Dict[str, str]] = None):
        """Increment a counter metric"""
        self._record_metric_value(name, value, labels or {})

    def set_gauge(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Set a gauge metric value"""
        self._record_metric_value(name, value, labels or {})

    def record_histogram(self, name: str, value: Union[int, float], labels: Optional[Dict[str, str]] = None):
        """Record a histogram metric value"""
        self._record_metric_value(name, value, labels or {})

    def record_timer(self, name: str, duration: float, labels: Optional[Dict[str, str]] = None):
        """Record a timer metric"""
        self._record_metric_value(name, duration, labels or {})

    def _record_metric_value(self, name: str, value: Union[int, float], labels: Dict[str, str]):
        """Record a metric value with thread safety"""
        if name not in self.metric_definitions:
            self.logger.warning(f"Recording value for unregistered metric: {name}")
            return

        timestamp = time.time()
        metric_value = MetricValue(value=value, timestamp=timestamp, labels=labels)

        with self.metrics_lock:
            self.metric_values[name].append(metric_value)

        # Check alert rules
        self._check_alert_rules(name, value, labels)

    def timer(self, name: str, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations"""
        return MetricTimer(self, name, labels or {})

    def get_metric_values(
        self,
        name: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        labels: Optional[Dict[str, str]] = None,
    ) -> List[MetricValue]:
        """Get metric values within time range and matching labels"""
        if name not in self.metric_values:
            return []

        with self.metrics_lock:
            values = list(self.metric_values[name])

        # Filter by time range
        if start_time is not None:
            values = [v for v in values if v.timestamp >= start_time]
        if end_time is not None:
            values = [v for v in values if v.timestamp <= end_time]

        # Filter by labels
        if labels:
            values = [v for v in values if all(
                v.labels.get(k) == v for k, v in labels.items()
            )]

        return values

    def get_metric_summary(self, name: str, time_window_seconds: int = 300) -> Dict[str, Any]:
        """Get summary statistics for a metric"""
        end_time = time.time()
        start_time = end_time - time_window_seconds
        values = self.get_metric_values(name, start_time, end_time)

        if not values:
            return {"name": name, "count": 0, "time_window_seconds": time_window_seconds}

        numeric_values = [v.value for v in values]

        return {
            "name": name,
            "count": len(values),
            "time_window_seconds": time_window_seconds,
            "min": min(numeric_values),
            "max": max(numeric_values),
            "avg": sum(numeric_values) / len(numeric_values),
            "sum": sum(numeric_values),
            "latest": numeric_values[-1],
            "first": numeric_values[0],
        }

    def add_alert_rule(
        self,
        metric_name: str,
        threshold: Union[int, float],
        condition: str,  # "gt", "lt", "eq", "gte", "lte"
        severity: AlertSeverity,
        message_template: str,
        labels: Optional[Dict[str, str]] = None,
    ):
        """Add an alert rule for a metric"""
        rule_key = f"{metric_name}_{condition}_{threshold}"

        with self.alerts_lock:
            self.alert_rules[rule_key] = {
                "metric_name": metric_name,
                "threshold": threshold,
                "condition": condition,
                "severity": severity,
                "message_template": message_template,
                "labels": labels or {},
            }

        self.logger.info(f"Added alert rule: {rule_key}")

    def _check_alert_rules(self, metric_name: str, value: Union[int, float], labels: Dict[str, str]):
        """Check if any alert rules are triggered"""
        with self.alerts_lock:
            for rule_key, rule in self.alert_rules.items():
                if rule["metric_name"] != metric_name:
                    continue

                # Check if alert is in cooldown
                if self._is_alert_in_cooldown(rule_key):
                    continue

                # Check condition
                if self._evaluate_condition(value, rule["condition"], rule["threshold"]):
                    self._trigger_alert(rule_key, rule, value, labels)

    def _is_alert_in_cooldown(self, rule_key: str) -> bool:
        """Check if alert is in cooldown period"""
        last_triggered = self.alert_last_triggered.get(rule_key, 0)
        return time.time() - last_triggered < self.alert_cooldown_seconds

    def _evaluate_condition(self, value: Union[int, float], condition: str, threshold: Union[int, float]) -> bool:
        """Evaluate alert condition"""
        if condition == "gt":
            return value > threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "eq":
            return value == threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lte":
            return value <= threshold
        else:
            self.logger.error(f"Unknown alert condition: {condition}")
            return False

    def _trigger_alert(self, rule_key: str, rule: Dict[str, Any], value: Union[int, float], labels: Dict[str, str]):
        """Trigger an alert"""
        timestamp = time.time()

        alert = Alert(
            name=rule_key,
            severity=rule["severity"],
            message=rule["message_template"].format(value=value, threshold=rule["threshold"]),
            timestamp=timestamp,
            metric_name=rule["metric_name"],
            metric_value=value,
            threshold=rule["threshold"],
            labels={**rule["labels"], **labels},
        )

        self.active_alerts.append(alert)
        self.alert_history.append(alert)
        self.alert_last_triggered[rule_key] = timestamp

        self.logger.warning(f"Alert triggered: {alert.name} - {alert.message}")

    def get_active_alerts(self, severity: Optional[AlertSeverity] = None) -> List[Alert]:
        """Get currently active alerts"""
        with self.alerts_lock:
            alerts = list(self.active_alerts)

        if severity:
            alerts = [a for a in alerts if a.severity == severity]

        return alerts

    def resolve_alert(self, alert_name: str):
        """Resolve an active alert"""
        with self.alerts_lock:
            self.active_alerts = [a for a in self.active_alerts if a.name != alert_name]

        self.logger.info(f"Alert resolved: {alert_name}")

    def get_system_health(self) -> Dict[str, Any]:
        """Get overall system health metrics"""
        current_time = time.time()
        uptime_seconds = current_time - self.service_start_time

        # Calculate error rates
        error_count_summary = self.get_metric_summary("error_count", 300)
        request_count_summary = self.get_metric_summary("request_count", 300)

        error_rate = 0.0
        if request_count_summary["count"] > 0:
            error_rate = (error_count_summary["sum"] / request_count_summary["sum"]) * 100

        # Get cache performance
        cache_hit_rate = self.get_metric_summary("cache_hit_rate", 300)

        # Count alerts by severity
        alert_counts = defaultdict(int)
        for alert in self.active_alerts:
            alert_counts[alert.severity.value] += 1

        return {
            "status": "healthy" if error_rate < 5.0 and len(self.active_alerts) == 0 else "degraded",
            "uptime_seconds": uptime_seconds,
            "uptime_human": str(timedelta(seconds=int(uptime_seconds))),
            "error_rate_percent": error_rate,
            "active_alerts": len(self.active_alerts),
            "alert_counts": dict(alert_counts),
            "cache_hit_rate": cache_hit_rate.get("latest", 0.0),
            "metrics_collected": len(self.metric_definitions),
            "total_metric_values": sum(len(values) for values in self.metric_values.values()),
            "timestamp": current_time,
        }

    def export_metrics(self, format: str = "json") -> Union[str, Dict[str, Any]]:
        """Export all metrics in specified format"""
        export_data = {
            "timestamp": time.time(),
            "service_uptime": time.time() - self.service_start_time,
            "metrics": {},
            "alerts": {
                "active": [self._alert_to_dict(a) for a in self.active_alerts],
                "total_active": len(self.active_alerts),
            },
            "system_health": self.get_system_health(),
        }

        # Export metric summaries
        for name in self.metric_definitions.keys():
            export_data["metrics"][name] = self.get_metric_summary(name)

        if format == "json":
            return json.dumps(export_data, indent=2, default=str)
        else:
            return export_data

    def _alert_to_dict(self, alert: Alert) -> Dict[str, Any]:
        """Convert alert to dictionary"""
        return {
            "name": alert.name,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp,
            "metric_name": alert.metric_name,
            "metric_value": alert.metric_value,
            "threshold": alert.threshold,
            "labels": alert.labels,
        }

    def cleanup_old_metrics(self, max_age_hours: int = 24):
        """Clean up old metric values"""
        cutoff_time = time.time() - (max_age_hours * 3600)
        cleaned_count = 0

        with self.metrics_lock:
            for name, values in self.metric_values.items():
                original_length = len(values)

                # Filter out old values
                while values and values[0].timestamp < cutoff_time:
                    values.popleft()

                cleaned_count += original_length - len(values)

        # Clean up old alerts
        with self.alerts_lock:
            while self.alert_history and self.alert_history[0].timestamp < cutoff_time:
                self.alert_history.popleft()

        self.last_cleanup_time = time.time()
        self.logger.info(f"Cleaned up {cleaned_count} old metric values")

    async def start_background_tasks(self):
        """Start background monitoring tasks"""
        if self.enable_auto_cleanup and not self.cleanup_task:
            self.cleanup_task = asyncio.create_task(self._cleanup_loop())
            self.logger.info("Started background cleanup task")

    async def stop_background_tasks(self):
        """Stop background monitoring tasks"""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass
            self.cleanup_task = None
            self.logger.info("Stopped background tasks")

    async def _cleanup_loop(self):
        """Background cleanup loop"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval_hours * 3600)
                self.cleanup_old_metrics()
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cleanup loop: {e}")

    def get_performance_report(self, time_window_hours: int = 1) -> Dict[str, Any]:
        """Generate comprehensive performance report"""
        window_seconds = time_window_hours * 3600
        current_time = time.time()

        # Key performance indicators
        request_summary = self.get_metric_summary("request_count", window_seconds)
        error_summary = self.get_metric_summary("error_count", window_seconds)
        duration_summary = self.get_metric_summary("request_duration", window_seconds)

        # Service-specific metrics
        embeddings_summary = self.get_metric_summary("embeddings_generated", window_seconds)
        similarity_summary = self.get_metric_summary("similarity_searches", window_seconds)
        patterns_summary = self.get_metric_summary("pattern_matches", window_seconds)

        return {
            "report_timestamp": current_time,
            "time_window_hours": time_window_hours,
            "performance_summary": {
                "requests_processed": request_summary["sum"],
                "avg_request_duration": duration_summary.get("avg", 0.0),
                "error_rate": (error_summary["sum"] / max(request_summary["sum"], 1)) * 100,
                "throughput_per_second": request_summary["sum"] / window_seconds,
            },
            "service_metrics": {
                "embeddings_generated": embeddings_summary["sum"],
                "similarity_searches": similarity_summary["sum"],
                "pattern_matches": patterns_summary["sum"],
            },
            "alerts_summary": {
                "active_critical": len([a for a in self.active_alerts if a.severity == AlertSeverity.CRITICAL]),
                "active_total": len(self.active_alerts),
            },
            "system_health": self.get_system_health(),
        }

    def __del__(self):
        """Cleanup on destruction"""
        try:
            if self.cleanup_task and not self.cleanup_task.done():
                self.cleanup_task.cancel()
        except Exception:
            pass


class MetricTimer:
    """Context manager for timing operations"""

    def __init__(self, metrics_service: MetricsService, metric_name: str, labels: Dict[str, str]):
        self.metrics_service = metrics_service
        self.metric_name = metric_name
        self.labels = labels
        self.start_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            duration = time.time() - self.start_time
            self.metrics_service.record_timer(self.metric_name, duration, self.labels)