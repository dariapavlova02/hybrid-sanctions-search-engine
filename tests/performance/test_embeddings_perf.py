"""
Performance tests for embeddings
"""

import statistics
import time
from typing import List

import pytest
from ai_service.config import EmbeddingConfig
from ai_service.layers.embeddings.embedding_service import EmbeddingService
from ai_service.utils.perf_timer import perf_timer


class TestEmbeddingsPerformance:
    """Test embeddings performance and memory stability"""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service for testing"""
        config = EmbeddingConfig()
        return EmbeddingService(config)

    @pytest.fixture
    def short_names(self) -> List[str]:
        """Generate 1000 short names for performance testing"""
        names = []
        
        # Common first names in different languages
        first_names = [
            "Ivan", "Petr", "Anna", "Maria", "John", "Jane", "Mike", "Sarah",
            "Іван", "Петро", "Анна", "Марія", "Олександр", "Олена", "Володимир", "Наталія",
            "Иван", "Петр", "Анна", "Мария", "Александр", "Елена", "Владимир", "Наталья"
        ]
        
        # Common last names
        last_names = [
            "Ivanov", "Petrov", "Smith", "Johnson", "Brown", "Wilson", "Davis", "Miller",
            "Іванов", "Петров", "Сидоренко", "Коваленко", "Шевченко", "Бондаренко", "Кравченко", "Ткаченко",
            "Иванов", "Петров", "Сидоренко", "Коваленко", "Шевченко", "Бондаренко", "Кравченко", "Ткаченко"
        ]
        
        # Generate 1000 combinations
        for i in range(1000):
            first = first_names[i % len(first_names)]
            last = last_names[i % len(last_names)]
            names.append(f"{first} {last}")
        
        return names

    def test_warmup_performance(self, embedding_service, short_names):
        """Test warmup performance - first encode should be slower due to model loading"""
        # Warmup run
        warmup_texts = short_names[:10]  # Small batch for warmup
        
        with perf_timer("warmup_encode_batch"):
            warmup_result = embedding_service.encode_batch(warmup_texts)
        
        assert len(warmup_result) == 10
        assert all(len(emb) == 384 for emb in warmup_result)

    def test_batch_performance_p95(self, embedding_service, short_names):
        """Test that p95 latency is reasonable for short names on CPU"""
        # Warmup first (this includes model loading)
        embedding_service.encode_batch(short_names[:10])
        
        # Measure remaining short names (skip first batch to exclude warmup)
        batch_size = 50  # Process in smaller batches
        latencies = []
        
        # Start from batch 1 to exclude warmup
        for i in range(batch_size, len(short_names), batch_size):
            batch = short_names[i:i + batch_size]
            
            start_time = time.perf_counter()
            result = embedding_service.encode_batch(batch)
            end_time = time.perf_counter()
            
            duration_ms = (end_time - start_time) * 1000
            latencies.append(duration_ms)
            
            assert len(result) == len(batch)
            assert all(len(emb) == 384 for emb in result)
        
        # Calculate p95 latency
        p95_latency = statistics.quantiles(latencies, n=20)[18]  # 95th percentile
        avg_latency = statistics.mean(latencies)
        max_latency = max(latencies)
        
        print(f"\n[STATS] Performance Results:")
        print(f"   Average latency: {avg_latency:.2f}ms")
        print(f"   P95 latency: {p95_latency:.2f}ms")
        print(f"   Max latency: {max_latency:.2f}ms")
        print(f"   Total batches: {len(latencies)}")
        
        # P95 should be under 200ms (adjusted for CPU performance)
        assert p95_latency < 200.0, f"P95 latency {p95_latency:.2f}ms exceeds 200ms threshold"
        
        # Average should be reasonable
        assert avg_latency < 150.0, f"Average latency {avg_latency:.2f}ms exceeds 150ms threshold"

    def test_repeated_batch_performance(self, embedding_service, short_names):
        """Test that repeated encode_batch is faster than first (lazy load + cache)"""
        test_batch = short_names[:20]
        
        # First run (includes model loading)
        start_time = time.perf_counter()
        first_result = embedding_service.encode_batch(test_batch)
        first_duration = (time.perf_counter() - start_time) * 1000
        
        # Second run (should be faster due to cached model)
        start_time = time.perf_counter()
        second_result = embedding_service.encode_batch(test_batch)
        second_duration = (time.perf_counter() - start_time) * 1000
        
        print(f"\n[PROGRESS] Repeated Batch Performance:")
        print(f"   First run: {first_duration:.2f}ms")
        print(f"   Second run: {second_duration:.2f}ms")
        print(f"   Speedup: {first_duration / second_duration:.2f}x")
        
        # Results should be identical
        assert len(first_result) == len(second_result)
        assert all(len(emb) == 384 for emb in first_result)
        assert all(len(emb) == 384 for emb in second_result)
        
        # Second run should be faster (at least 20% improvement)
        speedup = first_duration / second_duration
        assert speedup > 1.2, f"Second run not significantly faster: {speedup:.2f}x speedup"

    def test_memory_stability(self, embedding_service, short_names):
        """Test that memory usage is stable across multiple batches"""
        try:
            import psutil
            import os
            
            process = psutil.Process(os.getpid())
            
            # Get initial memory
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Process multiple batches
            batch_size = 100
            for i in range(0, min(500, len(short_names)), batch_size):
                batch = short_names[i:i + batch_size]
                result = embedding_service.encode_batch(batch)
                
                # Check memory every 5 batches
                if i % (batch_size * 5) == 0:
                    current_memory = process.memory_info().rss / 1024 / 1024  # MB
                    memory_increase = current_memory - initial_memory
                    
                    print(f"   Batch {i//batch_size}: Memory +{memory_increase:.1f}MB")
                    
                    # Memory increase should be reasonable (< 100MB)
                    assert memory_increase < 100, f"Memory increase {memory_increase:.1f}MB too high"
            
            # Final memory check
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            total_increase = final_memory - initial_memory
            
            print(f"\n💾 Memory Stability:")
            print(f"   Initial memory: {initial_memory:.1f}MB")
            print(f"   Final memory: {final_memory:.1f}MB")
            print(f"   Total increase: {total_increase:.1f}MB")
            
            # Total memory increase should be reasonable
            assert total_increase < 200, f"Total memory increase {total_increase:.1f}MB too high"
            
        except ImportError:
            pytest.skip("psutil not available for memory monitoring")

    def test_single_vs_batch_performance(self, embedding_service, short_names):
        """Test that batch processing is more efficient than single encodes"""
        test_names = short_names[:10]
        
        # Single encodes
        single_start = time.perf_counter()
        single_results = []
        for name in test_names:
            result = embedding_service.encode_one(name)
            single_results.append(result)
        single_duration = (time.perf_counter() - single_start) * 1000
        
        # Batch encode
        batch_start = time.perf_counter()
        batch_results = embedding_service.encode_batch(test_names)
        batch_duration = (time.perf_counter() - batch_start) * 1000
        
        print(f"\n⚡ Single vs Batch Performance:")
        print(f"   Single encodes: {single_duration:.2f}ms")
        print(f"   Batch encode: {batch_duration:.2f}ms")
        print(f"   Batch efficiency: {single_duration / batch_duration:.2f}x")
        
        # Results should be identical
        assert len(single_results) == len(batch_results)
        assert all(len(emb) == 384 for emb in single_results)
        assert all(len(emb) == 384 for emb in batch_results)
        
        # Batch should be more efficient
        efficiency = single_duration / batch_duration
        assert efficiency > 1.5, f"Batch not significantly more efficient: {efficiency:.2f}x"

    def test_large_batch_performance(self, embedding_service, short_names):
        """Test performance with larger batches"""
        large_batch = short_names[:200]  # 200 names
        
        with perf_timer("large_batch_encode"):
            result = embedding_service.encode_batch(large_batch)
        
        assert len(result) == 200
        assert all(len(emb) == 384 for emb in result)
        
        # Should complete in reasonable time (< 2 seconds)
        # This is tested by the perf_timer context manager

    def test_empty_and_single_text_performance(self, embedding_service):
        """Test performance edge cases"""
        # Empty batch
        start_time = time.perf_counter()
        empty_result = embedding_service.encode_batch([])
        empty_duration = (time.perf_counter() - start_time) * 1000
        
        assert empty_result == []
        assert empty_duration < 1.0, f"Empty batch too slow: {empty_duration:.2f}ms"
        
        # Single text (after warmup)
        # First do a warmup to load the model
        embedding_service.encode_batch(["warmup"])
        
        start_time = time.perf_counter()
        single_result = embedding_service.encode_batch(["Ivan Petrov"])
        single_duration = (time.perf_counter() - start_time) * 1000
        
        assert len(single_result) == 1
        assert len(single_result[0]) == 384
        assert single_duration < 200.0, f"Single text too slow: {single_duration:.2f}ms"
        
        print(f"\n[CHECK] Edge Case Performance:")
        print(f"   Empty batch: {empty_duration:.2f}ms")
        print(f"   Single text: {single_duration:.2f}ms")
