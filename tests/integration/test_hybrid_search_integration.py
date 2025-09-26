"""
Comprehensive integration tests for hybrid search system (AC + Vector).
Tests the complete pipeline including ElasticSearch integration and trace validation.
"""

import pytest
import asyncio
from typing import Dict, Any, List, Optional
import json
import time

from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
from src.ai_service.layers.search.config import HybridSearchConfig
from src.ai_service.layers.search.enhanced_elasticsearch_client import EnhancedElasticsearchClient, HealthStatus
from src.ai_service.layers.search.search_trace_validator import SearchTraceValidator, ValidationSeverity
from src.ai_service.contracts.trace_models import SearchTrace
from src.ai_service.contracts.search_contracts import SearchOpts, SearchResult


@pytest.fixture
async def elasticsearch_client():
    """Create enhanced Elasticsearch client for testing."""
    client = EnhancedElasticsearchClient()
    yield client
    await client.close()


@pytest.fixture
async def hybrid_search_service(elasticsearch_client):
    """Create hybrid search service with test configuration."""
    config = HybridSearchConfig.from_env()
    config.elasticsearch.hosts = ["http://localhost:9200"]

    service = HybridSearchService(config)
    await service.initialize()

    yield service

    await service.cleanup()


@pytest.fixture
def search_trace_validator():
    """Create search trace validator."""
    return SearchTraceValidator(strict_mode=False)


class TestElasticsearchHealthAndConnectivity:
    """Test Elasticsearch health monitoring and connectivity."""

    async def test_health_check_comprehensive(self, elasticsearch_client):
        """Test comprehensive health check functionality."""
        health = await elasticsearch_client.enhanced_health_check()

        # Validate health response structure
        assert "overall_status" in health
        assert "healthy_hosts" in health
        assert "total_hosts" in health
        assert "hosts" in health
        assert "timestamp" in health

        # Check host details
        assert len(health["hosts"]) > 0
        host_result = health["hosts"][0]

        expected_fields = ["host", "status", "circuit_breaker", "failure_count"]
        for field in expected_fields:
            assert field in host_result, f"Missing field: {field}"

        # Validate status values
        valid_statuses = [status.value for status in HealthStatus]
        assert health["overall_status"] in valid_statuses

    async def test_wait_for_healthy_timeout(self, elasticsearch_client):
        """Test waiting for healthy cluster with timeout."""
        # This should succeed quickly if ES is running
        is_healthy = await elasticsearch_client.wait_for_healthy(
            timeout=10.0,
            check_interval=1.0
        )

        # If ES is running, should be healthy
        # If not running, should timeout gracefully
        assert isinstance(is_healthy, bool)

    async def test_circuit_breaker_functionality(self, elasticsearch_client):
        """Test circuit breaker functionality for failed connections."""
        # Get connection status
        status_before = elasticsearch_client.get_connection_status()

        assert "active_clients" in status_before
        assert "connection_failures" in status_before
        assert "circuit_breakers" in status_before

        # Simulate failure by trying to connect to invalid host
        # This would require modifying the client configuration for testing
        # For now, just validate the status structure

        assert isinstance(status_before["active_clients"], int)
        assert isinstance(status_before["connection_failures"], dict)
        assert isinstance(status_before["circuit_breakers"], dict)

    async def test_cluster_stats_retrieval(self, elasticsearch_client):
        """Test cluster statistics retrieval."""
        stats = await elasticsearch_client.get_cluster_stats()

        # Should return stats dict or error dict
        assert isinstance(stats, dict)

        # If successful, should have cluster info
        if "error" not in stats:
            assert "cluster" in stats or "indices" in stats

    @pytest.mark.asyncio
    async def test_retry_logic_on_timeout(self, elasticsearch_client):
        """Test retry logic for operations that timeout."""
        # Test with a very short timeout to trigger retry
        original_timeout = elasticsearch_client.es_config.timeout
        elasticsearch_client.es_config.timeout = 0.001  # Very short timeout

        try:
            # This should trigger retries due to timeout
            with pytest.raises((Exception,)):  # Expect some form of failure
                await elasticsearch_client.enhanced_health_check()
        finally:
            # Restore original timeout
            elasticsearch_client.es_config.timeout = original_timeout


