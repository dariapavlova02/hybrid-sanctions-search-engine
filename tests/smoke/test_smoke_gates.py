"""
Smoke tests for normalization gates.

This module tests basic functionality to ensure the system is working
correctly after deployment.
"""

import pytest
import asyncio
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.config.feature_flags import FeatureFlags


class TestSmokeGates:
    """Test smoke gates for normalization."""
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def test_config(self):
        """Create test configuration."""
        return NormalizationConfig(
            language="ru",
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True,
            debug_tracing=True
        )
    
    @pytest.fixture(scope="class")
    def test_flags(self):
        """Create test feature flags."""
        return FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True
        )
    
    @pytest.mark.asyncio
    async def test_basic_russian_normalization(self, normalization_factory, test_config, test_flags):
        """Test basic Russian normalization."""
        test_cases = [
            "Иван Петров",
            "Анна Сидорова",
            "Владимир Иванович",
            "Екатерина Петровна"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{case}'"
            assert hasattr(result, 'success'), f"Result missing success attribute for '{case}'"
            assert hasattr(result, 'normalized'), f"Result missing normalized attribute for '{case}'"
            assert hasattr(result, 'tokens'), f"Result missing tokens attribute for '{case}'"
            
            # Should be successful
            assert result.success, f"Normalization failed for '{case}': {result.errors}"
            
            # Should have normalized text
            assert result.normalized, f"Normalized text is empty for '{case}'"
            
            # Should have tokens
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_basic_ukrainian_normalization(self, normalization_factory, test_config, test_flags):
        """Test basic Ukrainian normalization."""
        uk_config = NormalizationConfig(
            language="uk",
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True,
            debug_tracing=True
        )
        
        test_cases = [
            "Олександр Коваленко",
            "Наталія Шевченко",
            "Михайло Іванович",
            "Оксана Петрівна"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(case, uk_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{case}'"
            assert hasattr(result, 'success'), f"Result missing success attribute for '{case}'"
            assert hasattr(result, 'normalized'), f"Result missing normalized attribute for '{case}'"
            assert hasattr(result, 'tokens'), f"Result missing tokens attribute for '{case}'"
            
            # Should be successful
            assert result.success, f"Normalization failed for '{case}': {result.errors}"
            
            # Should have normalized text
            assert result.normalized, f"Normalized text is empty for '{case}'"
            
            # Should have tokens
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_basic_english_normalization(self, normalization_factory, test_config, test_flags):
        """Test basic English normalization."""
        en_config = NormalizationConfig(
            language="en",
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True,
            debug_tracing=True
        )
        
        test_cases = [
            "John Smith",
            "Jane Doe",
            "Dr. Robert Johnson",
            "Mary O'Connor"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(case, en_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{case}'"
            assert hasattr(result, 'success'), f"Result missing success attribute for '{case}'"
            assert hasattr(result, 'normalized'), f"Result missing normalized attribute for '{case}'"
            assert hasattr(result, 'tokens'), f"Result missing tokens attribute for '{case}'"
            
            # Should be successful
            assert result.success, f"Normalization failed for '{case}': {result.errors}"
            
            # Should have normalized text
            assert result.normalized, f"Normalized text is empty for '{case}'"
            
            # Should have tokens
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_ascii_fastpath_smoke(self, normalization_factory, test_flags):
        """Test ASCII fastpath smoke."""
        ascii_config = NormalizationConfig(
            language="en",
            ascii_fastpath=True,
            enable_advanced_features=False,
            enable_morphology=False,
            debug_tracing=True
        )
        
        test_cases = [
            "John Smith",
            "Jane Doe",
            "Dr. Robert Johnson",
            "Mary O'Connor"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(case, ascii_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{case}'"
            assert hasattr(result, 'success'), f"Result missing success attribute for '{case}'"
            assert hasattr(result, 'normalized'), f"Result missing normalized attribute for '{case}'"
            assert hasattr(result, 'tokens'), f"Result missing tokens attribute for '{case}'"
            
            # Should be successful
            assert result.success, f"ASCII fastpath failed for '{case}': {result.errors}"
            
            # Should have normalized text
            assert result.normalized, f"Normalized text is empty for '{case}'"
            
            # Should have tokens
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_feature_flags_smoke(self, normalization_factory, test_config, test_flags):
        """Test feature flags smoke."""
        test_cases = [
            "Иван Петров",
            "John Smith",
            "Олександр Коваленко"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{case}'"
            assert hasattr(result, 'success'), f"Result missing success attribute for '{case}'"
            assert hasattr(result, 'normalized'), f"Result missing normalized attribute for '{case}'"
            assert hasattr(result, 'tokens'), f"Result missing tokens attribute for '{case}'"
            
            # Should be successful
            assert result.success, f"Feature flags processing failed for '{case}': {result.errors}"
            
            # Should have normalized text
            assert result.normalized, f"Normalized text is empty for '{case}'"
            
            # Should have tokens
            assert len(result.tokens) > 0, f"No tokens found for '{case}'"
    
    @pytest.mark.asyncio
    async def test_error_handling_smoke(self, normalization_factory, test_config, test_flags):
        """Test error handling smoke."""
        # Test with empty input
        result = await normalization_factory.normalize_text("", test_config, test_flags)
        assert result is not None, "Result is None for empty input"
        assert hasattr(result, 'success'), "Result missing success attribute for empty input"
        
        # Test with None input
        result = await normalization_factory.normalize_text(None, test_config, test_flags)
        assert result is not None, "Result is None for None input"
        assert hasattr(result, 'success'), "Result missing success attribute for None input"
        
        # Test with very long input
        long_input = "Иван Петров " * 1000
        result = await normalization_factory.normalize_text(long_input, test_config, test_flags)
        assert result is not None, "Result is None for long input"
        assert hasattr(result, 'success'), "Result missing success attribute for long input"
    
    @pytest.mark.asyncio
    async def test_performance_smoke(self, normalization_factory, test_config, test_flags):
        """Test performance smoke."""
        import time
        
        test_cases = [
            "Иван Петров",
            "John Smith",
            "Олександр Коваленко"
        ]
        
        total_time = 0.0
        
        for case in test_cases:
            start_time = time.perf_counter()
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            end_time = time.perf_counter()
            
            total_time += (end_time - start_time)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{case}'"
            assert result.success, f"Normalization failed for '{case}': {result.errors}"
        
        # Should be reasonably fast
        avg_time = total_time / len(test_cases)
        assert avg_time < 1.0, f"Normalization too slow: {avg_time:.3f}s per case"
    
    @pytest.mark.asyncio
    async def test_trace_smoke(self, normalization_factory, test_config, test_flags):
        """Test trace smoke."""
        test_cases = [
            "Иван Петров",
            "John Smith",
            "Олександр Коваленко"
        ]
        
        for case in test_cases:
            result = await normalization_factory.normalize_text(case, test_config, test_flags)
            
            # Basic smoke test
            assert result is not None, f"Result is None for '{case}'"
            assert hasattr(result, 'trace'), f"Result missing trace attribute for '{case}'"
            assert isinstance(result.trace, list), f"Trace should be a list for '{case}'"
            
            # Should have trace when debug_tracing is enabled
            if test_config.debug_tracing:
                assert len(result.trace) > 0, f"Trace should not be empty for '{case}'"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
