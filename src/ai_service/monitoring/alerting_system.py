"""
Comprehensive alerting system for SLA violations, error spikes, and performance issues.
Integrates with metrics collection and provides monitoring dashboard support.
"""

import asyncio
import time
from typing import Dict, List, Optional, Callable, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime, timedelta

from .metrics_collector import get_metrics_collector, AggregationType
from ..utils.enhanced_logging import get_logger_for_component, LogCategory


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"
    ACKNOWLEDGED = "acknowledged"


class ThresholdType(Enum):
    """Types of threshold comparisons."""
    GREATER_THAN = "gt"
    LESS_THAN = "lt"
    GREATER_EQUAL = "gte"
    LESS_EQUAL = "lte"
    EQUAL = "eq"
    NOT_EQUAL = "ne"


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    name: str
    description: str
    metric_name: str
    threshold_value: float
    threshold_type: ThresholdType
    severity: AlertSeverity
    time_window_seconds: float = 300.0  # 5 minutes
    evaluation_interval_seconds: float = 60.0  # 1 minute
    min_data_points: int = 3
    aggregation: AggregationType = AggregationType.AVERAGE
    tags_filter: Dict[str, str] = field(default_factory=dict)
    suppress_duration_seconds: float = 3600.0  # 1 hour
    runbook_url: Optional[str] = None
    enabled: bool = True

    def evaluate(self, current_value: float, data_points: int) -> bool:
        """Evaluate if alert should trigger."""
        if not self.enabled or data_points < self.min_data_points:
            return False

        if self.threshold_type == ThresholdType.GREATER_THAN:
            return current_value > self.threshold_value
        elif self.threshold_type == ThresholdType.LESS_THAN:
            return current_value < self.threshold_value
        elif self.threshold_type == ThresholdType.GREATER_EQUAL:
            return current_value >= self.threshold_value
        elif self.threshold_type == ThresholdType.LESS_EQUAL:
            return current_value <= self.threshold_value
        elif self.threshold_type == ThresholdType.EQUAL:
            return abs(current_value - self.threshold_value) < 0.001
        elif self.threshold_type == ThresholdType.NOT_EQUAL:
            return abs(current_value - self.threshold_value) >= 0.001

        return False


@dataclass
class Alert:
    """Active alert instance."""
    rule_name: str
    severity: AlertSeverity
    message: str
    current_value: float
    threshold_value: float
    metric_name: str
    start_time: float
    status: AlertStatus = AlertStatus.ACTIVE
    resolution_time: Optional[float] = None
    acknowledgment_time: Optional[float] = None
    acknowledgment_user: Optional[str] = None
    tags: Dict[str, str] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        """Get alert duration in seconds."""
        end_time = self.resolution_time or time.time()
        return end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "message": self.message,
            "current_value": self.current_value,
            "threshold_value": self.threshold_value,
            "metric_name": self.metric_name,
            "start_time": self.start_time,
            "status": self.status.value,
            "resolution_time": self.resolution_time,
            "acknowledgment_time": self.acknowledgment_time,
            "acknowledgment_user": self.acknowledgment_user,
            "duration_seconds": self.duration_seconds,
            "tags": self.tags,
            "details": self.details
        }


