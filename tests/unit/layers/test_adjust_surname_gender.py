#!/usr/bin/env python3
"""
Unit tests for the adjust_surname_gender function in NormalizationService.

This module tests the surname gender adjustment logic based on determined gender
and confidence gap.
"""

import pytest
from typing import Optional

from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestAdjustSurnameGender:
    """Test cases for the adjust_surname_gender function."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = NormalizationService()

    def test_invariant_surnames_unchanged(self):
        """Test that invariant surnames are not changed."""
        invariant_surnames = [
            "Петренко", "Коваленко", "Шевченко",  # -енко
            "Петрук", "Ковалюк", "Шевчук",  # -ук, -юк, -чук
            "Петрян", "Ковалян", "Шевян",  # -ян
            "Петрдзе", "Ковалдзе", "Шевдзе",  # -дзе
        ]
        
        for surname in invariant_surnames:
            result = self.service.adjust_surname_gender(
                surname, "uk", "femn", 5, surname
            )
            assert result == surname, f"Invariant surname {surname} should not be changed"

    def test_russian_feminine_adjustment(self):
        """Test Russian feminine surname adjustments."""
        test_cases = [
            ("Петров", "ru", "femn", 5, "Петров", "Петрова"),
            ("Сергеев", "ru", "femn", 5, "Сергеев", "Сергеева"),
            ("Андреин", "ru", "femn", 5, "Андреин", "Андреина"),
            ("Лермонтовский", "ru", "femn", 5, "Лермонтовский", "Лермонтовская"),
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_russian_masculine_adjustment(self):
        """Test Russian masculine surname adjustments."""
        test_cases = [
            ("Петрова", "ru", "masc", 5, "Петрова", "Петров"),
            ("Сергеева", "ru", "masc", 5, "Сергеева", "Сергеев"),
            ("Андреина", "ru", "masc", 5, "Андреина", "Андреин"),
            ("Лермонтовская", "ru", "masc", 5, "Лермонтовская", "Лермонтовский"),
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_ukrainian_feminine_adjustment(self):
        """Test Ukrainian feminine surname adjustments."""
        test_cases = [
            ("Петровський", "uk", "femn", 5, "Петровський", "Петровська"),
            ("Сергіїв", "uk", "femn", 5, "Сергіїв", "Сергіїва"),
            ("Андрійович", "uk", "femn", 5, "Андрійович", "Андрійович"),  # No matching ending
            ("Лермонтів", "uk", "femn", 5, "Лермонтів", "Лермонтіва"),
            ("Шевченко", "uk", "femn", 5, "Шевченко", "Шевченко"),  # invariant
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_ukrainian_masculine_adjustment(self):
        """Test Ukrainian masculine surname adjustments."""
        test_cases = [
            ("Петровська", "uk", "masc", 5, "Петровська", "Петровський"),
            ("Сергіїва", "uk", "masc", 5, "Сергіїва", "Сергіїв"),
            ("Лермонтіва", "uk", "masc", 5, "Лермонтіва", "Лермонтів"),
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_insufficient_confidence_gap(self):
        """Test that surnames are not adjusted when confidence gap < 3."""
        test_cases = [
            ("Петров", "ru", "femn", 2, "Петров", "Петров"),  # gap < 3
            ("Петров", "ru", None, 5, "Петров", "Петров"),  # gender is None
            ("Петров", "ru", "femn", 1, "Петров", "Петров"),  # gap < 3
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_preserve_original_gendered_form(self):
        """Test that original gendered forms are preserved when gender is not determined."""
        test_cases = [
            # Original form is clearly feminine
            ("Петров", "ru", None, 2, "Петрова", "Петрова"),
            ("Сергеев", "ru", None, 2, "Сергеева", "Сергеева"),
            ("Андреин", "ru", None, 2, "Андреина", "Андреина"),
            
            # Original form is clearly masculine
            ("Петрова", "ru", None, 2, "Петров", "Петров"),
            ("Сергеева", "ru", None, 2, "Сергеев", "Сергеев"),
            ("Андреина", "ru", None, 2, "Андреин", "Андреина"),
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_no_matching_endings(self):
        """Test surnames that don't match any gender patterns."""
        test_cases = [
            ("Смит", "ru", "femn", 5, "Смит", "Смит"),  # English surname
            ("Гарсія", "uk", "masc", 5, "Гарсія", "Гарсія"),  # Spanish surname
            ("Мюллер", "ru", "femn", 5, "Мюллер", "Мюллер"),  # German surname
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_case_insensitive_matching(self):
        """Test that matching is case-insensitive."""
        test_cases = [
            ("петров", "ru", "femn", 5, "петров", "петрова"),
            ("СЕРГЕЕВ", "ru", "femn", 5, "СЕРГЕЕВ", "СЕРГЕЕВа"),
            ("андреин", "ru", "masc", 5, "андреина", "андреин"),
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_compound_surnames(self):
        """Test compound surnames (though this function handles single parts)."""
        # This function is called for individual parts of compound surnames
        test_cases = [
            ("Петров", "ru", "femn", 5, "Петров", "Петрова"),
            ("Сергеев", "ru", "femn", 5, "Сергеев", "Сергеева"),
        ]
        
        for lemma, lang, gender, gap, original, expected in test_cases:
            result = self.service.adjust_surname_gender(lemma, lang, gender, gap, original)
            assert result == expected, f"Expected {expected}, got {result} for {lemma}"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Empty string
        result = self.service.adjust_surname_gender("", "ru", "femn", 5, "")
        assert result == ""
        
        # Single character
        result = self.service.adjust_surname_gender("А", "ru", "femn", 5, "А")
        assert result == "А"
        
        # Very short surname
        result = self.service.adjust_surname_gender("Ан", "ru", "femn", 5, "Ан")
        assert result == "Ан"

    def test_confidence_gap_boundary(self):
        """Test confidence gap boundary conditions."""
        # Exactly 3 should trigger adjustment
        result = self.service.adjust_surname_gender("Петров", "ru", "femn", 3, "Петров")
        assert result == "Петрова"
        
        # Less than 3 should not trigger adjustment
        result = self.service.adjust_surname_gender("Петров", "ru", "femn", 2, "Петров")
        assert result == "Петров"
        
        # Greater than 3 should trigger adjustment
        result = self.service.adjust_surname_gender("Петров", "ru", "femn", 4, "Петров")
        assert result == "Петрова"
