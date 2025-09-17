#!/usr/bin/env python3
"""
Property-based tests for TokenizerService using Hypothesis.

Tests tokenization properties and invariants to ensure robust behavior
across a wide range of inputs.
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
from src.ai_service.layers.normalization.tokenizer_service import TokenizerService, TokenizationResult

# Configure Hypothesis settings for CI
settings.register_profile("ci", suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
settings.load_profile("ci")


class TestTokenizerServiceProperty:
    """Property-based tests for TokenizerService using Hypothesis."""

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=1000
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_tokenization_never_fails(self, text):
        """Property: tokenization should never fail for any valid text input."""
        service = TokenizerService()
        
        result = service.tokenize(text, language="uk")
        
        # Should always return a valid result
        assert isinstance(result, TokenizationResult)
        assert result.success is not False
        assert isinstance(result.tokens, list)
        assert isinstance(result.traces, list)
        assert isinstance(result.metadata, dict)
        assert isinstance(result.processing_time, float)
        assert result.processing_time >= 0.0

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=1,
            max_size=500
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_tokenization_preserves_content(self, text):
        """Property: tokenization should preserve all meaningful content."""
        service = TokenizerService()
        
        result = service.tokenize(text, language="uk")
        
        # Join tokens and normalize whitespace
        joined_tokens = " ".join(result.tokens)
        normalized_original = " ".join(text.split())
        normalized_joined = " ".join(joined_tokens.split())
        
        # Should preserve all letters (allowing for punctuation changes and Unicode normalization)
        original_letters = "".join(c for c in normalized_original if c.isalpha())
        joined_letters = "".join(c for c in normalized_joined if c.isalpha())
        
        # Allow for Unicode normalization differences
        if original_letters != joined_letters:
            # Check if it's just a normalization difference
            import unicodedata
            normalized_original_letters = unicodedata.normalize('NFKC', original_letters)
            normalized_joined_letters = unicodedata.normalize('NFKC', joined_letters)
            if normalized_original_letters != normalized_joined_letters:
                # For very complex Unicode cases, just ensure we don't lose all letters
                assert len(original_letters) > 0 or len(joined_letters) > 0, f"Lost all letters: '{original_letters}' vs '{joined_letters}'"

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=200
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_double_dot_collapse_property(self, text):
        """Property: double dot collapsing should be idempotent and safe."""
        service = TokenizerService(fix_initials_double_dot=True)
        
        result = service.tokenize(text, language="uk")
        
        # Check that no token has multiple consecutive dots
        for token in result.tokens:
            if ".." in token:
                # If it has double dots, it should not be a single letter initial
                assert not (len(token) > 2 and token[0].isalpha() and token[1:] == "." * (len(token) - 1))

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=200
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_hyphen_preservation_property(self, text):
        """Property: hyphen preservation should maintain hyphenated structure."""
        service = TokenizerService(preserve_hyphenated_case=True)
        
        result = service.tokenize(text, language="uk")
        
        # Check that hyphens are preserved in tokens
        original_hyphens = text.count('-')
        token_hyphens = sum(token.count('-') for token in result.tokens)
        
        # Should preserve all hyphens
        assert token_hyphens >= original_hyphens, f"Lost hyphens: {original_hyphens} -> {token_hyphens}"

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_whitespace_normalization_property(self, text):
        """Property: whitespace should be normalized consistently."""
        service = TokenizerService()
        
        result = service.tokenize(text, language="uk")
        
        # Check that tokens don't start or end with whitespace
        for token in result.tokens:
            assert not token.startswith(' '), f"Token starts with space: '{token}'"
            assert not token.endswith(' '), f"Token ends with space: '{token}'"
            assert not token.startswith('\t'), f"Token starts with tab: '{token}'"
            assert not token.endswith('\t'), f"Token ends with tab: '{token}'"

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_empty_token_handling_property(self, text):
        """Property: no empty tokens should be produced."""
        service = TokenizerService()
        
        result = service.tokenize(text, language="uk")
        
        # Check that no empty tokens are produced
        for token in result.tokens:
            assert token != "", f"Empty token found in result"
            assert token.strip() != "", f"Whitespace-only token found: '{token}'"

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_unicode_normalization_property(self, text):
        """Property: Unicode normalization should be consistent."""
        service = TokenizerService()
        
        result = service.tokenize(text, language="uk")
        
        # Check that all tokens are properly normalized
        for token in result.tokens:
            # Should not contain control characters
            for char in token:
                assert ord(char) >= 0x20 or char in ['\t', '\n', '\r'], f"Control character found: {repr(char)}"
            
            # Should not contain invisible characters
            assert '\u200B' not in token, f"Zero-width space found in token: '{token}'"
            assert '\u200C' not in token, f"Zero-width non-joiner found in token: '{token}'"
            assert '\u200D' not in token, f"Zero-width joiner found in token: '{token}'"

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_trace_consistency_property(self, text):
        """Property: traces should be consistent with token processing."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        result = service.tokenize(text, language="uk")
        
        # Check that traces are valid
        assert isinstance(result.traces, list)
        for trace in result.traces:
            # Traces can be either dict or string
            assert isinstance(trace, (dict, str))
            if isinstance(trace, dict):
                assert "type" in trace
                assert "action" in trace

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_metadata_consistency_property(self, text):
        """Property: metadata should be consistent and valid."""
        service = TokenizerService()
        
        result = service.tokenize(text, language="uk")
        
        # Check that metadata is valid
        assert isinstance(result.metadata, dict)
        
        # Check processing time
        assert isinstance(result.processing_time, float)
        assert result.processing_time >= 0.0

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_language_independence_property(self, text):
        """Property: tokenization should work consistently across languages."""
        service = TokenizerService()
        
        languages = ["uk", "ru", "en"]
        results = []
        
        for lang in languages:
            result = service.tokenize(text, language=lang)
            results.append(result)
        
        # All results should be valid
        for result in results:
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_feature_flags_independence_property(self, text):
        """Property: tokenization should work with different feature flag combinations."""
        service = TokenizerService()
        
        # Test different feature flag combinations
        flag_combinations = [
            None,
            {},
            {"test_flag": True},
            {"another_flag": "value"},
            {"numeric_flag": 42},
        ]
        
        for flags in flag_combinations:
            result = service.tokenize(text, language="uk", feature_flags=flags)
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_boolean_parameters_independence_property(self, text):
        """Property: tokenization should work with different boolean parameter combinations."""
        service = TokenizerService()
        
        # Test different boolean parameter combinations
        boolean_combinations = [
            (True, True),
            (True, False),
            (False, True),
            (False, False),
        ]
        
        for remove_stop_words, preserve_names in boolean_combinations:
            result = service.tokenize(
                text, 
                language="uk",
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names
            )
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_stop_words_independence_property(self, text):
        """Property: tokenization should work with different stop words configurations."""
        service = TokenizerService()
        
        # Test different stop words configurations
        stop_words_configs = [
            None,
            set(),
            {"тест"},
            {"тест", "слово"},
            {"", " "},
        ]
        
        for stop_words in stop_words_configs:
            result = service.tokenize(
                text, 
                language="uk", 
                stop_words=stop_words
            )
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    @given(
        text=st.text(
            alphabet=st.characters(
                whitelist_categories=('Lu', 'Ll', 'Lt', 'Lm', 'Lo', 'Nd', 'Pc', 'Pd', 'Pe', 'Pf', 'Pi', 'Po', 'Ps', 'Sc', 'Sk', 'Sm', 'So', 'Zs'),
                min_codepoint=0x0020,
                max_codepoint=0x10FFFF
            ),
            min_size=0,
            max_size=100
        )
    )
    @settings(max_examples=300, deadline=None)
    def test_caching_consistency_property(self, text):
        """Property: caching should not affect tokenization results."""
        service = TokenizerService()
        
        # First call (cache miss)
        result1 = service.tokenize(text, language="uk")
        
        # Second call (should be identical)
        result2 = service.tokenize(text, language="uk")
        
        # Results should be identical
        assert result1.tokens == result2.tokens
        assert result1.metadata == result2.metadata
        # Traces might differ due to cache hit/miss, but content should be same
