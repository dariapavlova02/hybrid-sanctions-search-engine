"""
Performance tests for ASCII fastpath optimization.
"""

import pytest
import time
import asyncio
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.utils.ascii_utils import is_ascii_name, ascii_fastpath_normalize


class TestAsciiFastpathPerformance:
    """Performance tests for ASCII fastpath optimization."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def ascii_performance_test_cases(self) -> List[Dict[str, Any]]:
        """ASCII test cases for performance testing."""
        return [
            {
                "text": "John Smith",
                "language": "en",
                "description": "Simple English name"
            },
            {
                "text": "Mary-Jane Watson",
                "language": "en",
                "description": "Hyphenated name"
            },
            {
                "text": "J. R. R. Tolkien",
                "language": "en",
                "description": "Name with initials"
            },
            {
                "text": "Dr. Sarah Johnson",
                "language": "en",
                "description": "Name with title"
            },
            {
                "text": "Michael O'Brien",
                "language": "en",
                "description": "Name with apostrophe"
            },
            {
                "text": "Robert Smith Jr.",
                "language": "en",
                "description": "Name with suffix"
            },
            {
                "text": "Elizabeth Taylor",
                "language": "en",
                "description": "Common English name"
            },
            {
                "text": "William Shakespeare",
                "language": "en",
                "description": "Famous English name"
            }
        ]
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_ascii_fastpath_vs_full_pipeline_performance(
        self,
        normalization_factory: NormalizationFactory,
        ascii_performance_test_cases: List[Dict[str, Any]]
    ):
        """Test performance comparison between ASCII fastpath and full pipeline."""
        
        results = []
        
        for test_case in ascii_performance_test_cases:
            text = test_case["text"]
            language = test_case["language"]
            description = test_case["description"]
            
            # Skip if not ASCII
            if not is_ascii_name(text):
                continue
            
            # Create configs
            fastpath_config = NormalizationConfig(
                language=language,
                ascii_fastpath=True,
                enable_advanced_features=False,
                enable_morphology=False
            )
            
            full_config = NormalizationConfig(
                language=language,
                ascii_fastpath=False,
                enable_advanced_features=True,
                enable_morphology=True
            )
            
            # Measure fastpath performance (10 iterations)
            fastpath_times = []
            for _ in range(10):
                start_time = time.perf_counter()
                await normalization_factory.normalize_text(text, fastpath_config)
                end_time = time.perf_counter()
                fastpath_times.append(end_time - start_time)
            
            # Measure full pipeline performance (10 iterations)
            full_times = []
            for _ in range(10):
                start_time = time.perf_counter()
                await normalization_factory.normalize_text(text, full_config)
                end_time = time.perf_counter()
                full_times.append(end_time - start_time)
            
            # Calculate statistics
            avg_fastpath_time = sum(fastpath_times) / len(fastpath_times)
            avg_full_time = sum(full_times) / len(full_times)
            improvement = (avg_full_time - avg_fastpath_time) / avg_full_time * 100
            
            results.append({
                "text": text,
                "description": description,
                "fastpath_time": avg_fastpath_time,
                "full_time": avg_full_time,
                "improvement": improvement
            })
            
            print(f"{description}: {improvement:.1f}% improvement "
                  f"({avg_fastpath_time:.4f}s vs {avg_full_time:.4f}s)")
        
        # Calculate overall statistics
        if results:
            avg_improvement = sum(r["improvement"] for r in results) / len(results)
            min_improvement = min(r["improvement"] for r in results)
            max_improvement = max(r["improvement"] for r in results)
            
            print(f"\nOverall ASCII fastpath performance:")
            print(f"  Average improvement: {avg_improvement:.1f}%")
            print(f"  Min improvement: {min_improvement:.1f}%")
            print(f"  Max improvement: {max_improvement:.1f}%")
            
            # Assert minimum improvement threshold
            assert min_improvement >= 20.0, \
                f"Minimum improvement too low: {min_improvement:.1f}% (expected >= 20%)"
            
            # Assert average improvement threshold
            assert avg_improvement >= 30.0, \
                f"Average improvement too low: {avg_improvement:.1f}% (expected >= 30%)"
    
    @pytest.mark.performance
    def test_ascii_detection_performance(self):
        """Test performance of ASCII name detection."""
        test_texts = [
            "John Smith",
            "Mary-Jane Watson", 
            "J. R. R. Tolkien",
            "Dr. Sarah Johnson",
            "Michael O'Brien",
            "Robert Smith Jr.",
            "Elizabeth Taylor",
            "William Shakespeare",
            "Иван Петров",  # Non-ASCII
            "玛丽",  # Non-ASCII
            "José García",  # Non-ASCII
        ]
        
        # Measure ASCII detection performance
        start_time = time.perf_counter()
        for _ in range(1000):  # 1000 iterations
            for text in test_texts:
                is_ascii_name(text)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time_per_text = total_time / (1000 * len(test_texts))
        
        print(f"ASCII detection performance:")
        print(f"  Total time for {1000 * len(test_texts)} detections: {total_time:.4f}s")
        print(f"  Average time per detection: {avg_time_per_text:.6f}s")
        
        # Should be very fast (microseconds per detection)
        assert avg_time_per_text < 0.001, \
            f"ASCII detection too slow: {avg_time_per_text:.6f}s per detection"
    
    @pytest.mark.performance
    def test_ascii_fastpath_normalize_performance(self):
        """Test performance of ASCII fastpath normalization."""
        test_cases = [
            ("John Smith", "en"),
            ("Mary-Jane Watson", "en"),
            ("J. R. R. Tolkien", "en"),
            ("Dr. Sarah Johnson", "en"),
            ("Michael O'Brien", "en"),
            ("Robert Smith Jr.", "en"),
            ("Elizabeth Taylor", "en"),
            ("William Shakespeare", "en"),
        ]
        
        # Measure ASCII fastpath normalization performance
        start_time = time.perf_counter()
        for _ in range(100):  # 100 iterations
            for text, language in test_cases:
                ascii_fastpath_normalize(text, language)
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        avg_time_per_text = total_time / (100 * len(test_cases))
        
        print(f"ASCII fastpath normalization performance:")
        print(f"  Total time for {100 * len(test_cases)} normalizations: {total_time:.4f}s")
        print(f"  Average time per normalization: {avg_time_per_text:.6f}s")
        
        # Should be very fast (microseconds per normalization)
        assert avg_time_per_text < 0.01, \
            f"ASCII fastpath normalization too slow: {avg_time_per_text:.6f}s per normalization"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_ascii_fastpath_throughput(
        self,
        normalization_factory: NormalizationFactory
    ):
        """Test ASCII fastpath throughput under load."""
        text = "John Smith"
        language = "en"
        
        config = NormalizationConfig(
            language=language,
            ascii_fastpath=True,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        # Measure throughput (concurrent requests)
        concurrent_requests = 50
        iterations_per_request = 10
        
        async def process_request():
            for _ in range(iterations_per_request):
                await normalization_factory.normalize_text(text, config)
        
        # Run concurrent requests
        start_time = time.perf_counter()
        await asyncio.gather(*[process_request() for _ in range(concurrent_requests)])
        end_time = time.perf_counter()
        
        total_time = end_time - start_time
        total_requests = concurrent_requests * iterations_per_request
        requests_per_second = total_requests / total_time
        
        print(f"ASCII fastpath throughput:")
        print(f"  Total requests: {total_requests}")
        print(f"  Total time: {total_time:.4f}s")
        print(f"  Requests per second: {requests_per_second:.1f}")
        
        # Should handle high throughput
        assert requests_per_second >= 100, \
            f"Throughput too low: {requests_per_second:.1f} requests/second (expected >= 100)"
    
    @pytest.mark.performance
    def test_ascii_fastpath_memory_usage(self):
        """Test ASCII fastpath memory usage."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Run many ASCII fastpath normalizations
        for _ in range(1000):
            ascii_fastpath_normalize("John Smith", "en")
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        print(f"ASCII fastpath memory usage:")
        print(f"  Initial memory: {initial_memory / 1024 / 1024:.2f} MB")
        print(f"  Final memory: {final_memory / 1024 / 1024:.2f} MB")
        print(f"  Memory increase: {memory_increase / 1024:.2f} KB")
        
        # Memory increase should be minimal (less than 1 MB)
        assert memory_increase < 1024 * 1024, \
            f"Memory usage too high: {memory_increase / 1024:.2f} KB increase"
    
    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_ascii_fastpath_latency_distribution(
        self,
        normalization_factory: NormalizationFactory
    ):
        """Test ASCII fastpath latency distribution."""
        text = "John Smith"
        language = "en"
        
        config = NormalizationConfig(
            language=language,
            ascii_fastpath=True,
            enable_advanced_features=False,
            enable_morphology=False
        )
        
        # Measure latency distribution
        latencies = []
        for _ in range(100):
            start_time = time.perf_counter()
            await normalization_factory.normalize_text(text, config)
            end_time = time.perf_counter()
            latencies.append(end_time - start_time)
        
        # Calculate statistics
        latencies.sort()
        p50 = latencies[50]  # 50th percentile
        p95 = latencies[95]  # 95th percentile
        p99 = latencies[99]  # 99th percentile
        max_latency = latencies[-1]
        
        print(f"ASCII fastpath latency distribution:")
        print(f"  P50: {p50:.4f}s")
        print(f"  P95: {p95:.4f}s")
        print(f"  P99: {p99:.4f}s")
        print(f"  Max: {max_latency:.4f}s")
        
        # P95 should be very low (less than 10ms)
        assert p95 < 0.01, \
            f"P95 latency too high: {p95:.4f}s (expected < 0.01s)"
        
        # Max latency should be reasonable (less than 50ms)
        assert max_latency < 0.05, \
            f"Max latency too high: {max_latency:.4f}s (expected < 0.05s)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "performance"])