class AlertingSystem:
    """Main alerting system with SLA monitoring and dashboard integration."""

    def __init__(self):
        self.logger = get_logger_for_component("alerting", LogCategory.MONITORING)
        self.metrics_collector = get_metrics_collector()

        # Alert management
        self.alert_rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.suppressed_alerts: Dict[str, float] = {}  # rule_name -> suppress_until_time

        # Notification callbacks
        self.notification_callbacks: List[Callable[[Alert], None]] = []

        # Statistics
        self.alerting_stats = {
            "total_alerts_triggered": 0,
            "alerts_by_severity": {severity.value: 0 for severity in AlertSeverity},
            "last_evaluation_time": 0,
            "evaluation_duration_ms": 0,
            "evaluation_errors": 0
        }

        # Initialize default alert rules
        self._initialize_default_rules()

    def _initialize_default_rules(self) -> None:
        """Initialize default alert rules for common SLA violations."""
        default_rules = [
            # API Performance SLA
            AlertRule(
                name="high_api_p95_latency",
                description="API P95 latency exceeds SLA threshold",
                metric_name="api_request_duration",
                threshold_value=200.0,  # 200ms
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                aggregation=AggregationType.P95,
                runbook_url="https://docs.company.com/runbooks/high-api-latency"
            ),
            AlertRule(
                name="critical_api_p95_latency",
                description="API P95 latency critically high",
                metric_name="api_request_duration",
                threshold_value=500.0,  # 500ms
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.CRITICAL,
                aggregation=AggregationType.P95
            ),
            AlertRule(
                name="high_api_error_rate",
                description="API error rate exceeds acceptable threshold",
                metric_name="api_requests_failed",
                threshold_value=5.0,  # 5%
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                time_window_seconds=300.0
            ),
            AlertRule(
                name="critical_api_error_rate",
                description="API error rate critically high",
                metric_name="api_requests_failed",
                threshold_value=10.0,  # 10%
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.CRITICAL,
                time_window_seconds=300.0
            ),

            # Search Performance SLA
            AlertRule(
                name="high_search_latency",
                description="Search operation latency high",
                metric_name="search_operation_duration",
                threshold_value=1000.0,  # 1 second
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                aggregation=AggregationType.P95
            ),
            AlertRule(
                name="search_error_spike",
                description="Search error rate spike detected",
                metric_name="search_operations_failed",
                threshold_value=10.0,  # 10%
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                time_window_seconds=180.0  # 3 minutes
            ),

            # ElasticSearch Health
            AlertRule(
                name="elasticsearch_slow_response",
                description="ElasticSearch response time degraded",
                metric_name="elasticsearch_response_time",
                threshold_value=1000.0,  # 1 second
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                aggregation=AggregationType.P95
            ),
            AlertRule(
                name="elasticsearch_connection_failures",
                description="ElasticSearch connection failures detected",
                metric_name="elasticsearch_requests_failed",
                threshold_value=5.0,  # 5%
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.CRITICAL,
                time_window_seconds=300.0
            ),

            # System Resource Alerts
            AlertRule(
                name="high_memory_usage",
                description="System memory usage high",
                metric_name="memory_usage_mb",
                threshold_value=1000.0,  # 1GB
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.WARNING,
                aggregation=AggregationType.AVERAGE
            ),
            AlertRule(
                name="concurrent_requests_high",
                description="High number of concurrent requests",
                metric_name="concurrent_requests",
                threshold_value=50.0,
                threshold_type=ThresholdType.GREATER_THAN,
                severity=AlertSeverity.INFO,
                aggregation=AggregationType.MAX
            )
        ]

        for rule in default_rules:
            self.add_alert_rule(rule)

    def add_alert_rule(self, rule: AlertRule) -> None:
        """Add alert rule to the system."""
        self.alert_rules[rule.name] = rule
        self.logger.info(f"Alert rule added: {rule.name}", context={"rule": rule.name})

    def remove_alert_rule(self, rule_name: str) -> bool:
        """Remove alert rule from the system."""
        if rule_name in self.alert_rules:
            del self.alert_rules[rule_name]
            # Also resolve any active alerts for this rule
            if rule_name in self.active_alerts:
                self.resolve_alert(rule_name)
            self.logger.info(f"Alert rule removed: {rule_name}", context={"rule": rule_name})
            return True
        return False

    def update_alert_rule(self, rule_name: str, updates: Dict[str, Any]) -> bool:
        """Update existing alert rule."""
        if rule_name not in self.alert_rules:
            return False

        rule = self.alert_rules[rule_name]
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        self.logger.info(f"Alert rule updated: {rule_name}", context={"rule": rule_name, "updates": list(updates.keys())})
        return True

    def add_notification_callback(self, callback: Callable[[Alert], None]) -> None:
        """Add notification callback for alerts."""
        self.notification_callbacks.append(callback)

    def remove_notification_callback(self, callback: Callable[[Alert], None]) -> None:
        """Remove notification callback."""
        if callback in self.notification_callbacks:
            self.notification_callbacks.remove(callback)

    def suppress_alert_rule(self, rule_name: str, duration_seconds: float) -> None:
        """Temporarily suppress alert rule."""
        suppress_until = time.time() + duration_seconds
        self.suppressed_alerts[rule_name] = suppress_until
        self.logger.info(f"Alert rule suppressed: {rule_name} for {duration_seconds}s",
                        context={"rule": rule_name, "duration": duration_seconds})

    def unsuppress_alert_rule(self, rule_name: str) -> None:
        """Remove suppression from alert rule."""
        if rule_name in self.suppressed_alerts:
            del self.suppressed_alerts[rule_name]
            self.logger.info(f"Alert rule suppression removed: {rule_name}", context={"rule": rule_name})

    def is_rule_suppressed(self, rule_name: str) -> bool:
        """Check if alert rule is currently suppressed."""
        if rule_name in self.suppressed_alerts:
            suppress_until = self.suppressed_alerts[rule_name]
            if time.time() < suppress_until:
                return True
            else:
                # Suppression expired, remove it
                del self.suppressed_alerts[rule_name]
        return False

    def _trigger_alert(self, rule: AlertRule, current_value: float, data_points: int) -> None:
        """Trigger new alert."""
        # Check if already active
        if rule.name in self.active_alerts:
            return

        # Check if suppressed
        if self.is_rule_suppressed(rule.name):
            return

        # Create alert
        alert = Alert(
            rule_name=rule.name,
            severity=rule.severity,
            message=f"{rule.description}: {current_value:.2f} {rule.threshold_type.value} {rule.threshold_value:.2f}",
            current_value=current_value,
            threshold_value=rule.threshold_value,
            metric_name=rule.metric_name,
            start_time=time.time(),
            tags=rule.tags_filter,
            details={
                "aggregation": rule.aggregation.value,
                "time_window_seconds": rule.time_window_seconds,
                "data_points": data_points,
                "runbook_url": rule.runbook_url
            }
        )

        # Add to active alerts
        self.active_alerts[rule.name] = alert
        self.alert_history.append(alert)

        # Update statistics
        self.alerting_stats["total_alerts_triggered"] += 1
        self.alerting_stats["alerts_by_severity"][rule.severity.value] += 1

        # Send notifications
        for callback in self.notification_callbacks:
            try:
                callback(alert)
            except Exception as e:
                self.logger.error(f"Alert notification callback failed: {e}", error=e)

        self.logger.warning(
            f"ALERT TRIGGERED: {rule.name}",
            context={
                "rule": rule.name,
                "severity": rule.severity.value,
                "current_value": current_value,
                "threshold": rule.threshold_value,
                "metric": rule.metric_name
            }
        )

    def resolve_alert(self, rule_name: str, user: Optional[str] = None) -> bool:
        """Resolve active alert."""
        if rule_name not in self.active_alerts:
            return False

        alert = self.active_alerts[rule_name]
        alert.status = AlertStatus.RESOLVED
        alert.resolution_time = time.time()

        # Remove from active alerts
        del self.active_alerts[rule_name]

        self.logger.info(
            f"ALERT RESOLVED: {rule_name}",
            context={
                "rule": rule_name,
                "duration_seconds": alert.duration_seconds,
                "resolved_by": user or "system"
            }
        )

        return True

    def acknowledge_alert(self, rule_name: str, user: str) -> bool:
        """Acknowledge active alert."""
        if rule_name not in self.active_alerts:
            return False

        alert = self.active_alerts[rule_name]
        alert.status = AlertStatus.ACKNOWLEDGED
        alert.acknowledgment_time = time.time()
        alert.acknowledgment_user = user

        self.logger.info(
            f"ALERT ACKNOWLEDGED: {rule_name}",
            context={"rule": rule_name, "user": user}
        )

        return True

    async def evaluate_all_rules(self) -> Dict[str, Any]:
        """Evaluate all alert rules and trigger/resolve alerts."""
        evaluation_start = time.time()
        evaluation_results = {}

        try:
            for rule_name, rule in self.alert_rules.items():
                try:
                    result = await self._evaluate_rule(rule)
                    evaluation_results[rule_name] = result
                except Exception as e:
                    self.logger.error(f"Error evaluating rule {rule_name}: {e}", error=e)
                    self.alerting_stats["evaluation_errors"] += 1
                    evaluation_results[rule_name] = {"error": str(e)}

            # Update statistics
            evaluation_duration = (time.time() - evaluation_start) * 1000
            self.alerting_stats.update({
                "last_evaluation_time": evaluation_start,
                "evaluation_duration_ms": evaluation_duration
            })

        except Exception as e:
            self.logger.error(f"Alert evaluation failed: {e}", error=e)
            self.alerting_stats["evaluation_errors"] += 1

        return evaluation_results

    async def _evaluate_rule(self, rule: AlertRule) -> Dict[str, Any]:
        """Evaluate single alert rule."""
        if not rule.enabled:
            return {"status": "disabled"}

        # Get metric statistics
        stats = self.metrics_collector.get_metric_stats(
            rule.metric_name,
            [rule.aggregation, AggregationType.COUNT],
            rule.time_window_seconds,
            rule.tags_filter
        )

        current_value = stats.get(rule.aggregation.value, 0)
        data_points = int(stats.get("count", 0))

        # Evaluate rule
        should_trigger = rule.evaluate(current_value, data_points)
        is_currently_active = rule.name in self.active_alerts

        result = {
            "current_value": current_value,
            "threshold_value": rule.threshold_value,
            "data_points": data_points,
            "should_trigger": should_trigger,
            "is_active": is_currently_active,
            "evaluation_time": time.time()
        }

        # Handle alert state changes
        if should_trigger and not is_currently_active:
            self._trigger_alert(rule, current_value, data_points)
            result["action"] = "triggered"
        elif not should_trigger and is_currently_active:
            # Auto-resolve if condition is no longer met
            self.resolve_alert(rule.name)
            result["action"] = "resolved"
        else:
            result["action"] = "no_change"

        return result

    def get_active_alerts_summary(self) -> Dict[str, Any]:
        """Get summary of active alerts."""
        current_time = time.time()

        alerts_by_severity = {severity.value: [] for severity in AlertSeverity}
        for alert in self.active_alerts.values():
            alerts_by_severity[alert.severity.value].append({
                "rule_name": alert.rule_name,
                "message": alert.message,
                "duration_seconds": alert.duration_seconds,
                "current_value": alert.current_value,
                "status": alert.status.value
            })

        return {
            "timestamp": current_time,
            "total_active_alerts": len(self.active_alerts),
            "alerts_by_severity": alerts_by_severity,
            "suppressed_rules": list(self.suppressed_alerts.keys()),
            "alerting_stats": dict(self.alerting_stats)
        }

    def get_alert_history(self, limit: int = 100, severity_filter: Optional[AlertSeverity] = None) -> List[Dict[str, Any]]:
        """Get alert history with optional filtering."""
        filtered_alerts = self.alert_history

        if severity_filter:
            filtered_alerts = [a for a in filtered_alerts if a.severity == severity_filter]

        # Sort by start time (most recent first)
        filtered_alerts = sorted(filtered_alerts, key=lambda a: a.start_time, reverse=True)

        # Limit results
        filtered_alerts = filtered_alerts[:limit]

        return [alert.to_dict() for alert in filtered_alerts]

    def get_sla_compliance_report(self, time_window_hours: float = 24.0) -> Dict[str, Any]:
        """Generate SLA compliance report."""
        current_time = time.time()
        start_time = current_time - (time_window_hours * 3600)

        # Get performance metrics for SLA analysis
        performance_metrics = self.metrics_collector.get_performance_metrics()
        error_metrics = self.metrics_collector.get_error_rate_metrics()

        # Calculate SLA compliance
        sla_targets = {
            "api_p95_latency_ms": 200.0,
            "api_p99_latency_ms": 500.0,
            "api_error_rate_percent": 1.0,
            "search_p95_latency_ms": 1000.0,
            "search_error_rate_percent": 2.0,
            "elasticsearch_p95_latency_ms": 500.0
        }

        compliance_status = {}
        overall_compliance = True

        for metric_name, target in sla_targets.items():
            # Check current performance
            if "latency" in metric_name:
                base_metric = metric_name.replace("_p95", "").replace("_p99", "")
                if base_metric in performance_metrics:
                    current_value = performance_metrics[base_metric].get("p95" if "p95" in metric_name else "p99", 0)
                else:
                    current_value = 0
            else:
                current_value = error_metrics.get(metric_name, 0)

            is_compliant = current_value <= target
            compliance_percentage = min((target / max(current_value, 0.001)) * 100, 100)

            compliance_status[metric_name] = {
                "target": target,
                "current": current_value,
                "compliant": is_compliant,
                "compliance_percentage": round(compliance_percentage, 2)
            }

            if not is_compliant:
                overall_compliance = False

        # Get alert statistics for the time window
        recent_alerts = [a for a in self.alert_history if a.start_time >= start_time]
        critical_alerts = len([a for a in recent_alerts if a.severity == AlertSeverity.CRITICAL])
        warning_alerts = len([a for a in recent_alerts if a.severity == AlertSeverity.WARNING])

        return {
            "timestamp": current_time,
            "time_window_hours": time_window_hours,
            "overall_compliance": overall_compliance,
            "sla_metrics": compliance_status,
            "alert_summary": {
                "total_alerts": len(recent_alerts),
                "critical_alerts": critical_alerts,
                "warning_alerts": warning_alerts,
                "current_active_alerts": len(self.active_alerts)
            },
            "availability": {
                "uptime_percentage": self._calculate_uptime_percentage(time_window_hours),
                "total_downtime_minutes": self._calculate_total_downtime(time_window_hours)
            }
        }

    def _calculate_uptime_percentage(self, time_window_hours: float) -> float:
        """Calculate uptime percentage based on critical alerts."""
        current_time = time.time()
        start_time = current_time - (time_window_hours * 3600)

        # Find critical alerts in time window
        critical_alerts = [
            a for a in self.alert_history
            if a.start_time >= start_time and a.severity == AlertSeverity.CRITICAL
        ]

        # Calculate total downtime
        total_downtime = 0
        for alert in critical_alerts:
            end_time = alert.resolution_time or current_time
            duration = end_time - max(alert.start_time, start_time)
            total_downtime += max(duration, 0)

        # Calculate uptime percentage
        total_time = time_window_hours * 3600
        uptime_percentage = ((total_time - total_downtime) / total_time) * 100
        return round(max(uptime_percentage, 0), 2)

    def _calculate_total_downtime(self, time_window_hours: float) -> float:
        """Calculate total downtime in minutes."""
        uptime_percentage = self._calculate_uptime_percentage(time_window_hours)
        total_minutes = time_window_hours * 60
        downtime_minutes = ((100 - uptime_percentage) / 100) * total_minutes
        return round(downtime_minutes, 1)

    def export_alerts_for_dashboard(self) -> Dict[str, Any]:
        """Export alert data for monitoring dashboard."""
        return {
            "active_alerts": [alert.to_dict() for alert in self.active_alerts.values()],
            "alert_rules": [
                {
                    "name": rule.name,
                    "description": rule.description,
                    "metric_name": rule.metric_name,
                    "threshold_value": rule.threshold_value,
                    "severity": rule.severity.value,
                    "enabled": rule.enabled,
                    "suppressed": self.is_rule_suppressed(rule.name)
                }
                for rule in self.alert_rules.values()
            ],
            "alerting_stats": dict(self.alerting_stats),
            "sla_compliance": self.get_sla_compliance_report(24.0)
        }

    async def start_background_evaluation(self, interval_seconds: float = 60.0) -> None:
        """Start background alert evaluation."""
        self.logger.info("Starting background alert evaluation")

        async def evaluation_loop():
            while True:
                try:
                    await self.evaluate_all_rules()
                except Exception as e:
                    self.logger.error(f"Background alert evaluation error: {e}", error=e)

                await asyncio.sleep(interval_seconds)

        # Start evaluation task
        asyncio.create_task(evaluation_loop())


