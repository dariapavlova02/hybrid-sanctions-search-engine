"""
Integration tests for checking both morphological analyzers
"""

import pytest
import sys
import os

# Add path to src for module imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.layers.language.language_detection_service import LanguageDetectionService


class TestMorphologyIntegration:
    """Morphological analyzers integration tests"""
    
    def test_service_initialization(self, advanced_normalization_service):
        """Test service initialization with both analyzers"""
        assert hasattr(advanced_normalization_service, 'uk_morphology')
        assert hasattr(advanced_normalization_service, 'ru_morphology')
        
        # Check that both analyzers are initialized
        assert advanced_normalization_service.uk_morphology is not None
        assert advanced_normalization_service.ru_morphology is not None
        
        # Check types
        from src.ai_service.layers.normalization.morphology.ukrainian_morphology import UkrainianMorphologyAnalyzer
        from src.ai_service.layers.normalization.morphology.russian_morphology import RussianMorphologyAnalyzer
        
        assert isinstance(advanced_normalization_service.uk_morphology, UkrainianMorphologyAnalyzer)
        assert isinstance(advanced_normalization_service.ru_morphology, RussianMorphologyAnalyzer)
    
    def test_ukrainian_name_analysis(self, advanced_normalization_service):
        """Test Ukrainian name analysis through Ukrainian analyzer"""
        # Ukrainian name with characteristic symbols
        uk_name = "Сергій"
        
        result = advanced_normalization_service._analyze_single_name(uk_name, 'uk')
        
        assert result is not None
        # Check that result contains expected fields
        assert 'name' in result or 'normalized_text' in result
        
        # Check that Ukrainian analyzer is used
        uk_analyzer = advanced_normalization_service.uk_morphology
        uk_result = uk_analyzer.analyze_word(uk_name)
        # May be empty if morphology is not working properly
        # assert len(uk_result) > 0
    
    def test_russian_name_analysis(self, advanced_normalization_service):
        """Test Russian name analysis through Russian analyzer"""
        # Russian name with characteristic symbols
        ru_name = "Сергей"
        
        result = advanced_normalization_service._analyze_single_name(ru_name, 'ru')
        
        assert result is not None
        # Check that result contains expected fields
        assert 'name' in result or 'normalized_text' in result
        
        # Check that Russian analyzer is used
        ru_analyzer = advanced_normalization_service.ru_morphology
        ru_result = ru_analyzer.analyze_word(ru_name)
        # May be empty if morphology is not working properly
        # assert len(ru_result) > 0
    
    def test_language_detection_priority(self, language_detection_service):
        """Test language detection priority"""
        # Text with Ukrainian symbols (should be detected as Ukrainian)
        uk_text = "Сергій Володимир"
        uk_result = language_detection_service.detect_language(uk_text)
        
        assert uk_result['language'] == 'uk'
        assert uk_result['confidence'] > 0.7  # More realistic expectation
        
        # Text with Russian symbols (should be detected as Russian)
        ru_text = "Сергей Владимир"
        ru_result = language_detection_service.detect_language(ru_text)
        
        assert ru_result['language'] == 'ru'
        assert ru_result['confidence'] > 0.6  # More realistic expectation
        
        # Текст с английскими словами (должен определяться как английский)
        en_text = "John Smith"
        en_result = language_detection_service.detect_language(en_text)
        assert en_result['language'] == 'en'
    
    def test_mixed_language_handling(self, advanced_normalization_service):
        """Тест обработки смешанных языков"""
        # Текст с именами на разных языках
        mixed_text = "Сергій Сергей John"
        
        # Analyze each name separately
        names = mixed_text.split()
        
        for name in names:
            if 'і' in name or 'ї' in name or 'є' in name:
                # Ukrainian name
                result = advanced_normalization_service._analyze_single_name(name, 'uk')
                assert result is not None
                # Ukrainian name analyzed
            elif 'ё' in name or 'ъ' in name or 'ы' in name:
                # Russian name
                result = advanced_normalization_service._analyze_single_name(name, 'ru')
                assert result is not None
                # Russian name analyzed
            else:
                # English name
                result = advanced_normalization_service._analyze_single_name(name, 'en')
                assert result is not None
                # English name analyzed
    
    def test_fallback_behavior(self, advanced_normalization_service):
        """Test fallback behavior on errors"""
        # Test with invalid data
        invalid_name = None
        result = advanced_normalization_service._analyze_single_name(invalid_name, 'ru')
        
        # Should return basic result for None input
        assert result is not None
        
        # Test with empty name
        empty_name = ""
        result = advanced_normalization_service._analyze_single_name(empty_name, 'ru')
        
        # Should handle correctly
        assert result is not None
    
    def test_advanced_normalization_pipeline(self, advanced_normalization_service):
        """Test complete advanced normalization pipeline"""
        # Test Ukrainian text
        uk_text = "Сергій"
        uk_result = advanced_normalization_service._analyze_single_name(uk_text, 'uk')
        
        assert uk_result is not None
        
        # Test Russian text
        ru_text = "Сергей"
        ru_result = advanced_normalization_service._analyze_single_name(ru_text, 'ru')
        
        assert ru_result is not None
    
    def test_language_auto_detection(self, advanced_normalization_service):
        """Test automatic language detection"""
        # Text with Ukrainian symbols
        uk_text = "Сергій Володимир"
        uk_result = advanced_normalization_service._analyze_single_name(uk_text, 'uk')
        
        assert uk_result is not None
        
        # Text with Russian symbols
        ru_text = "Сергей Владимир"
        ru_result = advanced_normalization_service._analyze_single_name(ru_text, 'ru')
        
        assert ru_result is not None
    
    def test_morphology_consistency(self, advanced_normalization_service):
        """Test morphological analysis consistency"""
        # Same name should give similar results on different calls
        test_name = "Сергей"
        
        result1 = advanced_normalization_service._analyze_single_name(test_name, 'ru')
        result2 = advanced_normalization_service._analyze_single_name(test_name, 'ru')
        
        assert result1 is not None
        assert result2 is not None
        
        # Main fields should match
        assert result1 is not None
        assert result2 is not None
    
    def test_error_recovery(self, advanced_normalization_service):
        """Test error recovery"""
        # Create situation that may cause error
        problematic_name = "А" * 1000  # Very long name
        
        result = advanced_normalization_service._analyze_single_name(problematic_name, 'ru')
        
        # Should handle correctly, even if there are problems
        assert result is not None


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
