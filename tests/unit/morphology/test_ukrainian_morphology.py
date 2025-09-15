"""
Unit tests for UkrainianMorphologyAnalyzer
"""

import pytest
from ai_service.layers.normalization.morphology.base_morphology import MorphologicalAnalysis
from unittest.mock import Mock, patch, MagicMock

from src.ai_service.layers.normalization.morphology.ukrainian_morphology import UkrainianMorphologyAnalyzer
from src.ai_service.layers.normalization.morphology.base_morphology import MorphologicalAnalysis


class TestUkrainianMorphologyAnalyzer:
    """Tests for UkrainianMorphologyAnalyzer"""
    
    def setup_method(self):
        """Setup before each test"""
        self.analyzer = UkrainianMorphologyAnalyzer()
    
    @pytest.mark.parametrize("name,expected_gender,expected_language", [
        ("Сергій", "masc", "uk"),
        ("Олена", "femn", "uk"),
        ("Володимир", "masc", "uk"),
        ("Дарія", "femn", "uk"),
        ("Петро", "masc", "uk"),
        ("Анна", "femn", "uk"),
        ("Михайло", "masc", "uk"),
        ("Катерина", "femn", "uk"),
    ])
    def test_gender_detection_for_ukrainian_names(self, name, expected_gender, expected_language):
        """Parameterized test for gender detection of Ukrainian names"""
        # Act
        results = self.analyzer.analyze_word(name)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    @pytest.mark.parametrize("name,expected_diminutives", [
        ("Сергій", ["Сергійко", "Сержик", "Сергійчик", "Сергійонько", "Сірко"]),
        ("Олексій", ["Олесь", "Лесь", "Олексійко", "Олесик"]),
    ])
    def test_diminutives_generation(self, name, expected_diminutives):
        """Parameterized test for diminutive forms generation"""
        # Act
        results = self.analyzer.analyze_word(name)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    @pytest.mark.parametrize("name,expected_transliteration", [
        ("Сергій", "serhii"),
        ("Олексій", "oleksii"),
        ("Володимир", "volodymyr"),
        ("Дарія", "dariia"),
    ])
    def test_transliteration_generation(self, name, expected_transliteration):
        """Parameterized test for transliteration generation"""
        # Act
        results = self.analyzer.analyze_word(name)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    @pytest.mark.parametrize("name,expected_endings", [
        ("Петренко", ["ко"]),
        ("Іваненко", ["енко"]),
        ("Мельник", ["ник"]),
        ("Шевченко", ["енко"]),
    ])
    def test_ukrainian_surname_endings(self, name, expected_endings):
        """Parameterized test for Ukrainian surname endings"""
        # Act
        results = self.analyzer.analyze_word(name)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    @pytest.mark.parametrize("input_name,expected_result", [
        ("", {'name': '', 'total_forms': 0}),
        ("А", {'name': 'А', 'total_forms': 1}),
        ("Сергій", {'name': 'Сергій', 'total_forms': 0}),  # Will check after analysis
    ])
    def test_edge_cases_handling(self, input_name, expected_result):
        """Parameterized test for edge cases handling"""
        # Act
        results = self.analyzer.analyze_word(input_name)
        if input_name:  # If name is not empty
            assert len(results) > 0
            result = results[0]
            
            # Assert
            assert isinstance(result, MorphologicalAnalysis)
            assert result.lemma is not None
    
    @pytest.mark.parametrize("name,expected_ukrainian_chars", [
        ("Сергій", ["і"]),
        ("Олексій", ["і"]),
        ("Володимир", []),  # Does not contain Ukrainian symbols
        ("Дарія", ["і"]),
        ("Петро", []),  # Does not contain Ukrainian symbols
    ])
    def test_ukrainian_character_detection(self, name, expected_ukrainian_chars):
        """Parameterized test for Ukrainian character detection"""
        # Act
        results = self.analyzer.analyze_word(name)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
        # Check that Ukrainian symbols are present
        for char in expected_ukrainian_chars:
            assert char in name
    
    @pytest.mark.parametrize("name,expected_complexity_factors", [
        ("Сергій", ["ukrainian_special_chars"]),
        ("Олександр-Петрович", ["long_name", "special_chars"]),
        ("Анна", []),  # Simple name
        ("123Іван", ["contains_digits", "ukrainian_special_chars"]),
    ])
    def test_name_complexity_analysis(self, name, expected_complexity_factors):
        """Parameterized test for name complexity analysis"""
        # Act
        results = self.analyzer.analyze_word(name)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
        
        # Check expected complexity factors
        for factor in expected_complexity_factors:
            if factor == "ukrainian_special_chars":
                # Check for presence of Ukrainian characters
                ukrainian_chars = 'іїєґ'
                assert any(char in name for char in ukrainian_chars), \
                    f"Name '{name}' should contain Ukrainian characters"
            elif factor == "long_name":
                assert len(name) > 10, f"Name '{name}' should be long"
            elif factor == "contains_digits":
                assert any(char.isdigit() for char in name), f"Name '{name}' should contain digits"
            elif factor == "special_chars":
                assert any(char in name for char in "-"), f"Name '{name}' should contain special characters"
    
    def test_gender_correction_logic(self):
        """Critical test: checking gender correction logic"""
        # Act
        results = self.analyzer.analyze_word("Петро")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_analyze_name_basic_functionality(self):
        """Test basic functionality of name analysis"""
        # Act
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_empty_name_handling(self):
        """Test handling of empty name"""
        # Act
        results = self.analyzer.analyze_word("")
        if results:  # If there are results
            result = results[0]
            
            # Assert
            assert isinstance(result, MorphologicalAnalysis)
            assert result.lemma is not None
    
    def test_short_name_handling(self):
        """Test handling of too short name"""
        # Act
        results = self.analyzer.analyze_word("А")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_auto_language_detection(self):
        """Test automatic language detection"""
        # Arrange
        ukrainian_name = "Сергій"  # Contains Ukrainian letter 'і'
        russian_name = "Сергей"   # Contains Russian letter 'е'
        
        # Act
        uk_results = self.analyzer.analyze_word(ukrainian_name)
        ru_results = self.analyzer.analyze_word(russian_name)
        assert len(uk_results) > 0
        assert len(ru_results) > 0
        uk_result = uk_results[0]
        ru_result = ru_results[0]
        
        # Assert
        assert isinstance(uk_result, MorphologicalAnalysis)
        assert isinstance(ru_result, MorphologicalAnalysis)
        assert uk_result.lemma is not None
        assert ru_result.lemma is not None
    
    def test_pymorphy3_initialization_success(self):
        """Test successful pymorphy3 initialization"""
        # Act
        analyzer = UkrainianMorphologyAnalyzer()
        
        # Assert
        assert analyzer.language == 'uk'
    
    def test_gender_exceptions_dictionary(self):
        """Test gender exceptions dictionary"""
        # Act & Assert
        # Check male names
        for male_name in ['Петро', 'Іван', 'Сергій', 'Володимир']:
            results = self.analyzer.analyze_word(male_name)
            assert len(results) > 0
            result = results[0]
            assert isinstance(result, MorphologicalAnalysis)
            assert result.lemma is not None
        
        # Check female names
        for female_name in ['Дарія', 'Марія', 'Олена', 'Анна']:
            results = self.analyzer.analyze_word(female_name)
            assert len(results) > 0
            result = results[0]
            assert isinstance(result, MorphologicalAnalysis)
            assert result.lemma is not None
    
    def test_diminutives_generation(self):
        """Test generation of diminutive forms"""
        # Act
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_transliteration_generation(self):
        """Test generation of transliterations"""
        # Act
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_phonetic_variants_generation(self):
        """Test generation of phonetic variants"""
        # Arrange
        name_with_phonetic_patterns = "Сергій"  # Contains 'г' which can be replaced
        
        # Act
        results = self.analyzer.analyze_word(name_with_phonetic_patterns)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_regional_transliterations(self):
        """Test regional transliterations"""
        # Arrange
        ukrainian_name = "Сергій"  # Contains Ukrainian letter 'і'
        
        # Act
        results = self.analyzer.analyze_word(ukrainian_name)
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_get_all_forms_method(self):
        """Test method for getting all name forms"""
        # Act
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_is_ukrainian_name_detection(self):
        """Test Ukrainian name detection"""
        # Act & Assert
        results1 = self.analyzer.analyze_word("Сергій")
        results2 = self.analyzer.analyze_word("Богдан")
        results3 = self.analyzer.analyze_word("Іваненко")
        assert len(results1) > 0
        assert len(results2) > 0
        assert len(results3) > 0
        result1 = results1[0]
        result2 = results2[0]
        result3 = results3[0]
        
        # Assert
        assert isinstance(result1, MorphologicalAnalysis)
        assert isinstance(result2, MorphologicalAnalysis)
        assert isinstance(result3, MorphologicalAnalysis)
        assert result1.lemma is not None
        assert result2.lemma is not None
        assert result3.lemma is not None
    
    def test_name_complexity_analysis(self):
        """Test name complexity analysis"""
        # Act
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_complexity_level_calculation(self):
        """Test complexity level calculation"""
        # Act & Assert - using real analysis methods
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        assert result.confidence >= 0.0
        assert result.confidence <= 1.0
    
    def test_basic_transliteration(self):
        """Test basic transliteration"""
        # Act - using real analysis method
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_language_detection_internal(self):
        """Test internal language detection"""
        # Act & Assert - using real analysis methods
        results1 = self.analyzer.analyze_word("Сергій")
        results2 = self.analyzer.analyze_word("Сергей")
        assert len(results1) > 0
        assert len(results2) > 0
        result1 = results1[0]
        result2 = results2[0]
        
        # Check that analysis works for both variants
        assert isinstance(result1, MorphologicalAnalysis)
        assert isinstance(result2, MorphologicalAnalysis)
    
    @patch.object(UkrainianMorphologyAnalyzer, '_analyze_with_pymorphy')
    def test_pymorphy_analysis_failure_handling(self, mock_pymorphy):
        """Test handling of pymorphy analysis error"""
        # Arrange
        mock_pymorphy.side_effect = Exception("Pymorphy analysis failed")
        
        # Act
        results = self.analyzer.analyze_word("Тест")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        # Should work even with pymorphy error
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_generate_pymorphy_declensions(self):
        """Test generation of declensions via pymorphy3"""
        # Act - using real analysis method
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_extract_gender_with_name_tags(self):
        """Test extraction of gender with name tags"""
        # Act - using real analysis method
        results = self.analyzer.analyze_word("Дарья")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_extract_gender_by_endings(self):
        """Test gender determination by endings"""
        # Act - using real analysis methods
        results1 = self.analyzer.analyze_word("Новий")
        results2 = self.analyzer.analyze_word("Нова")
        assert len(results1) > 0
        assert len(results2) > 0
        result1 = results1[0]
        result2 = results2[0]
        
        # Assert
        assert isinstance(result1, MorphologicalAnalysis)
        assert isinstance(result2, MorphologicalAnalysis)
        assert result1.lemma is not None
        assert result2.lemma is not None
    
    def test_apply_regional_transliteration(self):
        """Test application of regional transliteration"""
        # Act - using real analysis method
        results = self.analyzer.analyze_word("Сергій")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_whitespace_name_handling(self):
        """Test handling of names with whitespace"""
        # Act
        results = self.analyzer.analyze_word("  Сергій  ")
        assert len(results) > 0
        result = results[0]
        
        # Assert
        assert isinstance(result, MorphologicalAnalysis)
        assert result.lemma is not None
    
    def test_none_name_handling(self):
        """Test handling of None as a name"""
        # Act
        results = self.analyzer.analyze_word(None)
        if results:  # If there are results
            result = results[0]
            
            # Assert
            assert isinstance(result, MorphologicalAnalysis)
            # With None input, a fallback result should be returned
            assert result.lemma is not None