# Global alerting system
_global_alerting_system: Optional[AlertingSystem] = None


def get_alerting_system() -> AlertingSystem:
    """Get global alerting system instance."""
    global _global_alerting_system
    if _global_alerting_system is None:
        _global_alerting_system = AlertingSystem()
    return _global_alerting_system


# Notification callback examples
def log_alert_notification(alert: Alert) -> None:
    """Simple logging notification callback."""
    logger = get_logger_for_component("alerts", LogCategory.MONITORING)
    logger.warning(
        f"Alert notification: {alert.message}",
        context={
            "alert_rule": alert.rule_name,
            "severity": alert.severity.value,
            "current_value": alert.current_value,
            "threshold": alert.threshold_value
        }
    )


def slack_alert_notification(alert: Alert, webhook_url: str) -> None:
    """Slack notification callback (requires requests library)."""
    try:
        import requests

        severity_colors = {
            AlertSeverity.INFO: "#36a64f",
            AlertSeverity.WARNING: "#ff9500",
            AlertSeverity.CRITICAL: "#ff0000",
            AlertSeverity.EMERGENCY: "#8B0000"
        }

        payload = {
            "attachments": [{
                "color": severity_colors.get(alert.severity, "#cccccc"),
                "title": f"Alert: {alert.rule_name}",
                "text": alert.message,
                "fields": [
                    {"title": "Severity", "value": alert.severity.value.upper(), "short": True},
                    {"title": "Metric", "value": alert.metric_name, "short": True},
                    {"title": "Current Value", "value": f"{alert.current_value:.2f}", "short": True},
                    {"title": "Threshold", "value": f"{alert.threshold_value:.2f}", "short": True}
                ],
                "footer": "AI Service Monitoring",
                "ts": int(alert.start_time)
            }]
        }

        if alert.details.get("runbook_url"):
            payload["attachments"][0]["actions"] = [{
                "type": "button",
                "text": "View Runbook",
                "url": alert.details["runbook_url"]
            }]

        requests.post(webhook_url, json=payload, timeout=10)

    except Exception as e:
        logger = get_logger_for_component("alerts", LogCategory.MONITORING)
        logger.error(f"Slack notification failed: {e}", error=e)


# Configure default alerting
def configure_alerting_system(
    notification_callbacks: Optional[List[Callable[[Alert], None]]] = None,
    custom_rules: Optional[List[AlertRule]] = None
) -> AlertingSystem:
    """Configure alerting system with custom settings."""
    alerting_system = get_alerting_system()

    # Add notification callbacks
    if notification_callbacks:
        for callback in notification_callbacks:
            alerting_system.add_notification_callback(callback)
    else:
        # Default to logging notification
        alerting_system.add_notification_callback(log_alert_notification)

    # Add custom rules
    if custom_rules:
        for rule in custom_rules:
            alerting_system.add_alert_rule(rule)

    return alerting_system