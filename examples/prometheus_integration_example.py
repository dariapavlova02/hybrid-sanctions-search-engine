#!/usr/bin/env python3
"""
Example of integrating Prometheus metrics with search service.

This example shows how to:
1. Initialize Prometheus exporter
2. Record search metrics
3. Expose metrics endpoint
4. Use with FastAPI/Flask
"""

import asyncio
import time
from typing import Dict, List
from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
import uvicorn

# Import our Prometheus exporter
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_service.monitoring.prometheus_exporter import (
    SearchPrometheusExporter,
    SearchMode,
    ACHitType,
    ESErrorType,
    SearchMetrics,
    get_exporter
)


class SearchServiceWithMetrics:
    """Example search service with integrated Prometheus metrics."""
    
    def __init__(self):
        """Initialize search service with metrics."""
        self.exporter = get_exporter()
        self.request_count = 0
    
    async def search(self, query: str, mode: SearchMode = SearchMode.HYBRID) -> Dict:
        """
        Perform search with metrics recording.
        
        Args:
            query: Search query
            mode: Search mode
            
        Returns:
            Search results
        """
        start_time = time.time()
        self.request_count += 1
        
        try:
            # Simulate search processing
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Simulate AC search
            ac_hits = {
                ACHitType.EXACT: 5 if "exact" in query.lower() else 0,
                ACHitType.PHRASE: 3 if "phrase" in query.lower() else 0,
                ACHitType.NGRAM: 2 if "ngram" in query.lower() else 0
            }
            ac_weak_hits = 1 if "weak" in query.lower() else 0
            
            # Simulate KNN search
            knn_hits = 8 if "vector" in query.lower() else 0
            
            # Simulate fusion consensus
            fusion_consensus = 3 if "fusion" in query.lower() else 0
            
            # Simulate ES errors
            es_errors = {
                ESErrorType.TIMEOUT: 1 if "timeout" in query.lower() else 0,
                ESErrorType.CONNECTION: 1 if "conn" in query.lower() else 0,
                ESErrorType.MAPPING: 1 if "mapping" in query.lower() else 0
            }
            
            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000
            
            # Record metrics
            self.exporter.record_search_request(mode, latency_ms, success=True)
            self.exporter.record_ac_hits(ac_hits, ac_weak_hits)
            self.exporter.record_knn_hits(knn_hits)
            self.exporter.record_fusion_consensus(fusion_consensus)
            
            # Record ES errors
            for error_type, count in es_errors.items():
                for _ in range(count):
                    self.exporter.record_es_error(error_type)
            
            # Update success rate
            success_rate = 0.95 if self.request_count % 20 != 0 else 0.85  # Simulate occasional failures
            self.exporter.update_success_rate(success_rate)
            
            # Update active connections
            self.exporter.update_active_connections(min(self.request_count % 10, 5))
            
            # Update cache hit rate
            cache_hit_rate = 0.85 + (self.request_count % 10) * 0.01  # Simulate varying cache hit rate
            self.exporter.update_cache_hit_rate(cache_hit_rate)
            
            return {
                "query": query,
                "mode": mode.value,
                "results": {
                    "ac_hits": ac_hits,
                    "ac_weak_hits": ac_weak_hits,
                    "knn_hits": knn_hits,
                    "fusion_consensus": fusion_consensus,
                    "es_errors": es_errors
                },
                "latency_ms": latency_ms,
                "success": True
            }
            
        except Exception as e:
            # Record failed request
            latency_ms = (time.time() - start_time) * 1000
            self.exporter.record_search_request(mode, latency_ms, success=False)
            self.exporter.record_es_error(ESErrorType.QUERY)
            
            raise HTTPException(status_code=500, detail=str(e))


# FastAPI application
app = FastAPI(title="Search Service with Metrics", version="1.0.0")

# Initialize search service
search_service = SearchServiceWithMetrics()


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Search Service with Prometheus Metrics"}


@app.get("/search")
async def search_endpoint(query: str, mode: str = "hybrid"):
    """
    Search endpoint with metrics.
    
    Args:
        query: Search query
        mode: Search mode (ac, knn, hybrid)
        
    Returns:
        Search results
    """
    try:
        search_mode = SearchMode(mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid mode: {mode}")
    
    return await search_service.search(query, search_mode)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics_endpoint():
    """
    Prometheus metrics endpoint.
    
    Returns:
        Metrics in Prometheus text format
    """
    return search_service.exporter.get_metrics()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "request_count": search_service.request_count
    }


@app.get("/stats")
async def stats_endpoint():
    """Statistics endpoint."""
    return {
        "request_count": search_service.request_count,
        "success_rate": 0.95,  # This would be calculated from actual metrics
        "active_connections": 5,
        "cache_hit_rate": 0.85
    }


# Example of using the exporter directly
async def example_usage():
    """Example of using the Prometheus exporter directly."""
    print("=== Prometheus Metrics Integration Example ===\n")
    
    # Create exporter
    exporter = SearchPrometheusExporter()
    
    # Record some example metrics
    print("1. Recording search requests...")
    exporter.record_search_request(SearchMode.HYBRID, 45.2, True)
    exporter.record_search_request(SearchMode.AC, 25.1, True)
    exporter.record_search_request(SearchMode.KNN, 120.5, True)
    
    print("2. Recording AC hits...")
    exporter.record_ac_hits({
        ACHitType.EXACT: 5,
        ACHitType.PHRASE: 3,
        ACHitType.NGRAM: 2
    }, weak_hits=1)
    
    print("3. Recording KNN hits...")
    exporter.record_knn_hits(8)
    
    print("4. Recording fusion consensus...")
    exporter.record_fusion_consensus(3)
    
    print("5. Recording ES errors...")
    exporter.record_es_error(ESErrorType.TIMEOUT)
    exporter.record_es_error(ESErrorType.CONNECTION)
    
    print("6. Updating gauges...")
    exporter.update_success_rate(0.95)
    exporter.update_active_connections(5)
    exporter.update_cache_hit_rate(0.85)
    
    print("7. Generated metrics:")
    print(exporter.get_metrics())
    
    print("\n=== Example completed ===")


if __name__ == "__main__":
    # Run example
    asyncio.run(example_usage())
    
    # Start FastAPI server
    print("\nStarting FastAPI server...")
    print("Available endpoints:")
    print("  GET / - Root endpoint")
    print("  GET /search?query=<query>&mode=<mode> - Search endpoint")
    print("  GET /metrics - Prometheus metrics")
    print("  GET /health - Health check")
    print("  GET /stats - Statistics")
    print("\nServer will start on http://localhost:8000")
    print("Metrics available at http://localhost:8000/metrics")
    
    uvicorn.run(app, host="0.0.0.0", port=8000)
