"""
Property tests for normalization gates.

This module tests properties that should hold for all normalization operations
regardless of input.
"""

import pytest
from hypothesis import given, strategies as st
from typing import List, Dict, Any

from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.config.feature_flags import FeatureFlags


class TestPropertyGates:
    """Test property gates for normalization."""
    
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
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_idempotency(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization is idempotent."""
        # First normalization
        result1 = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        if not result1.success:
            pytest.skip("First normalization failed")
        
        # Second normalization
        result2 = await normalization_factory.normalize_text(
            result1.normalized, test_config, test_flags
        )
        
        if not result2.success:
            pytest.skip("Second normalization failed")
        
        # Results should be the same
        assert result1.normalized == result2.normalized, \
            f"Normalization not idempotent: '{result1.normalized}' != '{result2.normalized}'"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_length_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves reasonable length properties."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        if not result.success:
            pytest.skip("Normalization failed")
        
        # Normalized text should not be empty if input was not empty
        if text.strip():
            assert result.normalized, "Normalized text should not be empty for non-empty input"
        
        # Normalized text should not be excessively long
        assert len(result.normalized) <= len(text) * 2, \
            f"Normalized text too long: {len(result.normalized)} > {len(text) * 2}"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_tokens_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves reasonable token properties."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        if not result.success:
            pytest.skip("Normalization failed")
        
        # Should have tokens
        assert hasattr(result, 'tokens'), "Result should have tokens attribute"
        assert isinstance(result.tokens, list), "Tokens should be a list"
        
        # Token count should be reasonable
        if text.strip():
            assert len(result.tokens) > 0, "Should have at least one token for non-empty input"
        
        # Token count should not be excessive
        assert len(result.tokens) <= len(text.split()) * 2, \
            f"Too many tokens: {len(result.tokens)} > {len(text.split()) * 2}"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_success_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves success property."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        # Should have success attribute
        assert hasattr(result, 'success'), "Result should have success attribute"
        assert isinstance(result.success, bool), "Success should be a boolean"
        
        # If successful, should have normalized text
        if result.success:
            assert hasattr(result, 'normalized'), "Successful result should have normalized text"
            assert result.normalized is not None, "Normalized text should not be None"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_trace_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves trace property."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        # Should have trace attribute
        assert hasattr(result, 'trace'), "Result should have trace attribute"
        assert isinstance(result.trace, list), "Trace should be a list"
        
        # Trace should not be empty if debug_tracing is enabled
        if test_config.debug_tracing:
            assert len(result.trace) > 0, "Trace should not be empty when debug_tracing is enabled"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_errors_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves errors property."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        # Should have errors attribute
        assert hasattr(result, 'errors'), "Result should have errors attribute"
        assert isinstance(result.errors, list), "Errors should be a list"
        
        # If successful, should have no errors
        if result.success:
            assert len(result.errors) == 0, "Successful result should have no errors"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_processing_time_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves processing time property."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        # Should have processing_time attribute
        assert hasattr(result, 'processing_time'), "Result should have processing_time attribute"
        assert isinstance(result.processing_time, (int, float)), "Processing time should be a number"
        assert result.processing_time >= 0, "Processing time should be non-negative"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_language_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves language property."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        # Should have language attribute
        assert hasattr(result, 'language'), "Result should have language attribute"
        assert isinstance(result.language, str), "Language should be a string"
        assert result.language == test_config.language, "Language should match configuration"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_confidence_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves confidence property."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        # Should have confidence attribute
        assert hasattr(result, 'confidence'), "Result should have confidence attribute"
        assert isinstance(result.confidence, (int, float, type(None))), "Confidence should be a number or None"
        
        if result.confidence is not None:
            assert 0 <= result.confidence <= 1, "Confidence should be between 0 and 1"
    
    @given(st.text(min_size=1, max_size=100))
    @pytest.mark.hypothesis
    async def test_normalization_preserves_token_count_property(self, normalization_factory, test_config, test_flags, text):
        """Test that normalization preserves token count property."""
        result = await normalization_factory.normalize_text(text, test_config, test_flags)
        
        if not result.success:
            pytest.skip("Normalization failed")
        
        # Should have token_count attribute
        assert hasattr(result, 'token_count'), "Result should have token_count attribute"
        assert isinstance(result.token_count, int), "Token count should be an integer"
        assert result.token_count >= 0, "Token count should be non-negative"
        assert result.token_count == len(result.tokens), "Token count should match tokens length"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
