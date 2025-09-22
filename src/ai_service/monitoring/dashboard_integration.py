"""
Monitoring dashboard integration with comprehensive observability data export.
Provides unified interface for Grafana, custom dashboards, and monitoring tools.
"""

import asyncio
import time
import json
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from .metrics_collector import get_metrics_collector, AggregationType
from .alerting_system import get_alerting_system
from ..utils.enhanced_logging import get_logger_for_component, LogCategory


class DashboardFormat(Enum):
    """Dashboard data export formats."""
    JSON = "json"
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    CSV = "csv"


@dataclass
class DashboardPanel:
    """Dashboard panel configuration."""
    title: str
    metric_name: str
    panel_type: str = "graph"  # graph, singlestat, table, heatmap
    aggregation: AggregationType = AggregationType.AVERAGE
    time_window_seconds: float = 3600.0
    tags_filter: Dict[str, str] = field(default_factory=dict)
    thresholds: Dict[str, float] = field(default_factory=dict)
    unit: str = ""
    description: str = ""


@dataclass
class DashboardRow:
    """Dashboard row containing multiple panels."""
    title: str
    panels: List[DashboardPanel] = field(default_factory=list)
    collapsed: bool = False


@dataclass
class Dashboard:
    """Complete dashboard configuration."""
    title: str
    description: str
    rows: List[DashboardRow] = field(default_factory=list)
    refresh_interval: str = "30s"
    time_range: str = "1h"
    tags: List[str] = field(default_factory=list)


