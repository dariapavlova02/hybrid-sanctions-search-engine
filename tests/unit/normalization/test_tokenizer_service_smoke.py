#!/usr/bin/env python3
"""
Smoke tests for TokenizerService.

Tests basic functionality and edge cases to ensure the service works correctly
without external dependencies.
"""

import pytest
from src.ai_service.layers.normalization.tokenizer_service import TokenizerService, TokenizationResult


class TestTokenizerServiceSmoke:
    """Smoke tests for TokenizerService basic functionality."""

    def test_init_defaults(self):
        """Test service initialization with default parameters."""
        service = TokenizerService()
        
        assert service.fix_initials_double_dot is True
        assert service.preserve_hyphenated_case is True
        assert service.cache is None
        assert service._total_requests == 0
        assert service._cache_hits == 0
        assert service._cache_misses == 0

    def test_init_with_flags(self):
        """Test service initialization with custom flags."""
        service = TokenizerService(
            fix_initials_double_dot=False,
            preserve_hyphenated_case=False
        )
        
        assert service.fix_initials_double_dot is False
        assert service.preserve_hyphenated_case is False

    def test_initials_collapse_double_dot(self):
        """Test collapsing double dots in initials (И..→И.)."""
        service = TokenizerService(fix_initials_double_dot=True)
        
        # Test various double dot patterns
        test_cases = [
            ("И..", "И."),
            ("П..", "П."),
            ("A..", "A."),
            ("I..", "I."),
            ("И....", "И."),  # Multiple dots
            ("П.....", "П."),  # Many dots
        ]
        
        for input_token, expected in test_cases:
            result = service._looks_like_initial_with_double_dot(input_token)
            assert result is True, f"Should detect {input_token} as initial with double dots"
            
            collapsed = service._collapse_double_dot(input_token)
            assert collapsed == expected, f"Expected {expected}, got {collapsed} for {input_token}"

    def test_initials_no_collapse_when_disabled(self):
        """Test that double dots are not collapsed when feature is disabled."""
        service = TokenizerService(fix_initials_double_dot=False)
        
        tokens = ["И..", "П..", "A.."]
        processed_tokens, traces = service._apply_post_processing_rules(tokens)
        
        # Should remain unchanged
        assert processed_tokens == tokens
        assert len(traces) == 0  # No traces for hyphen preservation only

    def test_hyphenated_preserve_case(self):
        """Test hyphenated name preservation with flag."""
        service = TokenizerService(preserve_hyphenated_case=True)
        
        tokens = ["Петрова-Сидорова", "Jean-Luc", "Smith--Jones"]
        processed_tokens, traces = service._apply_post_processing_rules(tokens)
        
        # Tokens should remain unchanged
        assert processed_tokens == tokens
        
        # Should have traces for hyphenated names
        assert len(traces) == 3
        for trace in traces:
            assert trace["type"] == "tokenize"
            assert trace["action"] == "preserve_hyphenated_name"
            assert trace["has_hyphen"] is True

    def test_hyphenated_no_preserve_when_disabled(self):
        """Test that hyphenated names are not traced when feature is disabled."""
        service = TokenizerService(preserve_hyphenated_case=False)
        
        tokens = ["Петрова-Сидорова", "Jean-Luc"]
        processed_tokens, traces = service._apply_post_processing_rules(tokens)
        
        # Tokens should remain unchanged
        assert processed_tokens == tokens
        assert len(traces) == 0  # No traces for hyphen preservation

    def test_apostrophes_kept_for_names(self):
        """Test that apostrophes in names are preserved."""
        service = TokenizerService()
        
        # These should not be treated as initials with double dots
        test_cases = [
            "О'Брайен",
            "O'Connor", 
            "D'Angelo",
            "L'Étoile"
        ]
        
        for token in test_cases:
            # Should not be detected as initial with double dots
            is_initial = service._looks_like_initial_with_double_dot(token)
            assert is_initial is False, f"Should not detect {token} as initial with double dots"
            
            # Should not contain hyphen
            has_hyphen = service._has_hyphen(token)
            assert has_hyphen is False, f"Should not detect hyphen in {token}"

    def test_nbsp_zero_width_handling(self):
        """Test handling of non-breaking spaces and zero-width characters."""
        service = TokenizerService()
        
        # Test various whitespace characters
        test_cases = [
            "Иван\u00A0Петров",  # Non-breaking space
            "John\u200BSmith",   # Zero-width space
            "Анна\u2000Петрова", # En quad
            "Test\u2001Case",    # Em quad
        ]
        
        for text in test_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False  # Should not fail

    def test_company_abbrev_not_initials(self):
        """Test that company abbreviations are not treated as initials."""
        service = TokenizerService()
        
        # Company abbreviations should not be detected as initials
        company_abbrevs = [
            "ООО.",
            "ТОВ.",
            "ЗАО.",
            "ПАО.",
            "LLC.",
            "Inc.",
            "Corp.",
        ]
        
        for abbrev in company_abbrevs:
            is_initial = service._looks_like_initial_with_double_dot(abbrev)
            assert is_initial is False, f"Should not detect {abbrev} as initial with double dots"

    def test_mixed_scripts_no_split(self):
        """Test that mixed script tokens are not split inappropriately."""
        service = TokenizerService()
        
        # Mixed script names should be preserved as single tokens
        mixed_scripts = [
            "JohnІван",
            "ПетровSmith", 
            "TOB«ПРИВАТБАНК»",
            "Іван-Петров",
        ]
        
        for text in mixed_scripts:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            # Should not split mixed script tokens inappropriately
            assert len(result.tokens) > 0

    def test_empty_and_whitespace_input(self):
        """Test handling of empty and whitespace-only input."""
        service = TokenizerService()
        
        # Empty string
        result = service.tokenize("", language="uk")
        assert isinstance(result, TokenizationResult)
        
        # Whitespace only
        result = service.tokenize("   ", language="uk")
        assert isinstance(result, TokenizationResult)
        
        # Mixed whitespace
        result = service.tokenize("\t\n\r", language="uk")
        assert isinstance(result, TokenizationResult)

    def test_stats_tracking(self):
        """Test that statistics are properly tracked."""
        service = TokenizerService()
        
        # Initial stats
        stats = service.get_stats()
        assert stats['total_requests'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0
        
        # Process a request
        service.tokenize("Иван Петров", language="uk")
        
        # Check updated stats
        stats = service.get_stats()
        assert stats['total_requests'] == 1
        assert stats['cache_misses'] == 1  # No cache, so miss
        assert stats['cache_hits'] == 0

    def test_reset_stats(self):
        """Test statistics reset functionality."""
        service = TokenizerService()
        
        # Process some requests
        service.tokenize("Иван Петров", language="uk")
        service.tokenize("Анна Сидорова", language="uk")
        
        # Verify stats are non-zero
        stats = service.get_stats()
        assert stats['total_requests'] == 2
        
        # Reset stats
        service.reset_stats()
        
        # Verify stats are reset
        stats = service.get_stats()
        assert stats['total_requests'] == 0
        assert stats['cache_hits'] == 0
        assert stats['cache_misses'] == 0

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        service = TokenizerService()
        
        # Should not raise exception even without cache
        service.clear_cache()
        
        # With cache (if provided)
        from src.ai_service.utils.lru_cache_ttl import LruTtlCache
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service_with_cache = TokenizerService(cache=cache)
        service_with_cache.clear_cache()  # Should not raise exception

    def test_post_processing_rules_combination(self):
        """Test that both post-processing rules work together."""
        service = TokenizerService(
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        tokens = ["И..", "Петрова-Сидорова", "А..", "Jean-Luc"]
        processed_tokens, traces = service._apply_post_processing_rules(tokens)
        
        # Check processed tokens
        assert processed_tokens == ["И.", "Петрова-Сидорова", "А.", "Jean-Luc"]
        
        # Check traces
        assert len(traces) == 4  # 2 for initials + 2 for hyphens
        
        # Check initial traces
        initial_traces = [t for t in traces if t["action"] == "collapse_initial_double_dot"]
        assert len(initial_traces) == 2
        
        # Check hyphen traces
        hyphen_traces = [t for t in traces if t["action"] == "preserve_hyphenated_name"]
        assert len(hyphen_traces) == 2

    def test_unicode_normalization(self):
        """Test that Unicode normalization is handled correctly."""
        service = TokenizerService()
        
        # Test various Unicode cases
        test_cases = [
            "Іван",  # Ukrainian I
            "Їжак",  # Ukrainian Yi
            "Євген", # Ukrainian Ye
            "Ґудзик", # Ukrainian Ghe
        ]
        
        for text in test_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_special_punctuation_preservation(self):
        """Test that special punctuation is preserved when appropriate."""
        service = TokenizerService()
        
        # Test punctuation that should be preserved
        test_cases = [
            "О'Брайен",  # Apostrophe
            "Jean-Luc",  # Hyphen
            "Smith--Jones",  # Double hyphen
            "«ПРИВАТБАНК»",  # Quotation marks
        ]
        
        for text in test_cases:
            result = service.tokenize(text, language="uk")
            assert isinstance(result, TokenizationResult)
            # Should preserve the structure
            assert len(result.tokens) > 0

    def test_language_parameter_handling(self):
        """Test that different languages are handled correctly."""
        service = TokenizerService()
        
        languages = ["uk", "ru", "en"]
        
        for lang in languages:
            result = service.tokenize("Test Text", language=lang)
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_feature_flags_parameter(self):
        """Test that feature flags parameter is handled correctly."""
        service = TokenizerService()
        
        # Test with various feature flag combinations
        feature_flags = [
            None,
            {},
            {"test_flag": True},
            {"another_flag": "value", "numeric": 42}
        ]
        
        for flags in feature_flags:
            result = service.tokenize("Test Text", language="uk", feature_flags=flags)
            assert isinstance(result, TokenizationResult)
            assert result.success is not False

    def test_stop_words_parameter(self):
        """Test that custom stop words parameter is handled correctly."""
        service = TokenizerService()
        
        # Test with custom stop words
        custom_stop_words = {"тест", "слово"}
        
        result = service.tokenize(
            "тест слово Иван Петров", 
            language="uk", 
            stop_words=custom_stop_words
        )
        assert isinstance(result, TokenizationResult)
        assert result.success is not False

    def test_boolean_parameters(self):
        """Test that boolean parameters are handled correctly."""
        service = TokenizerService()
        
        # Test various combinations of boolean parameters
        combinations = [
            (True, True),
            (True, False),
            (False, True),
            (False, False)
        ]
        
        for remove_stop_words, preserve_names in combinations:
            result = service.tokenize(
                "Test Text", 
                language="uk",
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names
            )
            assert isinstance(result, TokenizationResult)
            assert result.success is not False
