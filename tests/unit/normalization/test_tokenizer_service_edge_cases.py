#!/usr/bin/env python3
"""
Edge case tests for TokenizerService.

Tests complex scenarios, boundary conditions, and error handling
to ensure robust tokenization behavior.
"""

import pytest
from src.ai_service.layers.normalization.tokenizer_service import TokenizerService, TokenizationResult


class TestTokenizerServiceEdgeCases:
    """Edge case tests for TokenizerService."""

    def test_initials_various_patterns(self):
        """Test various initial patterns and edge cases."""
        service = TokenizerService(fix_initials_double_dot=True)
        
        # Valid initial patterns
        valid_initials = [
            ("И..", "И."),
            ("П..", "П."),
            ("A..", "A."),
            ("I..", "I."),
            ("а..", "а."),  # lowercase
            ("і..", "і."),  # Ukrainian
            ("ё..", "ё."),  # Russian
            ("И....", "И."),  # Multiple dots
            ("П.....", "П."),  # Many dots
        ]
        
        for input_token, expected in valid_initials:
            result = service._looks_like_initial_with_double_dot(input_token)
            assert result is True, f"Should detect {input_token} as initial with double dots"
            
            collapsed = service._collapse_double_dot(input_token)
            assert collapsed == expected, f"Expected {expected}, got {collapsed} for {input_token}"

    def test_initials_invalid_patterns(self):
        """Test patterns that should NOT be treated as initials."""
        service = TokenizerService(fix_initials_double_dot=True)
        
        # Invalid patterns
        invalid_patterns = [
            "И.",      # Single dot (not double)
            "И",       # No dots
            "И.И.",    # Multiple letters
            "И.И..",   # Multiple letters with double dots
            "ООО.",    # Company abbreviation
            "ТОВ.",    # Company abbreviation
            "И.И.И.",  # Multiple initials
            "И-И.",    # With hyphen
            "И'И.",    # With apostrophe
            "И.И",     # Missing final dot
            ".И.",     # Starting with dot
            "И..И",    # Dot in middle
            "123.",    # Numbers
            "И.123",   # Numbers after dot
        ]
        
        for pattern in invalid_patterns:
            result = service._looks_like_initial_with_double_dot(pattern)
            assert result is False, f"Should NOT detect {pattern} as initial with double dots"

    def test_hyphen_various_types(self):
        """Test various types of hyphens and dashes."""
        service = TokenizerService(preserve_hyphenated_case=True)
        
        # Different hyphen types
        hyphen_types = [
            "Петрова-Сидорова",    # Regular hyphen
            "Jean–Luc",            # En dash
            "Smith—Jones",         # Em dash
            "Name−Surname",        # Minus sign
            "Test‐Name",           # Hyphen-minus
            "Word‐‐Word",          # Double hyphen
        ]
        
        for token in hyphen_types:
            has_hyphen = service._has_hyphen(token)
            assert has_hyphen is True, f"Should detect hyphen in {token}"

    def test_hyphen_edge_cases(self):
        """Test hyphen edge cases and boundary conditions."""
        service = TokenizerService(preserve_hyphenated_case=True)
        
        # Edge cases
        edge_cases = [
            ("-", True),           # Just hyphen
            ("--", True),          # Double hyphen
            ("---", True),         # Triple hyphen
            ("-word", True),       # Hyphen at start
            ("word-", True),       # Hyphen at end
            ("word", False),       # No hyphen
            ("word word", False),  # Space, not hyphen
            ("word.word", False),  # Dot, not hyphen
            ("word'word", False),  # Apostrophe, not hyphen
        ]
        
        for token, expected in edge_cases:
            has_hyphen = service._has_hyphen(token)
            assert has_hyphen == expected, f"Expected {expected} for {token}"

    def test_unicode_edge_cases(self):
        """Test Unicode edge cases and normalization."""
        service = TokenizerService()
        
        # Unicode edge cases
        unicode_cases = [
            "Іван",           # Ukrainian I
            "Їжак",           # Ukrainian Yi  
            "Євген",          # Ukrainian Ye
            "Ґудзик",         # Ukrainian Ghe
            "Анна",           # Regular Cyrillic
            "John",           # Regular Latin
            "Іван-Петров",    # Mixed with hyphen
            "O'Connor",       # Apostrophe
            "«ПРИВАТБАНК»",   # Quotation marks
        ]
        
        for text in unicode_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_whitespace_edge_cases(self):
        """Test various whitespace characters and edge cases."""
        service = TokenizerService()
        
        # Different whitespace types
        whitespace_cases = [
            "Иван\u00A0Петров",    # Non-breaking space
            "John\u200BSmith",     # Zero-width space
            "Анна\u2000Петрова",   # En quad
            "Test\u2001Case",      # Em quad
            "Word\u2002Space",     # En space
            "Text\u2003Space",     # Em space
            "Line\u2004Break",     # Three-per-em space
            "Para\u2005Graph",     # Four-per-em space
            "Six\u2006Per",        # Six-per-em space
            "Figure\u2007Space",   # Figure space
            "Punc\u2008Space",     # Punctuation space
            "Thin\u2009Space",     # Thin space
            "Hair\u200ASpace",     # Hair space
            "Zero\u200BWidth",     # Zero-width space
            "Narrow\u202FNoBreak", # Narrow no-break space
            "Medium\u205FMath",    # Medium mathematical space
            "Ideo\u3000Graphic",   # Ideographic space
        ]
        
        for text in whitespace_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_mixed_script_edge_cases(self):
        """Test mixed script handling and edge cases."""
        service = TokenizerService()
        
        # Mixed script cases
        mixed_script_cases = [
            "JohnІван",           # Latin + Cyrillic
            "ПетровSmith",        # Cyrillic + Latin
            "TOB«ПРИВАТБАНК»",    # Mixed with quotes
            "Іван-Петров",        # Cyrillic with hyphen
            "Jean-Luc",           # Latin with hyphen
            "O'Connor",           # Latin with apostrophe
            "О'Брайен",           # Cyrillic with apostrophe
            "Smith--Jones",       # Latin with double hyphen
            "Петрова-Сидорова",   # Cyrillic with hyphen
        ]
        
        for text in mixed_script_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_company_abbreviations_edge_cases(self):
        """Test company abbreviation edge cases."""
        service = TokenizerService()
        
        # Company abbreviations that should NOT be treated as initials
        company_abbrevs = [
            "ООО.",
            "ТОВ.",
            "ЗАО.",
            "ПАО.",
            "АО.",
            "ИП.",
            "ЧП.",
            "ФОП.",
            "ПП.",
            "LLC.",
            "Inc.",
            "Corp.",
            "Co.",
            "GmbH.",
            "SRL.",
            "SPA.",
            "BV.",
            "NV.",
            "OY.",
            "AB.",
            "AS.",
            "SA.",
            "AG.",
        ]
        
        for abbrev in company_abbrevs:
            is_initial = service._looks_like_initial_with_double_dot(abbrev)
            assert is_initial is False, f"Should not detect {abbrev} as initial with double dots"

    def test_special_characters_edge_cases(self):
        """Test special characters and punctuation edge cases."""
        service = TokenizerService()
        
        # Special character cases
        special_cases = [
            "О'Брайен",           # Apostrophe
            "O'Connor",           # Apostrophe
            "D'Angelo",           # Apostrophe
            "L'Étoile",           # Apostrophe with accent
            "«ПРИВАТБАНК»",       # Quotation marks
            "„Німецька",         # German quotes
            "„Українська",       # Ukrainian quotes
            "«Русские»",          # Russian quotes
            "„English",          # English quotes
            "Smith--Jones",       # Double hyphen
            "Name---Surname",     # Triple hyphen
            "Word‐Name",          # Hyphen-minus
            "Text–Dash",          # En dash
            "Line—Em",            # Em dash
            "Minus−Sign",         # Minus sign
        ]
        
        for text in special_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_empty_and_null_inputs(self):
        """Test handling of empty, null, and invalid inputs."""
        service = TokenizerService()
        
        # Empty and null cases
        empty_cases = [
            "",                   # Empty string
            "   ",                # Whitespace only
            "\t\n\r",             # Mixed whitespace
            "\u00A0\u200B",       # Non-breaking and zero-width spaces
            None,                 # None input
        ]
        
        for text in empty_cases:
            if text is None:
                # Should handle None gracefully
                try:
                    result = service.tokenize(text, language="uk")
                    # If it doesn't raise exception, result should be valid
                    assert isinstance(result, TokenizationResult)
                except (TypeError, AttributeError):
                    # Expected for None input
                    pass
            else:
                result = service.tokenize(text, language="uk")
                assert isinstance(result, TokenizationResult)

    def test_very_long_input(self):
        """Test handling of very long input strings."""
        service = TokenizerService()
        
        # Very long text
        long_text = "Иван " * 1000 + "Петров"
        
        result = service.tokenize(long_text, language="uk")
        assert isinstance(result, TokenizationResult)
        assert result.success is not False

    def test_repeated_patterns(self):
        """Test handling of repeated patterns and tokens."""
        service = TokenizerService()
        
        # Repeated patterns
        repeated_cases = [
            "Иван Иван Петров",           # Repeated first name
            "Петров Петров Сидоров",      # Repeated surname
            "И. И. Петров",               # Repeated initials
            "И.. И.. Петров",             # Repeated double-dot initials
            "Петрова-Петрова Сидорова",   # Repeated hyphenated names
        ]
        
        for text in repeated_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_case_sensitivity_edge_cases(self):
        """Test case sensitivity edge cases."""
        service = TokenizerService()
        
        # Case sensitivity cases
        case_cases = [
            "ИВАН ПЕТРОВ",         # All uppercase
            "иван петров",         # All lowercase
            "Иван Петров",         # Title case
            "ИВАН петров",         # Mixed case
            "иван ПЕТРОВ",         # Mixed case
            "ІВАН ПЕТРОВ",         # Ukrainian uppercase
            "іван петров",         # Ukrainian lowercase
        ]
        
        for text in case_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_language_edge_cases(self):
        """Test language parameter edge cases."""
        service = TokenizerService()
        
        # Language edge cases
        language_cases = [
            "uk",      # Ukrainian
            "ru",      # Russian
            "en",      # English
            "ukr",     # Extended Ukrainian
            "rus",     # Extended Russian
            "eng",     # Extended English
            "",        # Empty language
            "invalid", # Invalid language
        ]
        
        for lang in language_cases:
            result = service.tokenize("Test Text", language=lang)
            assert isinstance(result, TokenizationResult)
            # Should not fail even with invalid language

    def test_feature_flags_edge_cases(self):
        """Test feature flags edge cases."""
        service = TokenizerService()
        
        # Feature flags edge cases
        flag_cases = [
            None,                    # No flags
            {},                      # Empty flags
            {"flag1": True},         # Boolean flag
            {"flag2": "string"},     # String flag
            {"flag3": 42},           # Numeric flag
            {"flag4": [1, 2, 3]},    # List flag
            {"flag5": {"nested": True}},  # Nested flag
        ]
        
        for flags in flag_cases:
            result = service.tokenize("Test Text", language="uk", feature_flags=flags)
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_stop_words_edge_cases(self):
        """Test stop words edge cases."""
        service = TokenizerService()
        
        # Stop words edge cases
        stop_words_cases = [
            None,                    # No stop words
            set(),                   # Empty set
            {"тест"},                # Single stop word
            {"тест", "слово"},       # Multiple stop words
            {"", " "},               # Empty strings
            {"тест", "ТЕСТ"},        # Case variations
            {"тест", "тест"},        # Duplicates
        ]
        
        for stop_words in stop_words_cases:
            result = service.tokenize(
                "тест слово Иван Петров", 
                language="uk", 
                stop_words=stop_words
            )
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_boolean_parameters_edge_cases(self):
        """Test boolean parameters edge cases."""
        service = TokenizerService()
        
        # Boolean parameter combinations
        boolean_combinations = [
            (True, True),    # Both enabled
            (True, False),   # Only remove_stop_words
            (False, True),   # Only preserve_names
            (False, False),  # Both disabled
        ]
        
        for remove_stop_words, preserve_names in boolean_combinations:
            result = service.tokenize(
                "Test Text", 
                language="uk",
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names
            )
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_post_processing_rules_edge_cases(self):
        """Test post-processing rules edge cases."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Edge cases for post-processing
        edge_cases = [
            [],                    # Empty token list
            [""],                  # Empty token
            [" "],                 # Whitespace token
            ["И..", "Петрова-Сидорова"],  # Mixed rules
            ["И..", "И..", "И.."], # Multiple same initials
            ["Петрова-Сидорова", "Jean-Luc"],  # Multiple hyphens
        ]
        
        for tokens in edge_cases:
            processed_tokens, traces = service._apply_post_processing_rules(tokens)
            assert isinstance(processed_tokens, list)
            assert isinstance(traces, list)
            assert len(processed_tokens) == len(tokens)

    def test_collapse_double_dot_edge_cases(self):
        """Test collapse double dot edge cases."""
        service = TokenizerService()
        
        # Edge cases for double dot collapsing
        edge_cases = [
            ("И..", "И."),         # Basic case
            ("И....", "И."),       # Multiple dots
            ("И.....", "И."),      # Many dots
            ("И.", "И."),          # Single dot (no change)
            ("И", "И"),            # No dots (no change)
            ("", ""),              # Empty string
            ("И..И", "И.И"),       # Dot in middle
        ]
        
        for input_token, expected in edge_cases:
            result = service._collapse_double_dot(input_token)
            assert result == expected, f"Expected {expected}, got {result} for {input_token}"

    def test_has_hyphen_edge_cases(self):
        """Test has hyphen edge cases."""
        service = TokenizerService()
        
        # Edge cases for hyphen detection
        edge_cases = [
            ("word-word", True),   # Basic hyphen
            ("word--word", True),  # Double hyphen
            ("word---word", True), # Triple hyphen
            ("word", False),       # No hyphen
            ("word word", False),  # Space, not hyphen
            ("word.word", False),  # Dot, not hyphen
            ("word'word", False),  # Apostrophe, not hyphen
            ("-", True),           # Just hyphen
            ("--", True),          # Just double hyphen
            ("", False),           # Empty string
        ]
        
        for token, expected in edge_cases:
            result = service._has_hyphen(token)
            assert result == expected, f"Expected {expected}, got {result} for {token}"
