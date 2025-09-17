#!/usr/bin/env python3
"""
Tests for Ukrainian feminine surname suffix preservation.

Tests the preserve_feminine_suffix_uk flag functionality to ensure that
Ukrainian feminine suffixes (-ська/-цька) are preserved in nominative case.
"""

import pytest
from src.ai_service.layers.normalization.morphology.gender_rules import (
    convert_surname_to_nominative_uk,
    looks_like_feminine_uk
)
from src.ai_service.layers.normalization.processors.morphology_processor import MorphologyProcessor


class TestUkrainianFeminineSuffix:
    """Test Ukrainian feminine surname suffix preservation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.morphology_processor = MorphologyProcessor()

    def test_feminine_suffix_preservation_enabled(self):
        """Test that feminine suffixes are preserved when flag is enabled."""
        test_cases = [
            # (input, expected_output, description)
            ("Ковальська", "Ковальська", "Feminine nominative -ська"),
            ("Кравцівська", "Кравцівська", "Feminine nominative -ська"),
            ("Петренко", "Петренко", "Masculine -енко (unchanged)"),
            ("Шевченко", "Шевченко", "Masculine -енко (unchanged)"),
            ("Ковальської", "Ковальська", "Feminine genitive -ської -> nominative -ська"),
            ("Кравцівської", "Кравцівська", "Feminine genitive -ської -> nominative -ська"),
            ("Ковальською", "Ковальська", "Feminine instrumental -ською -> nominative -ська"),
            ("Кравцівською", "Кравцівська", "Feminine instrumental -ською -> nominative -ська"),
            ("Ковальській", "Ковальська", "Feminine dative -ській -> nominative -ська"),
            ("Кравцівській", "Кравцівська", "Feminine dative -ській -> nominative -ська"),
            ("Ковальську", "Ковальська", "Feminine accusative -ську -> nominative -ська"),
            ("Кравцівську", "Кравцівська", "Feminine accusative -ську -> nominative -ська"),
        ]

        for input_name, expected, description in test_cases:
            result = convert_surname_to_nominative_uk(input_name, preserve_feminine_suffix_uk=True)
            assert result == expected, f"{description}: '{input_name}' -> '{result}', expected '{expected}'"

    def test_feminine_suffix_preservation_disabled(self):
        """Test that feminine suffixes are not preserved when flag is disabled."""
        test_cases = [
            # (input, expected_output, description)
            ("Ковальська", "Ковальська", "Feminine nominative -ська (unchanged)"),
            ("Кравцівська", "Кравцівська", "Feminine nominative -ська (unchanged)"),
            ("Ковальської", "Ковальська", "Feminine genitive -ської -> nominative -ська"),
            ("Кравцівської", "Кравцівська", "Feminine genitive -ської -> nominative -ська"),
            ("Ковальською", "Ковальська", "Feminine instrumental -ською -> nominative -ська"),
            ("Кравцівською", "Кравцівська", "Feminine instrumental -ською -> nominative -ська"),
        ]

        for input_name, expected, description in test_cases:
            result = convert_surname_to_nominative_uk(input_name, preserve_feminine_suffix_uk=False)
            assert result == expected, f"{description}: '{input_name}' -> '{result}', expected '{expected}'"

    def test_looks_like_feminine_uk_detection(self):
        """Test detection of Ukrainian feminine surname forms."""
        test_cases = [
            # (input, expected_is_feminine, expected_nominative, description)
            ("Ковальська", True, "Ковальська", "Feminine nominative -ська"),
            ("Кравцівська", True, "Кравцівська", "Feminine nominative -ська"),
            ("Ковальської", True, "Ковальська", "Feminine genitive -ської"),
            ("Кравцівської", True, "Кравцівська", "Feminine genitive -ської"),
            ("Ковальською", True, "Ковальська", "Feminine instrumental -ською"),
            ("Кравцівською", True, "Кравцівська", "Feminine instrumental -ською"),
            ("Ковальській", True, "Ковальська", "Feminine dative -ській"),
            ("Кравцівській", True, "Кравцівська", "Feminine dative -ській"),
            ("Ковальську", True, "Ковальська", "Feminine accusative -ську"),
            ("Кравцівську", True, "Кравцівська", "Feminine accusative -ську"),
            ("Петренко", False, None, "Masculine -енко"),
            ("Шевченко", False, None, "Masculine -енко"),
            ("Іванов", False, None, "Masculine -ов"),
        ]

        for input_name, expected_is_fem, expected_nom, description in test_cases:
            is_fem, fem_nom = looks_like_feminine_uk(input_name)
            assert is_fem == expected_is_fem, f"{description}: is_feminine should be {expected_is_fem} for '{input_name}'"
            if expected_nom is not None:
                assert fem_nom == expected_nom, f"{description}: nominative should be '{expected_nom}' for '{input_name}', got '{fem_nom}'"

    def test_morphology_processor_integration(self):
        """Test integration with MorphologyProcessor."""
        import asyncio
        
        async def test_async():
            # Test with preserve_feminine_suffix_uk=True
            normalized, trace = await self.morphology_processor.normalize_slavic_token(
                "Ковальської",
                "surname", 
                "uk",
                enable_morphology=True,
                preserve_feminine_suffix_uk=True
            )
            
            # Should preserve feminine suffix
            assert normalized == "Ковальська", f"Expected 'Ковальська', got '{normalized}'"
            assert any("preserving feminine suffix" in t for t in trace), f"Should have feminine suffix preservation trace: {trace}"
            
            # Test with preserve_feminine_suffix_uk=False
            normalized2, trace2 = await self.morphology_processor.normalize_slavic_token(
                "Ковальської",
                "surname",
                "uk", 
                enable_morphology=True,
                preserve_feminine_suffix_uk=False
            )
            
            # Should still normalize to nominative but without special trace
            assert normalized2 == "Ковальська", f"Expected 'Ковальська', got '{normalized2}'"
            assert not any("preserving feminine suffix" in t for t in trace2), f"Should not have feminine suffix preservation trace: {trace2}"
        
        asyncio.run(test_async())

    def test_edge_cases(self):
        """Test edge cases for feminine suffix preservation."""
        test_cases = [
            # (input, expected_output, description)
            ("", "", "Empty string"),
            ("а", "а", "Single character"),
            ("ська", "ська", "Just suffix"),
            ("Ковальська", "Ковальська", "Already nominative"),
            ("Ковальської", "Ковальська", "Genitive to nominative"),
            ("Ковальською", "Ковальська", "Instrumental to nominative"),
            ("Ковальській", "Ковальська", "Dative to nominative"),
            ("Ковальську", "Ковальська", "Accusative to nominative"),
        ]

        for input_name, expected, description in test_cases:
            result = convert_surname_to_nominative_uk(input_name, preserve_feminine_suffix_uk=True)
            assert result == expected, f"{description}: '{input_name}' -> '{result}', expected '{expected}'"

    def test_mixed_case_handling(self):
        """Test that mixed case is handled correctly."""
        test_cases = [
            ("ковальська", "ковальська", "Lowercase feminine"),
            ("КОВАЛЬСЬКА", "КОВАЛЬСЬКА", "Uppercase feminine"),
            ("КовальСька", "КовальСька", "Mixed case feminine"),
        ]

        for input_name, expected, description in test_cases:
            result = convert_surname_to_nominative_uk(input_name, preserve_feminine_suffix_uk=True)
            assert result == expected, f"{description}: '{input_name}' -> '{result}', expected '{expected}'"

    def test_other_feminine_endings(self):
        """Test other Ukrainian feminine endings are handled correctly."""
        test_cases = [
            # (input, expected_output, description)
            ("Іванова", "Іванова", "Feminine -ова"),
            ("Петрова", "Петрова", "Feminine -ова"),
            ("Сидорова", "Сидорова", "Feminine -ова"),
            ("Іванової", "Іванова", "Feminine genitive -ової"),
            ("Петрової", "Петрова", "Feminine genitive -ової"),
            ("Сидорової", "Сидорова", "Feminine genitive -ової"),
        ]

        for input_name, expected, description in test_cases:
            result = convert_surname_to_nominative_uk(input_name, preserve_feminine_suffix_uk=True)
            assert result == expected, f"{description}: '{input_name}' -> '{result}', expected '{expected}'"
