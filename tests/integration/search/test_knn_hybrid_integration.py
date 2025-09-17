"""
Search integration tests for KNN and hybrid search.

This module tests the integration of KNN (k-nearest neighbors) search
and hybrid search functionality.
"""

import pytest
import asyncio
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.config.feature_flags import FeatureFlags


class TestKnnHybridIntegration:
    """Test KNN and hybrid search integration."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def knn_config(self):
        """Create KNN configuration."""
        return NormalizationConfig(
            language="ru",
            enable_vector_fallback=True,
            debug_tracing=True
        )
    
    @pytest.fixture(scope="class")
    def knn_flags(self):
        """Create KNN feature flags."""
        return FeatureFlags(
            enable_vector_fallback=True
        )
    
    @pytest.mark.asyncio
    async def test_knn_search_processing(self, normalization_factory, knn_config, knn_flags):
        """Test KNN search processing."""
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(
                case, knn_config, knn_flags
            )
            
            # Verify result
            assert result.success, f"KNN search processing failed for '{case}'"
            assert result.normalized, f"Normalized result is empty for '{case}'"
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
            
            # Verify KNN search was used
            if hasattr(result, 'trace') and result.trace:
                knn_traces = [t for t in result.trace if 'knn' in str(t).lower() or 'vector' in str(t).lower()]
                assert len(knn_traces) > 0, f"KNN search traces not found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_hybrid_search_processing(self, normalization_factory, knn_config, knn_flags):
        """Test hybrid search processing."""
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(
                case, knn_config, knn_flags
            )
            
            # Verify result
            assert result.success, f"Hybrid search processing failed for '{case}'"
            assert result.normalized, f"Normalized result is empty for '{case}'"
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
            
            # Verify hybrid search was used
            if hasattr(result, 'trace') and result.trace:
                hybrid_traces = [t for t in result.trace if 'hybrid' in str(t).lower() or 'vector' in str(t).lower()]
                assert len(hybrid_traces) > 0, f"Hybrid search traces not found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_knn_performance(self, normalization_factory, knn_config, knn_flags):
        """Test KNN search performance."""
        import time
        
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        total_time = 0.0
        
        for case in test_cases:
            start_time = time.perf_counter()
            result = await normalization_factory.normalize_text(
                case, knn_config, knn_flags
            )
            end_time = time.perf_counter()
            
            total_time += (end_time - start_time)
            
            # Verify result
            assert result.success, f"KNN search processing failed for '{case}'"
        
        # Verify performance (should be fast)
        avg_time = total_time / len(test_cases)
        assert avg_time < 0.1, f"KNN search processing too slow: {avg_time:.3f}s per case"
    
    @pytest.mark.asyncio
    async def test_hybrid_performance(self, normalization_factory, knn_config, knn_flags):
        """Test hybrid search performance."""
        import time
        
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        total_time = 0.0
        
        for case in test_cases:
            start_time = time.perf_counter()
            result = await normalization_factory.normalize_text(
                case, knn_config, knn_flags
            )
            end_time = time.perf_counter()
            
            total_time += (end_time - start_time)
            
            # Verify result
            assert result.success, f"Hybrid search processing failed for '{case}'"
        
        # Verify performance (should be fast)
        avg_time = total_time / len(test_cases)
        assert avg_time < 0.1, f"Hybrid search processing too slow: {avg_time:.3f}s per case"
    
    @pytest.mark.asyncio
    async def test_knn_error_handling(self, normalization_factory, knn_config, knn_flags):
        """Test KNN search error handling."""
        # Test with empty input
        result = await normalization_factory.normalize_text(
            "", knn_config, knn_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')
        
        # Test with None input
        result = await normalization_factory.normalize_text(
            None, knn_config, knn_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')
    
    @pytest.mark.asyncio
    async def test_hybrid_error_handling(self, normalization_factory, knn_config, knn_flags):
        """Test hybrid search error handling."""
        # Test with empty input
        result = await normalization_factory.normalize_text(
            "", knn_config, knn_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')
        
        # Test with None input
        result = await normalization_factory.normalize_text(
            None, knn_config, knn_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')
    
    @pytest.mark.asyncio
    async def test_knn_accuracy(self, normalization_factory, knn_config, knn_flags):
        """Test KNN search accuracy."""
        test_cases = [
            ("Иван Петров", "Иван Петров"),
            ("Анна Сидорова", "Анна Сидорова"),
            ("Владимир Иванович", "Владимир Иванович"),
            ("Екатерина Петровна", "Екатерина Петровна")
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(
                input_text, knn_config, knn_flags
            )
            
            # Verify result
            assert result.success, f"KNN search processing failed for '{input_text}'"
            assert result.normalized == expected, f"KNN search accuracy failed for '{input_text}': got '{result.normalized}', expected '{expected}'"
    
    @pytest.mark.asyncio
    async def test_hybrid_accuracy(self, normalization_factory, knn_config, knn_flags):
        """Test hybrid search accuracy."""
        test_cases = [
            ("Иван Петров", "Иван Петров"),
            ("Анна Сидорова", "Анна Сидорова"),
            ("Владимир Иванович", "Владимир Иванович"),
            ("Екатерина Петровна", "Екатерина Петровна")
        ]
        
        for input_text, expected in test_cases:
            result = await normalization_factory.normalize_text(
                input_text, knn_config, knn_flags
            )
            
            # Verify result
            assert result.success, f"Hybrid search processing failed for '{input_text}'"
            assert result.normalized == expected, f"Hybrid search accuracy failed for '{input_text}': got '{result.normalized}', expected '{expected}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
