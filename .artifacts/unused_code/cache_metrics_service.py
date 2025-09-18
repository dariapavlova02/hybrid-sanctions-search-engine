"""
Cache metrics service for exposing LRU cache metrics.
"""

from typing import Dict, Any
from ..utils.cache_utils import cache_metrics
from .metrics_service import MetricsService, MetricType


class CacheMetricsService:
    """Service for exposing cache metrics through the main metrics service."""
    
    def __init__(self, metrics_service: MetricsService):
        """
        Initialize cache metrics service.
        
        Args:
            metrics_service: Main metrics service instance
        """
        self.metrics_service = metrics_service
        self._register_metrics()
    
    def _register_metrics(self):
        """Register cache metrics with the main metrics service."""
        # Register cache hit rate metrics
        self.metrics_service.register_gauge(
            'cache.morph_nominal.hit_rate',
            'Cache hit rate for morphological nominative analysis',
            self._get_morph_nominal_hit_rate
        )
        
        self.metrics_service.register_gauge(
            'cache.classify_personal_role.hit_rate',
            'Cache hit rate for personal role classification',
            self._get_classify_personal_role_hit_rate
        )
        
        # Register cache size metrics
        self.metrics_service.register_gauge(
            'cache.morph_nominal.size',
            'Current cache size for morphological nominative analysis',
            self._get_morph_nominal_size
        )
        
        self.metrics_service.register_gauge(
            'cache.classify_personal_role.size',
            'Current cache size for personal role classification',
            self._get_classify_personal_role_size
        )
        
        # Register overall cache metrics
        self.metrics_service.register_gauge(
            'cache.total.hit_rate',
            'Overall cache hit rate across all caches',
            self._get_total_hit_rate
        )
        
        self.metrics_service.register_gauge(
            'cache.total.size',
            'Total cache size across all caches',
            self._get_total_size
        )
    
    def _get_morph_nominal_hit_rate(self) -> float:
        """Get hit rate for morph_nominal cache."""
        return cache_metrics.get_hit_rate('morph_nominal')
    
    def _get_classify_personal_role_hit_rate(self) -> float:
        """Get hit rate for classify_personal_role cache."""
        return cache_metrics.get_hit_rate('classify_personal_role')
    
    def _get_morph_nominal_size(self) -> int:
        """Get current size for morph_nominal cache."""
        return cache_metrics.get_size('morph_nominal')
    
    def _get_classify_personal_role_size(self) -> int:
        """Get current size for classify_personal_role cache."""
        return cache_metrics.get_size('classify_personal_role')
    
    def _get_total_hit_rate(self) -> float:
        """Get overall hit rate across all caches."""
        all_metrics = cache_metrics.get_all_metrics()
        if not all_metrics:
            return 0.0
        
        total_hits = sum(metrics['hits'] for metrics in all_metrics.values())
        total_misses = sum(metrics['misses'] for metrics in all_metrics.values())
        total_requests = total_hits + total_misses
        
        return total_hits / total_requests if total_requests > 0 else 0.0
    
    def _get_total_size(self) -> int:
        """Get total size across all caches."""
        all_metrics = cache_metrics.get_all_metrics()
        return sum(metrics['size'] for metrics in all_metrics.values())
    
    def get_detailed_metrics(self) -> Dict[str, Any]:
        """Get detailed cache metrics for debugging and monitoring."""
        return cache_metrics.get_all_metrics()
    
    def reset_metrics(self, cache_name: str = None):
        """Reset cache metrics for a specific cache or all caches."""
        cache_metrics.reset(cache_name)
    
    def clear_caches(self):
        """Clear all LRU caches."""
        # This would need to be implemented by calling cache_clear() on each cached method
        # For now, we'll just reset the metrics
        cache_metrics.reset()
