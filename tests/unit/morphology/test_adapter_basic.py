"""
Unit tests for MorphologyAdapter basic functionality.

Tests the core morphology adapter with caching, UK dictionary support,
and fallback behavior.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import List, Tuple

from src.ai_service.layers.normalization.morphology_adapter import (
    MorphologyAdapter,
    MorphParse,
    get_global_adapter,
    clear_global_cache,
)


class TestMorphologyAdapterBasic:
    """Test basic MorphologyAdapter functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        # Clear global cache before each test
        clear_global_cache()

    def test_adapter_initialization(self):
        """Test adapter initialization with custom cache size."""
        adapter = MorphologyAdapter(cache_size=1000)
        assert adapter._cache_size == 1000
        assert "ru" in adapter._analyzers
        assert "uk" in adapter._analyzers

    def test_parse_empty_token(self):
        """Test parsing empty token returns empty list."""
        adapter = MorphologyAdapter()
        result = adapter.parse("", "ru")
        assert result == []
        
        result = adapter.parse("   ", "ru")
        assert result == []

    def test_parse_invalid_language(self):
        """Test parsing with invalid language returns empty list."""
        adapter = MorphologyAdapter()
        result = adapter.parse("тест", "en")
        assert result == []
        
        result = adapter.parse("тест", "invalid")
        assert result == []

    def test_to_nominative_empty_token(self):
        """Test nominative conversion of empty token."""
        adapter = MorphologyAdapter()
        result = adapter.to_nominative("", "ru")
        assert result == ""

    def test_to_nominative_invalid_language(self):
        """Test nominative conversion with invalid language."""
        adapter = MorphologyAdapter()
        result = adapter.to_nominative("тест", "en")
        assert result == "тест"

    def test_detect_gender_empty_token(self):
        """Test gender detection of empty token."""
        adapter = MorphologyAdapter()
        result = adapter.detect_gender("", "ru")
        assert result == "unknown"

    def test_detect_gender_invalid_language(self):
        """Test gender detection with invalid language."""
        adapter = MorphologyAdapter()
        result = adapter.detect_gender("тест", "en")
        assert result == "unknown"

    def test_cache_functionality(self):
        """Test that caching works correctly."""
        adapter = MorphologyAdapter(cache_size=100)
        
        # First call should miss cache
        result1 = adapter.parse("тест", "ru")
        
        # Second call should hit cache
        result2 = adapter.parse("тест", "ru")
        
        # Results should be identical
        assert result1 == result2
        
        # Check cache stats
        stats = adapter.get_cache_stats()
        assert stats["parse_cache_size"] > 0

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        adapter = MorphologyAdapter()
        
        # Populate cache
        adapter.parse("тест", "ru")
        stats_before = adapter.get_cache_stats()
        assert stats_before["parse_cache_size"] > 0
        
        # Clear cache
        adapter.clear_cache()
        stats_after = adapter.get_cache_stats()
        assert stats_after["parse_cache_size"] == 0

    def test_warmup_functionality(self):
        """Test cache warmup with sample data."""
        adapter = MorphologyAdapter()
        
        samples = [
            ("Анна", "ru"),
            ("Иван", "ru"),
            ("Олена", "uk"),
            ("Іван", "uk"),
        ]
        
        # Warmup should not raise exceptions
        adapter.warmup(samples)
        
        # Check that samples are now cached
        stats = adapter.get_cache_stats()
        assert stats["parse_cache_size"] > 0

    def test_warmup_empty_samples(self):
        """Test warmup with empty samples list."""
        adapter = MorphologyAdapter()
        
        # Should not raise exceptions
        adapter.warmup([])
        adapter.warmup(None)

    def test_preserve_case_functionality(self):
        """Test case preservation in results."""
        adapter = MorphologyAdapter()
        
        # Test with mock parse results
        with patch.object(adapter, '_parse_uncached') as mock_parse:
            mock_parse.return_value = [
                MorphParse(
                    normal="тест",
                    tag="NOUN,masc,sing,nomn",
                    score=0.9,
                    case="nomn",
                    gender="masc",
                    nominative="тест"
                )
            ]
            
            # Test uppercase preservation
            result = adapter.to_nominative("ТЕСТ", "ru")
            assert result == "ТЕСТ"
            
            # Test title case preservation
            result = adapter.to_nominative("Тест", "ru")
            assert result == "Тест"
            
            # Test lowercase preservation
            result = adapter.to_nominative("тест", "ru")
            assert result == "тест"

    def test_best_parse_selection(self):
        """Test best parse selection logic."""
        adapter = MorphologyAdapter()
        
        # Create test parses with different scores
        parses = [
            MorphParse("тест1", "NOUN,masc,sing,nomn", 0.5, "nomn", "masc", "тест1"),
            MorphParse("тест2", "NOUN,masc,sing,gent", 0.9, "gent", "masc", "тест2"),
            MorphParse("тест3", "NOUN,femn,sing,nomn", 0.7, "nomn", "femn", "тест3"),
        ]
        
        best = adapter._best_parse(parses)
        assert best is not None
        assert best.score == 0.9  # Highest score should be selected

    def test_best_parse_empty_list(self):
        """Test best parse selection with empty list."""
        adapter = MorphologyAdapter()
        best = adapter._best_parse([])
        assert best is None

    def test_uk_availability_check(self):
        """Test Ukrainian dictionary availability check."""
        adapter = MorphologyAdapter()
        
        # Should return boolean
        is_available = adapter.is_uk_available()
        assert isinstance(is_available, bool)

    def test_global_adapter_singleton(self):
        """Test global adapter singleton behavior."""
        # Clear global state
        clear_global_cache()
        
        # Get first instance
        adapter1 = get_global_adapter()
        assert adapter1 is not None
        
        # Get second instance - should be same object
        adapter2 = get_global_adapter()
        assert adapter1 is adapter2

    def test_global_adapter_custom_cache_size(self):
        """Test global adapter with custom cache size."""
        # Clear global state
        clear_global_cache()
        
        # First call with custom size
        adapter1 = get_global_adapter(cache_size=1000)
        assert adapter1._cache_size == 1000
        
        # Second call with same size should return same instance
        adapter2 = get_global_adapter(cache_size=1000)
        assert adapter1 is adapter2
        assert adapter2._cache_size == 1000
        
        # Third call with different size should create new instance
        adapter3 = get_global_adapter(cache_size=2000)
        assert adapter1 is not adapter3
        assert adapter3._cache_size == 2000

    def test_thread_safety(self):
        """Test that adapter operations are thread-safe."""
        import threading
        import time
        
        adapter = MorphologyAdapter()
        results = []
        errors = []
        
        def worker(token: str, lang: str):
            try:
                result = adapter.parse(token, lang)
                results.append((token, lang, len(result)))
            except Exception as e:
                errors.append(e)
        
        # Create multiple threads
        threads = []
        for i in range(10):
            thread = threading.Thread(target=worker, args=(f"тест{i}", "ru"))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check that no errors occurred
        assert len(errors) == 0
        assert len(results) == 10

    def test_fallback_behavior_without_pymorphy3(self):
        """Test fallback behavior when pymorphy3 is not available."""
        with patch('builtins.__import__') as mock_import:
            def side_effect(name, *args, **kwargs):
                if name == 'pymorphy3':
                    raise ImportError("No module named 'pymorphy3'")
                return __import__(name, *args, **kwargs)
            
            mock_import.side_effect = side_effect
            
            adapter = MorphologyAdapter()
            
            # Should not crash
            result = adapter.parse("тест", "ru")
            assert result == []
            
            result = adapter.to_nominative("тест", "ru")
            assert result == "тест"
            
            result = adapter.detect_gender("тест", "ru")
            assert result == "unknown"

    def test_uk_fallback_behavior(self):
        """Test Ukrainian fallback behavior when UK dictionary is not available."""
        with patch.object(MorphologyAdapter, '_create_analyzer') as mock_create:
            # Mock UK analyzer creation to fail
            def mock_create_analyzer(lang):
                if lang == "uk":
                    raise Exception("UK dictionary not available")
                else:
                    return Mock()
            
            mock_create.side_effect = mock_create_analyzer
            
            # Create adapter with mocked analyzer creation
            try:
                adapter = MorphologyAdapter()
                
                # Should not crash and should indicate UK is not available
                assert not adapter.is_uk_available()
                
                # Should still work for Russian
                result = adapter.parse("тест", "ru")
                # Result depends on mock, but should not crash
            except Exception as e:
                # If adapter creation fails due to UK analyzer, that's also acceptable
                # as long as it doesn't crash the entire service
                assert "UK dictionary not available" in str(e)

    def test_morph_parse_dataclass(self):
        """Test MorphParse dataclass functionality."""
        parse = MorphParse(
            normal="тест",
            tag="NOUN,masc,sing,nomn",
            score=0.9,
            case="nomn",
            gender="masc",
            nominative="тест"
        )
        
        assert parse.normal == "тест"
        assert parse.tag == "NOUN,masc,sing,nomn"
        assert parse.score == 0.9
        assert parse.case == "nomn"
        assert parse.gender == "masc"
        assert parse.nominative == "тест"
        
        # Test immutability
        with pytest.raises(AttributeError):
            parse.normal = "другой"

    def test_cache_stats_structure(self):
        """Test cache statistics structure."""
        adapter = MorphologyAdapter()
        
        # Populate some cache
        adapter.parse("тест", "ru")
        adapter.to_nominative("тест", "ru")
        adapter.detect_gender("тест", "ru")
        
        stats = adapter.get_cache_stats()
        
        # Check that all expected keys are present
        expected_keys = [
            "parse_cache_size",
            "parse_cache_hits", 
            "parse_cache_misses",
            "nominative_cache_size",
            "gender_cache_size"
        ]
        
        for key in expected_keys:
            assert key in stats
            assert isinstance(stats[key], int)
            assert stats[key] >= 0

    def test_unicode_normalization(self):
        """Test that Unicode normalization is applied correctly."""
        adapter = MorphologyAdapter()
        
        # Test with different Unicode forms
        test_cases = [
            "тест",  # Normal form
            "тест",  # Same as above
        ]
        
        for token in test_cases:
            # Should not crash
            result = adapter.parse(token, "ru")
            assert isinstance(result, list)

    def test_large_cache_handling(self):
        """Test handling of large cache sizes."""
        # Test with very large cache size
        adapter = MorphologyAdapter(cache_size=1000000)
        assert adapter._cache_size == 1000000
        
        # Should not crash during initialization
        assert adapter is not None

    def test_error_handling_in_parse(self):
        """Test error handling during parsing."""
        adapter = MorphologyAdapter()
        
        # Mock analyzer to raise exception
        with patch.object(adapter, '_get_analyzer') as mock_get_analyzer:
            mock_analyzer = Mock()
            mock_analyzer.parse.side_effect = Exception("Parse error")
            mock_get_analyzer.return_value = mock_analyzer
            
            # Should not crash, should return empty list
            result = adapter.parse("тест", "ru")
            assert result == []

    def test_error_handling_in_inflection(self):
        """Test error handling during inflection."""
        adapter = MorphologyAdapter()
        
        # Mock parse to return valid parse but with inflection error
        with patch.object(adapter, '_parse_uncached') as mock_parse:
            mock_parse.return_value = [
                MorphParse(
                    normal="тест",
                    tag="NOUN,masc,sing,nomn",
                    score=0.9,
                    case="nomn",
                    gender="masc",
                    nominative="тест"  # Valid nominative
                )
            ]
            
            # Should work normally
            result = adapter.to_nominative("тест", "ru")
            assert result == "тест"
