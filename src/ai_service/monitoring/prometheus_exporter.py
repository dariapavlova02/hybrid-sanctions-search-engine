#!/usr/bin/env python3
"""
Prometheus metrics exporter for search integration.

Exports metrics for:
- hybrid_search_requests_total{mode="ac|knn|hybrid"}
- hybrid_search_latency_ms_bucket (histogram)
- ac_hits_total{type="exact|phrase|ngram"}, ac_weak_hits_total
- knn_hits_total, fusion_consensus_total
- es_errors_total{type="timeout|conn|mapping"}
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from prometheus_client import (
        Counter, Histogram, Gauge, CollectorRegistry,
        generate_latest, CONTENT_TYPE_LATEST
    )
    from prometheus_client.core import HistogramMetricFamily, CounterMetricFamily, GaugeMetricFamily
    PROMETHEUS_AVAILABLE = True
except ImportError:
    # Fallback mode when prometheus_client is not available
    PROMETHEUS_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; charset=utf-8"

    # Fallback implementations
    class FallbackMetric:
        def __init__(self, name, description, labels=None, **kwargs):
            self.name = name
            self.description = description
            self._labels = labels or []
            self.value = 0
            self.label_values = {}

        def labels(self, **kwargs):
            return self

        def inc(self, amount=1):
            self.value += amount

        def observe(self, value):
            self.value = value

        def set(self, value):
            self.value = value

    class Counter(FallbackMetric):
        pass

    class Histogram(FallbackMetric):
        def __init__(self, name, description, labels=None, buckets=None, **kwargs):
            super().__init__(name, description, labels, **kwargs)
            self.buckets = buckets or []

    class Gauge(FallbackMetric):
        pass

    class CollectorRegistry:
        def __init__(self):
            self.metrics = []


class SearchMode(str, Enum):
    """Search mode enumeration."""
    AC = "ac"
    KNN = "knn"
    HYBRID = "hybrid"


class ACHitType(str, Enum):
    """AC hit type enumeration."""
    EXACT = "exact"
    PHRASE = "phrase"
    NGRAM = "ngram"


class ESErrorType(str, Enum):
    """Elasticsearch error type enumeration."""
    TIMEOUT = "timeout"
    CONNECTION = "conn"
    MAPPING = "mapping"
    QUERY = "query"
    INDEX = "index"


@dataclass
class SearchMetrics:
    """Search metrics data structure."""
    mode: SearchMode
    latency_ms: float
    ac_hits: Dict[ACHitType, int]
    ac_weak_hits: int
    knn_hits: int
    fusion_consensus: int
    es_errors: Dict[ESErrorType, int]
    success: bool


class SearchPrometheusExporter:
    """Prometheus metrics exporter for search integration."""
    
    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        Initialize Prometheus exporter.

        Args:
            registry: Prometheus registry, uses default if None
        """
        self.registry = registry or CollectorRegistry()
        self.prometheus_available = PROMETHEUS_AVAILABLE
        self._fallback_metrics = {}  # For fallback mode
        self._setup_metrics()
    
    def _setup_metrics(self) -> None:
        """Setup Prometheus metrics."""
        
        # Hybrid search requests counter
        self.hybrid_search_requests_total = Counter(
            'hybrid_search_requests_total',
            'Total number of hybrid search requests',
            ['mode'],
            registry=self.registry
        )
        
        # Hybrid search latency histogram
        self.hybrid_search_latency_ms = Histogram(
            'hybrid_search_latency_ms',
            'Hybrid search latency in milliseconds',
            ['mode'],
            buckets=[10, 25, 50, 100, 200, 500, 1000, 2000, 5000],
            registry=self.registry
        )
        
        # AC hits counter
        self.ac_hits_total = Counter(
            'ac_hits_total',
            'Total number of AC search hits',
            ['type'],
            registry=self.registry
        )
        
        # AC weak hits counter
        self.ac_weak_hits_total = Counter(
            'ac_weak_hits_total',
            'Total number of AC weak hits',
            registry=self.registry
        )
        
        # KNN hits counter
        self.knn_hits_total = Counter(
            'knn_hits_total',
            'Total number of KNN search hits',
            registry=self.registry
        )
        
        # Fusion consensus counter
        self.fusion_consensus_total = Counter(
            'fusion_consensus_total',
            'Total number of fusion consensus hits',
            registry=self.registry
        )
        
        # Elasticsearch errors counter
        self.es_errors_total = Counter(
            'es_errors_total',
            'Total number of Elasticsearch errors',
            ['type'],
            registry=self.registry
        )
        
        # Search success rate gauge
        self.search_success_rate = Gauge(
            'search_success_rate',
            'Search success rate (0-1)',
            registry=self.registry
        )
        
        # Active search connections gauge
        self.active_search_connections = Gauge(
            'active_search_connections',
            'Number of active search connections',
            registry=self.registry
        )
        
        # Search cache hit rate gauge
        self.search_cache_hit_rate = Gauge(
            'search_cache_hit_rate',
            'Search cache hit rate (0-1)',
            registry=self.registry
        )
    
    def record_search_request(
        self,
        mode: SearchMode,
        latency_ms: float,
        success: bool = True
    ) -> None:
        """
        Record a search request.
        
        Args:
            mode: Search mode (AC, KNN, HYBRID)
            latency_ms: Request latency in milliseconds
            success: Whether the request was successful
        """
        # Increment request counter
        self.hybrid_search_requests_total.labels(mode=mode.value).inc()
        
        # Record latency
        self.hybrid_search_latency_ms.labels(mode=mode.value).observe(latency_ms)
    
    def record_ac_hits(
        self,
        hits: Dict[ACHitType, int],
        weak_hits: int = 0
    ) -> None:
        """
        Record AC search hits.
        
        Args:
            hits: Dictionary of hit types and counts
            weak_hits: Number of weak hits
        """
        for hit_type, count in hits.items():
            self.ac_hits_total.labels(type=hit_type.value).inc(count)
        
        if weak_hits > 0:
            self.ac_weak_hits_total.inc(weak_hits)
    
    def record_knn_hits(self, hits: int) -> None:
        """
        Record KNN search hits.
        
        Args:
            hits: Number of KNN hits
        """
        if hits > 0:
            self.knn_hits_total.inc(hits)
    
    def record_fusion_consensus(self, consensus: int) -> None:
        """
        Record fusion consensus hits.
        
        Args:
            consensus: Number of fusion consensus hits
        """
        if consensus > 0:
            self.fusion_consensus_total.inc(consensus)
    
    def record_es_error(self, error_type: ESErrorType) -> None:
        """
        Record Elasticsearch error.
        
        Args:
            error_type: Type of ES error
        """
        self.es_errors_total.labels(type=error_type.value).inc()
    
    def update_success_rate(self, rate: float) -> None:
        """
        Update search success rate.
        
        Args:
            rate: Success rate (0-1)
        """
        self.search_success_rate.set(rate)
    
    def update_active_connections(self, count: int) -> None:
        """
        Update active search connections count.
        
        Args:
            count: Number of active connections
        """
        self.active_search_connections.set(count)
    
    def update_cache_hit_rate(self, rate: float) -> None:
        """
        Update search cache hit rate.
        
        Args:
            rate: Cache hit rate (0-1)
        """
        self.search_cache_hit_rate.set(rate)
    
    def record_search_metrics(self, metrics: SearchMetrics) -> None:
        """
        Record complete search metrics.
        
        Args:
            metrics: Search metrics data
        """
        # Record request
        self.record_search_request(metrics.mode, metrics.latency_ms, metrics.success)
        
        # Record AC hits
        self.record_ac_hits(metrics.ac_hits, metrics.ac_weak_hits)
        
        # Record KNN hits
        self.record_knn_hits(metrics.knn_hits)
        
        # Record fusion consensus
        self.record_fusion_consensus(metrics.fusion_consensus)
        
        # Record ES errors
        for error_type, count in metrics.es_errors.items():
            for _ in range(count):
                self.record_es_error(error_type)
    
    def get_metrics(self) -> bytes:
        """
        Get metrics in Prometheus format.

        Returns:
            Metrics in Prometheus text format
        """
        if self.prometheus_available:
            return generate_latest(self.registry)
        else:
            # Fallback mode - generate basic metrics manually
            metrics_lines = []

            # Basic service metrics
            metrics_lines.append("# HELP ai_service_up Service is up and running")
            metrics_lines.append("# TYPE ai_service_up gauge")
            metrics_lines.append("ai_service_up 1")

            # Search requests
            if hasattr(self, 'hybrid_search_requests_total'):
                metrics_lines.append("# HELP hybrid_search_requests_total Total hybrid search requests")
                metrics_lines.append("# TYPE hybrid_search_requests_total counter")
                metrics_lines.append(f"hybrid_search_requests_total {{mode=\"hybrid\"}} {self.hybrid_search_requests_total.value}")

            # Success rate
            if hasattr(self, 'search_success_rate'):
                metrics_lines.append("# HELP search_success_rate Search success rate")
                metrics_lines.append("# TYPE search_success_rate gauge")
                metrics_lines.append(f"search_success_rate {self.search_success_rate.value}")

            # Active connections
            if hasattr(self, 'active_search_connections'):
                metrics_lines.append("# HELP active_search_connections Active search connections")
                metrics_lines.append("# TYPE active_search_connections gauge")
                metrics_lines.append(f"active_search_connections {self.active_search_connections.value}")

            # Cache hit rate
            if hasattr(self, 'search_cache_hit_rate'):
                metrics_lines.append("# HELP search_cache_hit_rate Search cache hit rate")
                metrics_lines.append("# TYPE search_cache_hit_rate gauge")
                metrics_lines.append(f"search_cache_hit_rate {self.search_cache_hit_rate.value}")

            return ("\n".join(metrics_lines) + "\n").encode('utf-8')
    
    def get_metrics_content_type(self) -> str:
        """
        Get content type for metrics.
        
        Returns:
            Content type for Prometheus metrics
        """
        return CONTENT_TYPE_LATEST


