"""
Unit tests for nominative enforcement and gender preservation.

Tests the functionality that ensures all personal names are converted to
nominative case while preserving feminine surname endings when appropriate.
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
    FEMALE_SUFFIXES_RU,
    FEMALE_SUFFIXES_UK,
    EXCEPTIONS_KEEP_FEM,
)


class TestMorphologyAdapter:
    """Test MorphologyAdapter nominative and gender functionality."""

    def test_to_nominative_explicit_nominative_case(self):
        """Test that explicit nominative case forms are preferred."""
        adapter = MorphologyAdapter()
        
        # Mock parse to return forms with explicit nominative case
        with patch.object(adapter, 'parse') as mock_parse:
            mock_parse.return_value = [
                MorphParse(
                    nominative_form="Иванова",
                    normal_form="иванов",
                    score=0.9,
                    tag="NOUN,femn,sing,nomn",
                    gender="femn",
                    case="nomn"
                ),
                MorphParse(
                    nominative_form="Иванову",
                    normal_form="иванов",
                    score=0.8,
                    tag="NOUN,femn,sing,datv",
                    gender="femn",
                    case="datv"
                )
            ]
            
            result = adapter.to_nominative("Иванову", "ru")
            assert result == "Иванова"

    def test_to_nominative_fallback_to_any_nominative(self):
        """Test fallback to any nominative form when explicit case not found."""
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            mock_parse.return_value = [
                MorphParse(
                    nominative_form="Петров",
                    normal_form="петров",
                    score=0.9,
                    tag="NOUN,masc,sing,gent",
                    gender="masc",
                    case="gent"
                )
            ]
            
            result = adapter.to_nominative("Петрова", "ru")
            assert result == "Петров"

    def test_to_nominative_preserves_case(self):
        """Test that original case is preserved in result."""
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            mock_parse.return_value = [
                MorphParse(
                    nominative_form="иванова",
                    normal_form="иванов",
                    score=0.9,
                    tag="NOUN,femn,sing,nomn",
                    gender="femn",
                    case="nomn"
                )
            ]
            
            # Test uppercase preservation
            result = adapter.to_nominative("ИВАНОВУ", "ru")
            assert result == "ИВАНОВА"
            
            # Test title case preservation
            result = adapter.to_nominative("Иванову", "ru")
            assert result == "Иванова"

    def test_detect_gender_finds_feminine(self):
        """Test gender detection finds feminine gender."""
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
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

    def test_detect_gender_finds_masculine(self):
        """Test gender detection finds masculine gender."""
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            mock_parse.return_value = [
                MorphParse(
                    nominative_form="Иван",
                    normal_form="иван",
                    score=0.9,
                    tag="NOUN,masc,sing,nomn",
                    gender="masc",
                    case="nomn"
                )
            ]
            
            result = adapter.detect_gender("Иван", "ru")
            assert result == "masc"

    def test_detect_gender_unknown_when_no_gender(self):
        """Test gender detection returns unknown when no gender found."""
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            mock_parse.return_value = [
                MorphParse(
                    nominative_form="test",
                    normal_form="test",
                    score=0.9,
                    tag="UNKN",
                    gender=None,
                    case=None
                )
            ]
            
            result = adapter.detect_gender("test", "ru")
            assert result == "unknown"


class TestGenderRules:
    """Test gender rules for feminine surname detection and preservation."""

    def test_is_likely_feminine_surname_russian_suffixes(self):
        """Test detection of Russian feminine surname suffixes."""
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

    def test_is_likely_feminine_surname_ukrainian_suffixes(self):
        """Test detection of Ukrainian feminine surname suffixes."""
        # Test -іна suffix
        assert is_likely_feminine_surname("Ковальська", "uk") is True
        
        # Test -ська suffix
        assert is_likely_feminine_surname("Шевченко", "uk") is False  # -ко is masculine
        
        # Test -цька suffix
        assert is_likely_feminine_surname("Кравцівська", "uk") is True
        
        # Test -а suffix
        assert is_likely_feminine_surname("Марія", "uk") is True

    def test_is_likely_feminine_surname_exceptions(self):
        """Test that exception names are always considered feminine."""
        for name in EXCEPTIONS_KEEP_FEM:
            assert is_likely_feminine_surname(name, "ru") is True
            assert is_likely_feminine_surname(name, "uk") is True

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

    def test_prefer_feminine_form_preserves_case(self):
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


class TestNominativeAndGenderIntegration:
    """Test integration of nominative enforcement and gender preservation."""

    def test_russian_feminine_name_preservation(self):
        """Test that Russian feminine names are preserved correctly."""
        # "Анна Ивановой" should become "Анна Иванова" (preserve feminine)
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            # Mock parse for "Анна" (given name)
            mock_parse.side_effect = [
                [MorphParse("Анна", "анна", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")],
                [MorphParse("Иванова", "иванов", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")]
            ]
            
            # Test given name detection
            gender = adapter.detect_gender("Анна", "ru")
            assert gender == "femn"
            
            # Test surname conversion
            nominative = adapter.to_nominative("Ивановой", "ru")
            assert nominative == "Иванова"

    def test_ukrainian_feminine_name_preservation(self):
        """Test that Ukrainian feminine names are preserved correctly."""
        # "Олена Ковальською" should become "Олена Ковальська" (preserve feminine)
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            # Mock parse for "Олена" (given name)
            mock_parse.side_effect = [
                [MorphParse("Олена", "олена", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")],
                [MorphParse("Ковальська", "ковальський", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")]
            ]
            
            # Test given name detection
            gender = adapter.detect_gender("Олена", "uk")
            assert gender == "femn"
            
            # Test surname conversion
            nominative = adapter.to_nominative("Ковальською", "uk")
            assert nominative == "Ковальська"

    def test_masculine_name_no_feminine_conversion(self):
        """Test that masculine names are not converted to feminine."""
        # "Иван Петров" should remain "Иван Петров" (not "Петрова")
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            # Mock parse for "Иван" (given name)
            mock_parse.side_effect = [
                [MorphParse("Иван", "иван", 0.9, "NOUN,masc,sing,nomn", "masc", "nomn")],
                [MorphParse("Петров", "петров", 0.9, "NOUN,masc,sing,nomn", "masc", "nomn")]
            ]
            
            # Test given name detection
            gender = adapter.detect_gender("Иван", "ru")
            assert gender == "masc"
            
            # Test surname conversion (should remain masculine)
            nominative = adapter.to_nominative("Петров", "ru")
            assert nominative == "Петров"

    def test_already_nominative_forms_unchanged(self):
        """Test that already nominative forms are not changed."""
        # "Мария Петрова" should remain "Мария Петрова" (already nominative)
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            mock_parse.return_value = [
                MorphParse("Петрова", "петров", 0.9, "NOUN,femn,sing,nomn", "femn", "nomn")
            ]
            
            # Test that already nominative forms are unchanged
            nominative = adapter.to_nominative("Петрова", "ru")
            assert nominative == "Петрова"

    def test_ukrainian_invariable_surnames(self):
        """Test that Ukrainian invariable surnames are not gender-adjusted."""
        # "Ірина Шевченко" should remain "Ірина Шевченко" (not "Шевченка")
        adapter = MorphologyAdapter()
        
        with patch.object(adapter, 'parse') as mock_parse:
            mock_parse.return_value = [
                MorphParse("Шевченко", "шевченко", 0.9, "NOUN,masc,sing,nomn", "masc", "nomn")
            ]
            
            # Test that invariable surnames are not changed
            nominative = adapter.to_nominative("Шевченко", "uk")
            assert nominative == "Шевченко"
