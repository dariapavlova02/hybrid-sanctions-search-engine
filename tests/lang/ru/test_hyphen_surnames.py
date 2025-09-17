#!/usr/bin/env python3
"""
Tests for Russian hyphenated surnames.

Tests that hyphenated surnames like "Петрова-Сидорова" are correctly
preserved and normalized with proper feminine form handling.
"""

import pytest
from src.ai_service.layers.normalization.token_ops import normalize_hyphenated_name


class TestRussianHyphenSurnames:
    """Test Russian hyphenated surname handling."""
    
    def test_basic_hyphenated_surname(self):
        """Test basic hyphenated surname normalization."""
        surname = "петрова-сидорова"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "Петрова-Сидорова"
    
    def test_feminine_hyphenated_surname(self):
        """Test feminine hyphenated surname preservation."""
        surname = "петрова-сидорова"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        # Should preserve feminine form
        assert normalized == "Петрова-Сидорова"
        assert normalized.endswith("ова")  # Should end with feminine form
    
    def test_masculine_hyphenated_surname(self):
        """Test masculine hyphenated surname normalization."""
        surname = "петров-сидоров"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "Петров-Сидоров"
        assert normalized.endswith("оров")  # Should end with masculine form
    
    def test_mixed_case_hyphenated_surname(self):
        """Test hyphenated surname with mixed case."""
        surname = "ПЕТРОВА-сидорова"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "Петрова-Сидорова"
    
    def test_hyphenated_surname_without_titlecase(self):
        """Test hyphenated surname without titlecase conversion."""
        surname = "петрова-сидорова"
        normalized = normalize_hyphenated_name(surname, titlecase=False)
        
        assert normalized == "петрова-сидорова"
    
    def test_multiple_hyphens_preserved(self):
        """Test that multiple hyphens are preserved."""
        surname = "петрова-сидорова-иванова"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "Петрова-Сидорова-Иванова"
        assert normalized.count("-") == 2
    
    def test_hyphenated_surname_with_apostrophe(self):
        """Test hyphenated surname with apostrophe."""
        surname = "о'нил-смит"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "О'Нил-Смит"
    
    def test_em_dash_preserved(self):
        """Test that em-dash is preserved (not processed as hyphen)."""
        surname = "петрова—сидорова"  # em-dash
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        # Should not be processed as hyphenated name
        assert normalized == "петрова—сидорова"
    
    def test_double_hyphen_preserved(self):
        """Test that double hyphen is preserved (not processed as hyphenated name)."""
        surname = "петрова--сидорова"  # double hyphen
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        # Should not be processed as hyphenated name
        assert normalized == "петрова--сидорова"
    
    def test_invalid_segment_returns_original(self):
        """Test that invalid segments return original token."""
        surname = "петрова-123-сидорова"  # contains numbers
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        # Should return original due to invalid segment
        assert normalized == "петрова-123-сидорова"
    
    def test_empty_segments_handled(self):
        """Test that empty segments are handled correctly."""
        surname = "-петрова-сидорова-"  # leading and trailing hyphens
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        # Should handle empty segments
        assert normalized == "-Петрова-Сидорова-"
    
    def test_single_hyphen_only(self):
        """Test that only single hyphens are processed."""
        test_cases = [
            ("петрова-сидорова", True),  # Single hyphen - should be processed
            ("петрова—сидорова", False),  # Em-dash - should not be processed
            ("петрова--сидорова", False),  # Double hyphen - should not be processed
        ]
        
        for surname, should_process in test_cases:
            normalized = normalize_hyphenated_name(surname, titlecase=True)
            if should_process:
                assert normalized != surname  # Should be processed
            else:
                assert normalized == surname  # Should not be processed
    
    def test_unicode_letters_supported(self):
        """Test that Unicode letters are supported."""
        surname = "петрова-сидорова"  # Cyrillic letters
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "Петрова-Сидорова"
    
    def test_mixed_script_hyphenated_name(self):
        """Test hyphenated name with mixed scripts."""
        surname = "петрова-smith"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "Петрова-Smith"
    
    def test_hyphenated_name_with_dots_invalid(self):
        """Test that segments with dots are invalid."""
        surname = "петрова-с.идорова"  # contains dot
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        # Should return original due to invalid segment
        assert normalized == "петрова-с.идорова"
    
    def test_hyphenated_name_validation(self):
        """Test hyphenated name validation rules."""
        valid_cases = [
            "петрова-сидорова",
            "о'нил-смит",
            "петров-сидоров",
            "а-б-в",
        ]
        
        invalid_cases = [
            "петрова-123-сидорова",  # numbers
            "петрова-с.идорова",     # dots
            "петрова-сид@орова",     # special chars
        ]
        
        for surname in valid_cases:
            normalized = normalize_hyphenated_name(surname, titlecase=True)
            assert normalized != surname  # Should be processed
        
        for surname in invalid_cases:
            normalized = normalize_hyphenated_name(surname, titlecase=True)
            assert normalized == surname  # Should not be processed
    
    def test_empty_token(self):
        """Test that empty token is handled correctly."""
        normalized = normalize_hyphenated_name("", titlecase=True)
        assert normalized == ""
    
    def test_none_token(self):
        """Test that None token is handled correctly."""
        normalized = normalize_hyphenated_name(None, titlecase=True)
        assert normalized is None
    
    def test_no_hyphen_token(self):
        """Test that token without hyphen is returned unchanged."""
        surname = "петрова"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "петрова"
    
    def test_titlecase_preserves_apostrophes(self):
        """Test that titlecase correctly handles apostrophes."""
        surname = "о.нил-смит"
        normalized = normalize_hyphenated_name(surname, titlecase=True)
        
        assert normalized == "О'Нил-Смит"
        assert "'" in normalized  # Apostrophe should be preserved