class SearchMetricsCollector:
    """Custom metrics collector for search integration."""
    
    def __init__(self, search_service=None):
        """
        Initialize metrics collector.
        
        Args:
            search_service: Search service instance for collecting metrics
        """
        self.search_service = search_service
    
    def collect(self):
        """Collect custom metrics."""
        
        # Search performance metrics
        if self.search_service:
            # Get performance data from search service
            perf_data = getattr(self.search_service, 'get_performance_metrics', lambda: {})()
            
            # Search throughput (requests per second)
            throughput = perf_data.get('throughput_rps', 0.0)
            yield GaugeMetricFamily(
                'search_throughput_rps',
                'Search throughput in requests per second',
                value=throughput
            )
            
            # Search queue length
            queue_length = perf_data.get('queue_length', 0)
            yield GaugeMetricFamily(
                'search_queue_length',
                'Number of requests in search queue',
                value=queue_length
            )
            
            # Search memory usage
            memory_usage = perf_data.get('memory_usage_bytes', 0)
            yield GaugeMetricFamily(
                'search_memory_usage_bytes',
                'Search service memory usage in bytes',
                value=memory_usage
            )
            
            # Search CPU usage
            cpu_usage = perf_data.get('cpu_usage_percent', 0.0)
            yield GaugeMetricFamily(
                'search_cpu_usage_percent',
                'Search service CPU usage percentage',
                value=cpu_usage
            )
        
        # Elasticsearch cluster health
        yield GaugeMetricFamily(
            'elasticsearch_cluster_health_status',
            'Elasticsearch cluster health status (0=red, 1=yellow, 2=green)',
            value=2  # Default to green
        )
        
        # Elasticsearch index count
        yield GaugeMetricFamily(
            'elasticsearch_indices_count',
            'Number of Elasticsearch indices',
            value=0  # Default value
        )
        
        # Elasticsearch document count
        yield GaugeMetricFamily(
            'elasticsearch_documents_count',
            'Total number of documents in Elasticsearch',
            value=0  # Default value
        )