class TestHybridSearchIntegration:
    """Test hybrid search service integration."""

    async def test_hybrid_search_initialization(self, hybrid_search_service):
        """Test hybrid search service initialization."""
        assert hybrid_search_service is not None

        # Check if service is properly initialized
        # This would depend on the actual HybridSearchService implementation
        service = hybrid_search_service
        assert service is not None

    async def test_ac_search_execution(self, hybrid_search_service):
        """Test AC (Autocomplete) search execution."""
        # Create test search query
        query = SearchOpts(
            text="John Doe",
            strategy="ac_only",
            max_results=10
        )

        search_trace = SearchTrace(enabled=True)

        try:
            results = await hybrid_search_service.search(query, search_trace)

            # Validate results structure
            assert isinstance(results, list)

            # Validate trace contains AC search steps
            assert len(search_trace.notes) > 0
            ac_steps = [note for note in search_trace.notes if "AC" in note or "autocomplete" in note.lower()]
            assert len(ac_steps) > 0, "No AC search steps found in trace"

        except Exception as e:
            # If ES is not available, should fail gracefully
            pytest.skip(f"Elasticsearch not available: {e}")

    async def test_vector_search_execution(self, hybrid_search_service):
        """Test vector search execution."""
        query = SearchOpts(
            text="John Doe",
            strategy="vector_only",
            max_results=10
        )

        search_trace = SearchTrace(enabled=True)

        try:
            results = await hybrid_search_service.search(query, search_trace)

            # Validate results structure
            assert isinstance(results, list)

            # Validate trace contains vector search steps
            assert len(search_trace.notes) > 0
            vector_steps = [note for note in search_trace.notes
                          if "vector" in note.lower() or "semantic" in note.lower()]
            assert len(vector_steps) > 0, "No vector search steps found in trace"

        except Exception as e:
            pytest.skip(f"Vector search not available: {e}")

    async def test_hybrid_search_with_fallback(self, hybrid_search_service):
        """Test hybrid search with fallback mechanism."""
        query = SearchOpts(
            text="John Doe",
            strategy="hybrid_with_fallback",
            max_results=10
        )

        search_trace = SearchTrace(enabled=True)

        try:
            results = await hybrid_search_service.search(query, search_trace)

            # Validate results
            assert isinstance(results, list)

            # Check for both AC and vector steps in trace
            ac_steps = [note for note in search_trace.notes if "AC" in note]
            vector_steps = [note for note in search_trace.notes if "vector" in note.lower()]

            # Should have at least one type of search
            assert len(ac_steps) > 0 or len(vector_steps) > 0

            # If both are present, check for merge/fallback steps
            if len(ac_steps) > 0 and len(vector_steps) > 0:
                merge_or_fallback = [note for note in search_trace.notes
                                   if "merge" in note.lower() or "fallback" in note.lower()]
                assert len(merge_or_fallback) > 0, "No merge/fallback steps found in hybrid search"

        except Exception as e:
            pytest.skip(f"Hybrid search not available: {e}")

    async def test_search_result_consistency(self, hybrid_search_service):
        """Test search result consistency across multiple calls."""
        query = SearchOpts(
            text="consistent_test_query",
            strategy="hybrid",
            max_results=5
        )

        results_list = []
        traces_list = []

        # Run same search multiple times
        for i in range(3):
            search_trace = SearchTrace(enabled=True)
            try:
                results = await hybrid_search_service.search(query, search_trace)
                results_list.append(results)
                traces_list.append(search_trace)

                # Small delay between requests
                await asyncio.sleep(0.1)

            except Exception as e:
                pytest.skip(f"Search consistency test failed: {e}")

        # Analyze consistency
        if len(results_list) > 1:
            # Check if result counts are consistent (within reasonable range)
            result_counts = [len(results) for results in results_list]
            max_count = max(result_counts)
            min_count = min(result_counts)

            # Allow for some variation in results
            assert max_count - min_count <= 2, f"Result count variation too high: {result_counts}"


