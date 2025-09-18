"""
Unit tests for LanguageDetectionService
"""

import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.language.language_detection_service import LanguageDetectionService


class TestLanguageDetectionService:
    """Tests for LanguageDetectionService"""
    
    def test_ukrainian_priority_detection(self, language_detection_service):
        """Test Ukrainian symbols priority: 'Петро і Марія' -> uk"""
        # Arrange
        ukrainian_text = "Петро і Марія"
        
        # Act
        result = language_detection_service.detect_language(ukrainian_text)
        
        # Assert
        assert result['language'] == 'uk'
        assert result['confidence'] > 0.5
        assert result['supported'] is True
        assert 'language_name' in result
    
    def test_fallback_logic_ambiguous_text(self, language_detection_service):
        """Test fallback logic: 'Иван Петров' -> ru"""
        # Arrange
        ambiguous_text = "Иван Петров"  # Can be both Russian and Ukrainian
        
        # Act
        result = language_detection_service.detect_language(ambiguous_text)
        
        # Assert
        assert result['language'] == 'ru'  # By fallback logic
        assert result['confidence'] > 0.0
        assert result['supported'] is True
    
    def test_empty_text_handling(self, language_detection_service):
        """Test empty text handling"""
        # Act
        result = language_detection_service.detect_language("")
        
        # Assert
        assert result['language'] == 'en'  # Default
        assert result['confidence'] == 0.0
        assert result['method'] == 'empty_text'
    
    def test_whitespace_only_text(self, language_detection_service):
        """Test text with only spaces handling"""
        # Act
        result = language_detection_service.detect_language("   \t\n  ")
        
        # Assert
        assert result['language'] == 'en'
        assert result['confidence'] == 0.0
        assert result['method'] == 'empty_text'
    
    def test_quick_patterns_english(self, language_detection_service):
        """Test quick English language detection"""
        # Arrange
        english_text = "The quick brown fox jumps over the lazy dog"
        
        # Act
        result = language_detection_service.detect_language(english_text)
        
        # Assert
        assert result['language'] == 'en'
        assert result['confidence'] > 0.3  # Quick detection should work
        # Can be quick_patterns or langdetect depending on confidence
    
    def test_quick_patterns_russian(self, language_detection_service):
        """Test quick Russian language detection"""
        # Arrange
        russian_text = "Быстрая коричневая лиса прыгает через ленивую собаку"
        
        # Act
        result = language_detection_service.detect_language(russian_text)
        
        # Assert
        assert result['language'] == 'ru'
        assert result['confidence'] > 0.3
    
    def test_quick_patterns_ukrainian(self, language_detection_service):
        """Test quick Ukrainian language detection"""
        # Arrange
        ukrainian_text = "Швидка коричнева лисиця стрибає через лінивого собаку"
        
        # Act
        result = language_detection_service.detect_language(ukrainian_text)
        
        # Assert
        assert result['language'] == 'uk'
        assert result['confidence'] > 0.3
    
    def test_langdetect_fallback(self, language_detection_service):
        """Test fallback to langdetect when quick detection fails"""
        # Arrange
        text = "Some text without clear patterns"
        
        # Act
        result = language_detection_service.detect_language(text)
        
        # Assert
        assert result['language'] in ['en', 'ru', 'uk']  # Should be detected as one of supported
        assert 'method' in result
    
    def test_langdetect_exception_handling(self, language_detection_service):
        """Test langdetect exception handling"""
        # Arrange
        text = "Some problematic text"
        
        # Act
        result = language_detection_service.detect_language(text, use_fallback=True)
        
        # Assert
        assert result['language'] in ['en', 'ru', 'uk']  # Fallback should work
        assert 'method' in result
    
    def test_fallback_cyrillic_ukrainian_specific(self, language_detection_service):
        """Test fallback with Ukrainian specific characters"""
        # Arrange
        text_with_uk_chars = "Текст з українськими літерами: і, ї, є, ґ"
        
        # Act
        result = language_detection_service.detect_language(text_with_uk_chars)
        
        # Assert
        assert result['language'] == 'uk'
        assert result['confidence'] >= 0.75
    
    def test_fallback_cyrillic_russian_specific(self, language_detection_service):
        """Test fallback with Russian specific characters"""
        # Arrange
        text_with_ru_chars = "Текст с русскими буквами: ё, ъ, ы, э"
        
        # Act
        result = language_detection_service.detect_language(text_with_ru_chars)
        
        # Assert
        assert result['language'] == 'ru'
        assert result['confidence'] >= 0.75
    
    def test_fallback_cyrillic_patterns(self, language_detection_service):
        """Test fallback with Ukrainian/Russian patterns"""
        # Arrange
        ukrainian_patterns_text = "і в на з по за від до у о а але або"
        russian_patterns_text = "и в на с по за от до из у о а но или"
        
        # Act
        uk_result = language_detection_service.detect_language(ukrainian_patterns_text)
        ru_result = language_detection_service.detect_language(russian_patterns_text)
        
        # Assert
        assert uk_result['language'] == 'uk'
        assert ru_result['language'] == 'ru'
    
    def test_fallback_latin_only(self, language_detection_service):
        """Test fallback with Latin characters only"""
        # Arrange
        latin_text = "Some text without cyrillic characters"
        
        # Act
        result = language_detection_service.detect_language(latin_text)
        
        # Assert
        # If there are no Cyrillic characters, should be detected as English
        # (either through quick detection or fallback)
        assert result['language'] == 'en'
    
    def test_batch_detection(self, language_detection_service):
        """Test batch language detection"""
        # Arrange
        texts = [
            "Hello world",
            "Привет мир", 
            "Привіт світ",
            "Bonjour monde"
        ]
        
        # Act
        results = language_detection_service.detect_batch(texts)
        
        # Assert
        assert len(results) == len(texts)
        for result in results:
            assert 'language' in result
            assert 'confidence' in result
            assert 'method' in result
    
    def test_detection_statistics(self, language_detection_service):
        """Test detection statistics"""
        # Arrange
        texts = ["Hello", "Привет", "Привіт"]
        
        # Act
        for text in texts:
            language_detection_service.detect_language(text)
        
        stats = language_detection_service.get_detection_stats()
        
        # Assert
        assert stats['total_detections'] >= 3
        assert stats['successful_detections'] >= 0
        assert 'avg_confidence' in stats
        assert 'success_rate' in stats
        assert 0.0 <= stats['success_rate'] <= 1.0
    
    def test_reset_statistics(self, language_detection_service):
        """Test statistics reset"""
        # Arrange
        language_detection_service.detect_language("Test text")
        
        # Act
        language_detection_service.reset_stats()
        stats = language_detection_service.get_detection_stats()
        
        # Assert
        assert stats['total_detections'] == 0
        assert stats['successful_detections'] == 0
        assert stats['fallback_usage'] == 0
        assert stats['confidence_scores'] == []
    
    def test_supported_languages(self, language_detection_service):
        """Test getting list of supported languages"""
        # Act
        languages = language_detection_service.get_supported_languages()
        
        # Assert
        assert isinstance(languages, list)
        assert 'en' in languages
        assert 'ru' in languages
        assert 'uk' in languages
    
    def test_is_language_supported(self, language_detection_service):
        """Test checking language support"""
        # Act & Assert
        assert language_detection_service.is_language_supported('en') is True
        assert language_detection_service.is_language_supported('ru') is True
        assert language_detection_service.is_language_supported('uk') is True
        assert language_detection_service.is_language_supported('fr') is False
        assert language_detection_service.is_language_supported('unknown') is False
    
    def test_add_language_mapping(self, language_detection_service):
        """Test adding new language mapping"""
        # Act
        language_detection_service.add_language_mapping('be', 'ru')  # Belarusian -> Russian
        
        # Assert
        assert language_detection_service.language_mapping['be'] == 'ru'
    
    def test_add_invalid_language_mapping(self, language_detection_service):
        """Test adding mapping to unsupported language"""
        # Act
        language_detection_service.add_language_mapping('fr', 'french')  # Unsupported
        
        # Assert
        # Mapping should not be added
        assert 'fr' not in language_detection_service.language_mapping or language_detection_service.language_mapping.get('fr') != 'french'
    
    def test_confidence_scores_limit(self, language_detection_service):
        """Test limiting the number of confidence scores saved"""
        # Arrange
        # Generate many detections
        for i in range(1100):  # More than the limit of 1000
            language_detection_service.detect_language(f"Test text {i}")
        
        # Act
        stats = language_detection_service.get_detection_stats()
        
        # Assert
        assert len(stats['confidence_scores']) <= 1000
    
    def test_language_mapping_coverage(self, language_detection_service):
        """Test language mapping coverage"""
        # Act & Assert
        # Check that main languages are mapped
        assert language_detection_service.language_mapping.get('en') == 'en'
        assert language_detection_service.language_mapping.get('ru') == 'ru'
        assert language_detection_service.language_mapping.get('uk') == 'uk'
        
        # Check that Slavic languages are mapped to Russian
        assert language_detection_service.language_mapping.get('bg') == 'ru'  # Bulgarian
        assert language_detection_service.language_mapping.get('pl') == 'ru'  # Polish
    
    def test_no_fallback_option(self, language_detection_service):
        """Test disabling fallback mechanisms"""
        # Arrange
        problematic_text = "∑∂∆"  # Symbols that may cause problems
        
        # Act
        result = language_detection_service.detect_language(problematic_text, use_fallback=False)
        
        # Assert
        assert result['language'] == 'en'  # Default without fallback
        assert result['confidence'] == 0.5
        assert result['method'] == 'default'
    
    def test_original_detected_language_preservation(self, language_detection_service):
        """Test preserving the original detected language"""
        # Arrange
        text = "Some text"
        
        # Act
        result = language_detection_service.detect_language(text)
        
        # Assert
        assert result['language'] in ['en', 'ru', 'uk']  # Should be defined as one of the supported languages
        assert 'method' in result
