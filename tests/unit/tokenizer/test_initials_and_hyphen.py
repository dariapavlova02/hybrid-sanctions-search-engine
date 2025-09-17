#!/usr/bin/env python3
"""
Unit tests for TokenizerService initials and hyphen handling.
"""

import pytest
from src.ai_service.layers.normalization.tokenizer_service import TokenizerService


class TestTokenizerServiceInitialsAndHyphen:
    """Test cases for TokenizerService initials and hyphen handling."""
    
    def test_collapse_double_dots_in_initials(self):
        """Test that double dots in initials are collapsed to single dot."""
        tokenizer = TokenizerService(fix_initials_double_dot=True)
        
        # Test various double dot patterns
        test_cases = [
            ("И..", "И."),
            ("А..", "А."),
            ("В...", "В."),
            ("П....", "П."),
            ("A..", "A."),  # Latin
            ("І..", "І."),  # Ukrainian
            ("И.И.", "И.И."),  # Should not change
            ("Иван", "Иван"),  # Should not change
            ("И.", "И."),      # Already single dot
            ("ООО", "ООО"),    # Abbreviation without dots
            ("ТОВ", "ТОВ"),    # Abbreviation without dots
            ("A..B.", "A.B."), # Compound initials
            ("И..П.", "И.П."), # Compound initials
        ]
        
        for input_token, expected in test_cases:
            result = tokenizer.collapse_double_dots(input_token)
            assert result == expected, f"Failed for input: {input_token}"
    
    def test_looks_like_initial_with_double_dot(self):
        """Test detection of initials with double dots."""
        tokenizer = TokenizerService()
        
        # Should match
        assert tokenizer._looks_like_initial_with_double_dot("И..")
        assert tokenizer._looks_like_initial_with_double_dot("А...")
        assert tokenizer._looks_like_initial_with_double_dot("В....")
        assert tokenizer._looks_like_initial_with_double_dot("и..")  # lowercase
        
        # Should not match
        assert not tokenizer._looks_like_initial_with_double_dot("И.")
        assert not tokenizer._looks_like_initial_with_double_dot("Иван")
        assert not tokenizer._looks_like_initial_with_double_dot("И.И.")
        assert not tokenizer._looks_like_initial_with_double_dot("123")
        assert not tokenizer._looks_like_initial_with_double_dot("")
    
    def test_has_hyphen_detection(self):
        """Test hyphen detection in tokens."""
        tokenizer = TokenizerService()
        
        # Should detect hyphens
        assert tokenizer._has_hyphen("Петрова-Сидорова")
        assert tokenizer._has_hyphen("Иван-Петр")
        assert tokenizer._has_hyphen("-")
        assert tokenizer._has_hyphen("а-б")
        
        # Should not detect hyphens
        assert not tokenizer._has_hyphen("Петрова")
        assert not tokenizer._has_hyphen("Иван")
        assert not tokenizer._has_hyphen("")
        assert not tokenizer._has_hyphen("123")
    
    def test_post_processing_rules_with_double_dots(self):
        """Test post-processing rules with double dots enabled."""
        tokenizer = TokenizerService(fix_initials_double_dot=True)
        
        tokens = ["И..", "Петрова-Сидорова", "А.", "В..."]
        processed_tokens, traces = tokenizer._apply_post_processing_rules(tokens)
        
        # Check processed tokens
        assert processed_tokens == ["И.", "Петрова-Сидорова", "А.", "В."]
        
        # Check traces
        assert len(traces) == 3  # 2 double dot fixes + 1 hyphen detection
        assert any(trace["rule"] == "collapse_double_dots" for trace in traces)
        assert any(trace.get("action") == "preserve_hyphenated_name" for trace in traces)
    
    def test_post_processing_rules_without_double_dots(self):
        """Test post-processing rules with double dots disabled."""
        tokenizer = TokenizerService(fix_initials_double_dot=False)
        
        tokens = ["И..", "Петрова-Сидорова", "А.", "В..."]
        processed_tokens, traces = tokenizer._apply_post_processing_rules(tokens)
        
        # Check processed tokens (should not change double dots)
        assert processed_tokens == ["И..", "Петрова-Сидорова", "А.", "В..."]
        
        # Check traces (only hyphen detection)
        assert len(traces) == 1
        assert any(trace.get("action") == "preserve_hyphenated_name" for trace in traces)
    
    def test_post_processing_rules_without_hyphen_preservation(self):
        """Test post-processing rules with hyphen preservation disabled."""
        tokenizer = TokenizerService(preserve_hyphenated_case=False)
        
        tokens = ["И..", "Петрова-Сидорова", "А.", "В..."]
        processed_tokens, traces = tokenizer._apply_post_processing_rules(tokens)
        
        # Check processed tokens
        assert processed_tokens == ["И.", "Петрова-Сидорова", "А.", "В."]
        
        # Check traces (only double dot fixes)
        assert len(traces) == 2
        assert all(trace["rule"] == "collapse_double_dots" for trace in traces)
    
    def test_full_tokenization_with_rules(self):
        """Test full tokenization with post-processing rules."""
        tokenizer = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Mock the token processor to return specific tokens
        original_strip_noise = tokenizer.token_processor.strip_noise_and_tokenize
        
        def mock_strip_noise(text, **kwargs):
            # Simulate tokenization result
            tokens = ["И..", "Петрова-Сидорова", "А.", "В..."]
            traces = ["Applied Unicode NFC normalisation", "Collapsed whitespace"]
            metadata = {"quoted_segments": []}
            return tokens, traces, metadata
        
        tokenizer.token_processor.strip_noise_and_tokenize = mock_strip_noise
        
        try:
            result = tokenizer.tokenize("И.. Петрова-Сидорова А. В...")
            
            # Check that post-processing was applied
            assert result.tokens == ["И.", "Петрова-Сидорова", "А.", "В."]
            
            # Check that traces include post-processing
            assert any("collapse_double_dots" in str(trace) for trace in result.traces)
            assert any("preserve_hyphenated_name" in str(trace) for trace in result.traces)
            
        finally:
            # Restore original method
            tokenizer.token_processor.strip_noise_and_tokenize = original_strip_noise
    
    def test_unicode_normalization_in_initials(self):
        """Test that Unicode normalization works correctly with initials."""
        tokenizer = TokenizerService(fix_initials_double_dot=True)
        
        # Test with different Unicode representations of the same character
        test_cases = [
            ("И..", "И."),  # Basic case
            ("И\u0301..", "И\u0301."),  # With combining accent
        ]
        
        for input_token, expected in test_cases:
            result = tokenizer._collapse_double_dot(input_token)
            assert result == expected, f"Failed for input: {input_token}"
    
    def test_edge_cases(self):
        """Test edge cases for post-processing rules."""
        tokenizer = TokenizerService()
        
        # Empty tokens
        tokens, traces = tokenizer._apply_post_processing_rules([])
        assert tokens == []
        assert traces == []
        
        # Single character tokens
        tokens, traces = tokenizer._apply_post_processing_rules(["a", "1", "."])
        assert tokens == ["a", "1", "."]
        assert traces == []
        
        # Mixed case initials
        tokens, traces = tokenizer._apply_post_processing_rules(["и..", "А..", "в..."])
        assert tokens == ["и.", "А.", "в."]
        assert len(traces) == 3
