"""
FastAPI endpoints for monitoring and metrics
"""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .metrics_service import MetricsService, Alert


class HealthStatus(BaseModel):
    """Health status response model"""
    status: str
    uptime: float
    metrics_count: int
    active_alerts: int
    details: Dict[str, Any]


class MetricResponse(BaseModel):
    """Metric response model"""
    name: str
    type: str
    value: Any
    labels: Optional[Dict[str, str]] = None
    last_updated: float


class AlertResponse(BaseModel):
    """Alert response model"""
    metric_name: str
    severity: str
    value: float
    threshold: float
    message: str
    triggered_at: float


class PerformanceReport(BaseModel):
    """Performance report response model"""
    counters: Dict[str, Any]
    gauges: Dict[str, Any]
    histograms: Dict[str, Any]
    timers: Dict[str, Any]
    summary: Dict[str, Any]


def create_monitoring_router(metrics_service: MetricsService) -> APIRouter:
    """
    Create FastAPI router for monitoring endpoints

    Args:
        metrics_service: MetricsService instance for collecting metrics

    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/monitoring", tags=["monitoring"])

    @router.get("/health", response_model=HealthStatus)
    async def get_health():
        """Get system health status"""
        try:
            health = metrics_service.check_system_health()
            return HealthStatus(
                status=health["status"],
                uptime=health["uptime"],
                metrics_count=len(metrics_service.metrics),
                active_alerts=len(metrics_service.get_active_alerts()),
                details=health
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Health check failed: {str(e)}")

    @router.get("/metrics", response_model=List[MetricResponse])
    async def get_metrics(
        metric_type: Optional[str] = Query(None, description="Filter by metric type"),
        name_pattern: Optional[str] = Query(None, description="Filter by name pattern"),
    ):
        """Get all metrics with optional filtering"""
        try:
            exported_metrics = metrics_service.export_metrics()

            # Apply filters
            if metric_type:
                exported_metrics = [m for m in exported_metrics if m["type"] == metric_type]

            if name_pattern:
                exported_metrics = [m for m in exported_metrics if name_pattern in m["name"]]

            return [
                MetricResponse(
                    name=m["name"],
                    type=m["type"],
                    value=m["value"],
                    labels=m.get("labels"),
                    last_updated=m["last_updated"]
                )
                for m in exported_metrics
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get metrics: {str(e)}")

    @router.get("/metrics/{metric_name}")
    async def get_metric(metric_name: str):
        """Get specific metric by name"""
        try:
            if metric_name not in metrics_service.metrics:
                raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")

            metric = metrics_service.metrics[metric_name]
            return MetricResponse(
                name=metric_name,
                type=metric["type"].value,
                value=metric.get("value", metric),
                labels=metric.get("labels"),
                last_updated=metric["last_updated"]
            )
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get metric: {str(e)}")

    @router.get("/alerts", response_model=List[AlertResponse])
    async def get_alerts():
        """Get active alerts"""
        try:
            alerts = metrics_service.get_active_alerts()
            return [
                AlertResponse(
                    metric_name=alert.metric_name,
                    severity=alert.severity.value,
                    value=alert.value,
                    threshold=alert.threshold,
                    message=alert.message,
                    triggered_at=alert.triggered_at
                )
                for alert in alerts
            ]
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get alerts: {str(e)}")

    @router.get("/performance", response_model=PerformanceReport)
    async def get_performance_report():
        """Get comprehensive performance report"""
        try:
            report = metrics_service.get_performance_report()
            return PerformanceReport(**report)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate performance report: {str(e)}")

    @router.post("/metrics/reset")
    async def reset_metrics():
        """Reset all metrics (use with caution)"""
        try:
            metrics_service.reset_all_metrics()
            return {"message": "All metrics reset successfully"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to reset metrics: {str(e)}")

    @router.post("/metrics/{metric_name}/reset")
    async def reset_metric(metric_name: str):
        """Reset specific metric"""
        try:
            if metric_name not in metrics_service.metrics:
                raise HTTPException(status_code=404, detail=f"Metric '{metric_name}' not found")

            metric = metrics_service.metrics[metric_name]
            if metric["type"].value == "counter":
                metrics_service.reset_counter(metric_name)
            else:
                # Remove the metric entirely for non-counters
                del metrics_service.metrics[metric_name]

            return {"message": f"Metric '{metric_name}' reset successfully"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to reset metric: {str(e)}")

    @router.get("/metrics/search")
    async def search_metrics(
        query: str = Query(..., description="Search query for metric names"),
        limit: int = Query(50, description="Maximum number of results")
    ):
        """Search metrics by name"""
        try:
            matching_metrics = []
            query_lower = query.lower()

            for name, metric in metrics_service.metrics.items():
                if query_lower in name.lower():
                    matching_metrics.append({
                        "name": name,
                        "type": metric["type"].value,
                        "value": metric.get("value", str(metric)),
                        "last_updated": metric["last_updated"]
                    })

                if len(matching_metrics) >= limit:
                    break

            return {
                "query": query,
                "results": matching_metrics,
                "total": len(matching_metrics)
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    @router.get("/statistics")
    async def get_statistics():
        """Get monitoring system statistics"""
        try:
            total_metrics = len(metrics_service.metrics)
            active_alerts = len(metrics_service.get_active_alerts())

            # Count metrics by type
            type_counts = {}
            for metric in metrics_service.metrics.values():
                metric_type = metric["type"].value
                type_counts[metric_type] = type_counts.get(metric_type, 0) + 1

            # Get registered metric definitions
            registered_metrics = len(metrics_service.metric_definitions)

            return {
                "total_metrics": total_metrics,
                "active_alerts": active_alerts,
                "registered_definitions": registered_metrics,
                "metrics_by_type": type_counts,
                "system_health": metrics_service.check_system_health()["status"]
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get statistics: {str(e)}")

    @router.post("/cleanup")
    async def cleanup_old_metrics(
        max_age_seconds: int = Query(3600, description="Maximum age for metrics in seconds")
    ):
        """Clean up old metrics"""
        try:
            initial_count = len(metrics_service.metrics)
            metrics_service.cleanup_old_metrics(max_age=max_age_seconds)
            final_count = len(metrics_service.metrics)

            cleaned_count = initial_count - final_count
            return {
                "message": "Cleanup completed",
                "initial_count": initial_count,
                "final_count": final_count,
                "cleaned_count": cleaned_count
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Cleanup failed: {str(e)}")

    return router


def create_prometheus_endpoint(metrics_service: MetricsService) -> APIRouter:
    """
    Create Prometheus-compatible metrics endpoint

    Args:
        metrics_service: MetricsService instance

    Returns:
        APIRouter with Prometheus endpoint
    """
    router = APIRouter()

    @router.get("/metrics", response_class=PlainTextResponse)
    async def prometheus_metrics():
        """Export metrics in Prometheus format"""
        try:
            lines = []

            for name, metric in metrics_service.metrics.items():
                # Sanitize metric name for Prometheus
                prometheus_name = name.replace(".", "_").replace("-", "_")

                metric_type = metric["type"].value

                if metric_type == "counter":
                    lines.append(f"# TYPE {prometheus_name} counter")
                    lines.append(f"{prometheus_name} {metric['value']}")

                elif metric_type == "gauge":
                    lines.append(f"# TYPE {prometheus_name} gauge")
                    lines.append(f"{prometheus_name} {metric['value']}")

                elif metric_type == "histogram":
                    lines.append(f"# TYPE {prometheus_name} histogram")
                    lines.append(f"{prometheus_name}_count {metric['count']}")
                    lines.append(f"{prometheus_name}_sum {metric['sum']}")

                    # Add percentiles as separate metrics
                    for percentile, value in metric.get("percentiles", {}).items():
                        lines.append(f"{prometheus_name}_{percentile} {value}")

                elif metric_type == "timer":
                    lines.append(f"# TYPE {prometheus_name}_seconds histogram")
                    lines.append(f"{prometheus_name}_seconds_count {metric['count']}")
                    lines.append(f"{prometheus_name}_seconds_sum {metric['sum']}")

                    # Add percentiles
                    for percentile, value in metric.get("percentiles", {}).items():
                        lines.append(f"{prometheus_name}_seconds_{percentile} {value}")

            return "\n".join(lines)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to export Prometheus metrics: {str(e)}")

    return router


# For Prometheus compatibility
from fastapi.responses import PlainTextResponse