#!/usr/bin/env python3
"""
Performance tests for decomposed normalization pipeline.

These tests verify that the decomposed pipeline meets performance
requirements and doesn't significantly degrade compared to the
original implementation.
"""

import time
import asyncio
import pytest
from src.ai_service.layers.normalization.normalization_service_decomposed import NormalizationServiceDecomposed
from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestDecomposedPipelinePerformance:
    """Performance tests for decomposed normalization pipeline."""
    
    @pytest.fixture
    def decomposed_service(self):
        """Create decomposed normalization service."""
        return NormalizationServiceDecomposed()
    
    @pytest.fixture
    def original_service(self):
        """Create original normalization service."""
        return NormalizationService()
    
    @pytest.mark.asyncio
    async def test_single_request_performance(self, decomposed_service):
        """Test performance of single request."""
        text = "Иван Петров"
        
        start_time = time.perf_counter()
        result = await decomposed_service.normalize_async(text, language="ru")
        end_time = time.perf_counter()
        
        processing_time = end_time - start_time
        
        # Check that request completed successfully
        assert result.success
        assert processing_time > 0
        
        # Performance budget: total time should be reasonable
        assert processing_time < 0.1, f"Processing time {processing_time:.4f}s exceeds 100ms budget"
        
        # Check that pipeline metrics are present
        timing_trace = next(
            (entry for entry in result.trace if entry.role == "metrics"),
            None
        )
        assert timing_trace is not None
        
        # Check that timing information is present
        assert "total:" in timing_trace.output
        assert "stages:" in timing_trace.output
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self, decomposed_service):
        """Test performance of batch processing."""
        texts = [
            "Иван Петров",
            "Анна Сидорова",
            "Петр Иванович Козлов",
            "Мария-Анна Петрова-Сидорова",
            "И. П. Козлов"
        ] * 20  # 100 requests total
        
        start_time = time.perf_counter()
        
        # Process all requests
        tasks = [
            decomposed_service.normalize_async(text, language="ru")
            for text in texts
        ]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # Check that all requests completed successfully
        assert all(result.success for result in results)
        
        # Performance budget: should process 100 requests in reasonable time
        assert total_time < 5.0, f"Batch processing time {total_time:.4f}s exceeds 5s budget"
        
        # Calculate average time per request
        avg_time_per_request = total_time / len(texts)
        assert avg_time_per_request < 0.05, f"Average time per request {avg_time_per_request:.4f}s exceeds 50ms budget"
    
    @pytest.mark.asyncio
    async def test_complex_text_performance(self, decomposed_service):
        """Test performance with complex text."""
        text = "ТОВ ПРИВАТБАНК директор Иван Петрович Сидоров и главный бухгалтер Анна-Мария Петрова-Сидорова"
        
        start_time = time.perf_counter()
        result = await decomposed_service.normalize_async(text, language="ru")
        end_time = time.perf_counter()
        
        processing_time = end_time - start_time
        
        # Check that request completed successfully
        assert result.success
        assert processing_time > 0
        
        # Performance budget: complex text should still be processed quickly
        assert processing_time < 0.2, f"Complex text processing time {processing_time:.4f}s exceeds 200ms budget"
        
        # Check that organization tokens are excluded
        assert "ТОВ" not in result.normalized
        assert "ПРИВАТБАНК" not in result.normalized
        assert "директор" not in result.normalized
        assert "главный" not in result.normalized
        assert "бухгалтер" not in result.normalized
        
        # Check that person names are included
        assert "Иван Петрович Сидоров" in result.normalized
        assert "Анна-Мария Петрова-Сидорова" in result.normalized
    
    @pytest.mark.asyncio
    async def test_performance_comparison(self, decomposed_service, original_service):
        """Test that decomposed service performance is comparable to original."""
        text = "Иван Петров"
        
        # Test decomposed service
        decomposed_start = time.perf_counter()
        decomposed_result = await decomposed_service.normalize_async(text, language="ru")
        decomposed_time = time.perf_counter() - decomposed_start
        
        # Test original service
        original_start = time.perf_counter()
        original_result = await original_service.normalize_async(text, language="ru")
        original_time = time.perf_counter() - original_start
        
        # Both should succeed
        assert decomposed_result.success
        assert original_result.success
        
        # Decomposed service should not be significantly slower
        # Allow up to 2x slower for the decomposed version
        assert decomposed_time <= original_time * 2, (
            f"Decomposed service {decomposed_time:.4f}s is more than 2x slower than original {original_time:.4f}s"
        )
        
        # Results should be equivalent
        assert decomposed_result.normalized == original_result.normalized
    
    @pytest.mark.asyncio
    async def test_memory_usage(self, decomposed_service):
        """Test that memory usage is reasonable."""
        import psutil
        import os
        
        # Get initial memory usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Process many requests
        texts = [f"Иван Петров {i}" for i in range(100)]
        
        for text in texts:
            result = await decomposed_service.normalize_async(text, language="ru")
            assert result.success
        
        # Get final memory usage
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB)
        assert memory_increase < 50 * 1024 * 1024, f"Memory increase {memory_increase / 1024 / 1024:.2f}MB exceeds 50MB budget"
    
    @pytest.mark.asyncio
    async def test_p95_metrics(self, decomposed_service):
        """Test that p95 metrics are tracked correctly."""
        # Process many requests to get meaningful statistics
        texts = [f"Иван Петров {i}" for i in range(50)]
        
        for text in texts:
            result = await decomposed_service.normalize_async(text, language="ru")
            assert result.success
        
        # Get statistics
        stats = decomposed_service.get_stats()
        
        # Check that stage statistics are present
        assert 'stage_stats' in stats
        stage_stats = stats['stage_stats']
        
        for stage in ['tokenize', 'role_tag', 'morphology', 'assemble']:
            assert stage in stage_stats
            stage_stat = stage_stats[stage]
            
            # Check that p95 time is reasonable
            assert stage_stat['p95_time'] < 0.01, f"P95 time for {stage} {stage_stat['p95_time']:.4f}s exceeds 10ms budget"
            
            # Check that we have enough samples
            assert stage_stat['count'] >= 50, f"Not enough samples for {stage}: {stage_stat['count']}"
    
    def test_component_initialization_performance(self):
        """Test that component initialization is fast."""
        start_time = time.perf_counter()
        service = NormalizationServiceDecomposed()
        end_time = time.perf_counter()
        
        initialization_time = end_time - start_time
        
        # Initialization should be fast (less than 1 second)
        assert initialization_time < 1.0, f"Initialization time {initialization_time:.4f}s exceeds 1s budget"
    
    @pytest.mark.asyncio
    async def test_concurrent_requests_performance(self, decomposed_service):
        """Test performance with concurrent requests."""
        text = "Иван Петров"
        num_concurrent = 10
        
        start_time = time.perf_counter()
        
        # Process concurrent requests
        tasks = [
            decomposed_service.normalize_async(text, language="ru")
            for _ in range(num_concurrent)
        ]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time = end_time - start_time
        
        # All requests should succeed
        assert all(result.success for result in results)
        
        # Concurrent processing should be efficient
        assert total_time < 1.0, f"Concurrent processing time {total_time:.4f}s exceeds 1s budget"
        
        # Average time per request should be reasonable
        avg_time = total_time / num_concurrent
        assert avg_time < 0.1, f"Average concurrent time {avg_time:.4f}s exceeds 100ms budget"
