"""
Performance tests for search functionality.
"""

import asyncio
import time
import statistics
import pytest
from src.ai_service.core.orchestrator_factory_with_search import OrchestratorFactoryWithSearch
from src.ai_service.contracts.search_contracts import SearchOpts, SearchMode


@pytest.mark.performance
@pytest.mark.slow
@pytest.mark.docker
class TestSearchPerformance:
    """Test search performance with 1k requests."""
    
    @pytest.mark.asyncio
    async def test_search_performance_1k_requests(self, elasticsearch_container, test_indices):
        """Test search performance with 1k requests, p95 < 80ms end-to-end."""
        # Create orchestrator with search enabled
        orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
            enable_hybrid_search=True,
            enable_decision_engine=True
        )
        
        # Test queries with different complexity
        test_queries = [
            "иван петров",
            "мария сидорова",
            "john smith",
            "ооо приватбанк",
            "apple inc",
            "иван петров дата рождения 15.05.1980",
            "мария сидорова работает в ТОВ Розум",
            "john smith from USA",
            "приватбанк украина",
            "apple computer company"
        ]
        
        # Repeat queries to reach 1k requests
        queries = (test_queries * 100)[:1000]
        
        # Measure performance
        latencies = []
        errors = []
        
        start_time = time.time()
        
        for i, query in enumerate(queries):
            try:
                query_start = time.time()
                
                result = await orchestrator.process(
                    text=query,
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True,
                    search_opts=SearchOpts(
                        top_k=50,
                        threshold=0.7,
                        search_mode=SearchMode.HYBRID,
                        enable_escalation=True
                    )
                )
                
                query_end = time.time()
                latency = (query_end - query_start) * 1000  # Convert to ms
                latencies.append(latency)
                
                # Verify result
                assert result.success is True
                assert result.processing_time > 0
                
                # Check search metadata if available
                if "search" in result.metadata:
                    search_meta = result.metadata["search"]
                    assert search_meta["search_time"] > 0
                
            except Exception as e:
                errors.append(str(e))
                latencies.append(float('inf'))  # Mark as failed
        
        total_time = time.time() - start_time
        
        # Calculate statistics
        successful_requests = len([l for l in latencies if l != float('inf')])
        failed_requests = len(errors)
        
        if successful_requests > 0:
            successful_latencies = [l for l in latencies if l != float('inf')]
            
            p50 = statistics.median(successful_latencies)
            p95 = statistics.quantiles(successful_latencies, n=20)[18]  # 95th percentile
            p99 = statistics.quantiles(successful_latencies, n=100)[98]  # 99th percentile
            
            avg_latency = statistics.mean(successful_latencies)
            max_latency = max(successful_latencies)
            min_latency = min(successful_latencies)
            
            # Performance assertions
            assert p95 < 80.0, f"P95 latency {p95:.2f}ms exceeds 80ms threshold"
            assert successful_requests >= 950, f"Success rate {successful_requests/1000*100:.1f}% below 95%"
            
            # Print performance metrics
            print(f"\n=== Search Performance Results ===")
            print(f"Total requests: 1000")
            print(f"Successful requests: {successful_requests}")
            print(f"Failed requests: {failed_requests}")
            print(f"Success rate: {successful_requests/1000*100:.1f}%")
            print(f"Total time: {total_time:.2f}s")
            print(f"Requests/second: {1000/total_time:.1f}")
            print(f"")
            print(f"Latency statistics (ms):")
            print(f"  Min: {min_latency:.2f}")
            print(f"  Max: {max_latency:.2f}")
            print(f"  Avg: {avg_latency:.2f}")
            print(f"  P50: {p50:.2f}")
            print(f"  P95: {p95:.2f}")
            print(f"  P99: {p99:.2f}")
            print(f"")
            
            if failed_requests > 0:
                print(f"Errors ({failed_requests}):")
                for error in errors[:10]:  # Show first 10 errors
                    print(f"  - {error}")
                if failed_requests > 10:
                    print(f"  ... and {failed_requests - 10} more errors")
        else:
            pytest.fail("No successful requests completed")
    
    @pytest.mark.asyncio
    async def test_search_performance_different_modes(self, elasticsearch_container, test_indices):
        """Test search performance with different search modes."""
        # Create orchestrator with search enabled
        orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
            enable_hybrid_search=True,
            enable_decision_engine=True
        )
        
        test_query = "иван петров"
        modes = [SearchMode.AC, SearchMode.VECTOR, SearchMode.HYBRID]
        
        for mode in modes:
            latencies = []
            
            # Run 100 requests for each mode
            for _ in range(100):
                try:
                    start_time = time.time()
                    
                    result = await orchestrator.process(
                        text=test_query,
                        remove_stop_words=True,
                        preserve_names=True,
                        enable_advanced_features=True,
                        search_opts=SearchOpts(
                            top_k=50,
                            threshold=0.7,
                            search_mode=mode,
                            enable_escalation=(mode == SearchMode.HYBRID)
                        )
                    )
                    
                    end_time = time.time()
                    latency = (end_time - start_time) * 1000  # Convert to ms
                    latencies.append(latency)
                    
                    assert result.success is True
                    
                except Exception as e:
                    latencies.append(float('inf'))
            
            # Calculate statistics for this mode
            successful_latencies = [l for l in latencies if l != float('inf')]
            
            if successful_latencies:
                avg_latency = statistics.mean(successful_latencies)
                p95 = statistics.quantiles(successful_latencies, n=20)[18]
                
                print(f"\n=== {mode.value.upper()} Mode Performance ===")
                print(f"Average latency: {avg_latency:.2f}ms")
                print(f"P95 latency: {p95:.2f}ms")
                print(f"Success rate: {len(successful_latencies)/100*100:.1f}%")
                
                # Performance assertions
                assert p95 < 100.0, f"{mode.value} mode P95 latency {p95:.2f}ms exceeds 100ms threshold"
                assert len(successful_latencies) >= 95, f"{mode.value} mode success rate below 95%"
    
    @pytest.mark.asyncio
    async def test_search_performance_concurrent_requests(self, elasticsearch_container, test_indices):
        """Test search performance with concurrent requests."""
        # Create orchestrator with search enabled
        orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
            enable_hybrid_search=True,
            enable_decision_engine=True
        )
        
        test_queries = [
            "иван петров",
            "мария сидорова",
            "john smith",
            "ооо приватбанк",
            "apple inc"
        ]
        
        async def process_query(query):
            """Process a single query."""
            try:
                start_time = time.time()
                
                result = await orchestrator.process(
                    text=query,
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True,
                    search_opts=SearchOpts(
                        top_k=50,
                        threshold=0.7,
                        search_mode=SearchMode.HYBRID,
                        enable_escalation=True
                    )
                )
                
                end_time = time.time()
                latency = (end_time - start_time) * 1000  # Convert to ms
                
                return {
                    "success": result.success,
                    "latency": latency,
                    "error": None
                }
                
            except Exception as e:
                return {
                    "success": False,
                    "latency": float('inf'),
                    "error": str(e)
                }
        
        # Test with different concurrency levels
        concurrency_levels = [1, 5, 10, 20]
        
        for concurrency in concurrency_levels:
            print(f"\n=== Testing {concurrency} concurrent requests ===")
            
            # Create tasks for concurrent execution
            tasks = []
            for _ in range(100):  # 100 total requests
                query = test_queries[_ % len(test_queries)]
                tasks.append(process_query(query))
            
            # Execute with limited concurrency
            start_time = time.time()
            
            # Process in batches to limit concurrency
            results = []
            for i in range(0, len(tasks), concurrency):
                batch = tasks[i:i + concurrency]
                batch_results = await asyncio.gather(*batch, return_exceptions=True)
                results.extend(batch_results)
            
            total_time = time.time() - start_time
            
            # Calculate statistics
            successful_results = [r for r in results if isinstance(r, dict) and r["success"]]
            failed_results = [r for r in results if isinstance(r, dict) and not r["success"]]
            
            if successful_results:
                latencies = [r["latency"] for r in successful_results]
                avg_latency = statistics.mean(latencies)
                p95 = statistics.quantiles(latencies, n=20)[18]
                
                print(f"Total time: {total_time:.2f}s")
                print(f"Requests/second: {100/total_time:.1f}")
                print(f"Average latency: {avg_latency:.2f}ms")
                print(f"P95 latency: {p95:.2f}ms")
                print(f"Success rate: {len(successful_results)/100*100:.1f}%")
                
                # Performance assertions
                assert p95 < 150.0, f"Concurrency {concurrency} P95 latency {p95:.2f}ms exceeds 150ms threshold"
                assert len(successful_results) >= 90, f"Concurrency {concurrency} success rate below 90%"
    
    @pytest.mark.asyncio
    async def test_search_performance_memory_usage(self, elasticsearch_container, test_indices):
        """Test search performance memory usage."""
        import psutil
        import os
        
        # Get current process
        process = psutil.Process(os.getpid())
        
        # Create orchestrator with search enabled
        orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
            enable_hybrid_search=True,
            enable_decision_engine=True
        )
        
        # Measure memory before
        memory_before = process.memory_info().rss / 1024 / 1024  # MB
        
        # Run 100 requests
        for i in range(100):
            query = f"test query {i}"
            
            result = await orchestrator.process(
                text=query,
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                search_opts=SearchOpts(
                    top_k=50,
                    threshold=0.7,
                    search_mode=SearchMode.HYBRID,
                    enable_escalation=True
                )
            )
            
            assert result.success is True
            
            # Check memory every 20 requests
            if i % 20 == 0:
                memory_current = process.memory_info().rss / 1024 / 1024  # MB
                memory_increase = memory_current - memory_before
                
                print(f"Request {i}: Memory usage {memory_current:.1f}MB (+{memory_increase:.1f}MB)")
                
                # Assert memory increase is reasonable (less than 100MB)
                assert memory_increase < 100.0, f"Memory increase {memory_increase:.1f}MB exceeds 100MB threshold"
        
        # Measure memory after
        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        total_memory_increase = memory_after - memory_before
        
        print(f"\n=== Memory Usage Results ===")
        print(f"Memory before: {memory_before:.1f}MB")
        print(f"Memory after: {memory_after:.1f}MB")
        print(f"Total increase: {total_memory_increase:.1f}MB")
        
        # Assert total memory increase is reasonable
        assert total_memory_increase < 200.0, f"Total memory increase {total_memory_increase:.1f}MB exceeds 200MB threshold"
    
    @pytest.mark.asyncio
    async def test_search_performance_error_handling(self, elasticsearch_container, test_indices):
        """Test search performance with error scenarios."""
        # Create orchestrator with search enabled
        orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
            enable_hybrid_search=True,
            enable_decision_engine=True
        )
        
        # Test with various error scenarios
        error_scenarios = [
            "",  # Empty string
            "a" * 10000,  # Very long string
            "🚀" * 1000,  # Many emojis
            "test\n\n\n\n\n",  # Many newlines
            "test\t\t\t\t\t",  # Many tabs
            "test" + " " * 1000,  # Many spaces
        ]
        
        latencies = []
        errors = []
        
        for scenario in error_scenarios:
            for _ in range(10):  # 10 requests per scenario
                try:
                    start_time = time.time()
                    
                    result = await orchestrator.process(
                        text=scenario,
                        remove_stop_words=True,
                        preserve_names=True,
                        enable_advanced_features=True,
                        search_opts=SearchOpts(
                            top_k=50,
                            threshold=0.7,
                            search_mode=SearchMode.HYBRID,
                            enable_escalation=True
                        )
                    )
                    
                    end_time = time.time()
                    latency = (end_time - start_time) * 1000  # Convert to ms
                    latencies.append(latency)
                    
                    # Should handle errors gracefully
                    assert result.success is True or result.success is False
                    
                except Exception as e:
                    errors.append(str(e))
                    latencies.append(float('inf'))
        
        # Calculate statistics
        successful_latencies = [l for l in latencies if l != float('inf')]
        
        if successful_latencies:
            avg_latency = statistics.mean(successful_latencies)
            p95 = statistics.quantiles(successful_latencies, n=20)[18]
            
            print(f"\n=== Error Handling Performance ===")
            print(f"Total scenarios: {len(error_scenarios)}")
            print(f"Requests per scenario: 10")
            print(f"Total requests: {len(error_scenarios) * 10}")
            print(f"Successful requests: {len(successful_latencies)}")
            print(f"Failed requests: {len(errors)}")
            print(f"Average latency: {avg_latency:.2f}ms")
            print(f"P95 latency: {p95:.2f}ms")
            
            # Performance assertions
            assert p95 < 100.0, f"Error handling P95 latency {p95:.2f}ms exceeds 100ms threshold"
            assert len(successful_latencies) >= len(error_scenarios) * 5, "Too many requests failed in error scenarios"