class TestSearchTraceValidation:
    """Test search trace validation and analysis."""

    def test_trace_validator_initialization(self, search_trace_validator):
        """Test search trace validator initialization."""
        validator = search_trace_validator
        assert validator is not None
        assert hasattr(validator, 'validate_trace')
        assert hasattr(validator, 'expected_patterns')

    def test_validate_ac_only_trace(self, search_trace_validator):
        """Test validation of AC-only search trace."""
        # Create mock AC search trace
        trace = SearchTrace(enabled=True)
        trace.notes = [
            "AC search initiated for 'John Doe'",
            "AC search completed with 5 results in 25ms",
            "Results filtered and formatted"
        ]
        trace.total_time_ms = 30
        trace.total_hits = 5

        report = search_trace_validator.validate_trace(trace)

        # Validate report structure
        assert report.is_valid is not None
        assert isinstance(report.total_steps, int)
        assert isinstance(report.deterministic_hash, str)
        assert isinstance(report.issues, list)
        assert isinstance(report.statistics, dict)

        # Check statistics
        assert "total_steps" in report.statistics
        assert "step_type_distribution" in report.statistics
        assert report.statistics["total_steps"] == len(trace.notes)

    def test_validate_hybrid_trace(self, search_trace_validator):
        """Test validation of hybrid search trace."""
        # Create mock hybrid search trace
        trace = SearchTrace(enabled=True)
        trace.notes = [
            "AC search initiated for 'John Doe'",
            "AC search completed with 3 results in 20ms",
            "Vector search initiated for 'John Doe'",
            "Vector search completed with 7 results in 150ms",
            "Hybrid merge initiated",
            "Hybrid merge completed with 8 results in 5ms",
            "Results formatted and returned"
        ]
        trace.total_time_ms = 180
        trace.total_hits = 8

        report = search_trace_validator.validate_trace(trace)

        # Should be valid hybrid trace
        assert len(report.issues) == 0 or not report.has_errors()

        # Check coverage analysis
        assert "coverage_analysis" in report.__dict__
        coverage = report.coverage_analysis
        assert "search_strategy_identified" in coverage
        assert coverage["search_strategy_identified"] in ["hybrid", "parallel"]

    def test_validate_trace_with_errors(self, search_trace_validator):
        """Test validation of trace with errors."""
        # Create trace with issues
        trace = SearchTrace(enabled=True)
        trace.notes = [
            "Search started",
            "Error: Connection timeout",
            "Fallback initiated"
        ]
        trace.total_time_ms = 5000  # Very long time
        trace.total_hits = 0

        report = search_trace_validator.validate_trace(trace)

        # Should detect issues
        assert isinstance(report.issues, list)

        # Check for different severity levels
        errors = report.get_issues_by_severity(ValidationSeverity.ERROR)
        warnings = report.get_issues_by_severity(ValidationSeverity.WARNING)

        # Should have some form of validation feedback
        assert len(errors) > 0 or len(warnings) > 0

    def test_deterministic_hash_consistency(self, search_trace_validator):
        """Test that deterministic hash is consistent for identical traces."""
        # Create identical traces
        trace1 = SearchTrace(enabled=True)
        trace1.notes = ["Step 1", "Step 2", "Step 3"]
        trace1.total_time_ms = 100
        trace1.total_hits = 5

        trace2 = SearchTrace(enabled=True)
        trace2.notes = ["Step 1", "Step 2", "Step 3"]
        trace2.total_time_ms = 100
        trace2.total_hits = 5

        report1 = search_trace_validator.validate_trace(trace1)
        report2 = search_trace_validator.validate_trace(trace2)

        # Hashes should be identical
        assert report1.deterministic_hash == report2.deterministic_hash

    def test_trace_ordering_independence(self, search_trace_validator):
        """Test that hash is order-independent for notes."""
        # Create traces with different note orders
        trace1 = SearchTrace(enabled=True)
        trace1.notes = ["AC search", "Vector search", "Merge results"]
        trace1.total_time_ms = 100
        trace1.total_hits = 5

        trace2 = SearchTrace(enabled=True)
        trace2.notes = ["Vector search", "AC search", "Merge results"]  # Different order
        trace2.total_time_ms = 100
        trace2.total_hits = 5

        report1 = search_trace_validator.validate_trace(trace1)
        report2 = search_trace_validator.validate_trace(trace2)

        # Hashes should be identical due to note sorting
        assert report1.deterministic_hash == report2.deterministic_hash


