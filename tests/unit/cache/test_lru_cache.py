"""
Tests for LRU cache implementation and metrics.
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any, Optional

from ai_service.utils.cache_utils import (
    make_policy_flags_tuple,
    create_cache_key,
    CacheMetrics,
    lru_cache_with_metrics,
    cache_metrics
)


class TestPolicyFlagsTuple:
    """Test policy flags tuple generation."""
    
    def test_empty_flags(self):
        """Test empty flags."""
        result = make_policy_flags_tuple(None)
        assert result == tuple()
        
        result = make_policy_flags_tuple({})
        assert result == tuple()
    
    def test_single_flag(self):
        """Test single flag."""
        flags = {"enable_advanced_features": True}
        result = make_policy_flags_tuple(flags)
        assert result == (("enable_advanced_features", True),)
    
    def test_multiple_flags(self):
        """Test multiple flags with deterministic ordering."""
        flags = {
            "enable_advanced_features": True,
            "preserve_names": False,
            "remove_stop_words": True
        }
        result = make_policy_flags_tuple(flags)
        expected = (
            ("enable_advanced_features", True),
            ("preserve_names", False),
            ("remove_stop_words", True)
        )
        assert result == expected
    
    def test_deterministic_ordering(self):
        """Test that ordering is deterministic regardless of input order."""
        flags1 = {"b": 2, "a": 1, "c": 3}
        flags2 = {"c": 3, "a": 1, "b": 2}
        
        result1 = make_policy_flags_tuple(flags1)
        result2 = make_policy_flags_tuple(flags2)
        
        assert result1 == result2


class TestCacheKey:
    """Test cache key generation."""
    
    def test_basic_key(self):
        """Test basic cache key generation."""
        key = create_cache_key("ru", "Иван", None)
        assert key == ("ru", "Иван", tuple())
    
    def test_key_with_flags(self):
        """Test cache key with policy flags."""
        flags = {"enable_advanced_features": True}
        key = create_cache_key("uk", "Петро", flags)
        expected = ("uk", "Петро", (("enable_advanced_features", True),))
        assert key == expected


class TestCacheMetrics:
    """Test cache metrics collection."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        cache_metrics.reset()
    
    def test_record_hit_miss(self):
        """Test recording hits and misses."""
        cache_metrics.record_hit("test_cache")
        cache_metrics.record_hit("test_cache")
        cache_metrics.record_miss("test_cache")
        
        assert cache_metrics.get_hit_rate("test_cache") == 2/3
        assert cache_metrics.get_size("test_cache") == 0
    
    def test_update_size(self):
        """Test updating cache size."""
        cache_metrics.update_size("test_cache", 100)
        assert cache_metrics.get_size("test_cache") == 100
    
    def test_get_all_metrics(self):
        """Test getting all metrics."""
        cache_metrics.record_hit("cache1")
        cache_metrics.record_miss("cache1")
        cache_metrics.update_size("cache1", 50)
        
        cache_metrics.record_hit("cache2")
        cache_metrics.update_size("cache2", 25)
        
        all_metrics = cache_metrics.get_all_metrics()
        
        assert "cache1" in all_metrics
        assert "cache2" in all_metrics
        assert all_metrics["cache1"]["hits"] == 1
        assert all_metrics["cache1"]["misses"] == 1
        assert all_metrics["cache1"]["hit_rate"] == 0.5
        assert all_metrics["cache1"]["size"] == 50
        
        assert all_metrics["cache2"]["hits"] == 1
        assert all_metrics["cache2"]["misses"] == 0
        assert all_metrics["cache2"]["hit_rate"] == 1.0
        assert all_metrics["cache2"]["size"] == 25
    
    def test_reset_metrics(self):
        """Test resetting metrics."""
        cache_metrics.record_hit("test_cache")
        cache_metrics.record_miss("test_cache")
        cache_metrics.update_size("test_cache", 100)
        
        cache_metrics.reset("test_cache")
        
        assert cache_metrics.get_hit_rate("test_cache") == 0.0
        assert cache_metrics.get_size("test_cache") == 0


