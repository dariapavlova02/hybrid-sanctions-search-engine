"""
Metrics utilities for safe metrics recording.
Provides fallback mechanisms when prometheus_client is not available.
"""

import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)


def safe_get_metrics_exporter():
    """
    Safely get metrics exporter with fallback.

    Returns:
        Metrics exporter instance or None if not available
    """
    try:
        from ..monitoring.prometheus_exporter import get_exporter
        return get_exporter()
    except Exception as e:
        logger.debug(f"Metrics exporter not available: {e}")
        return None


def safe_record_metric(metrics_func, *args, **kwargs):
    """
    Safely record a metric with error handling.

    Args:
        metrics_func: Function to call for recording metric
        *args: Positional arguments for metrics function
        **kwargs: Keyword arguments for metrics function

    Returns:
        True if metric was recorded, False otherwise
    """
    try:
        if callable(metrics_func):
            metrics_func(*args, **kwargs)
            return True
    except Exception as e:
        logger.debug(f"Failed to record metric: {e}")

    return False


class SafeMetricsWrapper:
    """
    A safe wrapper around metrics exporter that gracefully handles failures.
    """

    def __init__(self):
        self._exporter = safe_get_metrics_exporter()
        self._available = self._exporter is not None

    @property
    def available(self) -> bool:
        """Check if metrics are available."""
        return self._available

    def record_pipeline_stage_duration(self, stage: str, duration_ms: float) -> bool:
        """Safely record pipeline stage duration."""
        if not self._available:
            return False

        return safe_record_metric(
            self._exporter.record_pipeline_stage_duration,
            stage,
            duration_ms
        )

    def record_fast_path_cache_lookup(self, hit: bool) -> bool:
        """Safely record fast path cache lookup."""
        if not self._available:
            return False

        return safe_record_metric(
            self._exporter.record_fast_path_cache_lookup,
            hit
        )

    def record_sanctions_decision(self, risk_level: str, fast_path_used: bool) -> bool:
        """Safely record sanctions decision."""
        if not self._available:
            return False

        return safe_record_metric(
            self._exporter.record_sanctions_decision,
            risk_level,
            fast_path_used
        )

    def update_fast_path_cache_hit_rate(self, rate: float) -> bool:
        """Safely update fast path cache hit rate."""
        if not self._available:
            return False

        return safe_record_metric(
            self._exporter.update_fast_path_cache_hit_rate,
            rate
        )


# Global safe metrics instance
_safe_metrics: Optional[SafeMetricsWrapper] = None


def get_safe_metrics() -> SafeMetricsWrapper:
    """
    Get global safe metrics wrapper instance.

    Returns:
        SafeMetricsWrapper instance
    """
    global _safe_metrics
    if _safe_metrics is None:
        _safe_metrics = SafeMetricsWrapper()
    return _safe_metrics