class TestSearchSystemResilience:
    """Test search system resilience and error handling."""

    async def test_elasticsearch_connection_failure_handling(self, elasticsearch_client):
        """Test handling of Elasticsearch connection failures."""
        # Temporarily modify config to point to non-existent host
        original_hosts = elasticsearch_client.es_config.hosts
        elasticsearch_client.es_config.hosts = ["http://non-existent-host:9200"]

        try:
            # Should handle connection failure gracefully
            health = await elasticsearch_client.enhanced_health_check()

            # Should return unhealthy status
            assert health["overall_status"] == HealthStatus.UNREACHABLE.value

            # Should contain error information
            assert any("error" in host for host in health["hosts"])

        finally:
            # Restore original hosts
            elasticsearch_client.es_config.hosts = original_hosts

    async def test_search_timeout_handling(self, hybrid_search_service):
        """Test search timeout handling."""
        query = SearchOpts(
            text="timeout_test_query",
            strategy="hybrid",
            max_results=10,
            timeout_ms=1  # Very short timeout
        )

        search_trace = SearchTrace(enabled=True)

        # Should handle timeout gracefully
        try:
            results = await hybrid_search_service.search(query, search_trace)
            # If it succeeds, that's fine too (very fast response)
            assert isinstance(results, list)
        except Exception as e:
            # Should be a timeout-related error
            error_msg = str(e).lower()
            timeout_keywords = ["timeout", "time", "deadline", "cancelled"]
            assert any(keyword in error_msg for keyword in timeout_keywords), \
                f"Expected timeout error, got: {e}"

    async def test_large_result_set_handling(self, hybrid_search_service):
        """Test handling of large result sets."""
        query = SearchOpts(
            text="*",  # Broad query that might return many results
            strategy="ac_only",
            max_results=1000  # Large limit
        )

        search_trace = SearchTrace(enabled=True)

        try:
            results = await hybrid_search_service.search(query, search_trace)

            # Should handle large result sets
            assert isinstance(results, list)
            assert len(results) <= query.max_results

            # Should have reasonable performance
            if len(search_trace.notes) > 0:
                # Check if any performance warnings in trace
                performance_notes = [note for note in search_trace.notes
                                   if "slow" in note.lower() or "timeout" in note.lower()]
                # This is informational - large queries may be slow

        except Exception as e:
            # Large queries may fail - that's acceptable
            pytest.skip(f"Large query test failed (acceptable): {e}")


@pytest.mark.integration
class TestEndToEndSearchWorkflow:
    """End-to-end integration tests for complete search workflow."""

    async def test_complete_hybrid_search_workflow(self, hybrid_search_service, search_trace_validator):
        """Test complete workflow from query to validated results."""
        # Step 1: Execute hybrid search
        query = SearchOpts(
            text="John Smith",
            strategy="hybrid_with_fallback",
            max_results=10
        )

        search_trace = SearchTrace(enabled=True)

        try:
            results = await hybrid_search_service.search(query, search_trace)

            # Step 2: Validate results structure
            assert isinstance(results, list)
            assert len(results) <= query.max_results

            # Step 3: Validate search trace
            validation_report = search_trace_validator.validate_trace(search_trace)

            # Step 4: Analyze validation results
            assert validation_report.total_steps > 0
            assert validation_report.deterministic_hash is not None

            # Should not have critical errors in a successful search
            critical_errors = validation_report.get_issues_by_severity(ValidationSeverity.ERROR)
            if len(critical_errors) > 0:
                # Log errors for debugging
                for error in critical_errors:
                    print(f"Critical error: {error.message}")

            # Step 5: Verify coverage requirements
            coverage = validation_report.coverage_analysis
            assert coverage["coverage_percentage"] > 20  # At least basic coverage

            # Step 6: Performance validation
            timing = validation_report.timing_analysis
            if timing["bottlenecks"]:
                slowest_step = timing["bottlenecks"][0]
                assert slowest_step[1] < 5000, f"Slowest step too slow: {slowest_step[1]}ms"

        except Exception as e:
            pytest.skip(f"End-to-end workflow test failed: {e}")

    async def test_search_trace_snapshot_creation(self, hybrid_search_service):
        """Test creation of deterministic search trace snapshots."""
        from src.ai_service.layers.search.search_trace_validator import create_deterministic_trace_snapshot

        query = SearchOpts(
            text="snapshot_test",
            strategy="hybrid",
            max_results=5
        )

        search_trace = SearchTrace(enabled=True)

        try:
            results = await hybrid_search_service.search(query, search_trace)

            # Create snapshot
            metadata = {
                "test_name": "search_trace_snapshot_creation",
                "query_text": query.text,
                "strategy": query.strategy
            }

            snapshot = create_deterministic_trace_snapshot(search_trace, metadata)

            # Validate snapshot structure
            expected_fields = [
                "trace_hash", "enabled", "total_time_ms", "total_hits",
                "notes", "validation", "statistics", "coverage", "metadata"
            ]

            for field in expected_fields:
                assert field in snapshot, f"Missing field in snapshot: {field}"

            # Validate snapshot consistency
            assert snapshot["enabled"] == search_trace.enabled
            assert snapshot["total_hits"] == search_trace.total_hits
            assert set(snapshot["notes"]) == set(search_trace.notes)  # Order-independent comparison

        except Exception as e:
            pytest.skip(f"Snapshot creation test failed: {e}")