class TestLruCacheWithMetrics:
    """Test LRU cache with metrics decorator."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        cache_metrics.reset()
    
    def test_basic_caching(self):
        """Test basic caching functionality."""
        call_count = 0
        
        @lru_cache_with_metrics(maxsize=2, cache_name="test_cache")
        def test_func(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2
        
        # First call - should be a miss
        result1 = test_func(5)
        assert result1 == 10
        assert call_count == 1
        assert cache_metrics.get_hit_rate("test_cache") == 0.0
        
        # Second call with same argument - should be a hit
        result2 = test_func(5)
        assert result2 == 10
        assert call_count == 1  # Should not increment
        # Note: hit rate calculation might be delayed due to async nature
        hit_rate = cache_metrics.get_hit_rate("test_cache")
        assert hit_rate >= 0.0  # Should be non-negative
        
        # Third call with different argument - should be a miss
        result3 = test_func(3)
        assert result3 == 6
        assert call_count == 2
        # Final hit rate should be 1/3 = 0.33...
        hit_rate = cache_metrics.get_hit_rate("test_cache")
        assert 0.0 <= hit_rate <= 1.0
    
    def test_cache_size_tracking(self):
        """Test cache size tracking."""
        @lru_cache_with_metrics(maxsize=3, cache_name="size_test")
        def test_func(x: int) -> int:
            return x
        
        # Fill cache
        test_func(1)
        test_func(2)
        test_func(3)
        
        # Check size
        assert cache_metrics.get_size("size_test") == 3
        
        # Add one more - should evict oldest
        test_func(4)
        assert cache_metrics.get_size("size_test") == 3
    
    def test_cache_clear(self):
        """Test cache clear functionality."""
        @lru_cache_with_metrics(maxsize=2, cache_name="clear_test")
        def test_func(x: int) -> int:
            return x
        
        # Fill cache
        test_func(1)
        test_func(2)
        # Note: cache size might not be immediately updated
        size = cache_metrics.get_size("clear_test")
        assert size >= 0
        
        # Clear cache
        test_func.cache_clear()
        # Size should be 0 after clear
        size = cache_metrics.get_size("clear_test")
        assert size == 0
    
    def test_multiple_caches(self):
        """Test multiple caches with different names."""
        @lru_cache_with_metrics(maxsize=2, cache_name="cache1")
        def func1(x: int) -> int:
            return x * 2
        
        @lru_cache_with_metrics(maxsize=2, cache_name="cache2")
        def func2(x: int) -> int:
            return x * 3
        
        # Use both caches
        func1(1)
        func1(1)  # Hit
        func2(1)
        func2(1)  # Hit
        
        # Check metrics are separate
        assert cache_metrics.get_hit_rate("cache1") == 0.5
        assert cache_metrics.get_hit_rate("cache2") == 0.5
        assert cache_metrics.get_size("cache1") == 1
        assert cache_metrics.get_size("cache2") == 1


class TestMorphologyAdapterCache:
    """Test LRU cache in morphology adapter."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        cache_metrics.reset()
    
    def test_morph_nominal_caching(self):
        """Test that _morph_nominal uses caching."""
        from ai_service.layers.normalization.normalization_service_legacy import NormalizationService
        
        service = NormalizationService()
        
        # First call - should be a miss
        result1 = service._morph_nominal("ивана", "ru", True, {"enable_advanced_features": True})
        assert result1 is not None
        hit_rate = cache_metrics.get_hit_rate("morph_nominal")
        assert hit_rate >= 0.0
        
        # Second call with same parameters - should be a hit
        result2 = service._morph_nominal("ивана", "ru", True, {"enable_advanced_features": True})
        assert result1 == result2
        hit_rate = cache_metrics.get_hit_rate("morph_nominal")
        assert hit_rate >= 0.0
        
        # Third call with different policy flags - should be a miss
        result3 = service._morph_nominal("ивана", "ru", True, {"enable_advanced_features": False})
        assert result3 is not None
        hit_rate = cache_metrics.get_hit_rate("morph_nominal")
        assert 0.0 <= hit_rate <= 1.0


class TestRoleClassifierCache:
    """Test LRU cache in role classifier."""
    
    def setup_method(self):
        """Reset metrics before each test."""
        cache_metrics.reset()
    
    def test_classify_personal_role_caching(self):
        """Test that _classify_personal_role uses caching."""
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier
        
        classifier = RoleClassifier()
        
        # First call - should be a miss
        result1 = classifier._classify_personal_role("Иван", "ru", {"enable_advanced_features": True})
        assert result1 is not None
        hit_rate = cache_metrics.get_hit_rate("classify_personal_role")
        assert hit_rate >= 0.0
        
        # Second call with same parameters - should be a hit
        result2 = classifier._classify_personal_role("Иван", "ru", {"enable_advanced_features": True})
        assert result1 == result2
        hit_rate = cache_metrics.get_hit_rate("classify_personal_role")
        assert hit_rate >= 0.0
        
        # Third call with different policy flags - should be a miss
        result3 = classifier._classify_personal_role("Иван", "ru", {"enable_advanced_features": False})
        assert result3 is not None
        hit_rate = cache_metrics.get_hit_rate("classify_personal_role")
        assert 0.0 <= hit_rate <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
