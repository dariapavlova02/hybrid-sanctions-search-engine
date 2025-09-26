#!/usr/bin/env python3
"""
Performance test script for AI normalization service.

This script tests performance with cache enabled and measures key metrics.
"""

import argparse
import os
import sys
import time
import statistics
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.utils import get_logger

logger = get_logger(__name__)

# Performance test data
PERFORMANCE_TEST_DATA = [
    "John Smith",
    "Mary Johnson", 
    "Robert Brown",
    "Jennifer Davis",
    "Michael Wilson",
    "Elizabeth Taylor",
    "William Anderson",
    "Sarah Martinez",
    "David Thompson",
    "Lisa Garcia",
    "Christopher Lee",
    "Amanda White",
    "James Wilson",
    "Jessica Brown",
    "Matthew Davis",
    "Ashley Miller",
    "Daniel Garcia",
    "Emily Rodriguez",
    "Andrew Martinez",
    "Samantha Anderson"
]

class PerformanceTestService:
    """Service for testing performance of the normalization service."""
    
    def __init__(self):
        self.service = None
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "response_times": [],
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    def initialize_service(self) -> None:
        """Initialize the normalization service."""
        try:
            logger.info("Initializing normalization service...")
            self.service = NormalizationService()
            logger.info("✓ Service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize service: {e}")
            raise
    
    def test_single_request(self, text: str, language: str = "en") -> Dict[str, Any]:
        """Test a single request and measure performance."""
        start_time = time.time()
        
        try:
            result = self.service.normalize(text, language=language)
            end_time = time.time()
            
            response_time = end_time - start_time
            self.stats["total_requests"] += 1
            self.stats["successful_requests"] += 1
            self.stats["total_time"] += response_time
            self.stats["response_times"].append(response_time)
            
            return {
                "text": text,
                "language": language,
                "success": result.success,
                "normalized": result.normalized_text,
                "tokens": len(result.tokens),
                "response_time": response_time,
                "response_time_ms": response_time * 1000
            }
            
        except Exception as e:
            end_time = time.time()
            response_time = end_time - start_time
            self.stats["total_requests"] += 1
            self.stats["failed_requests"] += 1
            self.stats["total_time"] += response_time
            self.stats["response_times"].append(response_time)
            
            logger.warning(f"Failed to normalize '{text}': {e}")
            return {
                "text": text,
                "language": language,
                "success": False,
                "error": str(e),
                "response_time": response_time,
                "response_time_ms": response_time * 1000
            }
    
    def run_performance_test(self, n: int = 1000, warmup_rounds: int = 100) -> None:
        """Run comprehensive performance test."""
        logger.info(f"Starting performance test with {n} requests (warmup: {warmup_rounds})...")
        
        # Initialize service
        self.initialize_service()
        
        # Warmup phase
        logger.info(f"Phase 1: Warmup ({warmup_rounds} requests)...")
        warmup_data = PERFORMANCE_TEST_DATA * (warmup_rounds // len(PERFORMANCE_TEST_DATA) + 1)
        warmup_data = warmup_data[:warmup_rounds]
        
        for i, text in enumerate(warmup_data):
            if i % 20 == 0:
                logger.info(f"Warmup {i+1}/{warmup_rounds}: {text[:30]}...")
            self.test_single_request(text, "en")
        
        # Clear stats for actual test
        self.stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "total_time": 0.0,
            "response_times": [],
            "cache_hits": 0,
            "cache_misses": 0
        }
        
        # Performance test phase
        logger.info(f"Phase 2: Performance test ({n} requests)...")
        test_data = PERFORMANCE_TEST_DATA * (n // len(PERFORMANCE_TEST_DATA) + 1)
        test_data = test_data[:n]
        
        for i, text in enumerate(test_data):
            if i % 100 == 0:
                logger.info(f"Test {i+1}/{n}: {text[:30]}...")
            self.test_single_request(text, "en")
        
        # Print performance statistics
        self.print_performance_statistics()
    
    def print_performance_statistics(self) -> None:
        """Print comprehensive performance statistics."""
        logger.info("=== Performance Test Results ===")
        logger.info(f"Total requests: {self.stats['total_requests']}")
        logger.info(f"Successful requests: {self.stats['successful_requests']}")
        logger.info(f"Failed requests: {self.stats['failed_requests']}")
        logger.info(f"Success rate: {self.stats['successful_requests']/self.stats['total_requests']*100:.1f}%")
        logger.info(f"Total time: {self.stats['total_time']:.3f}s")
        logger.info(f"Average time per request: {self.stats['total_time']/self.stats['total_requests']*1000:.2f}ms")
        
        if self.stats['response_times']:
            response_times_ms = [rt * 1000 for rt in self.stats['response_times']]
            logger.info(f"Min response time: {min(response_times_ms):.2f}ms")
            logger.info(f"Max response time: {max(response_times_ms):.2f}ms")
            logger.info(f"Median response time: {statistics.median(response_times_ms):.2f}ms")
            logger.info(f"P95 response time: {self._percentile(response_times_ms, 95):.2f}ms")
            logger.info(f"P99 response time: {self._percentile(response_times_ms, 99):.2f}ms")
            
            # Check SLA compliance
            p95_ms = self._percentile(response_times_ms, 95)
            p99_ms = self._percentile(response_times_ms, 99)
            
            logger.info("=== SLA Compliance ===")
            logger.info(f"P95 ≤ 10ms: {'✅ PASS' if p95_ms <= 10 else '❌ FAIL'} ({p95_ms:.2f}ms)")
            logger.info(f"P99 ≤ 20ms: {'✅ PASS' if p99_ms <= 20 else '❌ FAIL'} ({p99_ms:.2f}ms)")
            
            # Cache statistics if available
            if hasattr(self.service, '_morph_cache') and hasattr(self.service._morph_cache, 'cache_info'):
                cache_info = self.service._morph_cache.cache_info()
                # Defensive access to cache_info attributes
                hits = getattr(cache_info, 'hits', cache_info.get('hits', 0) if isinstance(cache_info, dict) else 0)
                misses = getattr(cache_info, 'misses', cache_info.get('misses', 0) if isinstance(cache_info, dict) else 0)
                total_cache_requests = hits + misses
                if total_cache_requests > 0:
                    cache_hit_rate = hits / total_cache_requests * 100
                    logger.info(f"Cache hit rate: {cache_hit_rate:.1f}%")
                    logger.info(f"Cache hits: {hits}")
                    logger.info(f"Cache misses: {misses}")
    
    def _percentile(self, data: List[float], percentile: int) -> float:
        """Calculate percentile of data."""
        sorted_data = sorted(data)
        index = int(len(sorted_data) * percentile / 100)
        return sorted_data[min(index, len(sorted_data) - 1)]

def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Performance test for AI normalization service")
    parser.add_argument("--n", type=int, default=1000, help="Number of test requests")
    parser.add_argument("--warmup", type=int, default=100, help="Number of warmup requests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    # Set up logging
    if args.verbose:
        import logging
        logging.basicConfig(level=logging.INFO)
    
    # Create and run performance test
    perf_test = PerformanceTestService()
    perf_test.run_performance_test(args.n, args.warmup)
    
    logger.info("✓ Performance test completed successfully!")

if __name__ == "__main__":
    main()
