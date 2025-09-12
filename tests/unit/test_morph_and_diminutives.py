"""
Unit tests for morphological normalization and diminutives expansion
"""

import pytest
from src.ai_service.services.normalization_service import NormalizationService


class TestMorphologyAndDiminutives:
    """Test morphological normalization and diminutives expansion"""
    
    @pytest.fixture
    def service(self):
        """Create NormalizationService instance"""
        return NormalizationService()
    
    def test_morph_nominal_caching(self, service):
        """Test that _morph_nominal uses caching"""
        # First call should populate cache
        result1 = service._morph_nominal("Петрович", "ru")
        
        # Second call should use cache
        result2 = service._morph_nominal("Петрович", "ru")
        
        assert result1 == result2
        assert result1 == "Петрович"  # Should be nominative
    
    def test_morph_nominal_name_surn_priority(self, service):
        """Test that Name/Surn parts of speech are prioritized"""
        # Test with a word that could be multiple parts of speech
        result = service._morph_nominal("Петров", "ru")
        assert result == "Петров"  # Should be nominative
    
    def test_ukrainian_surname_enko_indeclinable(self, service):
        """Test that -енко surnames are kept indeclinable"""
        result = service._morph_nominal("Коваленко", "uk")
        assert result == "Коваленко"  # Should remain unchanged
    
    def test_ukrainian_surname_sky_forms(self, service):
        """Test Ukrainian -ський/-ська surname forms"""
        # Test feminine form -> masculine
        result = service._ukrainian_surname_normalization("Петровська")
        assert result == "Петровський"
        
        # Test genitive feminine -> masculine
        result = service._ukrainian_surname_normalization("Петровської")
        assert result == "Петровський"
        
        # Test dative masculine -> masculine
        result = service._ukrainian_surname_normalization("Петровському")
        assert result == "Петровський"
    
    def test_ukrainian_surname_tsky_forms(self, service):
        """Test Ukrainian -цький/-цька surname forms"""
        # Test feminine form -> masculine
        result = service._ukrainian_surname_normalization("Петровцька")
        assert result == "Петровцький"
        
        # Test genitive feminine -> masculine
        result = service._ukrainian_surname_normalization("Петровцької")
        assert result == "Петровцький"
    
    def test_ukrainian_surname_ov_forms(self, service):
        """Test Ukrainian -ов/-ова surname forms"""
        # Test feminine form -> masculine
        result = service._ukrainian_surname_normalization("Петрова")
        assert result == "Петров"
        
        # Test genitive feminine -> masculine
        result = service._ukrainian_surname_normalization("Петрової")
        assert result == "Петров"
    
    def test_russian_diminutives_expansion(self, service):
        """Test Russian diminutives expansion"""
        # Test common Russian diminutives
        test_cases = [
            ("вова", "Владимир"),
            ("петрик", "Петр"),
            ("саша", "Александр"),
            ("дима", "Дмитрий"),
            ("женя", "Евгений"),
            ("даша", "Дарья"),
            ("катя", "Екатерина"),
            ("настя", "Анастасия"),
        ]
        
        for diminutive, expected in test_cases:
            result = service._normalize_sync(f"{diminutive} Петров", language="ru")
            assert expected in result.normalized
            assert diminutive.capitalize() not in result.normalized
    
    def test_ukrainian_diminutives_expansion(self, service):
        """Test Ukrainian diminutives expansion"""
        # Test common Ukrainian diminutives
        test_cases = [
            ("вова", "Володимир"),
            ("петрик", "Петро"),
            ("сашка", "Олександр"),
            ("діма", "Дмитро"),
            ("женя", "Євген"),
            ("даша", "Дарія"),
            ("катя", "Катерина"),
            ("настя", "Анастасія"),
        ]
        
        for diminutive, expected in test_cases:
            result = service._normalize_sync(f"{diminutive} Коваленко", language="uk")
            assert expected in result.normalized
            assert diminutive.capitalize() not in result.normalized
    
    def test_english_nicknames_expansion(self, service):
        """Test English nicknames expansion"""
        # Test common English nicknames
        test_cases = [
            ("bill", "William"),
            ("mike", "Michael"),
            ("bob", "Robert"),
            ("jim", "James"),
            ("tom", "Thomas"),
            ("liz", "Elizabeth"),
            ("kate", "Katherine"),
            ("jen", "Jennifer"),
        ]
        
        for nickname, expected in test_cases:
            result = service._normalize_sync(f"{nickname} Smith", language="en")                                
            assert expected in result.normalized
            # Check that the original nickname is not in the result (exact match, case-insensitive)
            assert f" {nickname.lower()} " not in f" {result.normalized.lower()} "
    
    def test_surname_gender_adjustment_male(self, service):
        """Test surname gender adjustment for male person"""
        # Test with male given name
        result = service._normalize_sync("Владимир Петров", language="ru")
        assert "Петров" in result.normalized  # Should remain masculine
        
        # Test with female given name
        result = service._normalize_sync("Анна Петров", language="ru")
        assert "Петрова" in result.normalized  # Should be feminine
    
    def test_surname_gender_adjustment_ukrainian(self, service):
        """Test surname gender adjustment for Ukrainian"""
        # Test with male given name
        result = service._normalize_sync("Володимир Коваленко", language="uk")
        assert "Коваленко" in result.normalized  # Should remain indeclinable
        
        # Test with -ський surname
        result = service._normalize_sync("Володимир Петровський", language="uk")
        assert "Петровський" in result.normalized  # Should remain masculine
    
    def test_compound_surname_gender_adjustment(self, service):
        """Test gender adjustment for compound surnames"""
        # Test compound surname with female name
        result = service._normalize_sync("Анна Петров-Сидоров", language="ru")
        assert "Петрова-Сидорова" in result.normalized
        
        # Test compound surname with male name
        result = service._normalize_sync("Владимир Петров-Сидоров", language="ru")
        assert "Петров-Сидоров" in result.normalized
    
    def test_morphology_preserves_case(self, service):
        """Test that morphology preserves original case"""
        # Test with uppercase
        result = service._morph_nominal("ПЕТРОВ", "ru")
        assert result == "ПЕТРОВ"
        
        # Test with title case
        result = service._morph_nominal("Петров", "ru")
        assert result == "Петров"
        
        # Test with lowercase
        result = service._morph_nominal("петров", "ru")
        assert result == "петров"
    
    def test_morphology_handles_compound_words(self, service):
        """Test that morphology handles compound words correctly"""
        # Test compound word with hyphen
        result = service._morph_nominal("Петров-Сидоров", "ru")
        assert result == "Петров-Сидоров"
        
        # Test compound word with apostrophe
        result = service._morph_nominal("O'Brien", "en")
        assert result == "O'Brien"
    
    def test_diminutives_with_morphology(self, service):
        """Test diminutives expansion with morphological analysis"""
        # Test that diminutives are expanded even after morphological analysis
        result = service._normalize_sync("петрика", language="uk")
        assert "Петро" in result.normalized
        assert "петрика" not in result.normalized
    
    def test_advanced_features_flag_affects_diminutives(self, service):
        """Test that enable_advanced_features flag affects diminutives"""
        # With advanced features enabled
        result_enabled = service._normalize_sync("петрик Коваленко", language="uk", 
                                               enable_advanced_features=True)
        assert "Петро" in result_enabled.normalized
        
        # With advanced features disabled
        result_disabled = service._normalize_sync("петрик Коваленко", language="uk", 
                                                enable_advanced_features=False)
        assert "Петрик" in result_disabled.normalized  # Should not expand diminutive
    
    def test_advanced_features_flag_affects_morphology(self, service):
        """Test that enable_advanced_features flag affects morphology"""
        # With advanced features enabled
        result_enabled = service._normalize_sync("Сергея Петрова", language="ru", 
                                               enable_advanced_features=True)
        assert "Сергей Петров" in result_enabled.normalized
        
        # With advanced features disabled
        result_disabled = service._normalize_sync("Сергея Петрова", language="ru", 
                                                enable_advanced_features=False)
        assert "Сергея Петрова" in result_disabled.normalized  # Should not morph
    
    def test_unknown_diminutive_fallback(self, service):
        """Test fallback when diminutive is not found"""
        # Test with unknown diminutive
        result = service._normalize_sync("неизвестный Коваленко", language="uk")                                
        assert "Коваленко" in result.normalized  # Should keep the surname
    
    def test_mixed_language_diminutives(self, service):
        """Test diminutives in mixed language context"""
        # Test Ukrainian diminutive in Russian context
        result = service._normalize_sync("петрик Коваленко", language="ru")
        # Should try both languages
        assert "Петр" in result.normalized or "Петро" in result.normalized
