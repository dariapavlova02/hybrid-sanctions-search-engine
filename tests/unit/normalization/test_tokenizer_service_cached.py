#!/usr/bin/env python3
"""
Tests for CachedTokenizerService.

Tests the enhanced caching capabilities and token classification
functionality of the cached tokenizer service.
"""

import pytest
from src.ai_service.layers.normalization.tokenizer_service import CachedTokenizerService, TokenizationResult
from src.ai_service.utils.lru_cache_ttl import LruTtlCache


class TestCachedTokenizerService:
    """Tests for CachedTokenizerService functionality."""

    def test_init_defaults(self):
        """Test service initialization with default parameters."""
        service = CachedTokenizerService()
        
        assert service.tokenizer_service is not None
        assert service._classification_cache is None
        assert service._classification_requests == 0
        assert service._classification_hits == 0
        assert service._classification_misses == 0

    def test_init_with_cache(self):
        """Test service initialization with cache."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        assert service.tokenizer_service is not None
        assert service._classification_cache is cache
        assert service._classification_requests == 0

    def test_tokenize_with_classification_basic(self):
        """Test basic tokenization with classification."""
        service = CachedTokenizerService()
        
        result, classes = service.tokenize_with_classification(
            "Иван Петров", 
            language="uk"
        )
        
        assert isinstance(result, TokenizationResult)
        assert isinstance(classes, list)
        assert len(classes) == len(result.tokens)
        assert result.success is not False

    def test_tokenize_with_classification_caching(self):
        """Test that classification results are cached."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        text = "Иван Петров"
        
        # First call (cache miss)
        result1, classes1 = service.tokenize_with_classification(text, language="uk")
        
        # Second call (cache hit)
        result2, classes2 = service.tokenize_with_classification(text, language="uk")
        
        # Results should be identical
        assert result1.tokens == result2.tokens
        assert classes1 == classes2
        
        # Check cache statistics
        stats = service.get_stats()
        assert stats['classification_requests'] == 2
        assert stats['classification_hits'] == 1
        assert stats['classification_misses'] == 1

    def test_classify_tokens_direct(self):
        """Test direct token classification without caching."""
        service = CachedTokenizerService()
        
        tokens = ["Иван", "Петров", "А.", "ООО"]
        classes = service._classify_tokens_direct(tokens, "uk")
        
        assert isinstance(classes, list)
        assert len(classes) == len(tokens)
        
        # Check classification logic
        for i, token in enumerate(tokens):
            if len(token) == 1 and token.isalpha():
                assert classes[i] == "initial"
            elif token.isupper():
                assert classes[i] == "acronym"
            elif token.istitle():
                assert classes[i] == "name"
            else:
                assert classes[i] == "word"

    def test_classify_tokens_cached_with_cache(self):
        """Test cached token classification with cache."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        tokens = ["Иван", "Петров", "А.", "ООО"]
        
        # First call (cache miss)
        classes1 = service._classify_tokens_cached(tokens, "uk")
        
        # Second call (cache hit)
        classes2 = service._classify_tokens_cached(tokens, "uk")
        
        # Results should be identical
        assert classes1 == classes2
        
        # Check cache statistics
        stats = service.get_stats()
        assert stats['classification_requests'] == 2
        assert stats['classification_hits'] == 1
        assert stats['classification_misses'] == 1

    def test_classify_tokens_cached_without_cache(self):
        """Test cached token classification without cache."""
        service = CachedTokenizerService()  # No cache
        
        tokens = ["Иван", "Петров", "А.", "ООО"]
        classes = service._classify_tokens_cached(tokens, "uk")
        
        assert isinstance(classes, list)
        assert len(classes) == len(tokens)

    def test_classify_tokens_with_feature_flags(self):
        """Test token classification with feature flags."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        tokens = ["Иван", "Петров"]
        feature_flags = {"test_flag": True}
        
        classes = service._classify_tokens_cached(tokens, "uk", feature_flags)
        
        assert isinstance(classes, list)
        assert len(classes) == len(tokens)

    def test_get_stats_comprehensive(self):
        """Test comprehensive statistics collection."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        # Process some requests
        service.tokenize_with_classification("Иван Петров", language="uk")
        service.tokenize_with_classification("Анна Сидорова", language="uk")
        
        stats = service.get_stats()
        
        # Check basic stats
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'hit_rate' in stats
        assert 'avg_processing_time' in stats
        assert 'total_processing_time' in stats
        
        # Check classification stats
        assert 'classification_requests' in stats
        assert 'classification_hits' in stats
        assert 'classification_misses' in stats
        assert 'classification_hit_rate' in stats
        
        # Check cache stats
        assert 'cache' in stats

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        # Process some requests
        service.tokenize_with_classification("Иван Петров", language="uk")
        
        # Clear cache
        service.clear_cache()
        
        # Should not raise exception
        assert True

    def test_reset_stats(self):
        """Test statistics reset functionality."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        # Process some requests
        service.tokenize_with_classification("Иван Петров", language="uk")
        service.tokenize_with_classification("Анна Сидорова", language="uk")
        
        # Check stats are non-zero
        stats = service.get_stats()
        assert stats['total_requests'] > 0
        assert stats['classification_requests'] > 0
        
        # Reset stats
        service.reset_stats()
        
        # Check stats are reset
        stats = service.get_stats()
        assert stats['total_requests'] == 0
        assert stats['classification_requests'] == 0
        assert stats['classification_hits'] == 0
        assert stats['classification_misses'] == 0

    def test_classification_edge_cases(self):
        """Test token classification edge cases."""
        service = CachedTokenizerService()
        
        # Edge cases for classification
        edge_cases = [
            ("", "word"),           # Empty string
            (" ", "word"),          # Whitespace
            ("123", "word"),        # Numbers
            ("!@#", "word"),        # Special characters
            ("А", "initial"),       # Single Cyrillic letter
            ("A", "initial"),       # Single Latin letter
            ("АБВ", "acronym"),     # Multiple uppercase letters
            ("ABC", "acronym"),     # Multiple uppercase letters
            ("Иван", "name"),       # Title case
            ("John", "name"),       # Title case
            ("ivan", "word"),       # Lowercase
            ("john", "word"),       # Lowercase
        ]
        
        for token, expected_class in edge_cases:
            classes = service._classify_tokens_direct([token], "uk")
            assert classes[0] == expected_class, f"Expected {expected_class} for '{token}', got {classes[0]}"

    def test_classification_with_different_languages(self):
        """Test token classification with different languages."""
        service = CachedTokenizerService()
        
        tokens = ["Иван", "John", "Анна", "Anna"]
        
        for lang in ["uk", "ru", "en"]:
            classes = service._classify_tokens_direct(tokens, lang)
            assert isinstance(classes, list)
            assert len(classes) == len(tokens)

    def test_classification_caching_consistency(self):
        """Test that classification caching is consistent."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        tokens = ["Иван", "Петров", "А.", "ООО"]
        
        # Multiple calls with same tokens
        classes1 = service._classify_tokens_cached(tokens, "uk")
        classes2 = service._classify_tokens_cached(tokens, "uk")
        classes3 = service._classify_tokens_cached(tokens, "uk")
        
        # All results should be identical
        assert classes1 == classes2 == classes3
        
        # Check cache statistics
        stats = service.get_stats()
        assert stats['classification_requests'] == 3
        assert stats['classification_hits'] == 2
        assert stats['classification_misses'] == 1

    def test_classification_with_empty_tokens(self):
        """Test token classification with empty tokens."""
        service = CachedTokenizerService()
        
        # Empty token list
        classes = service._classify_tokens_direct([], "uk")
        assert classes == []
        
        # Tokens with empty strings
        classes = service._classify_tokens_direct(["", " ", "Иван"], "uk")
        assert len(classes) == 3
        assert classes[0] == "word"  # Empty string
        assert classes[1] == "word"  # Whitespace
        assert classes[2] == "name"  # Valid name

    def test_classification_with_special_characters(self):
        """Test token classification with special characters."""
        service = CachedTokenizerService()
        
        special_tokens = [
            "Иван-Петров",    # Hyphenated
            "O'Connor",       # Apostrophe
            "«ПРИВАТБАНК»",   # Quotation marks
            "И..",            # Double dots
            "ООО.",           # Company abbreviation
        ]
        
        classes = service._classify_tokens_direct(special_tokens, "uk")
        
        assert isinstance(classes, list)
        assert len(classes) == len(special_tokens)
        
        # Check classification results
        for i, token in enumerate(special_tokens):
            # Check actual classification results
            if token in ['Иван-Петров', 'Jean-Luc', 'Smith--Jones', 'Name---Surname', 'Word‐Name', 'Text–Dash', 'Line—Em', 'Minus−Sign']:
                # Hyphenated names should be classified as "name" if they start with capital letter
                assert classes[i] == "name", f"Expected 'name' for '{token}', got '{classes[i]}'"
            elif token in ['И..', "О'Брайен", "O'Connor", "D'Angelo", "L'Étoile"]:
                # Single letters with dots or apostrophes should be classified as "initial", "name", or "acronym"
                assert classes[i] in ["initial", "name", "acronym"], f"Expected 'initial', 'name', or 'acronym' for '{token}', got '{classes[i]}'"
            elif token.isupper():
                # All uppercase tokens should be acronyms
                assert classes[i] == "acronym", f"Expected 'acronym' for '{token}', got '{classes[i]}'"
            else:
                assert classes[i] == "word", f"Expected 'word' for '{token}', got '{classes[i]}'"

    def test_classification_hit_rate_calculation(self):
        """Test classification hit rate calculation."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        # No requests yet
        stats = service.get_stats()
        assert stats['classification_hit_rate'] == 0.0
        
        # One request (miss)
        service._classify_tokens_cached(["Иван"], "uk")
        stats = service.get_stats()
        assert stats['classification_hit_rate'] == 0.0
        
        # Second request (hit)
        service._classify_tokens_cached(["Иван"], "uk")
        stats = service.get_stats()
        assert stats['classification_hit_rate'] == 50.0
        
        # Third request (hit)
        service._classify_tokens_cached(["Иван"], "uk")
        stats = service.get_stats()
        assert stats['classification_hit_rate'] == 66.66666666666666

    def test_classification_with_different_feature_flags(self):
        """Test classification with different feature flags."""
        cache = LruTtlCache(maxsize=100, ttl_seconds=300)
        service = CachedTokenizerService(cache=cache)
        
        tokens = ["Иван", "Петров"]
        
        # Different feature flags should create different cache keys
        flags1 = {"flag1": True}
        flags2 = {"flag2": True}
        flags3 = {"flag1": False}
        
        classes1 = service._classify_tokens_cached(tokens, "uk", flags1)
        classes2 = service._classify_tokens_cached(tokens, "uk", flags2)
        classes3 = service._classify_tokens_cached(tokens, "uk", flags3)
        
        # All should be cache misses due to different flags
        stats = service.get_stats()
        assert stats['classification_misses'] == 3
        assert stats['classification_hits'] == 0
