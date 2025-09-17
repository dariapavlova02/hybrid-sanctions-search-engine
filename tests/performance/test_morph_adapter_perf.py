"""
Performance tests for MorphologyAdapter.

Tests performance requirements:
- 1k short tokens → p95 < 8-10ms, average < 2ms (with warmed cache)
"""

import pytest
import time
import statistics
from typing import List, Tuple

from src.ai_service.layers.normalization.morphology_adapter import (
    MorphologyAdapter,
    get_global_adapter,
    clear_global_cache,
)


class TestMorphologyAdapterPerformance:
    """Performance tests for MorphologyAdapter."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear global cache before each test
        clear_global_cache()

    def generate_test_tokens(self, count: int = 1000) -> List[Tuple[str, str]]:
        """Generate test tokens for performance testing."""
        # Common Russian names and surnames
        russian_names = [
            "Анна", "Мария", "Елена", "Ольга", "Татьяна", "Наталья", "Ирина", "Светлана",
            "Иван", "Сергей", "Александр", "Дмитрий", "Андрей", "Максим", "Владимир", "Алексей",
            "Иванова", "Петрова", "Сидорова", "Кузнецова", "Морозова", "Волкова", "Новикова",
            "Иванов", "Петров", "Сидоров", "Кузнецов", "Морозов", "Волков", "Новиков",
            "Анны", "Марии", "Елены", "Ольги", "Татьяны", "Натальи", "Ирины", "Светланы",
            "Ивана", "Сергея", "Александра", "Дмитрия", "Андрея", "Максима", "Владимира", "Алексея",
            "Ивановой", "Петровой", "Сидоровой", "Кузнецовой", "Морозовой", "Волковой", "Новиковой",
        ]
        
        # Common Ukrainian names and surnames
        ukrainian_names = [
            "Олена", "Ірина", "Марія", "Наталія", "Тетяна", "Світлана", "Людмила", "Валентина",
            "Іван", "Сергій", "Олександр", "Дмитро", "Андрій", "Максим", "Володимир", "Олексій",
            "Ковальська", "Шевченко", "Петренко", "Кравцівська", "Морозова", "Волкова", "Новак",
            "Ковальський", "Шевченко", "Петренко", "Кравцівський", "Морозов", "Волков", "Новак",
            "Олени", "Ірини", "Марії", "Наталії", "Тетяни", "Світлани", "Людмили", "Валентини",
            "Івана", "Сергія", "Олександра", "Дмитра", "Андрія", "Максима", "Володимира", "Олексія",
            "Ковальською", "Шевченком", "Петренком", "Кравцівською", "Морозовою", "Волковою", "Новак",
        ]
        
        # Generate tokens with 70% Russian, 30% Ukrainian
        tokens = []
        for i in range(count):
            if i % 10 < 7:  # 70% Russian
                token = russian_names[i % len(russian_names)]
                lang = "ru"
            else:  # 30% Ukrainian
                token = ukrainian_names[i % len(ukrainian_names)]
                lang = "uk"
            tokens.append((token, lang))
        
        return tokens

    def measure_operation_time(self, operation, *args, **kwargs) -> float:
        """Measure execution time of an operation in milliseconds."""
        start_time = time.perf_counter()
        operation(*args, **kwargs)
        end_time = time.perf_counter()
        return (end_time - start_time) * 1000  # Convert to milliseconds

    def test_parse_performance_cold_cache(self):
        """Test parse performance with cold cache."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(100)  # Start with smaller set
        
        times = []
        for token, lang in tokens:
            time_ms = self.measure_operation_time(adapter.parse, token, lang)
            times.append(time_ms)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        print(f"Parse performance (cold cache): avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")
        
        # Performance requirements are more lenient for cold cache
        assert avg_time < 50, f"Average time {avg_time:.2f}ms exceeds 50ms limit"
        assert p95_time < 100, f"P95 time {p95_time:.2f}ms exceeds 100ms limit"

    def test_parse_performance_warm_cache(self):
        """Test parse performance with warmed cache."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(1000)
        
        # Warm up cache
        print("Warming up cache...")
        adapter.warmup(tokens)
        
        # Measure performance with warm cache
        times = []
        for token, lang in tokens:
            time_ms = self.measure_operation_time(adapter.parse, token, lang)
            times.append(time_ms)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]  # 95th percentile
        
        print(f"Parse performance (warm cache): avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")
        
        # Performance requirements
        assert avg_time < 2, f"Average time {avg_time:.2f}ms exceeds 2ms limit"
        assert p95_time < 10, f"P95 time {p95_time:.2f}ms exceeds 10ms limit"

    def test_to_nominative_performance_warm_cache(self):
        """Test to_nominative performance with warmed cache."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(1000)
        
        # Warm up cache
        adapter.warmup(tokens)
        
        # Measure performance
        times = []
        for token, lang in tokens:
            time_ms = self.measure_operation_time(adapter.to_nominative, token, lang)
            times.append(time_ms)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        
        print(f"To nominative performance (warm cache): avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")
        
        # Performance requirements
        assert avg_time < 2, f"Average time {avg_time:.2f}ms exceeds 2ms limit"
        assert p95_time < 10, f"P95 time {p95_time:.2f}ms exceeds 10ms limit"

    def test_detect_gender_performance_warm_cache(self):
        """Test detect_gender performance with warmed cache."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(1000)
        
        # Warm up cache
        adapter.warmup(tokens)
        
        # Measure performance
        times = []
        for token, lang in tokens:
            time_ms = self.measure_operation_time(adapter.detect_gender, token, lang)
            times.append(time_ms)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        
        print(f"Detect gender performance (warm cache): avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")
        
        # Performance requirements
        assert avg_time < 2, f"Average time {avg_time:.2f}ms exceeds 2ms limit"
        assert p95_time < 10, f"P95 time {p95_time:.2f}ms exceeds 10ms limit"

    def test_mixed_operations_performance(self):
        """Test performance of mixed operations with warm cache."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(1000)
        
        # Warm up cache
        adapter.warmup(tokens)
        
        # Measure mixed operations
        times = []
        for i, (token, lang) in enumerate(tokens):
            start_time = time.perf_counter()
            
            # Mix of operations
            if i % 3 == 0:
                adapter.parse(token, lang)
            elif i % 3 == 1:
                adapter.to_nominative(token, lang)
            else:
                adapter.detect_gender(token, lang)
            
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        
        print(f"Mixed operations performance (warm cache): avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")
        
        # Performance requirements
        assert avg_time < 2, f"Average time {avg_time:.2f}ms exceeds 2ms limit"
        assert p95_time < 10, f"P95 time {p95_time:.2f}ms exceeds 10ms limit"

    def test_cache_hit_ratio(self):
        """Test cache hit ratio with repeated operations."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(100)
        
        # First pass - should miss cache
        for token, lang in tokens:
            adapter.parse(token, lang)
        
        stats_after_first = adapter.get_cache_stats()
        first_misses = stats_after_first["parse_cache_misses"]
        
        # Second pass - should hit cache
        for token, lang in tokens:
            adapter.parse(token, lang)
        
        stats_after_second = adapter.get_cache_stats()
        second_hits = stats_after_second["parse_cache_hits"] - stats_after_first["parse_cache_hits"]
        
        # Calculate hit ratio
        hit_ratio = second_hits / (second_hits + first_misses) if (second_hits + first_misses) > 0 else 0
        
        print(f"Cache hit ratio: {hit_ratio:.2%}")
        
        # Should have high hit ratio on second pass
        assert hit_ratio > 0.8, f"Cache hit ratio {hit_ratio:.2%} is too low"

    def test_memory_usage_stability(self):
        """Test that memory usage remains stable with large cache."""
        adapter = MorphologyAdapter(cache_size=100000)
        tokens = self.generate_test_tokens(5000)
        
        # Fill cache
        for token, lang in tokens:
            adapter.parse(token, lang)
        
        # Get initial stats
        initial_stats = adapter.get_cache_stats()
        
        # Perform more operations
        for i in range(1000):
            token, lang = tokens[i % len(tokens)]
            adapter.parse(token, lang)
        
        # Get final stats
        final_stats = adapter.get_cache_stats()
        
        # Cache size should not grow beyond limit
        assert final_stats["parse_cache_size"] <= adapter._cache_size
        print(f"Cache size: {final_stats['parse_cache_size']}/{adapter._cache_size}")

    def test_concurrent_performance(self):
        """Test performance under concurrent access."""
        import threading
        import queue
        
        adapter = get_global_adapter(cache_size=50000)
        tokens = self.generate_test_tokens(500)
        
        # Warm up cache
        adapter.warmup(tokens)
        
        # Results queue
        results = queue.Queue()
        
        def worker(worker_id: int, token_subset: List[Tuple[str, str]]):
            """Worker function for concurrent testing."""
            times = []
            for token, lang in token_subset:
                start_time = time.perf_counter()
                adapter.parse(token, lang)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            
            results.put((worker_id, times))
        
        # Create multiple threads
        num_threads = 4
        threads = []
        tokens_per_thread = len(tokens) // num_threads
        
        for i in range(num_threads):
            start_idx = i * tokens_per_thread
            end_idx = start_idx + tokens_per_thread if i < num_threads - 1 else len(tokens)
            thread_tokens = tokens[start_idx:end_idx]
            
            thread = threading.Thread(target=worker, args=(i, thread_tokens))
            threads.append(thread)
        
        # Start all threads
        start_time = time.perf_counter()
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        end_time = time.perf_counter()
        
        # Collect results
        all_times = []
        while not results.empty():
            worker_id, times = results.get()
            all_times.extend(times)
        
        # Calculate statistics
        avg_time = statistics.mean(all_times)
        p95_time = statistics.quantiles(all_times, n=20)[18]
        total_time = (end_time - start_time) * 1000
        
        print(f"Concurrent performance: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms, total={total_time:.2f}ms")
        
        # Performance should still be good under concurrent access
        assert avg_time < 5, f"Average time {avg_time:.2f}ms exceeds 5ms limit under concurrency"
        assert p95_time < 20, f"P95 time {p95_time:.2f}ms exceeds 20ms limit under concurrency"

    def test_global_adapter_performance(self):
        """Test performance of global adapter."""
        # Clear global state
        clear_global_cache()
        
        # Get global adapter
        adapter = get_global_adapter(cache_size=50000)
        tokens = self.generate_test_tokens(1000)
        
        # Warm up cache
        adapter.warmup(tokens)
        
        # Measure performance
        times = []
        for token, lang in tokens:
            time_ms = self.measure_operation_time(adapter.parse, token, lang)
            times.append(time_ms)
        
        # Calculate statistics
        avg_time = statistics.mean(times)
        p95_time = statistics.quantiles(times, n=20)[18]
        
        print(f"Global adapter performance: avg={avg_time:.2f}ms, p95={p95_time:.2f}ms")
        
        # Performance requirements
        assert avg_time < 2, f"Average time {avg_time:.2f}ms exceeds 2ms limit"
        assert p95_time < 10, f"P95 time {p95_time:.2f}ms exceeds 10ms limit"

    def test_warmup_performance(self):
        """Test warmup performance."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(1000)
        
        # Measure warmup time
        warmup_time = self.measure_operation_time(adapter.warmup, tokens)
        
        print(f"Warmup performance: {warmup_time:.2f}ms for {len(tokens)} tokens")
        
        # Warmup should be reasonably fast
        assert warmup_time < 1000, f"Warmup time {warmup_time:.2f}ms exceeds 1000ms limit"

    def test_cache_clear_performance(self):
        """Test cache clear performance."""
        adapter = MorphologyAdapter(cache_size=50000)
        tokens = self.generate_test_tokens(1000)
        
        # Fill cache
        adapter.warmup(tokens)
        
        # Measure clear time
        clear_time = self.measure_operation_time(adapter.clear_cache)
        
        print(f"Cache clear performance: {clear_time:.2f}ms")
        
        # Clear should be very fast
        assert clear_time < 10, f"Cache clear time {clear_time:.2f}ms exceeds 10ms limit"
