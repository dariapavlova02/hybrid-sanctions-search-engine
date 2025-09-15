#!/usr/bin/env python3
"""
Unit tests for NormalizationResult metadata fields and TokenTrace completeness.
"""

import pytest
import asyncio
from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.contracts.base_contracts import NormalizationResult


class TestNormalizationResultFields:
    """Test that NormalizationResult carries rich metadata and TokenTrace is complete."""
    
    @pytest.fixture
    def service(self):
        """Create normalization service instance."""
        return NormalizationService()
    
    def test_normalization_result_metadata_fields(self, service):
        """Test that NormalizationResult has all required metadata fields."""
        # Test with Ukrainian text
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"
        result = service.normalize(text, language="uk")
        
        # Assert result is a NormalizationResult
        assert isinstance(result, NormalizationResult)
        
        # Assert presence of all required fields
        assert hasattr(result, 'normalized')
        assert hasattr(result, 'tokens')
        assert hasattr(result, 'errors')
        assert hasattr(result, 'language')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'original_length')
        assert hasattr(result, 'normalized_length')
        assert hasattr(result, 'token_count')
        assert hasattr(result, 'processing_time')
        assert hasattr(result, 'success')
        
        # Assert field types
        assert isinstance(result.normalized, str)
        assert isinstance(result.tokens, list)
        assert isinstance(result.errors, (list, type(None)))
        assert isinstance(result.language, str)
        assert isinstance(result.confidence, (float, type(None)))
        assert isinstance(result.original_length, int)
        assert isinstance(result.normalized_length, int)
        assert isinstance(result.token_count, int)
        assert isinstance(result.processing_time, (float, type(None)))
        assert isinstance(result.success, bool)
        
        # Assert success is True (no errors)
        assert result.success is True
        
        # Assert token_count equals tokens length
        assert result.token_count == len(result.tokens)
        
        # Assert lengths are greater than 0
        assert result.original_length > 0
        assert result.normalized_length > 0
        assert result.token_count > 0
        
        # Assert processing time is reasonable (should be > 0)
        assert result.processing_time is not None
        assert result.processing_time > 0
        
        # Assert language is detected correctly
        assert result.language == "uk"
        
        # Assert confidence is reasonable
        assert result.confidence is not None
        assert 0.0 <= result.confidence <= 1.0
        
        # Assert no errors
        assert result.errors is None or len(result.errors) == 0
    
    def test_normalization_result_tokens(self, service):
        """Test that normalization produces valid tokens."""
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"
        result = service.normalize(text, language="uk")
        
        # Assert we have tokens
        assert len(result.tokens) > 0
        
        # Check each token is valid
        for token in result.tokens:
            assert isinstance(token, str)
            assert len(token) > 0
            # Tokens should not be empty strings
            assert token.strip() != ""
    
    def test_normalization_result_extra_fields_allowed(self, service):
        """Test that NormalizationResult allows extra fields."""
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"
        result = service.normalize(text, language="uk")
        
        # Test that we can add extra fields to the dataclass
        result.custom_field = 'test_value'
        assert hasattr(result, 'custom_field')
        assert result.custom_field == 'test_value'
    
    def test_normalization_result_basic_serialization(self, service):
        """Test that NormalizationResult can be converted to dict."""
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"
        result = service.normalize(text, language="uk")
        
        # Test conversion to dict using Pydantic model_dump
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert 'normalized' in result_dict
        assert 'tokens' in result_dict
        assert 'language' in result_dict
        assert 'success' in result_dict
        
        # Test that we can reconstruct from dict
        reconstructed = NormalizationResult(**result_dict)
        assert isinstance(reconstructed, NormalizationResult)
        assert reconstructed.normalized == result.normalized
        assert reconstructed.tokens == result.tokens
        assert reconstructed.success == result.success
