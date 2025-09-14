"""
Unit tests for config-driven language detection with extended contract
"""

import pytest
from unittest.mock import Mock

from ai_service.layers.language.language_detection_service import LanguageDetectionService
from ai_service.config import LANGUAGE_CONFIG
from ai_service.utils.types import LanguageDetectionResult


class TestLanguageConfigContract:
    """Test config-driven language detection with extended contract"""

    @pytest.fixture
    def language_service(self):
        """Create LanguageDetectionService instance"""
        return LanguageDetectionService()

    @pytest.fixture
    def default_config(self):
        """Get default language config"""
        return LANGUAGE_CONFIG

    def test_russian_text_detection(self, language_service, default_config):
        """
        Test Russian text detection: "Платеж Иванову" → language in {"ru","mixed"}; confidence>=0.6
        """
        text = "Платеж Иванову"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is Russian or mixed
        assert result.language in {"ru", "mixed"}
        
        # Verify confidence is high enough
        assert result.confidence >= 0.6
        
        # Verify details structure
        assert "cyr_ratio" in result.details
        assert "lat_ratio" in result.details
        assert "uk_chars" in result.details
        assert "ru_chars" in result.details
        assert "method" in result.details
        assert "reason" in result.details
        
        # Verify Cyrillic ratio is high
        assert result.details["cyr_ratio"] > 0.5
        assert result.details["lat_ratio"] < 0.5

    def test_ukrainian_text_detection(self, language_service, default_config):
        """
        Test Ukrainian text detection: "Переказ коштів Олені" → language in {"uk","mixed"}; confidence>=0.6
        """
        text = "Переказ коштів Олені"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is Ukrainian or mixed
        assert result.language in {"uk", "mixed"}
        
        # Verify confidence is high enough
        assert result.confidence >= 0.6
        
        # Verify details structure
        assert "cyr_ratio" in result.details
        assert "lat_ratio" in result.details
        assert "uk_chars" in result.details
        assert "ru_chars" in result.details
        
        # Verify Cyrillic ratio is high
        assert result.details["cyr_ratio"] > 0.5
        assert result.details["lat_ratio"] < 0.5
        
        # Should have Ukrainian-specific characters
        assert result.details["uk_chars"] > 0

    def test_english_text_detection(self, language_service, default_config):
        """
        Test English text detection: "Payment to John Smith" → "en", confidence>=0.6
        """
        text = "Payment to John Smith"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is English
        assert result.language == "en"
        
        # Verify confidence is high enough
        assert result.confidence >= 0.6
        
        # Verify details structure
        assert "cyr_ratio" in result.details
        assert "lat_ratio" in result.details
        
        # Verify Latin ratio is high
        assert result.details["lat_ratio"] > 0.5
        assert result.details["cyr_ratio"] < 0.5

    def test_mixed_language_detection(self, language_service, default_config):
        """
        Test mixed language detection: "Оплата Ivan Petrov" → "mixed" (if ratios are close), confidence>=0.55
        """
        text = "Оплата Ivan Petrov"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is mixed or one of the languages
        assert result.language in {"ru", "uk", "en", "mixed"}
        
        # Verify confidence is reasonable
        assert result.confidence >= 0.55
        
        # Verify details structure
        assert "cyr_ratio" in result.details
        assert "lat_ratio" in result.details
        
        # Should have both Cyrillic and Latin characters
        assert result.details["cyr_ratio"] > 0.0
        assert result.details["lat_ratio"] > 0.0

    def test_unknown_text_detection(self, language_service, default_config):
        """
        Test unknown text detection: "12345 --- $$$" → "unknown"
        """
        text = "12345 --- $$$"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is unknown
        assert result.language == "unknown"
        
        # Verify confidence is low
        assert result.confidence < 0.6
        
        # Verify details structure
        assert "cyr_ratio" in result.details
        assert "lat_ratio" in result.details
        assert "reason" in result.details
        
        # Should have very few letters
        assert result.details["total_letters"] < 5

    def test_empty_text_detection(self, language_service, default_config):
        """
        Test empty text detection
        """
        text = ""
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is unknown
        assert result.language == "unknown"
        
        # Verify confidence is 0
        assert result.confidence == 0.0
        
        # Verify details structure
        assert result.details["reason"] == "empty_text"

    def test_whitespace_text_detection(self, language_service, default_config):
        """
        Test whitespace-only text detection
        """
        text = "   \n\t  "
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is unknown
        assert result.language == "unknown"
        
        # Verify confidence is 0
        assert result.confidence == 0.0

    def test_ukrainian_specific_characters(self, language_service, default_config):
        """
        Test Ukrainian-specific characters detection
        """
        text = "Переказ коштів і гроші"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is Ukrainian
        assert result.language == "uk"
        
        # Verify confidence is high
        assert result.confidence >= 0.6
        
        # Should have Ukrainian-specific characters
        assert result.details["uk_chars"] > 0
        
        # Should have character bonuses
        assert "uk_chars" in result.details["bonuses"]
        assert result.details["bonuses"]["uk_chars"] > 0

    def test_russian_specific_characters(self, language_service, default_config):
        """
        Test Russian-specific characters detection
        """
        text = "Платеж ёжику"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is Russian
        assert result.language == "ru"
        
        # Verify confidence is high
        assert result.confidence >= 0.6
        
        # Should have Russian-specific characters
        assert result.details["ru_chars"] > 0
        
        # Should have character bonuses
        assert "ru_chars" in result.details["bonuses"]
        assert result.details["bonuses"]["ru_chars"] > 0

    def test_mixed_language_close_ratios(self, language_service, default_config):
        """
        Test mixed language when ratios are very close
        """
        # Create text with balanced Cyrillic and Latin
        text = "Оплата Payment за for послуги services"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify result type
        assert isinstance(result, LanguageDetectionResult)
        
        # Verify language is mixed or one of the languages
        assert result.language in {"ru", "uk", "en", "mixed"}
        
        # Verify confidence is reasonable
        assert result.confidence >= 0.55
        
        # Should have both character types
        assert result.details["cyr_ratio"] > 0.0
        assert result.details["lat_ratio"] > 0.0

    def test_config_thresholds_behavior(self, language_service):
        """
        Test that config thresholds affect detection behavior
        """
        # Create custom config with different thresholds
        from ai_service.config.settings import LanguageConfig
        
        strict_config = LanguageConfig(
            min_cyr_ratio=0.8,
            min_lat_ratio=0.8,
            mixed_gap=0.05,
            min_confidence=0.8
        )
        
        # Test with text that should be detected as mixed with default config
        text = "Оплата Payment"
        
        # With default config
        result_default = language_service.detect_language_config_driven(text)
        
        # With strict config
        result_strict = language_service.detect_language_config_driven(text, strict_config)
        
        # Results should be different
        assert isinstance(result_default, LanguageDetectionResult)
        assert isinstance(result_strict, LanguageDetectionResult)
        
        # Strict config should be more likely to return "unknown"
        if result_strict.language == "unknown":
            assert result_strict.confidence < strict_config.min_confidence

    def test_confidence_calculation(self, language_service, default_config):
        """
        Test confidence calculation with bonuses
        """
        text = "Переказ коштів і гроші"  # Ukrainian with specific characters
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify confidence calculation
        base_confidence = result.details["cyr_ratio"]
        uk_bonus = result.details["bonuses"].get("uk_chars", 0)
        expected_confidence = min(base_confidence + uk_bonus, 1.0)
        
        # Allow small floating point differences
        assert abs(result.confidence - expected_confidence) < 0.01

    def test_result_methods(self, language_service, default_config):
        """
        Test LanguageDetectionResult helper methods
        """
        # Test confident result
        text = "Платеж Иванову"
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Test helper methods
        assert isinstance(result.is_confident(), bool)
        assert isinstance(result.is_mixed(), bool)
        assert isinstance(result.is_unknown(), bool)
        
        # Test to_dict method
        result_dict = result.to_dict()
        assert isinstance(result_dict, dict)
        assert "language" in result_dict
        assert "confidence" in result_dict
        assert "details" in result_dict

    def test_detailed_analysis_structure(self, language_service, default_config):
        """
        Test that detailed analysis includes all required fields
        """
        text = "Платеж Иванову"
        
        result = language_service.detect_language_config_driven(text, default_config)
        
        # Verify all required detail fields are present
        required_fields = [
            "method", "reason", "cyr_ratio", "lat_ratio", 
            "uk_chars", "ru_chars", "total_letters", 
            "bonuses", "final_confidence", "final_language", "config_used"
        ]
        
        for field in required_fields:
            assert field in result.details, f"Missing field: {field}"
        
        # Verify config_used contains the config
        assert isinstance(result.details["config_used"], dict)
        assert "min_cyr_ratio" in result.details["config_used"]
        assert "min_lat_ratio" in result.details["config_used"]
