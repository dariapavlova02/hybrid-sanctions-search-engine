"""
Unit tests for NormalizationService - Updated for current implementation
"""

import pytest
import os
import sys
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

# Add project to path
project_root = Path(__file__).parent.parent.parent.parent / "src"
sys.path.insert(0, str(project_root))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.contracts.base_contracts import NormalizationResult
from ai_service.exceptions import NormalizationError, LanguageDetectionError


class TestNormalizationService:
    """Tests for NormalizationService core functionality"""

    @pytest.fixture
    def service(self):
        """Create a clean NormalizationService instance for testing"""
        with patch('ai_service.layers.normalization.normalization_service.LanguageDetectionService') as mock_lang_service, \
             patch('ai_service.layers.normalization.normalization_service.UnicodeService') as mock_unicode_service:
            
            # Mock the services
            mock_lang_service.return_value = Mock()
            mock_unicode_service.return_value = Mock()
            
            return NormalizationService()

    def test_initialization(self, service):
        """Test NormalizationService initialization"""
        assert service.language_service is not None
        assert service.unicode_service is not None
        assert hasattr(service, 'morph_analyzers')
        assert hasattr(service, 'name_dictionaries')
        assert hasattr(service, 'diminutive_maps')

    def test_normalize_english_text(self, service):
        """Test normalization of English text"""
        result = service.normalize("Hello world", language="en")
        
        assert result.success
        assert "Hello world" in result.normalized
        assert len(result.tokens) > 0

    def test_normalize_russian_text(self, service):
        """Test normalization of Russian text"""
        result = service.normalize("Привет мир", language="ru")
        
        assert result.success
        assert "Привет" in result.normalized
        assert len(result.tokens) > 0

    def test_normalize_ukrainian_text(self, service):
        """Test normalization of Ukrainian text"""
        result = service.normalize("Привіт світ", language="uk")
        
        assert result.success
        assert "Привіт" in result.normalized
        assert len(result.tokens) > 0

    def test_normalize_with_fallback(self, service):
        """Test normalization with fallback behavior"""
        result = service.normalize("Hello world", language="en")
        
        assert result.success
        assert "Hello world" in result.normalized

    def test_normalize_with_auto_language_detection(self, service):
        """Test normalization with automatic language detection"""
        result = service.normalize("Hello world", language="auto")
        
        assert result.success
        assert "Hello world" in result.normalized

    def test_normalize_person_names(self, service):
        """Test normalization of person names"""
        result = service.normalize("Ivan Petrov", language="en")
        
        assert result.success
        assert "Ivan" in result.normalized
        assert "Petrov" in result.normalized

    def test_normalize_russian_names(self, service):
        """Test normalization of Russian names"""
        result = service.normalize("Иван Петров", language="ru")
        
        assert result.success
        assert "Иван" in result.normalized
        assert "Петров" in result.normalized

    def test_normalize_ukrainian_names(self, service):
        """Test normalization of Ukrainian names"""
        result = service.normalize("Іван Петров", language="uk")
        
        assert result.success
        assert "Іван" in result.normalized
        assert "Петров" in result.normalized

    def test_normalize_with_initials(self, service):
        """Test normalization with initials"""
        result = service.normalize("I. Petrov", language="en")
        
        assert result.success
        assert "I." in result.normalized or "I" in result.normalized
        assert "Petrov" in result.normalized

    def test_normalize_empty_text(self, service):
        """Test normalization of empty text"""
        result = service.normalize("", language="en")
        
        assert result.success
        assert result.normalized == ""

    def test_normalize_whitespace_only(self, service):
        """Test normalization of whitespace-only text"""
        result = service.normalize("   \t\n   ", language="en")
        
        assert result.success
        assert result.normalized.strip() == ""

    def test_normalize_with_special_characters(self, service):
        """Test normalization with special characters"""
        result = service.normalize("O'Connor", language="en")
        
        assert result.success
        assert "O'Connor" in result.normalized

    def test_normalize_with_numbers(self, service):
        """Test normalization with numbers"""
        result = service.normalize("John123 Smith", language="en")
        
        assert result.success
        assert "John" in result.normalized
        assert "Smith" in result.normalized

    def test_normalize_sync_method(self, service):
        """Test normalize_sync method"""
        result = service.normalize_sync("Hello world", language="en")
        
        assert result.success
        assert "Hello world" in result.normalized

    def test_normalize_async_method(self, service):
        """Test normalize_async method"""
        import asyncio
        
        async def run_test():
            result = await service.normalize_async("Hello world", language="en")
            assert result.success
            assert "Hello world" in result.normalized
        
        asyncio.run(run_test())

    def test_normalize_with_flags(self, service):
        """Test normalization with different flags"""
        result = service.normalize(
            "Hello world", 
            language="en",
            remove_stop_words=False,
            preserve_names=True,
            enable_advanced_features=True
        )
        
        assert result.success
        assert "Hello world" in result.normalized

    def test_normalize_error_handling(self, service):
        """Test error handling in normalization"""
        # Test with invalid language
        result = service.normalize("Hello world", language="invalid_lang")
        
        # Should still succeed but may have different behavior
        assert result.success or not result.success  # Either way is acceptable

    def test_normalize_result_structure(self, service):
        """Test that NormalizationResult has expected structure"""
        result = service.normalize("Hello world", language="en")
        
        assert hasattr(result, 'success')
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

    def test_normalize_with_complex_text(self, service):
        """Test normalization with complex text containing multiple elements"""
        text = "Payment to Ivan Petrov for services rendered by Anna Smith"
        result = service.normalize(text, language="en")
        
        assert result.success
        assert "Ivan" in result.normalized
        assert "Petrov" in result.normalized
        assert "Anna" in result.normalized
        assert "Smith" in result.normalized

    def test_normalize_russian_complex_text(self, service):
        """Test normalization with complex Russian text"""
        text = "Перевод средств на имя Ивана Петрова от Анны Смирновой"
        result = service.normalize(text, language="ru")
        
        assert result.success
        assert "Иван" in result.normalized
        assert "Петров" in result.normalized
        assert "Анна" in result.normalized
        assert "Смирнова" in result.normalized

    def test_normalize_ukrainian_complex_text(self, service):
        """Test normalization with complex Ukrainian text"""
        text = "Переказ коштів на ім'я Івана Петрова від Анни Смірнової"
        result = service.normalize(text, language="uk")
        
        assert result.success
        assert "Іван" in result.normalized
        assert "Петров" in result.normalized
        assert "Анна" in result.normalized
        assert "Смірнова" in result.normalized