class DashboardDataExporter:
    """Main dashboard integration and data export system."""

    def __init__(self):
        self.logger = get_logger_for_component("dashboard", LogCategory.MONITORING)
        self.metrics_collector = get_metrics_collector()
        self.alerting_system = get_alerting_system()

        # Dashboard configurations
        self.dashboards: Dict[str, Dashboard] = {}

        # Initialize default dashboards
        self._initialize_default_dashboards()

    def _initialize_default_dashboards(self) -> None:
        """Initialize default dashboard configurations."""
        # Main System Overview Dashboard
        system_dashboard = Dashboard(
            title="AI Service - System Overview",
            description="High-level system performance and health metrics",
            tags=["ai-service", "overview"]
        )

        # API Performance Row
        api_row = DashboardRow(title="API Performance")
        api_row.panels.extend([
            DashboardPanel(
                title="API Request Rate",
                metric_name="api_requests_total",
                aggregation=AggregationType.RATE_PER_MINUTE,
                unit="req/min",
                description="API requests per minute"
            ),
            DashboardPanel(
                title="API P95 Latency",
                metric_name="api_request_duration",
                aggregation=AggregationType.P95,
                unit="ms",
                thresholds={"warning": 200, "critical": 500},
                description="95th percentile API response time"
            ),
            DashboardPanel(
                title="API Error Rate",
                metric_name="api_requests_failed",
                aggregation=AggregationType.RATE_PER_MINUTE,
                unit="%",
                thresholds={"warning": 5, "critical": 10},
                description="API error rate percentage"
            ),
            DashboardPanel(
                title="API Status Codes",
                metric_name="api_requests_total",
                panel_type="table",
                description="API requests by status code"
            )
        ])

        # Search Performance Row
        search_row = DashboardRow(title="Search Performance")
        search_row.panels.extend([
            DashboardPanel(
                title="Search Request Rate",
                metric_name="search_operations_total",
                aggregation=AggregationType.RATE_PER_MINUTE,
                unit="search/min"
            ),
            DashboardPanel(
                title="Search P95 Latency",
                metric_name="search_operation_duration",
                aggregation=AggregationType.P95,
                unit="ms",
                thresholds={"warning": 1000, "critical": 2000}
            ),
            DashboardPanel(
                title="Search Result Count",
                metric_name="search_result_count",
                aggregation=AggregationType.AVERAGE,
                unit="results"
            ),
            DashboardPanel(
                title="Search Strategies",
                metric_name="search_operations_total",
                panel_type="pie",
                description="Search operations by strategy"
            )
        ])

        # ElasticSearch Health Row
        elasticsearch_row = DashboardRow(title="ElasticSearch Health")
        elasticsearch_row.panels.extend([
            DashboardPanel(
                title="ES Response Time",
                metric_name="elasticsearch_response_time",
                aggregation=AggregationType.P95,
                unit="ms",
                thresholds={"warning": 500, "critical": 1000}
            ),
            DashboardPanel(
                title="ES Request Rate",
                metric_name="elasticsearch_requests_total",
                aggregation=AggregationType.RATE_PER_MINUTE,
                unit="req/min"
            ),
            DashboardPanel(
                title="ES Error Rate",
                metric_name="elasticsearch_requests_failed",
                aggregation=AggregationType.RATE_PER_MINUTE,
                unit="%"
            ),
            DashboardPanel(
                title="ES Connection Status",
                metric_name="elasticsearch_connection_status",
                panel_type="singlestat",
                unit=""
            )
        ])

        # System Resources Row
        resources_row = DashboardRow(title="System Resources")
        resources_row.panels.extend([
            DashboardPanel(
                title="Memory Usage",
                metric_name="memory_usage_mb",
                aggregation=AggregationType.AVERAGE,
                unit="MB",
                thresholds={"warning": 1000, "critical": 2000}
            ),
            DashboardPanel(
                title="CPU Usage",
                metric_name="cpu_usage_percent",
                aggregation=AggregationType.AVERAGE,
                unit="%",
                thresholds={"warning": 70, "critical": 85}
            ),
            DashboardPanel(
                title="Concurrent Requests",
                metric_name="concurrent_requests",
                aggregation=AggregationType.MAX,
                unit="requests"
            ),
            DashboardPanel(
                title="Active Connections",
                metric_name="active_connections",
                aggregation=AggregationType.AVERAGE,
                unit="connections"
            )
        ])

        # Add rows to dashboard
        system_dashboard.rows.extend([api_row, search_row, elasticsearch_row, resources_row])
        self.dashboards["system_overview"] = system_dashboard

        # Alerts Dashboard
        alerts_dashboard = Dashboard(
            title="AI Service - Alerts & SLA",
            description="Alert status and SLA compliance monitoring",
            tags=["ai-service", "alerts", "sla"]
        )

        # Active Alerts Row
        active_alerts_row = DashboardRow(title="Active Alerts")
        active_alerts_row.panels.extend([
            DashboardPanel(
                title="Active Alerts Count",
                metric_name="active_alerts_total",
                panel_type="singlestat",
                unit="alerts",
                thresholds={"warning": 1, "critical": 5}
            ),
            DashboardPanel(
                title="Alerts by Severity",
                metric_name="alerts_by_severity",
                panel_type="pie",
                description="Distribution of active alerts by severity"
            ),
            DashboardPanel(
                title="Alert Timeline",
                metric_name="alerts_triggered_total",
                aggregation=AggregationType.RATE_PER_MINUTE,
                description="Alert triggering rate over time"
            )
        ])

        # SLA Compliance Row
        sla_row = DashboardRow(title="SLA Compliance")
        sla_row.panels.extend([
            DashboardPanel(
                title="Overall SLA Compliance",
                metric_name="sla_compliance_percentage",
                panel_type="singlestat",
                unit="%",
                thresholds={"critical": 95, "warning": 99}
            ),
            DashboardPanel(
                title="API SLA Compliance",
                metric_name="api_sla_compliance",
                unit="%",
                description="API performance SLA compliance"
            ),
            DashboardPanel(
                title="Search SLA Compliance",
                metric_name="search_sla_compliance",
                unit="%",
                description="Search performance SLA compliance"
            ),
            DashboardPanel(
                title="Uptime",
                metric_name="uptime_percentage",
                panel_type="singlestat",
                unit="%",
                thresholds={"critical": 99.0, "warning": 99.9}
            )
        ])

        alerts_dashboard.rows.extend([active_alerts_row, sla_row])
        self.dashboards["alerts_sla"] = alerts_dashboard

    async def get_dashboard_data(
        self,
        dashboard_name: str,
        time_window_seconds: float = 3600.0,
        format_type: DashboardFormat = DashboardFormat.JSON
    ) -> Dict[str, Any]:
        """Get complete dashboard data in specified format."""
        if dashboard_name not in self.dashboards:
            raise ValueError(f"Dashboard '{dashboard_name}' not found")

        dashboard = self.dashboards[dashboard_name]
        current_time = time.time()

        dashboard_data = {
            "dashboard_info": {
                "title": dashboard.title,
                "description": dashboard.description,
                "timestamp": current_time,
                "time_window_seconds": time_window_seconds,
                "refresh_interval": dashboard.refresh_interval,
                "tags": dashboard.tags
            },
            "rows": []
        }

        # Process each row
        for row in dashboard.rows:
            row_data = {
                "title": row.title,
                "collapsed": row.collapsed,
                "panels": []
            }

            # Process each panel
            for panel in row.panels:
                panel_data = await self._get_panel_data(panel, time_window_seconds)
                row_data["panels"].append(panel_data)

            dashboard_data["rows"].append(row_data)

        # Add global metrics
        dashboard_data["global_metrics"] = await self._get_global_metrics()

        # Format based on requested type
        if format_type == DashboardFormat.GRAFANA:
            return self._convert_to_grafana_format(dashboard_data, dashboard)
        elif format_type == DashboardFormat.PROMETHEUS:
            return self._convert_to_prometheus_format(dashboard_data)
        else:
            return dashboard_data

    async def _get_panel_data(self, panel: DashboardPanel, time_window_seconds: float) -> Dict[str, Any]:
        """Get data for individual panel."""
        panel_data = {
            "title": panel.title,
            "type": panel.panel_type,
            "unit": panel.unit,
            "description": panel.description,
            "thresholds": panel.thresholds,
            "data": {}
        }

        try:
            # Get metric statistics
            stats = self.metrics_collector.get_metric_stats(
                panel.metric_name,
                [panel.aggregation, AggregationType.COUNT, AggregationType.MIN, AggregationType.MAX],
                time_window_seconds,
                panel.tags_filter
            )

            panel_data["data"] = {
                "current_value": stats.get(panel.aggregation.value, 0),
                "data_points": stats.get("count", 0),
                "min_value": stats.get("min", 0),
                "max_value": stats.get("max", 0),
                "timestamp": time.time()
            }

            # Add threshold status
            current_value = stats.get(panel.aggregation.value, 0)
            panel_data["status"] = self._get_threshold_status(current_value, panel.thresholds)

            # Get time series data for graphs
            if panel.panel_type == "graph":
                panel_data["time_series"] = await self._get_time_series_data(
                    panel.metric_name,
                    panel.aggregation,
                    time_window_seconds,
                    panel.tags_filter
                )

        except Exception as e:
            self.logger.error(f"Error getting panel data for {panel.title}: {e}", error=e)
            panel_data["error"] = str(e)

        return panel_data

    def _get_threshold_status(self, value: float, thresholds: Dict[str, float]) -> str:
        """Get threshold status for value."""
        if not thresholds:
            return "ok"

        if "critical" in thresholds and value >= thresholds["critical"]:
            return "critical"
        elif "warning" in thresholds and value >= thresholds["warning"]:
            return "warning"
        else:
            return "ok"

    async def _get_time_series_data(
        self,
        metric_name: str,
        aggregation: AggregationType,
        time_window_seconds: float,
        tags_filter: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """Get time series data for metric."""
        # Get metric buffer data points
        buffer = self.metrics_collector._get_metric_buffer(metric_name)
        points = buffer.get_points(
            start_time=time.time() - time_window_seconds,
            tags_filter=tags_filter
        )

        # Group points into time buckets for time series
        bucket_duration = time_window_seconds / 60  # 60 data points
        time_series = []

        if points:
            start_time = points[0].timestamp
            current_bucket_start = start_time

            while current_bucket_start < time.time():
                bucket_end = current_bucket_start + bucket_duration
                bucket_points = [
                    p for p in points
                    if current_bucket_start <= p.timestamp < bucket_end
                ]

                if bucket_points:
                    values = [p.value for p in bucket_points]

                    if aggregation == AggregationType.AVERAGE:
                        bucket_value = sum(values) / len(values)
                    elif aggregation == AggregationType.MAX:
                        bucket_value = max(values)
                    elif aggregation == AggregationType.MIN:
                        bucket_value = min(values)
                    elif aggregation == AggregationType.SUM:
                        bucket_value = sum(values)
                    else:
                        bucket_value = sum(values) / len(values)  # Default to average

                    time_series.append({
                        "timestamp": current_bucket_start,
                        "value": bucket_value
                    })

                current_bucket_start = bucket_end

        return time_series

    async def _get_global_metrics(self) -> Dict[str, Any]:
        """Get global system metrics."""
        # Get alert summary
        alert_summary = self.alerting_system.get_active_alerts_summary()

        # Get SLA compliance
        sla_report = self.alerting_system.get_sla_compliance_report(24.0)

        # Get performance metrics
        performance_metrics = self.metrics_collector.get_performance_metrics()

        # Get error rate metrics
        error_metrics = self.metrics_collector.get_error_rate_metrics()

        return {
            "alerts": alert_summary,
            "sla_compliance": sla_report,
            "performance": performance_metrics,
            "error_rates": error_metrics,
            "system_health": await self._get_system_health_score()
        }

    async def _get_system_health_score(self) -> Dict[str, Any]:
        """Calculate overall system health score."""
        health_factors = []

        # API health (30% weight)
        api_stats = self.metrics_collector.get_metric_stats(
            "api_request_duration", [AggregationType.P95], 300
        )
        api_latency = api_stats.get("p95", 0)
        api_health = max(0, 100 - (api_latency / 200 * 100))  # 200ms = 0% health
        health_factors.append(("api_performance", api_health, 0.3))

        # Search health (25% weight)
        search_stats = self.metrics_collector.get_metric_stats(
            "search_operation_duration", [AggregationType.P95], 300
        )
        search_latency = search_stats.get("p95", 0)
        search_health = max(0, 100 - (search_latency / 1000 * 100))  # 1000ms = 0% health
        health_factors.append(("search_performance", search_health, 0.25))

        # Error rate health (25% weight)
        error_metrics = self.metrics_collector.get_error_rate_metrics()
        api_error_rate = error_metrics.get("api_requests_error_rate_percent", 0)
        error_health = max(0, 100 - (api_error_rate * 10))  # 10% error rate = 0% health
        health_factors.append(("error_rate", error_health, 0.25))

        # Alert health (20% weight)
        active_alerts = len(self.alerting_system.active_alerts)
        alert_health = max(0, 100 - (active_alerts * 20))  # 5 alerts = 0% health
        health_factors.append(("alerts", alert_health, 0.2))

        # Calculate weighted average
        total_weight = sum(weight for _, _, weight in health_factors)
        weighted_score = sum(score * weight for _, score, weight in health_factors)
        overall_health = weighted_score / total_weight if total_weight > 0 else 0

        return {
            "overall_score": round(overall_health, 1),
            "status": self._get_health_status(overall_health),
            "factors": [
                {"name": name, "score": round(score, 1), "weight": weight}
                for name, score, weight in health_factors
            ]
        }

    def _get_health_status(self, score: float) -> str:
        """Get health status based on score."""
        if score >= 90:
            return "excellent"
        elif score >= 75:
            return "good"
        elif score >= 50:
            return "fair"
        elif score >= 25:
            return "poor"
        else:
            return "critical"

    def _convert_to_grafana_format(self, dashboard_data: Dict[str, Any], dashboard: Dashboard) -> Dict[str, Any]:
        """Convert dashboard data to Grafana format."""
        grafana_dashboard = {
            "id": None,
            "title": dashboard.title,
            "description": dashboard.description,
            "tags": dashboard.tags,
            "timezone": "browser",
            "refresh": dashboard.refresh_interval,
            "time": {
                "from": "now-" + dashboard.time_range,
                "to": "now"
            },
            "panels": []
        }

        panel_id = 1
        grid_pos_y = 0

        for row_data in dashboard_data["rows"]:
            # Add row panel
            grafana_dashboard["panels"].append({
                "id": panel_id,
                "title": row_data["title"],
                "type": "row",
                "collapsed": row_data.get("collapsed", False),
                "gridPos": {"h": 1, "w": 24, "x": 0, "y": grid_pos_y}
            })
            panel_id += 1
            grid_pos_y += 1

            # Add panels in row
            grid_pos_x = 0
            for panel_data in row_data["panels"]:
                grafana_panel = {
                    "id": panel_id,
                    "title": panel_data["title"],
                    "type": self._map_panel_type_to_grafana(panel_data["type"]),
                    "gridPos": {"h": 8, "w": 6, "x": grid_pos_x, "y": grid_pos_y},
                    "targets": [{
                        "expr": f"ai_service_{panel_data['title'].lower().replace(' ', '_')}",
                        "refId": "A"
                    }],
                    "options": {
                        "unit": panel_data.get("unit", ""),
                        "thresholds": self._convert_thresholds_to_grafana(panel_data.get("thresholds", {}))
                    }
                }

                if panel_data.get("description"):
                    grafana_panel["description"] = panel_data["description"]

                grafana_dashboard["panels"].append(grafana_panel)
                panel_id += 1
                grid_pos_x += 6

                if grid_pos_x >= 24:
                    grid_pos_x = 0
                    grid_pos_y += 8

            if grid_pos_x > 0:
                grid_pos_y += 8

        return grafana_dashboard

    def _map_panel_type_to_grafana(self, panel_type: str) -> str:
        """Map internal panel types to Grafana panel types."""
        mapping = {
            "graph": "timeseries",
            "singlestat": "stat",
            "table": "table",
            "pie": "piechart",
            "heatmap": "heatmap"
        }
        return mapping.get(panel_type, "timeseries")

    def _convert_thresholds_to_grafana(self, thresholds: Dict[str, float]) -> Dict[str, Any]:
        """Convert threshold configuration to Grafana format."""
        steps = [{"color": "green", "value": None}]

        if "warning" in thresholds:
            steps.append({"color": "yellow", "value": thresholds["warning"]})

        if "critical" in thresholds:
            steps.append({"color": "red", "value": thresholds["critical"]})

        return {"steps": steps}

    def _convert_to_prometheus_format(self, dashboard_data: Dict[str, Any]) -> str:
        """Convert dashboard data to Prometheus metrics format."""
        return self.metrics_collector.export_prometheus_metrics()

    def export_dashboard_config(self, dashboard_name: str) -> Dict[str, Any]:
        """Export dashboard configuration for external tools."""
        if dashboard_name not in self.dashboards:
            raise ValueError(f"Dashboard '{dashboard_name}' not found")

        dashboard = self.dashboards[dashboard_name]

        config = {
            "dashboard": {
                "title": dashboard.title,
                "description": dashboard.description,
                "refresh_interval": dashboard.refresh_interval,
                "time_range": dashboard.time_range,
                "tags": dashboard.tags
            },
            "rows": []
        }

        for row in dashboard.rows:
            row_config = {
                "title": row.title,
                "collapsed": row.collapsed,
                "panels": []
            }

            for panel in row.panels:
                panel_config = {
                    "title": panel.title,
                    "metric_name": panel.metric_name,
                    "panel_type": panel.panel_type,
                    "aggregation": panel.aggregation.value,
                    "time_window_seconds": panel.time_window_seconds,
                    "tags_filter": panel.tags_filter,
                    "thresholds": panel.thresholds,
                    "unit": panel.unit,
                    "description": panel.description
                }
                row_config["panels"].append(panel_config)

            config["rows"].append(row_config)

        return config

    def get_available_dashboards(self) -> List[Dict[str, Any]]:
        """Get list of available dashboards."""
        return [
            {
                "name": name,
                "title": dashboard.title,
                "description": dashboard.description,
                "tags": dashboard.tags
            }
            for name, dashboard in self.dashboards.items()
        ]

    def create_custom_dashboard(self, dashboard_config: Dict[str, Any]) -> str:
        """Create custom dashboard from configuration."""
        dashboard_name = dashboard_config.get("name", f"custom_{int(time.time())}")

        dashboard = Dashboard(
            title=dashboard_config.get("title", "Custom Dashboard"),
            description=dashboard_config.get("description", ""),
            refresh_interval=dashboard_config.get("refresh_interval", "30s"),
            time_range=dashboard_config.get("time_range", "1h"),
            tags=dashboard_config.get("tags", [])
        )

        # Add rows and panels from config
        for row_config in dashboard_config.get("rows", []):
            row = DashboardRow(
                title=row_config.get("title", ""),
                collapsed=row_config.get("collapsed", False)
            )

            for panel_config in row_config.get("panels", []):
                panel = DashboardPanel(
                    title=panel_config.get("title", ""),
                    metric_name=panel_config.get("metric_name", ""),
                    panel_type=panel_config.get("panel_type", "graph"),
                    aggregation=AggregationType(panel_config.get("aggregation", "avg")),
                    time_window_seconds=panel_config.get("time_window_seconds", 3600.0),
                    tags_filter=panel_config.get("tags_filter", {}),
                    thresholds=panel_config.get("thresholds", {}),
                    unit=panel_config.get("unit", ""),
                    description=panel_config.get("description", "")
                )
                row.panels.append(panel)

            dashboard.rows.append(row)

        self.dashboards[dashboard_name] = dashboard
        self.logger.info(f"Custom dashboard created: {dashboard_name}")

        return dashboard_name


# Global dashboard exporter
_global_dashboard_exporter: Optional[DashboardDataExporter] = None


def get_dashboard_exporter() -> DashboardDataExporter:
    """Get global dashboard data exporter."""
    global _global_dashboard_exporter
    if _global_dashboard_exporter is None:
        _global_dashboard_exporter = DashboardDataExporter()
    return _global_dashboard_exporter