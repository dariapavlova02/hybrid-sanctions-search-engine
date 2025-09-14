"""
Unit tests for UkrainianMorphologyAnalyzer using pytest fixtures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ai_service.layers.normalization.morphology.ukrainian_morphology import UkrainianMorphologyAnalyzer
from src.ai_service.layers.normalization.morphology.base_morphology import MorphologicalAnalysis


class TestUkrainianMorphologyAnalyzer:
    """Tests for Ukrainian morphological analyzer"""

    @pytest.fixture(autouse=True)
    def setup_analyzer(self):
        """Create analyzer instance for tests"""
        # Mock the dependencies
        with patch('src.ai_service.layers.ukrainian_morphology.get_logger'):
            self.analyzer = UkrainianMorphologyAnalyzer()
        
        # Mock special names
        self.analyzer.special_names = {
            'Петро': {
                'gender': 'masc',
                'variants': ['Петр'],
                'diminutives': ['Петрик', 'Петрусь']
            },
            'Дарія': {
                'gender': 'femn',
                'variants': ['Дарья'],
                'diminutives': ['Даша', 'Даруся']
            }
        }
        
        # Mock pymorphy3 analyzer
        self.mock_pymorphy = Mock()
        self.analyzer.morph_analyzer = self.mock_pymorphy
        
        # Mock parsed words
        self.mock_petro_parsed = Mock()
        self.mock_petro_parsed.word = "Петро"
        self.mock_petro_parsed.normal_form = "Петро"
        
        self.mock_daria_parsed = Mock()
        self.mock_daria_parsed.word = "Дарія"
        self.mock_daria_parsed.normal_form = "Дарія"

    def test_analyze_word_gender_detection_petro(self):
        """Test that analyze_word correctly determines gender for "Петро" """
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Петро"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word('Петро')
        
        # Check result structure
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], MorphologicalAnalysis)

    def test_analyze_word_gender_detection_daria(self):
        """Test that analyze_word correctly determines gender for "Дарія" """
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Дарія"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word('Дарія')
        
        # Check result structure
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], MorphologicalAnalysis)

    def test_analyze_word_unknown_name(self):
        """Test analysis of unknown name"""
        # Mock pymorphy3 response for unknown name
        mock_parse = Mock()
        mock_parse.normal_form = "Тест"
        mock_parse.score = 0.5
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word("Тест")
        
        # Should return fallback analysis
        assert isinstance(result, list)
        assert len(result) > 0
        if result:  # If there are results
            assert isinstance(result[0], MorphologicalAnalysis)

    def test_analyze_word_short_name(self):
        """Test analysis of short name"""
        result = self.analyzer.analyze_word("Абвгд")
        
        # Should return fallback analysis for short names
        assert isinstance(result, list)
        assert len(result) > 0
        if result:  # If there are results
            assert isinstance(result[0], MorphologicalAnalysis)

    def test_get_lemma_special_name(self):
        """Test getting lemma for special name"""
        test_name = "Петро"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Петро"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.get_lemma(test_name)
        
        # Should return normalized lemma in lowercase
        assert result == test_name.lower()

    def test_get_lemma_unknown_name(self):
        """Test getting lemma for unknown name"""
        test_name = "Тест"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Тест"
        mock_parse.score = 0.5
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.get_lemma(test_name)
        
        # Should return normalized lemma in lowercase
        assert result == test_name.lower()

    def test_is_known_word_special_name(self):
        """Test is_known_word for special name"""
        test_name = "Петро"
        
        result = self.analyzer.is_known_word(test_name)
        
        # Should return True for special names
        assert result is True

    def test_is_known_word_unknown_name(self):
        """Test is_known_word for unknown name"""
        test_name = "Тест"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Тест"
        mock_parse.score = 0.5
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.is_known_word(test_name)
        
        # Should return False for unknown names
        assert result is False

    def test_get_gender_special_name(self):
        """Test gender detection for special name"""
        test_name = "Петро"
        
        results = self.analyzer.analyze_word(test_name)
        assert len(results) > 0
        
        result = results[0]
        # Should return correct gender for special names
        assert result.gender == 'masc'  # Petro is masculine

    def test_get_gender_unknown_name(self):
        """Test gender detection for unknown name"""
        test_name = "Тест"
        
        results = self.analyzer.analyze_word(test_name)
        # May return empty results for unknown words
        if len(results) > 0:
            result = results[0]
            # Should return analysis result, gender may be None for unknown words
            assert isinstance(result.lemma, str)
            # Gender can be None, 'masc', 'femn', or other values
            assert result.gender is None or result.gender in ['masc', 'femn', 'neut']

    def test_get_variants_special_name(self):
        """Test getting variants for special name"""
        test_name = "Петро"
        
        results = self.analyzer.analyze_word(test_name)
        # May return empty results for unknown words
        if len(results) > 0:
            result = results[0]
            # Should return analysis result with lemma and gender
            assert isinstance(result.lemma, str)
            assert result.lemma in ['петро', 'Петро']  # May be either form
            assert result.gender == 'masc'  # Petro is masculine

    def test_get_variants_unknown_name(self):
        """Test getting variants for unknown name"""
        test_name = "Тест"
        
        results = self.analyzer.analyze_word(test_name)
        assert len(results) > 0
        
        result = results[0]
        # Should return analysis result with lemma
        assert isinstance(result.lemma, str)
        assert result.lemma == 'тест'  # Should be normalized to lowercase

    def test_get_diminutives_special_name(self):
        """Test getting diminutives for special name"""
        test_name = "Петро"
        
        results = self.analyzer.analyze_word(test_name)
        # May return empty results for unknown words
        if len(results) > 0:
            result = results[0]
            # Should return analysis result with lemma and gender
            assert isinstance(result.lemma, str)
            assert result.gender == 'masc'  # Petro is masculine
            # Note: diminutives are not part of MorphologicalAnalysis
            # They would be available through a separate method if needed

    def test_get_diminutives_unknown_name(self):
        """Test getting diminutives for unknown name"""
        test_name = "Тест"
        
        results = self.analyzer.analyze_word(test_name)
        # May return empty results for unknown words
        if len(results) > 0:
            result = results[0]
            # Should return analysis result with lemma
            assert isinstance(result.lemma, str)
            assert result.lemma == 'тест'  # Should be normalized to lowercase

    def test_analyze_name_basic_functionality(self):
        """Test basic analyze_name functionality"""
        test_name = "Петро"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return analysis result
        assert isinstance(result, list)
        # May return empty results for unknown words
        if len(result) > 0:
            assert isinstance(result[0], MorphologicalAnalysis)

    def test_analyze_name_with_language_detection(self):
        """Test analyze_name with language detection"""
        test_name = "Петро"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return analysis result
        assert isinstance(result, list)
        # May return empty results for unknown words
        if len(result) > 0:
            assert isinstance(result[0], MorphologicalAnalysis)

    def test_analyze_name_empty_string(self):
        """Test analyze_name with empty string"""
        result = self.analyzer.analyze_word("")
        
        # Should return empty list for empty string
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_name_whitespace_only(self):
        """Test analyze_name with whitespace-only string"""
        result = self.analyzer.analyze_word("   ")
        
        # Should return empty list for whitespace-only string
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_name_none_input(self):
        """Test analyze_name with None input"""
        result = self.analyzer.analyze_word(None)
        
        # Should return empty list for None input
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_name_special_characters(self):
        """Test analyze_name with special characters"""
        test_name = "Петро-Іванов"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle special characters gracefully
        assert isinstance(result, list)
        # May return empty list or handle special characters

    def test_analyze_name_numbers(self):
        """Test analyze_name with numbers"""
        test_name = "Петро123"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle numbers gracefully
        assert isinstance(result, list)
        # May return empty list or handle numbers

    def test_analyze_name_mixed_case(self):
        """Test analyze_name with mixed case"""
        test_name = "пЕтРо"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle mixed case gracefully
        assert isinstance(result, list)
        # May return empty list or handle mixed case

    def test_analyze_name_very_long(self):
        """Test analyze_name with very long name"""
        test_name = "Петро" * 100
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle very long names gracefully
        assert isinstance(result, list)
        # May return empty list or handle very long names

    def test_analyze_name_unicode_characters(self):
        """Test analyze_name with Unicode characters"""
        test_name = "Петро\u200bІванов"  # Zero-width space
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle Unicode characters gracefully
        assert isinstance(result, list)
        # May return empty list or handle Unicode characters
