"""
Simple unit tests for nominative enforcement and gender preservation.

These tests focus on the core functionality without complex dependencies.
"""

import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.normalization.morphology_adapter import (
    MorphologyAdapter,
    MorphParse,
)
from src.ai_service.layers.normalization.morphology.gender_rules import (
    is_likely_feminine_surname,
    prefer_feminine_form,
)


class TestNominativeGenderSimple:
    """Simple tests for nominative and gender functionality."""

    def test_russian_feminine_surname_detection(self):
        """Test detection of Russian feminine surnames."""
        # Test -ова suffix
        assert is_likely_feminine_surname("Иванова", "ru") is True
        assert is_likely_feminine_surname("Петрова", "ru") is True
        
        # Test -ева suffix
        assert is_likely_feminine_surname("Сидорова", "ru") is True
        
        # Test -ина suffix
        assert is_likely_feminine_surname("Кузнецова", "ru") is True
        
        # Test -ая suffix
        assert is_likely_feminine_surname("Красная", "ru") is True
        
        # Test masculine forms
        assert is_likely_feminine_surname("Иванов", "ru") is False
        assert is_likely_feminine_surname("Петров", "ru") is False

    def test_ukrainian_feminine_surname_detection(self):
        """Test detection of Ukrainian feminine surnames."""
        # Test -ська suffix
        assert is_likely_feminine_surname("Ковальська", "uk") is True
        
        # Test -цька suffix
        assert is_likely_feminine_surname("Кравцівська", "uk") is True
        
        # Test -а suffix
        assert is_likely_feminine_surname("Марія", "uk") is True
        
        # Test masculine forms
        assert is_likely_feminine_surname("Шевченко", "uk") is False
        assert is_likely_feminine_surname("Ковальський", "uk") is False

    def test_prefer_feminine_form_with_feminine_gender(self):
        """Test feminine form preference when gender is feminine."""
        # Test Russian feminine form preservation
        result = prefer_feminine_form("Иванова", "femn", "ru")
        assert result == "Иванова"  # Already feminine, no change
        
        # Test Ukrainian feminine form preservation
        result = prefer_feminine_form("Ковальська", "femn", "uk")
        assert result == "Ковальська"  # Already feminine, no change

    def test_prefer_feminine_form_converts_masculine_to_feminine(self):
        """Test conversion of masculine forms to feminine when gender is feminine."""
        # Test Russian conversion
        result = prefer_feminine_form("Иванов", "femn", "ru")
        assert result == "Иванова"
        
        result = prefer_feminine_form("Петров", "femn", "ru")
        assert result == "Петрова"
        
        # Test Ukrainian conversion
        result = prefer_feminine_form("Ковальський", "femn", "uk")
        assert result == "Ковальська"

    def test_prefer_feminine_form_no_change_for_masculine_gender(self):
        """Test that masculine forms are not changed when gender is masculine."""
        result = prefer_feminine_form("Иванов", "masc", "ru")
        assert result == "Иванов"  # No change for masculine gender
        
        result = prefer_feminine_form("Петров", "masc", "ru")
        assert result == "Петров"

    def test_prefer_feminine_form_no_change_for_unknown_gender(self):
        """Test that forms are not changed when gender is unknown."""
        result = prefer_feminine_form("Иванов", "unknown", "ru")
        assert result == "Иванов"  # No change for unknown gender

    def test_morphology_adapter_to_nominative(self):
        """Test MorphologyAdapter to_nominative method."""
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            # Mock parse to return forms with explicit nominative case
            mock_parse.return_value = [
                MorphParse(
                    nominative_form="Иванова",
                    normal_form="иванов",
                    score=0.9,
                    tag="NOUN,femn,sing,nomn",
                    gender="femn",
                    case="nomn"
                )
            ]
            
            result = adapter.to_nominative("Иванову", "ru")
            assert result == "Иванова"

    def test_morphology_adapter_detect_gender(self):
        """Test MorphologyAdapter detect_gender method."""
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            # Mock parse to return feminine gender
            mock_parse.return_value = [
                MorphParse(
                    nominative_form="Анна",
                    normal_form="анна",
                    score=0.9,
                    tag="NOUN,femn,sing,nomn",
                    gender="femn",
                    case="nomn"
                )
            ]
            
            result = adapter.detect_gender("Анна", "ru")
            assert result == "femn"

    def test_case_preservation_in_feminine_conversion(self):
        """Test that case is preserved in feminine form conversion."""
        # Test uppercase preservation
        result = prefer_feminine_form("ИВАНОВ", "femn", "ru")
        assert result == "ИВАНОВА"
        
        # Test title case preservation
        result = prefer_feminine_form("Иванов", "femn", "ru")
        assert result == "Иванова"
        
        # Test lowercase preservation
        result = prefer_feminine_form("иванов", "femn", "ru")
        assert result == "иванова"

    def test_ukrainian_invariable_surnames(self):
        """Test that Ukrainian invariable surnames are handled correctly."""
        # -енко surnames should not be gender-adjusted
        result = prefer_feminine_form("Шевченко", "femn", "uk")
        assert result == "Шевченко"  # Should remain unchanged
        
        result = prefer_feminine_form("Петренко", "femn", "uk")
        assert result == "Петренко"  # Should remain unchanged

    def test_exception_names_always_feminine(self):
        """Test that exception names are always considered feminine."""
        from src.ai_service.layers.normalization.morphology.gender_rules import EXCEPTIONS_KEEP_FEM
        
        for name in EXCEPTIONS_KEEP_FEM:
            assert is_likely_feminine_surname(name, "ru") is True
            assert is_likely_feminine_surname(name, "uk") is True

    def test_integration_scenario_russian(self):
        """Test integration scenario for Russian names."""
        # Scenario: "Анна Ивановой" -> "Анна Иванова"
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            with patch.object(adapter, 'detect_gender') as mock_gender:
                # Mock parse to return different results based on token
                def mock_parse_func(token, lang):
                    if token == "Анна":
                        return [MorphParse("Анна", "анна", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")]
                    elif token == "Ивановой":
                        return [MorphParse("Иванова", "иванов", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")]
                    return []
                
                mock_parse.side_effect = mock_parse_func
                
                mock_gender.side_effect = lambda token, lang: {
                    "Анна": "femn",
                }.get(token, "unknown")
                
                # Test given name detection
                gender = adapter.detect_gender("Анна", "ru")
                assert gender == "femn"
                
                # Test surname conversion
                nominative = adapter.to_nominative("Ивановой", "ru")
                assert nominative == "Иванова"

    def test_integration_scenario_ukrainian(self):
        """Test integration scenario for Ukrainian names."""
        # Scenario: "Олена Ковальською" -> "Олена Ковальська"
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            with patch.object(adapter, 'detect_gender') as mock_gender:
                # Mock parse to return different results based on token
                def mock_parse_func(token, lang):
                    if token == "Олена":
                        return [MorphParse("Олена", "олена", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")]
                    elif token == "Ковальською":
                        return [MorphParse("Ковальська", "ковальський", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")]
                    return []
                
                mock_parse.side_effect = mock_parse_func
                
                mock_gender.side_effect = lambda token, lang: {
                    "Олена": "femn",
                }.get(token, "unknown")
                
                # Test given name detection
                gender = adapter.detect_gender("Олена", "uk")
                assert gender == "femn"
                
                # Test surname conversion
                nominative = adapter.to_nominative("Ковальською", "uk")
                assert nominative == "Ковальська"
