"""
Search integration tests for AC tier 0/1 and vector fallback.

This module tests the integration of AC (Autocomplete) tier 0/1 processing
and vector fallback functionality.
"""

import pytest
import asyncio
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.config.feature_flags import FeatureFlags


class TestAcTierIntegration:
    """Test AC tier 0/1 integration."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def ac_tier_config(self):
        """Create AC tier configuration."""
        return NormalizationConfig(
            language="ru",
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            debug_tracing=True
        )
    
    @pytest.fixture(scope="class")
    def ac_tier_flags(self):
        """Create AC tier feature flags."""
        return FeatureFlags(
            enable_ac_tier0=True,
            enable_vector_fallback=True
        )
    
    @pytest.mark.asyncio
    async def test_ac_tier0_processing(self, normalization_factory, ac_tier_config, ac_tier_flags):
        """Test AC tier 0 processing."""
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(
                case, ac_tier_config, ac_tier_flags
            )
            
            # Verify result
            assert result.success, f"AC tier 0 processing failed for '{case}'"
            assert result.normalized, f"Normalized result is empty for '{case}'"
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
            
            # Verify AC tier 0 was used
            if hasattr(result, 'trace') and result.trace:
                ac_tier_traces = [t for t in result.trace if 'ac_tier' in str(t).lower()]
                assert len(ac_tier_traces) > 0, f"AC tier 0 traces not found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_vector_fallback_processing(self, normalization_factory, ac_tier_config, ac_tier_flags):
        """Test vector fallback processing."""
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(
                case, ac_tier_config, ac_tier_flags
            )
            
            # Verify result
            assert result.success, f"Vector fallback processing failed for '{case}'"
            assert result.normalized, f"Normalized result is empty for '{case}'"
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
            
            # Verify vector fallback was used
            if hasattr(result, 'trace') and result.trace:
                vector_traces = [t for t in result.trace if 'vector' in str(t).lower()]
                assert len(vector_traces) > 0, f"Vector fallback traces not found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_ac_tier_hybrid_processing(self, normalization_factory, ac_tier_config, ac_tier_flags):
        """Test hybrid AC tier + vector fallback processing."""
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(
                case, ac_tier_config, ac_tier_flags
            )
            
            # Verify result
            assert result.success, f"Hybrid processing failed for '{case}'"
            assert result.normalized, f"Normalized result is empty for '{case}'"
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
            
            # Verify both AC tier and vector fallback were used
            if hasattr(result, 'trace') and result.trace:
                ac_tier_traces = [t for t in result.trace if 'ac_tier' in str(t).lower()]
                vector_traces = [t for t in result.trace if 'vector' in str(t).lower()]
                
                # At least one should be present
                assert len(ac_tier_traces) > 0 or len(vector_traces) > 0, \
                    f"Neither AC tier nor vector fallback traces found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_ac_tier_performance(self, normalization_factory, ac_tier_config, ac_tier_flags):
        """Test AC tier performance."""
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
                case, ac_tier_config, ac_tier_flags
            )
            end_time = time.perf_counter()
            
            total_time += (end_time - start_time)
            
            # Verify result
            assert result.success, f"AC tier processing failed for '{case}'"
        
        # Verify performance (should be fast)
        avg_time = total_time / len(test_cases)
        assert avg_time < 0.1, f"AC tier processing too slow: {avg_time:.3f}s per case"
    
    @pytest.mark.asyncio
    async def test_vector_fallback_performance(self, normalization_factory, ac_tier_config, ac_tier_flags):
        """Test vector fallback performance."""
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
                case, ac_tier_config, ac_tier_flags
            )
            end_time = time.perf_counter()
            
            total_time += (end_time - start_time)
            
            # Verify result
            assert result.success, f"Vector fallback processing failed for '{case}'"
        
        # Verify performance (should be fast)
        avg_time = total_time / len(test_cases)
        assert avg_time < 0.1, f"Vector fallback processing too slow: {avg_time:.3f}s per case"
    
    @pytest.mark.asyncio
    async def test_ac_tier_error_handling(self, normalization_factory, ac_tier_config, ac_tier_flags):
        """Test AC tier error handling."""
        # Test with empty input
        result = await normalization_factory.normalize_text(
            "", ac_tier_config, ac_tier_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')
        
        # Test with None input
        result = await normalization_factory.normalize_text(
            None, ac_tier_config, ac_tier_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')
    
    @pytest.mark.asyncio
    async def test_vector_fallback_error_handling(self, normalization_factory, ac_tier_config, ac_tier_flags):
        """Test vector fallback error handling."""
        # Test with empty input
        result = await normalization_factory.normalize_text(
            "", ac_tier_config, ac_tier_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')
        
        # Test with None input
        result = await normalization_factory.normalize_text(
            None, ac_tier_config, ac_tier_flags
        )
        
        # Should handle gracefully
        assert result is not None
        assert hasattr(result, 'success')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