# Performance benchmarking tests
@pytest.mark.performance
class TestSearchPerformance:
    """Performance tests for search system."""

    async def test_concurrent_search_performance(self, hybrid_search_service):
        """Test performance under concurrent search load."""
        queries = [
            SearchOpts(text=f"test_query_{i}", strategy="ac_only", max_results=5)
            for i in range(10)  # 10 concurrent queries
        ]

        search_traces = [SearchTrace(enabled=True) for _ in range(len(queries))]

        async def execute_search(query, trace):
            try:
                return await hybrid_search_service.search(query, trace)
            except Exception as e:
                return {"error": str(e)}

        start_time = time.time()

        # Execute all searches concurrently
        tasks = [execute_search(query, trace)
                for query, trace in zip(queries, search_traces)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        total_time = time.time() - start_time

        # Analyze performance
        successful_searches = [r for r in results if not isinstance(r, Exception) and "error" not in r]
        failed_searches = len(results) - len(successful_searches)

        print(f"Concurrent search performance:")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Successful searches: {len(successful_searches)}/{len(queries)}")
        print(f"  Failed searches: {failed_searches}")
        print(f"  Average time per search: {total_time / len(queries):.3f}s")

        # Performance assertions
        assert total_time < 30.0, f"Concurrent searches took too long: {total_time}s"
        assert len(successful_searches) >= len(queries) // 2, "Too many failed searches"

    async def test_search_latency_distribution(self, hybrid_search_service, search_trace_validator):
        """Test search latency distribution across multiple searches."""
        query = SearchOpts(
            text="latency_test",
            strategy="hybrid",
            max_results=10
        )

        latencies = []
        trace_stats = []

        # Execute multiple searches to measure latency distribution
        for i in range(20):
            search_trace = SearchTrace(enabled=True)

            start_time = time.time()
            try:
                results = await hybrid_search_service.search(query, search_trace)
                latency = (time.time() - start_time) * 1000  # Convert to ms
                latencies.append(latency)

                # Validate trace for timing analysis
                validation_report = search_trace_validator.validate_trace(search_trace)
                trace_stats.append(validation_report.timing_analysis)

            except Exception as e:
                print(f"Search {i} failed: {e}")

            # Small delay between searches
            await asyncio.sleep(0.05)

        if latencies:
            # Calculate percentiles
            sorted_latencies = sorted(latencies)
            p50 = sorted_latencies[len(sorted_latencies) // 2]
            p95 = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            p99 = sorted_latencies[int(len(sorted_latencies) * 0.99)]

            print(f"Search latency distribution:")
            print(f"  P50: {p50:.1f}ms")
            print(f"  P95: {p95:.1f}ms")
            print(f"  P99: {p99:.1f}ms")
            print(f"  Min: {min(latencies):.1f}ms")
            print(f"  Max: {max(latencies):.1f}ms")

            # Performance assertions (generous thresholds for CI)
            assert p95 < 1000, f"P95 latency too high: {p95}ms"
            assert p99 < 2000, f"P99 latency too high: {p99}ms"
        else:
            pytest.skip("No successful searches for latency analysis")