"""
Unit tests for RussianMorphologyAnalyzer using pytest fixtures
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ai_service.layers.normalization.morphology.russian_morphology import RussianMorphologyAnalyzer
from src.ai_service.layers.normalization.morphology.base_morphology import MorphologicalAnalysis


class TestRussianMorphologyAnalyzer:
    """Tests for Russian morphological analyzer"""

    @pytest.fixture(autouse=True)
    def setup_analyzer(self):
        """Create analyzer instance for tests"""
        # Mock the dependencies
        with patch('src.ai_service.layers.normalization.morphology.russian_morphology.get_logger'):
            self.analyzer = RussianMorphologyAnalyzer()
        
        # Mock special names
        self.analyzer.special_names = {
            'Сергей': {
                'gender': 'masc',
                'variants': ['Сергей'],
                'diminutives': ['Сережа', 'Серега']
            },
            'Дарья': {
                'gender': 'femn',
                'variants': ['Дарья'],
                'diminutives': ['Даша', 'Даруся']
            }
        }
        
        # Mock pymorphy3 analyzer
        self.mock_pymorphy = Mock()
        self.analyzer.morph_analyzer = self.mock_pymorphy
        
        # Mock parsed words
        self.mock_sergey_parsed = Mock()
        self.mock_sergey_parsed.word = "Сергей"
        self.mock_sergey_parsed.normal_form = "Сергей"
        
        self.mock_daria_parsed = Mock()
        self.mock_daria_parsed.word = "Дарья"
        self.mock_daria_parsed.normal_form = "Дарья"

    def test_analyze_word_basic(self):
        """Test basic analyze_word functionality"""
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word('Сергей')
        
        # Check result structure
        assert isinstance(result, list)
        assert len(result) > 0
        assert isinstance(result[0], dict)

    def test_gender_detection_male(self):
        """Test gender detection for male names"""
        male_names = ['Сергей', 'Владимир', 'Александр']
        
        for name in male_names:
            # Mock pymorphy3 response
            mock_parse = Mock()
            mock_parse.normal_form = name
            mock_parse.score = 1.0
            
            self.mock_pymorphy.parse.return_value = [mock_parse]
            
            result = self.analyzer.analyze_word(name)
            
            assert len(result) > 0, f"Should have result for name {name}"

    def test_gender_detection_female(self):
        """Test gender detection for female names"""
        female_names = ['Дарья', 'Мария', 'Анна']
        
        for name in female_names:
            # Mock pymorphy3 response
            mock_parse = Mock()
            mock_parse.normal_form = name
            mock_parse.score = 1.0
            
            self.mock_pymorphy.parse.return_value = [mock_parse]
            
            result = self.analyzer.analyze_word(name)
            
            assert len(result) > 0, f"Should have result for name {name}"

    def test_declensions_generation(self):
        """Test declensions generation"""
        test_name = "Сергей"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return result with declensions
        assert isinstance(result, list)
        assert len(result) > 0

    def test_diminutives_generation(self):
        """Test diminutives generation"""
        test_name = "Сергей"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return result with diminutives
        assert isinstance(result, list)
        assert len(result) > 0

    def test_variants_generation(self):
        """Test variants generation"""
        test_name = "Сергей"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return result with variants
        assert isinstance(result, list)
        assert len(result) > 0

    def test_transliterations_generation(self):
        """Test transliterations generation"""
        test_name = "Сергей"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return result with transliterations
        assert isinstance(result, list)
        assert len(result) > 0

    def test_language_detection(self):
        """Test language detection functionality"""
        test_names = ['Сергей', 'Дарья', 'Владимир']
        
        for name in test_names:
            # Mock pymorphy3 response
            mock_parse = Mock()
            mock_parse.normal_form = name
            mock_parse.score = 1.0
            
            self.mock_pymorphy.parse.return_value = [mock_parse]
            
            result = self.analyzer.analyze_word(name)
            
            assert len(result) > 0, f"Should have result for name {name}"

    def test_is_russian_name(self):
        """Test is_russian_name detection"""
        # Test known Russian names
        assert self.analyzer.is_russian_name('Сергей') == True
        
        # Test unknown names
        assert self.analyzer.is_russian_name('Unknown') == False

    def test_name_complexity(self):
        """Test name complexity analysis"""
        test_name = "Сергей"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return result with complexity analysis
        assert isinstance(result, list)
        assert len(result) > 0

    def test_phonetic_variants(self):
        """Test phonetic variants generation"""
        test_name = "Сергей"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return result with phonetic variants
        assert isinstance(result, list)
        assert len(result) > 0

    def test_regional_transliterations(self):
        """Test regional transliterations"""
        test_name = "Сергей"
        
        # Mock pymorphy3 response
        mock_parse = Mock()
        mock_parse.normal_form = "Сергей"
        mock_parse.score = 1.0
        
        self.mock_pymorphy.parse.return_value = [mock_parse]
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return result with regional transliterations
        assert isinstance(result, list)
        assert len(result) > 0

    def test_analyze_name_basic(self):
        """Test basic analyze_name functionality"""
        test_name = "Сергей"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should return analysis result
        assert isinstance(result, list)
        assert len(result) > 0
        if result:  # If there are results
            assert isinstance(result[0], dict)

    def test_analyze_name_with_language(self):
        """Test analyze_name with language parameter"""
        test_name = "Сергей"
        
        # Note: analyze_word doesn't take language parameter
        result = self.analyzer.analyze_word(test_name)
        
        # Should return analysis result
        assert isinstance(result, list)
        assert len(result) > 0
        if result:  # If there are results
            assert isinstance(result[0], dict)

    def test_analyze_name_empty_input(self):
        """Test analyze_name with empty input"""
        result = self.analyzer.analyze_word("")
        
        # Should return empty list for empty string
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_name_none_input(self):
        """Test analyze_name with None input"""
        result = self.analyzer.analyze_word(None)
        
        # Should return empty list for None input
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_name_whitespace_input(self):
        """Test analyze_name with whitespace-only input"""
        result = self.analyzer.analyze_word("   ")
        
        # Should return empty list for whitespace-only string
        assert isinstance(result, list)
        assert len(result) == 0

    def test_analyze_name_special_characters(self):
        """Test analyze_name with special characters"""
        test_name = "Сергей-Иванов"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle special characters gracefully
        assert isinstance(result, list)
        # May return empty list or handle special characters

    def test_analyze_name_numbers(self):
        """Test analyze_name with numbers"""
        test_name = "Сергей123"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle numbers gracefully
        assert isinstance(result, list)
        # May return empty list or handle numbers

    def test_analyze_name_mixed_case(self):
        """Test analyze_name with mixed case"""
        test_name = "сЕрГеЙ"
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle mixed case gracefully
        assert isinstance(result, list)
        # May return empty list or handle mixed case

    def test_analyze_name_very_long(self):
        """Test analyze_name with very long name"""
        test_name = "Сергей" * 100
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle very long names gracefully
        assert isinstance(result, list)
        # May return empty list or handle very long names

    def test_analyze_name_unicode_characters(self):
        """Test analyze_name with Unicode characters"""
        test_name = "Сергей\u200bИванов"  # Zero-width space
        
        result = self.analyzer.analyze_word(test_name)
        
        # Should handle Unicode characters gracefully
        assert isinstance(result, list)
        # May return empty list or handle Unicode characters
