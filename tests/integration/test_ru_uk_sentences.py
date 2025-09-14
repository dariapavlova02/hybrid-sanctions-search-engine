"""
Integration tests for Russian and Ukrainian sentence normalization
"""

import pytest
from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestRussianUkrainianSentences:
    """Test complex Russian and Ukrainian sentence normalization"""
    
    @pytest.fixture
    def service(self):
        """Create NormalizationService instance"""
        return NormalizationService()
    
    def test_russian_complex_sentence(self, service):
        """Test complex Russian sentence with multiple names and diminutives"""
        text = "Перевод средств на имя Петра Ивановича Коваленко от Сергея Петровича Сидорова"
        result = service._normalize_sync(text, language="ru")
        
        # Check that all personal names are normalized
        assert "Петр Иванович Коваленко" in result.normalized
        assert "Сергей Петрович Сидоров" in result.normalized
        
        # Check that diminutives are expanded
        assert "Петр" in result.normalized
        assert "Сергей" in result.normalized
        
        # Check that patronymics are normalized
        assert "Иванович" in result.normalized
        assert "Петрович" in result.normalized
    
    def test_ukrainian_complex_sentence(self, service):
        """Test complex Ukrainian sentence with multiple names and diminutives"""
        text = "Переказ коштів на ім'я Петра Івановича Коваленка від Сергія Петровича Сидорова"
        result = service._normalize_sync(text, language="uk")
        
        # Check that all personal names are normalized
        assert "Петро Іванович Коваленко" in result.normalized
        assert "Сергій Петрович Сидоров" in result.normalized
        
        # Check that diminutives are expanded
        assert "Петро" in result.normalized
        assert "Сергій" in result.normalized
        
        # Check that patronymics are normalized
        assert "Іванович" in result.normalized
        assert "Петрович" in result.normalized
    
    def test_mixed_case_names(self, service):
        """Test names with mixed case"""
        text = "петр ИВАНОВИЧ коваленко"
        result = service._normalize_sync(text, language="ru")
        
        # Check that case is normalized
        assert "Петр Иванович Коваленко" in result.normalized
    
    def test_compound_surnames(self, service):
        """Test compound surnames"""
        text = "Анна Петровна Петрова-Сидорова"
        result = service._normalize_sync(text, language="ru")
        
        # Check that compound surname is normalized
        assert "Анна Петровна Петрова-Сидорова" in result.normalized
    
    def test_quoted_names(self, service):
        """Test quoted names"""
        text = "Перевод от 'Петра Ивановича' Коваленко"
        result = service._normalize_sync(text, language="ru")
        
        # Check that quoted name is handled
        assert "Петр Иванович" in result.normalized
        assert "Коваленко" in result.normalized
    
    def test_organizations_with_personal_names(self, service):
        """Test organizations alongside personal names"""
        text = "ТОВ 'ПРИВАТБАНК' та Петро Коваленко працюють разом"
        result = service._normalize_sync(text, language="uk")
        
        # Check that personal names are normalized
        assert "Петро Коваленко" in result.normalized
        
        # Check that organizations are extracted separately
        assert result.organizations == ["ПРИВАТБАНК"]
        
        # Check that non-name words are filtered out
        assert "працюють" not in result.normalized
        assert "разом" not in result.normalized
    
    def test_multiple_persons_same_surname(self, service):
        """Test multiple persons with same surname"""
        text = "Владимир и Анна Петровы работают вместе"
        result = service._normalize_sync(text, language="ru")
        
        # Check that both names are normalized with correct gender
        assert "Владимир Петров" in result.normalized
        assert "Анна Петрова" in result.normalized
    
    def test_diminutives_in_context(self, service):
        """Test diminutives in full sentence context"""
        text = "Вова и Петя пришли к нам в гости"
        result = service._normalize_sync(text, language="ru")
        
        # Check that diminutives are expanded
        assert "Владимир" in result.normalized
        assert "Петр" in result.normalized
        
        # Check that diminutives are not in final result
        assert "Вова" not in result.normalized
        assert "Петя" not in result.normalized
    
    def test_ukrainian_diminutives_in_context(self, service):
        """Test Ukrainian diminutives in full sentence context"""
        text = "Вова і Петрик прийшли до нас у гості"
        result = service._normalize_sync(text, language="uk")
        
        # Check that diminutives are expanded
        assert "Володимир" in result.normalized
        assert "Петро" in result.normalized
        
        # Check that diminutives are not in final result
        assert "Вова" not in result.normalized
        assert "Петрик" not in result.normalized
    
    def test_english_names_in_ukrainian_context(self, service):
        """Test English names in Ukrainian context"""
        text = "Bill Smith та Петро Коваленко працюють разом"
        result = service._normalize_sync(text, language="uk")
        
        # Check that English name is normalized
        assert "William Smith" in result.normalized
        assert "Петро Коваленко" in result.normalized
    
    def test_initial_handling_in_sentences(self, service):
        """Test initial handling in full sentences"""
        text = "П.І. Коваленко та В.С. Сидоров прийшли"
        result = service._normalize_sync(text, language="uk")
        
        # Check that initials are properly handled
        assert "П. І. Коваленко" in result.normalized
        assert "В. С. Сидоров" in result.normalized
    
    def test_patronymic_variations(self, service):
        """Test various patronymic forms"""
        text = "Петр Иванович, Петр Ивановна, Петр Иваныч"
        result = service._normalize_sync(text, language="ru")
        
        # Check that patronymics are normalized
        assert "Петр Иванович" in result.normalized
        assert "Петр Ивановна" in result.normalized
        assert "Петр Иваныч" in result.normalized
    
    def test_surname_variations(self, service):
        """Test various surname forms"""
        text = "Петров, Петрова, Петровым, Петрову"
        result = service._normalize_sync(text, language="ru")
        
        # Check that surnames are normalized to nominative
        assert "Петров" in result.normalized
        assert "Петрова" in result.normalized
    
    def test_ukrainian_surname_variations(self, service):
        """Test Ukrainian surname variations"""
        text = "Коваленко, Коваленка, Коваленком, Коваленку"
        result = service._normalize_sync(text, language="uk")
        
        # Check that -енко surnames remain unchanged
        assert "Коваленко" in result.normalized
    
    def test_organization_legal_forms_filtering(self, service):
        """Test that legal forms are filtered out"""
        text = "ТОВ 'ПРИВАТБАНК' ООО 'ТЕСТ' LLC 'EXAMPLE'"
        result = service._normalize_sync(text, language="uk")
        
        # Check that legal forms are not in normalized
        assert "ТОВ" not in result.normalized
        assert "ООО" not in result.normalized
        assert "LLC" not in result.normalized
        
        # Check that organization cores are extracted
        assert "ПРИВАТБАНК" in result.organizations
        assert "ТЕСТ" in result.organizations
        assert "EXAMPLE" in result.organizations
    
    def test_performance_with_long_text(self, service):
        """Test performance with longer text"""
        text = " ".join([
            "Петр Иванович Коваленко", "Анна Петровна Сидорова",
            "Владимир Сергеевич Петров", "Елена Александровна Козлова",
            "Михаил Николаевич Смирнов", "Ольга Владимировна Морозова"
        ])
        
        result = service._normalize_sync(text, language="ru")
        
        # Check that all names are normalized
        assert "Петр Иванович Коваленко" in result.normalized
        assert "Анна Петровна Сидорова" in result.normalized
        assert "Владимир Сергеевич Петров" in result.normalized
        assert "Елена Александровна Козлова" in result.normalized
        assert "Михаил Николаевич Смирнов" in result.normalized
        assert "Ольга Владимировна Морозова" in result.normalized
    
    def test_error_handling_malformed_input(self, service):
        """Test error handling with malformed input"""
        # Test with empty string
        result = service._normalize_sync("", language="ru")
        assert result.normalized == ""
        assert result.success == True
        
        # Test with only punctuation
        result = service._normalize_sync("!!!", language="ru")
        assert result.normalized == ""
        assert result.success == True
        
        # Test with only numbers
        result = service._normalize_sync("123 456", language="ru")
        assert result.normalized == ""
        assert result.success == True
    
    def test_confidence_scoring(self, service):
        """Test confidence scoring in results"""
        # Test with clear names
        result = service._normalize_sync("Петр Иванович Коваленко", language="ru")
        assert result.confidence is not None
        assert result.confidence > 0.5
        
        # Test with ambiguous input
        result = service._normalize_sync("Тест Тест", language="ru")
        assert result.confidence is not None
        assert result.confidence >= 0.0
