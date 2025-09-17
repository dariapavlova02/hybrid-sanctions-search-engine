#!/usr/bin/env python3
"""
Prometheus metrics for caching in normalization pipeline.

This module provides Prometheus metrics for monitoring cache performance
and normalization pipeline latency.
"""

from typing import Dict, Any, Optional

try:
    from prometheus_client import Counter, Gauge, Histogram, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    # Mock classes for when prometheus_client is not available
    class Counter:
        def __init__(self, *args, **kwargs): pass
        def labels(self, **kwargs): return self
        def inc(self, value=1): pass
    class Gauge:
        def __init__(self, *args, **kwargs): pass
        def labels(self, **kwargs): return self
        def set(self, value): pass
    class Histogram:
        def __init__(self, *args, **kwargs): pass
        def labels(self, **kwargs): return self
        def observe(self, value): pass
    class CollectorRegistry:
        pass

from ..utils.logging_config import get_logger


class CacheMetrics:
    """
    Prometheus metrics for cache monitoring.
    
    Provides counters, gauges, and histograms for monitoring
    cache performance and normalization pipeline latency.
    """
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize cache metrics.
        
        Args:
            registry: Optional Prometheus registry
        """
        self.logger = get_logger(__name__)
        self.registry = registry
        self.prometheus_available = PROMETHEUS_AVAILABLE
        
        if not self.prometheus_available:
            self.logger.warning("prometheus_client not available, using mock metrics")
        
        # Cache hit/miss counters
        self.tokenizer_cache_hits = Counter(
            'normalization_tokenizer_cache_hits_total',
            'Total number of tokenizer cache hits',
            ['language'],
            registry=registry
        )
        
        self.tokenizer_cache_misses = Counter(
            'normalization_tokenizer_cache_misses_total',
            'Total number of tokenizer cache misses',
            ['language'],
            registry=registry
        )
        
        self.morphology_cache_hits = Counter(
            'normalization_morph_cache_hits_total',
            'Total number of morphology cache hits',
            ['language'],
            registry=registry
        )
        
        self.morphology_cache_misses = Counter(
            'normalization_morph_cache_misses_total',
            'Total number of morphology cache misses',
            ['language'],
            registry=registry
        )
        
        # Cache size gauges
        self.tokenizer_cache_size = Gauge(
            'normalization_cache_size',
            'Current cache size',
            ['layer', 'language'],
            registry=registry
        )
        
        self.morphology_cache_size = Gauge(
            'normalization_cache_size',
            'Current cache size',
            ['layer', 'language'],
            registry=registry
        )
        
        # Cache hit rate gauges
        self.tokenizer_cache_hit_rate = Gauge(
            'normalization_cache_hit_rate',
            'Cache hit rate percentage',
            ['layer', 'language'],
            registry=registry
        )
        
        self.morphology_cache_hit_rate = Gauge(
            'normalization_cache_hit_rate',
            'Cache hit rate percentage',
            ['layer', 'language'],
            registry=registry
        )
        
        # Latency histograms
        self.layer_latency = Histogram(
            'normalization_layer_latency_seconds',
            'Normalization layer processing latency',
            ['layer', 'language'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=registry
        )
        
        # Overall normalization latency
        self.normalization_latency = Histogram(
            'normalization_total_latency_seconds',
            'Total normalization processing latency',
            ['language'],
            buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
            registry=registry
        )
        
        # Cache eviction counters
        self.cache_evictions = Counter(
            'normalization_cache_evictions_total',
            'Total number of cache evictions',
            ['layer', 'reason'],
            registry=registry
        )
        
        # Cache expiration counters
        self.cache_expirations = Counter(
            'normalization_cache_expirations_total',
            'Total number of cache expirations',
            ['layer'],
            registry=registry
        )
    
    def record_tokenizer_cache_hit(self, language: str) -> None:
        """Record tokenizer cache hit."""
        self.tokenizer_cache_hits.labels(language=language).inc()
    
    def record_tokenizer_cache_miss(self, language: str) -> None:
        """Record tokenizer cache miss."""
        self.tokenizer_cache_misses.labels(language=language).inc()
    
    def record_morphology_cache_hit(self, language: str) -> None:
        """Record morphology cache hit."""
        self.morphology_cache_hits.labels(language=language).inc()
    
    def record_morphology_cache_miss(self, language: str) -> None:
        """Record morphology cache miss."""
        self.morphology_cache_misses.labels(language=language).inc()
    
    def update_tokenizer_cache_size(self, language: str, size: int) -> None:
        """Update tokenizer cache size."""
        self.tokenizer_cache_size.labels(
            layer='tokenizer',
            language=language
        ).set(size)
    
    def update_morphology_cache_size(self, language: str, size: int) -> None:
        """Update morphology cache size."""
        self.morphology_cache_size.labels(
            layer='morph',
            language=language
        ).set(size)
    
    def update_tokenizer_cache_hit_rate(self, language: str, hit_rate: float) -> None:
        """Update tokenizer cache hit rate."""
        self.tokenizer_cache_hit_rate.labels(
            layer='tokenizer',
            language=language
        ).set(hit_rate)
    
    def update_morphology_cache_hit_rate(self, language: str, hit_rate: float) -> None:
        """Update morphology cache hit rate."""
        self.morphology_cache_hit_rate.labels(
            layer='morph',
            language=language
        ).set(hit_rate)
    
    def record_layer_latency(self, layer: str, language: str, latency: float) -> None:
        """Record layer processing latency."""
        self.layer_latency.labels(
            layer=layer,
            language=language
        ).observe(latency)
    
    def record_normalization_latency(self, language: str, latency: float) -> None:
        """Record total normalization latency."""
        self.normalization_latency.labels(language=language).observe(latency)
    
    def record_cache_eviction(self, layer: str, reason: str) -> None:
        """Record cache eviction."""
        self.cache_evictions.labels(layer=layer, reason=reason).inc()
    
    def record_cache_expiration(self, layer: str) -> None:
        """Record cache expiration."""
        self.cache_expirations.labels(layer=layer).inc()
    
    def update_from_cache_stats(
        self,
        layer: str,
        language: str,
        stats: Dict[str, Any]
    ) -> None:
        """
        Update metrics from cache statistics.
        
        Args:
            layer: Cache layer name (tokenizer, morph)
            language: Language code
            stats: Cache statistics dictionary
        """
        # Update cache size
        if layer == 'tokenizer':
            self.update_tokenizer_cache_size(language, stats.get('size', 0))
        elif layer == 'morph':
            self.update_morphology_cache_size(language, stats.get('size', 0))
        
        # Update hit rate
        hit_rate = stats.get('hit_rate', 0.0)
        if layer == 'tokenizer':
            self.update_tokenizer_cache_hit_rate(language, hit_rate)
        elif layer == 'morph':
            self.update_morphology_cache_hit_rate(language, hit_rate)
        
        # Record evictions and expirations
        evictions = stats.get('evictions', 0)
        if evictions > 0:
            self.record_cache_eviction(layer, 'lru')
        
        expirations = stats.get('expirations', 0)
        if expirations > 0:
            self.record_cache_expiration(layer)
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get metrics summary for monitoring.
        
        Returns:
            Dictionary with metrics summary
        """
        # This would typically query the Prometheus registry
        # For now, return a placeholder structure
        return {
            'tokenizer_cache': {
                'hits': 'N/A',  # Would be actual values from registry
                'misses': 'N/A',
                'hit_rate': 'N/A',
                'size': 'N/A'
            },
            'morphology_cache': {
                'hits': 'N/A',
                'misses': 'N/A',
                'hit_rate': 'N/A',
                'size': 'N/A'
            },
            'latency': {
                'p50': 'N/A',
                'p95': 'N/A',
                'p99': 'N/A'
            }
        }


