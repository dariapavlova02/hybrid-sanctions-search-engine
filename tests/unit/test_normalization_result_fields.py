#!/usr/bin/env python3
"""
Unit tests for NormalizationResult metadata fields and TokenTrace completeness.
"""

import pytest
from ai_service.services.normalization_service import NormalizationService
from ai_service.utils.trace import TokenTrace, NormalizationResult


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
        result = service._normalize_sync(text, language="uk")
        
        # Assert result is a NormalizationResult
        assert isinstance(result, NormalizationResult)
        
        # Assert presence of all required fields
        assert hasattr(result, 'normalized')
        assert hasattr(result, 'tokens')
        assert hasattr(result, 'trace')
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
        assert isinstance(result.trace, list)
        assert isinstance(result.errors, list)
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
        assert len(result.errors) == 0
    
    def test_token_trace_completeness(self, service):
        """Test that TokenTrace has all required fields."""
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"
        result = service._normalize_sync(text, language="uk")
        
        # Assert we have traces
        assert len(result.trace) > 0
        
        # Check each trace has all required fields
        for trace in result.trace:
            assert isinstance(trace, TokenTrace)
            
            # Required fields
            assert hasattr(trace, 'token')
            assert hasattr(trace, 'role')
            assert hasattr(trace, 'rule')
            assert hasattr(trace, 'output')
            assert hasattr(trace, 'fallback')
            
            # Optional fields
            assert hasattr(trace, 'morph_lang')
            assert hasattr(trace, 'normal_form')
            assert hasattr(trace, 'notes')
            
            # Assert field types
            assert isinstance(trace.token, str)
            assert isinstance(trace.role, str)
            assert isinstance(trace.rule, str)
            assert isinstance(trace.output, str)
            assert isinstance(trace.fallback, bool)
            assert isinstance(trace.morph_lang, (str, type(None)))
            assert isinstance(trace.normal_form, (str, type(None)))
            assert isinstance(trace.notes, (str, type(None)))
            
            # Assert token and output are not empty
            assert len(trace.token) > 0
            assert len(trace.output) > 0
    
    def test_normalization_result_extra_fields_allowed(self, service):
        """Test that NormalizationResult allows extra fields."""
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"
        result = service._normalize_sync(text, language="uk")
        
        # Test that we can add extra fields
        result_dict = result.model_dump()
        result_dict['custom_field'] = 'test_value'
        
        # Should be able to create a new result with extra fields
        new_result = NormalizationResult(**result_dict)
        assert hasattr(new_result, 'custom_field')
        assert new_result.custom_field == 'test_value'
    
    def test_normalization_result_serialization(self, service):
        """Test that NormalizationResult can be serialized and deserialized."""
        text = "Переказ коштів на ім'я Петро Іванович Коваленко"
        result = service._normalize_sync(text, language="uk")
        
        # Test to_dict method
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert 'normalized' in result_dict
        assert 'tokens' in result_dict
        assert 'trace' in result_dict
        
        # Test to_json method
        result_json = result.to_json()
        assert isinstance(result_json, str)
        
        # Test from_dict method
        reconstructed = NormalizationResult.from_dict(result_dict)
        assert isinstance(reconstructed, NormalizationResult)
        assert reconstructed.normalized == result.normalized
        assert reconstructed.tokens == result.tokens
        assert reconstructed.success == result.success
        
        # Test from_json method
        reconstructed_from_json = NormalizationResult.from_json(result_json)
        assert isinstance(reconstructed_from_json, NormalizationResult)
        assert reconstructed_from_json.normalized == result.normalized
        assert reconstructed_from_json.tokens == result.tokens
        assert reconstructed_from_json.success == result.success