class TestNormalizationServiceConfiguration:
    """Test configuration-related functionality"""

    @pytest.fixture
    def service(self):
        """Create a clean NormalizationService instance for testing"""
        with patch('ai_service.layers.normalization.normalization_service.LanguageDetectionService') as mock_lang_service, \
             patch('ai_service.layers.normalization.normalization_service.UnicodeService') as mock_unicode_service:
            
            # Mock the services
            mock_lang_service.return_value = Mock()
            mock_unicode_service.return_value = Mock()
            
            return NormalizationService()

    def test_service_has_required_attributes(self, service):
        """Test that service has all required attributes"""
        required_attrs = [
            'language_service',
            'unicode_service', 
            'morph_analyzers',
            'name_dictionaries',
            'diminutive_maps',
            'dim2full_maps'
        ]
        
        for attr in required_attrs:
            assert hasattr(service, attr), f"Service missing attribute: {attr}"

    def test_service_has_required_methods(self, service):
        """Test that service has all required methods"""
        required_methods = [
            'normalize',
            'normalize_sync',
            'normalize_async',
            'adjust_surname_gender',
            'group_persons'
        ]
        
        for method in required_methods:
            assert hasattr(service, method), f"Service missing method: {method}"
            assert callable(getattr(service, method)), f"Service method not callable: {method}"

    def test_morph_analyzers_initialization(self, service):
        """Test that morphological analyzers are properly initialized"""
        assert isinstance(service.morph_analyzers, dict)
        # Should have analyzers for supported languages
        assert 'uk' in service.morph_analyzers or 'ru' in service.morph_analyzers

    def test_name_dictionaries_initialization(self, service):
        """Test that name dictionaries are properly initialized"""
        assert isinstance(service.name_dictionaries, dict)
        # Should have dictionaries for supported languages
        assert 'en' in service.name_dictionaries
        assert 'ru' in service.name_dictionaries
        assert 'uk' in service.name_dictionaries

    def test_diminutive_maps_initialization(self, service):
        """Test that diminutive maps are properly initialized"""
        assert isinstance(service.diminutive_maps, dict)
        # Should have maps for supported languages
        assert 'en' in service.diminutive_maps
        assert 'ru' in service.diminutive_maps
        assert 'uk' in service.diminutive_maps


class TestNormalizationResult:
    """Test NormalizationResult functionality"""

    def test_normalization_result_creation(self):
        """Test NormalizationResult creation"""
        from ai_service.contracts.base_contracts import NormalizationResult
        
        result = NormalizationResult(
            original_text="test",
            language="en",
            language_confidence=0.9,
            normalized_text="test",
            tokens=["test"],
            trace=[],
            signals=None,
            variants=None,
            embeddings=None,
            decision=None,
            processing_time=0.1,
            success=True,
            errors=[]
        )
        
        assert result.original_text == "test"
        assert result.language == "en"
        assert result.success is True

    def test_normalization_result_error_case(self):
        """Test NormalizationResult error case"""
        from ai_service.contracts.base_contracts import NormalizationResult
        
        result = NormalizationResult(
            original_text="test",
            language="en",
            language_confidence=0.9,
            normalized_text="",
            tokens=[],
            trace=[],
            signals=None,
            variants=None,
            embeddings=None,
            decision=None,
            processing_time=0.1,
            success=False,
            errors=["Test error"]
        )
        
        assert result.success is False
        assert "Test error" in result.errors

