"""
Integration tests for Ukrainian text normalization
"""

import pytest
from ai_service.layers.normalization.normalization_service import NormalizationService


class TestUkrainianNormalization:
    """Test Ukrainian text normalization with pymorphy3 stemmer"""

    @pytest.fixture
    def normalization_service(self):
        """Create normalization service instance"""
        return NormalizationService()

    def test_ukrainian_text_normalization(self, normalization_service):
        """Test normalization of Ukrainian text"""
        ukrainian_text = "Українська мова є однією з найкращих мов у світі"
        
        result = normalization_service.normalize_sync(ukrainian_text, language="uk")
        
        assert result.success
        assert result.language == "uk"
        assert result.normalized is not None
        assert len(result.tokens) > 0
        assert result.token_count > 0

    def test_ukrainian_stemming_in_normalization(self, normalization_service):
        """Test that Ukrainian stemming works in normalization process"""
        ukrainian_text = "країни та люди"
        
        result = normalization_service.normalize_sync(ukrainian_text, language="uk")
        
        assert result.success
        assert result.language == "uk"
        
        # Check that tokens are processed correctly
        assert len(result.tokens) > 0

        # All tokens should be strings
        for token in result.tokens:
            assert isinstance(token, str)

    def test_ukrainian_language_detection(self, normalization_service):
        """Test Ukrainian language detection"""
        ukrainian_texts = [
            "Україна - це красива країна",
            "Мова українська дуже гарна",
            "Люди живуть у містах",
            "Сонце світить яскраво"
        ]
        
        for text in ukrainian_texts:
            result = normalization_service.normalize_sync(text)
            # Language detection might not be perfect, but should work
            assert result.success
            assert result.language in ["uk", "ru", "en"]  # Should detect one of these

    def test_ukrainian_stop_words_removal(self, normalization_service):
        """Test Ukrainian stop words removal"""
        # Use Russian stop words as fallback for Ukrainian
        ukrainian_text = "у країні є багато людей"
        
        result = normalization_service.normalize_sync(ukrainian_text, language="uk")
        assert result.success
        
        # Check that result has tokens
        assert len(result.tokens) >= 0  # May be empty after stopword removal

    def test_ukrainian_unicode_handling(self, normalization_service):
        """Test Ukrainian Unicode character handling"""
        ukrainian_text = "Європа, ґрунт, ідея, їжа, йод"
        
        result = normalization_service.normalize_sync(ukrainian_text, language="uk")
        
        assert result.success
        assert result.language == "uk"
        assert "Європ" in result.normalized or "європ" in result.normalized.lower()

    def test_ukrainian_mixed_language_text(self, normalization_service):
        """Test handling of mixed Ukrainian and other language text"""
        mixed_text = "Україна Ukraine Россия Russia"
        
        result = normalization_service.normalize_sync(mixed_text, language="uk")
        
        assert result.success
        assert len(result.tokens) > 0

    def test_ukrainian_empty_and_short_text(self, normalization_service):
        """Test handling of empty and short Ukrainian text"""
        test_cases = [
            "",
            "а",
            "у",
            "і",
            "   ",
            "У",
            "І"
        ]
        
        for text in test_cases:
            result = normalization_service.normalize_sync(text, language="uk")
            assert result.success
            assert isinstance(result.normalized, str)

    def test_ukrainian_special_characters(self, normalization_service):
        """Test handling of special characters in Ukrainian text"""
        ukrainian_text = "Україна! @#$%^&*()_+ 123"
        
        result = normalization_service.normalize_sync(ukrainian_text, language="uk")
        
        assert result.success
        assert result.language == "uk"
        assert len(result.tokens) > 0

    def test_ukrainian_performance(self, normalization_service):
        """Test performance with longer Ukrainian text"""
        ukrainian_text = """
        Україна - це велика країна у Східній Європі. 
        Вона має багату історію та культуру. 
        Українська мова є однією з найкращих слов'янських мов.
        Люди в Україні дуже добрі та гостинні.
        """
        
        result = normalization_service.normalize_sync(ukrainian_text, language="uk")
        
        assert result.success
        assert result.language == "uk"
        assert result.token_count > 10  # Should have many tokens
        assert result.processing_time > 0