# Global exporter instance
_exporter: Optional[SearchPrometheusExporter] = None


def get_exporter() -> SearchPrometheusExporter:
    """
    Get global Prometheus exporter instance.
    
    Returns:
        Global exporter instance
    """
    global _exporter
    if _exporter is None:
        _exporter = SearchPrometheusExporter()
    return _exporter


def record_search_request(mode: SearchMode, latency_ms: float, success: bool = True) -> None:
    """
    Record a search request (convenience function).
    
    Args:
        mode: Search mode
        latency_ms: Latency in milliseconds
        success: Whether request was successful
    """
    get_exporter().record_search_request(mode, latency_ms, success)


def record_ac_hits(hits: Dict[ACHitType, int], weak_hits: int = 0) -> None:
    """
    Record AC hits (convenience function).
    
    Args:
        hits: Dictionary of hit types and counts
        weak_hits: Number of weak hits
    """
    get_exporter().record_ac_hits(hits, weak_hits)


def record_knn_hits(hits: int) -> None:
    """
    Record KNN hits (convenience function).
    
    Args:
        hits: Number of KNN hits
    """
    get_exporter().record_knn_hits(hits)


def record_fusion_consensus(consensus: int) -> None:
    """
    Record fusion consensus (convenience function).
    
    Args:
        consensus: Number of fusion consensus hits
    """
    get_exporter().record_fusion_consensus(consensus)


def record_es_error(error_type: ESErrorType) -> None:
    """
    Record ES error (convenience function).
    
    Args:
        error_type: Type of ES error
    """
    get_exporter().record_es_error(error_type)


def get_metrics() -> str:
    """
    Get metrics in Prometheus format (convenience function).
    
    Returns:
        Metrics in Prometheus text format
    """
    return get_exporter().get_metrics()


# Example usage
if __name__ == "__main__":
    # Create exporter
    exporter = SearchPrometheusExporter()
    
    # Record some example metrics
    exporter.record_search_request(SearchMode.HYBRID, 45.2, True)
    exporter.record_ac_hits({
        ACHitType.EXACT: 5,
        ACHitType.PHRASE: 3,
        ACHitType.NGRAM: 2
    }, weak_hits=1)
    exporter.record_knn_hits(8)
    exporter.record_fusion_consensus(3)
    exporter.record_es_error(ESErrorType.TIMEOUT)
    
    # Update gauges
    exporter.update_success_rate(0.95)
    exporter.update_active_connections(5)
    exporter.update_cache_hit_rate(0.85)
    
    # Print metrics
    print("Prometheus Metrics:")
    print(exporter.get_metrics())