class MetricsCollector:
    """
    Metrics collector for normalization pipeline.
    
    Collects and aggregates metrics from various components
    in the normalization pipeline.
    """
    
    def __init__(self, metrics: CacheMetrics):
        """
        Initialize metrics collector.
        
        Args:
            metrics: Cache metrics instance
        """
        self.metrics = metrics
        self.logger = get_logger(__name__)
    
    def collect_tokenizer_metrics(
        self,
        language: str,
        stats: Dict[str, Any]
    ) -> None:
        """
        Collect tokenizer metrics.
        
        Args:
            language: Language code
            stats: Tokenizer statistics
        """
        # Record hit/miss events
        hits = stats.get('cache_hits', 0)
        misses = stats.get('cache_misses', 0)
        
        for _ in range(hits):
            self.metrics.record_tokenizer_cache_hit(language)
        
        for _ in range(misses):
            self.metrics.record_tokenizer_cache_miss(language)
        
        # Update cache metrics
        self.metrics.update_from_cache_stats('tokenizer', language, stats)
        
        # Record latency
        avg_latency = stats.get('avg_processing_time', 0.0)
        if avg_latency > 0:
            self.metrics.record_layer_latency('tokenizer', language, avg_latency)
    
    def collect_morphology_metrics(
        self,
        language: str,
        stats: Dict[str, Any]
    ) -> None:
        """
        Collect morphology metrics.
        
        Args:
            language: Language code
            stats: Morphology statistics
        """
        # Record hit/miss events
        hits = stats.get('cache_hits', 0)
        misses = stats.get('cache_misses', 0)
        
        for _ in range(hits):
            self.metrics.record_morphology_cache_hit(language)
        
        for _ in range(misses):
            self.metrics.record_morphology_cache_miss(language)
        
        # Update cache metrics
        self.metrics.update_from_cache_stats('morph', language, stats)
        
        # Record latency
        avg_latency = stats.get('avg_processing_time', 0.0)
        if avg_latency > 0:
            self.metrics.record_layer_latency('morphology', language, avg_latency)
    
    def collect_normalization_metrics(
        self,
        language: str,
        total_latency: float
    ) -> None:
        """
        Collect overall normalization metrics.
        
        Args:
            language: Language code
            total_latency: Total processing latency
        """
        self.metrics.record_normalization_latency(language, total_latency)
    
    def get_collected_metrics(self) -> Dict[str, Any]:
        """
        Get collected metrics summary.
        
        Returns:
            Dictionary with collected metrics
        """
        return self.metrics.get_metrics_summary()
