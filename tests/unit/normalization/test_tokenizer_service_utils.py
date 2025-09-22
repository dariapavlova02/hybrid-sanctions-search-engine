#!/usr/bin/env python3
"""
Tests for TokenizerService utility methods and helper functions.

Tests the internal utility methods that support tokenization functionality.
"""

import pytest
from src.ai_service.layers.normalization.tokenizer_service import TokenizerService, TokenizationResult


class TestTokenizerServiceUtils:
    """Tests for TokenizerService utility methods."""

    def test_looks_like_initial_with_double_dot_valid_cases(self):
        """Test detection of valid initial patterns with double dots."""
        service = TokenizerService()
        
        # Valid patterns
        valid_patterns = [
            "И..",      # Cyrillic uppercase
            "П..",      # Cyrillic uppercase
            "А..",      # Cyrillic uppercase
            "а..",      # Cyrillic lowercase
            "і..",      # Ukrainian lowercase
            "ё..",      # Russian lowercase
            "A..",      # Latin uppercase
            "I..",      # Latin uppercase
            "a..",      # Latin lowercase
            "i..",      # Latin lowercase
            "И....",    # Multiple dots
            "П.....",   # Many dots
        ]
        
        for pattern in valid_patterns:
            result = service._looks_like_initial_with_double_dot(pattern)
            assert result is True, f"Should detect {pattern} as initial with double dots"

    def test_looks_like_initial_with_double_dot_invalid_cases(self):
        """Test detection of invalid initial patterns."""
        service = TokenizerService()
        
        # Invalid patterns
        invalid_patterns = [
            "И.",       # Single dot
            "И",        # No dots
            "И.И.",     # Multiple letters
            "И.И..",    # Multiple letters with double dots
            "ООО.",     # Company abbreviation
            "ТОВ.",     # Company abbreviation
            "И.И.И.",   # Multiple initials
            "И-И.",     # With hyphen
            "И'И.",     # With apostrophe
            "И.И",      # Missing final dot
            ".И.",      # Starting with dot
            "И..И",     # Dot in middle
            "123.",     # Numbers
            "И.123",    # Numbers after dot
            "И.И.И..",  # Multiple letters with double dots
            "И.И.И.",   # Multiple letters with single dots
            "И.И.И",    # Multiple letters without final dot
            "И.И.И.И.", # Too many letters
            "И.И.И.И..", # Too many letters with double dots
        ]
        
        for pattern in invalid_patterns:
            result = service._looks_like_initial_with_double_dot(pattern)
            assert result is False, f"Should NOT detect {pattern} as initial with double dots"

    def test_looks_like_initial_with_double_dot_edge_cases(self):
        """Test edge cases for initial detection."""
        service = TokenizerService()
        
        # Edge cases
        edge_cases = [
            ("", False),           # Empty string
            (" ", False),          # Whitespace
            ("..", False),         # Just dots
            (".", False),          # Single dot
            ("И", False),          # Single letter, no dots
            ("И.", False),         # Single letter, single dot
            ("И..", True),         # Single letter, double dots
            ("И...", True),        # Single letter, triple dots
            ("И....", True),       # Single letter, many dots
            ("И.....", True),      # Single letter, many dots
        ]
        
        for pattern, expected in edge_cases:
            result = service._looks_like_initial_with_double_dot(pattern)
            assert result == expected, f"Expected {expected} for {pattern}, got {result}"

    def test_collapse_double_dot_valid_cases(self):
        """Test collapsing double dots in valid cases."""
        service = TokenizerService()
        
        # Valid cases
        valid_cases = [
            ("И..", "И."),         # Basic case
            ("П..", "П."),         # Basic case
            ("А..", "А."),         # Basic case
            ("а..", "а."),         # Lowercase
            ("і..", "і."),         # Ukrainian
            ("ё..", "ё."),         # Russian
            ("A..", "A."),         # Latin uppercase
            ("a..", "a."),         # Latin lowercase
            ("И....", "И."),       # Multiple dots
            ("П.....", "П."),      # Many dots
            ("А......", "А."),     # Many dots
        ]
        
        for input_token, expected in valid_cases:
            result = service._collapse_double_dot(input_token)
            assert result == expected, f"Expected {expected}, got {result} for {input_token}"

    def test_collapse_double_dot_edge_cases(self):
        """Test edge cases for double dot collapsing."""
        service = TokenizerService()
        
        # Edge cases
        edge_cases = [
            ("И.", "И."),          # Single dot (no change)
            ("И", "И"),            # No dots (no change)
            ("", ""),              # Empty string
            ("И..И", "И.И"),       # Dot in middle
            ("И.И..", "И.И."),     # Mixed single and double dots
            ("И.И.И..", "И.И.И."), # Multiple letters with double dots
            ("И.И.И.", "И.И.И."),  # Multiple letters with single dots
            ("И.И.И", "И.И.И"),    # Multiple letters without final dot
        ]
        
        for input_token, expected in edge_cases:
            result = service._collapse_double_dot(input_token)
            assert result == expected, f"Expected {expected}, got {result} for {input_token}"

    def test_has_hyphen_valid_cases(self):
        """Test hyphen detection in valid cases."""
        service = TokenizerService()
        
        # Valid cases
        valid_cases = [
            "word-word",           # Basic hyphen
            "word--word",          # Double hyphen
            "word---word",         # Triple hyphen
            "word----word",        # Many hyphens
            "-word",               # Hyphen at start
            "word-",               # Hyphen at end
            "-",                   # Just hyphen
            "--",                  # Just double hyphen
            "---",                 # Just triple hyphen
            "word-word-word",      # Multiple hyphens
            "word--word--word",    # Multiple double hyphens
        ]
        
        for token in valid_cases:
            result = service._has_hyphen(token)
            assert result is True, f"Should detect hyphen in {token}"

    def test_has_hyphen_invalid_cases(self):
        """Test hyphen detection in invalid cases."""
        service = TokenizerService()
        
        # Invalid cases
        invalid_cases = [
            "word",                # No hyphen
            "word word",           # Space, not hyphen
            "word.word",           # Dot, not hyphen
            "word'word",           # Apostrophe, not hyphen
            "word_word",           # Underscore, not hyphen
            "word=word",           # Equals, not hyphen
            "word+word",           # Plus, not hyphen
            "word*word",           # Asterisk, not hyphen
            "word/word",           # Slash, not hyphen
            "word\\word",          # Backslash, not hyphen
            "word|word",           # Pipe, not hyphen
            "word&word",           # Ampersand, not hyphen
            "word%word",           # Percent, not hyphen
            "word#word",           # Hash, not hyphen
            "word@word",           # At, not hyphen
            "word$word",           # Dollar, not hyphen
            "word!word",           # Exclamation, not hyphen
            "word?word",           # Question, not hyphen
            "word:word",           # Colon, not hyphen
            "word;word",           # Semicolon, not hyphen
            "word,word",           # Comma, not hyphen
            "word.word",           # Period, not hyphen
            "word'word",           # Apostrophe, not hyphen
            "word\"word",          # Quote, not hyphen
            "word'word",           # Single quote, not hyphen
            "word(word",           # Parenthesis, not hyphen
            "word)word",           # Parenthesis, not hyphen
            "word[word",           # Bracket, not hyphen
            "word]word",           # Bracket, not hyphen
            "word{word",           # Brace, not hyphen
            "word}word",           # Brace, not hyphen
            "word<word",           # Less than, not hyphen
            "word>word",           # Greater than, not hyphen
            "word^word",           # Caret, not hyphen
            "word~word",           # Tilde, not hyphen
            "word`word",           # Backtick, not hyphen
            "word\tword",          # Tab, not hyphen
            "word\nword",          # Newline, not hyphen
            "word\rword",          # Carriage return, not hyphen
            "word\fword",          # Form feed, not hyphen
            "word\vword",          # Vertical tab, not hyphen
        ]
        
        for token in invalid_cases:
            result = service._has_hyphen(token)
            assert result is False, f"Should NOT detect hyphen in {token}"

    def test_has_hyphen_edge_cases(self):
        """Test edge cases for hyphen detection."""
        service = TokenizerService()
        
        # Edge cases
        edge_cases = [
            ("", False),           # Empty string
            (" ", False),          # Whitespace
            ("-", True),           # Just hyphen
            ("--", True),          # Just double hyphen
            ("---", True),         # Just triple hyphen
            ("word", False),       # No hyphen
            ("word-", True),       # Hyphen at end
            ("-word", True),       # Hyphen at start
            ("word-word", True),   # Hyphen in middle
            ("word--word", True),  # Double hyphen in middle
            ("word---word", True), # Triple hyphen in middle
        ]
        
        for token, expected in edge_cases:
            result = service._has_hyphen(token)
            assert result == expected, f"Expected {expected} for {token}, got {result}"

    def test_apply_post_processing_rules_empty_input(self):
        """Test post-processing rules with empty input."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Empty input
        tokens, traces, token_traces = service._apply_post_processing_rules([])
        assert tokens == []
        assert traces == []
        assert token_traces == []

    def test_apply_post_processing_rules_single_token(self):
        """Test post-processing rules with single token."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Single token with double dots
        tokens, traces, token_traces = service._apply_post_processing_rules(["И.."])
        assert tokens == ["И."]
        assert len(traces) == 1
        assert traces[0]["rule"] == "collapse_double_dots"
        
        # Single token with hyphen
        tokens, traces, token_traces = service._apply_post_processing_rules(["Петрова-Сидорова"])
        assert tokens == ["Петрова-Сидорова"]
        assert len(traces) == 1
        assert traces[0]["action"] == "preserve_hyphenated_name"
        
        # Single token with both
        tokens, traces, token_traces = service._apply_post_processing_rules(["И.."])
        assert tokens == ["И."]
        assert len(traces) == 1
        assert traces[0]["rule"] == "collapse_double_dots"

    def test_apply_post_processing_rules_multiple_tokens(self):
        """Test post-processing rules with multiple tokens."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Multiple tokens with various patterns
        tokens = ["И..", "Петрова-Сидорова", "А..", "Jean-Luc"]
        processed_tokens, traces, token_traces = service._apply_post_processing_rules(tokens)
        
        # Check processed tokens
        assert processed_tokens == ["И.", "Петрова-Сидорова", "А.", "Jean-Luc"]
        
        # Check traces
        assert len(traces) == 4  # 2 for initials + 2 for hyphens
        
        # Check initial traces
        initial_traces = [t for t in traces if t.get("rule") == "collapse_double_dots"]
        assert len(initial_traces) == 2
        
        # Check hyphen traces
        hyphen_traces = [t for t in traces if t.get("action") == "preserve_hyphenated_name"]
        assert len(hyphen_traces) == 2

    def test_apply_post_processing_rules_disabled_features(self):
        """Test post-processing rules with disabled features."""
        service = TokenizerService(
            fix_initials_double_dot=False,
            preserve_hyphenated_case=False
        )
        
        # Tokens with patterns that would be processed if enabled
        tokens = ["И..", "Петрова-Сидорова", "А..", "Jean-Luc"]
        processed_tokens, traces, token_traces = service._apply_post_processing_rules(tokens)
        
        # Should remain unchanged
        assert processed_tokens == tokens
        assert len(traces) == 0

    def test_apply_post_processing_rules_partial_features(self):
        """Test post-processing rules with partial features enabled."""
        # Only initials enabled
        service1 = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=False
        )
        
        tokens = ["И..", "Петрова-Сидорова", "А..", "Jean-Luc"]
        processed_tokens, traces, token_traces = service1._apply_post_processing_rules(tokens)
        
        assert processed_tokens == ["И.", "Петрова-Сидорова", "А.", "Jean-Luc"]
        assert len(traces) == 2  # Only initials
        
        # Only hyphens enabled
        service2 = TokenizerService(
            fix_initials_double_dot=False,
            preserve_hyphenated_case=True
        )
        
        processed_tokens, traces, token_traces = service2._apply_post_processing_rules(tokens)
        
        assert processed_tokens == ["И..", "Петрова-Сидорова", "А..", "Jean-Luc"]
        assert len(traces) == 2  # Only hyphens

    def test_apply_post_processing_rules_trace_structure(self):
        """Test that traces have correct structure."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        tokens = ["И..", "Петрова-Сидорова"]
        processed_tokens, traces, token_traces = service._apply_post_processing_rules(tokens)
        
        # Check trace structure
        for trace in traces:
            assert isinstance(trace, dict)

            # Handle different trace structures
            if "rule" in trace and trace["rule"] == "collapse_double_dots":
                assert "before" in trace
                assert "after" in trace
                assert trace["before"] == "И.."
                assert trace["after"] == "И."
            elif "action" in trace and trace["action"] == "preserve_hyphenated_name":
                assert "type" in trace
                assert trace["type"] == "tokenize"
                assert "token" in trace
                assert "has_hyphen" in trace
                assert trace["token"] == "Петрова-Сидорова"
                assert trace["has_hyphen"] is True

    def test_apply_post_processing_rules_no_changes(self):
        """Test post-processing rules when no changes are needed."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Tokens that don't need processing
        tokens = ["Иван", "Петров", "ООО", "ТОВ"]
        processed_tokens, traces, token_traces = service._apply_post_processing_rules(tokens)
        
        # Should remain unchanged
        assert processed_tokens == tokens
        assert len(traces) == 0

    def test_apply_post_processing_rules_whitespace_tokens(self):
        """Test post-processing rules with whitespace tokens."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Tokens with whitespace
        tokens = [" ", "\t", "\n", "И..", "Петрова-Сидорова"]
        processed_tokens, traces, token_traces = service._apply_post_processing_rules(tokens)
        
        # Should process only valid tokens
        assert len(processed_tokens) == len(tokens)
        assert processed_tokens[3] == "И."  # Double dots collapsed
        assert processed_tokens[4] == "Петрова-Сидорова"  # Hyphen preserved
        
        # Should have traces for valid tokens
        assert len(traces) == 2  # One for initials, one for hyphens
