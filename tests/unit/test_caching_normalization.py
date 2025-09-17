#!/usr/bin/env python3
"""
Unit tests for caching in normalization pipeline.

Tests LRU cache with TTL, cache integration in services,
and cache performance metrics.
"""

import pytest
import time
from unittest.mock import Mock, patch

from src.ai_service.utils.lru_cache_ttl import LruTtlCache, CacheManager, create_cache_key, create_flags_hash
from src.ai_service.layers.normalization.tokenizer_service import TokenizerService
from src.ai_service.layers.normalization.morphology_adapter import MorphologyAdapter
from src.ai_service.monitoring.cache_metrics import CacheMetrics, MetricsCollector


class TestLruTtlCache:
    """Test LRU TTL cache functionality."""
    
    def test_basic_operations(self):
        """Test basic cache operations."""
        cache = LruTtlCache(maxsize=3, ttl_seconds=60)
        
        # Test set and get
        cache.set("key1", "value1")
        hit, value = cache.get("key1")
        assert hit is True
        assert value == "value1"
        
        # Test miss
        hit, value = cache.get("nonexistent")
        assert hit is False
        assert value is None
    
    def test_lru_eviction(self):
        """Test LRU eviction when maxsize is reached."""
        cache = LruTtlCache(maxsize=2, ttl_seconds=60)
        
        # Fill cache to capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Add one more - should evict key1 (least recently used)
        cache.set("key3", "value3")
        
        # key1 should be evicted
        hit, _ = cache.get("key1")
        assert hit is False
        
        # key2 and key3 should still be there
        hit, value = cache.get("key2")
        assert hit is True
        assert value == "value2"
        
        hit, value = cache.get("key3")
        assert hit is True
        assert value == "value3"
    
    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=0.1)  # Very short TTL
        
        # Set value
        cache.set("key1", "value1")
        
        # Should be available immediately
        hit, value = cache.get("key1")
        assert hit is True
        assert value == "value1"
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Should be expired now
        hit, value = cache.get("key1")
        assert hit is False
        assert value is None
    
    def test_purge_expired(self):
        """Test purging expired entries."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=0.1)
        
        # Set values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Wait for expiration
        time.sleep(0.2)
        
        # Purge expired
        purged_count = cache.purge_expired()
        assert purged_count == 2
        
        # Cache should be empty
        assert len(cache) == 0
    
    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        import threading
        
        cache = LruTtlCache(maxsize=100, ttl_seconds=60)
        results = []
        
        def worker(thread_id):
            for i in range(10):
                key = f"key_{thread_id}_{i}"
                value = f"value_{thread_id}_{i}"
                cache.set(key, value)
                
                hit, retrieved_value = cache.get(key)
                results.append((hit, retrieved_value == value))
        
        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All operations should have succeeded
        assert len(results) == 50
        assert all(hit and correct for hit, correct in results)
    
    def test_statistics(self):
        """Test cache statistics."""
        cache = LruTtlCache(maxsize=2, ttl_seconds=60)
        
        # Initial stats
        stats = cache.get_stats()
        assert stats['hits'] == 0
        assert stats['misses'] == 0
        assert stats['hit_rate'] == 0.0
        
        # Test hits and misses
        cache.set("key1", "value1")
        cache.get("key1")  # hit
        cache.get("key2")  # miss
        
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['hit_rate'] == 50.0
    
    def test_enable_disable(self):
        """Test enabling and disabling cache."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=60)
        
        # Test disabled cache
        cache.disable()
        cache.set("key1", "value1")
        hit, value = cache.get("key1")
        assert hit is False
        assert value is None
        
        # Test re-enabling
        cache.enable()
        cache.set("key1", "value1")
        hit, value = cache.get("key1")
        assert hit is True
        assert value == "value1"


class TestCacheManager:
    """Test cache manager functionality."""
    
    def test_cache_manager_creation(self):
        """Test cache manager creation."""
        config = {
            'max_size': 100,
            'ttl_sec': 300,
            'enable_cache': True
        }
        
        manager = CacheManager(config)
        
        assert manager.maxsize == 100
        assert manager.ttl_seconds == 300
        assert manager.enabled is True
        
        # Check caches are created
        assert manager.tokenizer_cache is not None
        assert manager.morphology_cache is not None
    
    def test_cache_manager_disabled(self):
        """Test cache manager when caching is disabled."""
        config = {'enable_cache': False}
        manager = CacheManager(config)
        
        assert manager.enabled is False
        assert not manager.tokenizer_cache._enabled
        assert not manager.morphology_cache._enabled
    
    def test_get_all_stats(self):
        """Test getting statistics from all caches."""
        manager = CacheManager()
        
        # Add some data
        manager.tokenizer_cache.set("key1", "value1")
        manager.morphology_cache.set("key2", "value2")
        
        stats = manager.get_all_stats()
        
        assert 'tokenizer' in stats
        assert 'morphology' in stats
        assert 'config' in stats
        
        assert stats['tokenizer']['size'] == 1
        assert stats['morphology']['size'] == 1


class TestCacheKeyGeneration:
    """Test cache key generation utilities."""
    
    def test_create_cache_key(self):
        """Test cache key creation."""
        key = create_cache_key("ru", "test text", "abc123")
        assert key == ("ru", "test text", "abc123")
    
    def test_create_flags_hash(self):
        """Test flags hash creation."""
        flags1 = {"flag1": True, "flag2": False}
        flags2 = {"flag2": False, "flag1": True}  # Different order
        
        hash1 = create_flags_hash(flags1)
        hash2 = create_flags_hash(flags2)
        
        # Should be the same regardless of order
        assert hash1 == hash2
        assert len(hash1) == 10  # Should be 10 characters


class TestTokenizerServiceCaching:
    """Test tokenizer service with caching."""
    
    def test_tokenizer_service_without_cache(self):
        """Test tokenizer service without cache."""
        service = TokenizerService()
        
        result = service.tokenize("Test text", "en", True, True, None)
        
        assert result.tokens is not None
        assert result.cache_hit is False
        assert result.processing_time > 0
    
    def test_tokenizer_service_with_cache(self):
        """Test tokenizer service with cache."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=60)
        service = TokenizerService(cache)
        
        # First call - should be cache miss
        result1 = service.tokenize("Test text", "en", True, True, None)
        assert result1.cache_hit is False
        
        # Second call - should be cache hit
        result2 = service.tokenize("Test text", "en", True, True, None)
        assert result2.cache_hit is True
        assert result1.tokens == result2.tokens
    
    def test_tokenizer_service_stats(self):
        """Test tokenizer service statistics."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=60)
        service = TokenizerService(cache)
        
        # Make some requests
        service.tokenize("Test text 1", "en", True, True, None)
        service.tokenize("Test text 1", "en", True, True, None)  # Hit
        service.tokenize("Test text 2", "en", True, True, None)  # Miss
        
        stats = service.get_stats()
        
        assert stats['total_requests'] == 3
        assert stats['cache_hits'] == 1
        assert stats['cache_misses'] == 2
        assert stats['hit_rate'] == pytest.approx(33.33, rel=1e-2)


class TestMorphologyAdapterCaching:
    """Test morphology adapter with caching."""
    
    def test_morphology_adapter_without_cache(self):
        """Test morphology adapter without cache."""
        adapter = MorphologyAdapter()
        
        result = adapter.parse("Test", "en")
        
        assert result is not None
        assert len(result) >= 0  # Should return list of parses
    
    def test_morphology_adapter_with_cache(self):
        """Test morphology adapter with cache."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=60)
        adapter = MorphologyAdapter(cache_size=10, cache=cache)
        
        # First call - should be cache miss
        result1 = adapter.parse("Test", "en")
        assert result1 is not None
        
        # Second call - should be cache hit (cached by lru_cache)
        result2 = adapter.parse("Test", "en")
        assert result2 is not None
        assert result1 == result2
    
    def test_morphology_adapter_stats(self):
        """Test morphology adapter statistics."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=60)
        adapter = MorphologyAdapter(cache_size=10, cache=cache)
        
        # Make some requests
        adapter.parse("Test1", "en")
        adapter.parse("Test1", "en")  # Hit
        adapter.parse("Test2", "en")  # Miss
        
        stats = adapter.get_cache_stats()
        
        assert 'parse_cache_hits' in stats
        assert 'parse_cache_misses' in stats


class TestCacheMetrics:
    """Test cache metrics functionality."""
    
    def test_cache_metrics_creation(self):
        """Test cache metrics creation."""
        metrics = CacheMetrics()
        
        # Check that all metrics are created
        assert metrics.tokenizer_cache_hits is not None
        assert metrics.tokenizer_cache_misses is not None
        assert metrics.morphology_cache_hits is not None
        assert metrics.morphology_cache_misses is not None
        assert metrics.layer_latency is not None
    
    def test_record_cache_events(self):
        """Test recording cache events."""
        metrics = CacheMetrics()
        
        # Record some events
        metrics.record_tokenizer_cache_hit("en")
        metrics.record_tokenizer_cache_miss("en")
        metrics.record_morphology_cache_hit("ru")
        metrics.record_morphology_cache_miss("ru")
        
        # Record latency
        metrics.record_layer_latency("tokenizer", "en", 0.01)
        metrics.record_normalization_latency("en", 0.05)
    
    def test_update_from_cache_stats(self):
        """Test updating metrics from cache statistics."""
        metrics = CacheMetrics()
        
        stats = {
            'size': 100,
            'hit_rate': 75.5,
            'evictions': 5,
            'expirations': 2
        }
        
        metrics.update_from_cache_stats('tokenizer', 'en', stats)
        
        # Metrics should be updated (exact values depend on Prometheus implementation)
        # This is more of a smoke test


class TestCachedServices:
    """Test cached service implementations."""
    
    def test_cached_tokenizer_service(self):
        """Test cached tokenizer service."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=60)
        service = TokenizerService(cache)
        
        # Test tokenization
        result = service.tokenize("Test text", "en", True, True, None)
        
        assert result.tokens is not None
        assert result.cache_hit is False
        
        # Second call should hit cache
        result2 = service.tokenize("Test text", "en", True, True, None)
        
        assert result2.cache_hit is True
        assert result.tokens == result2.tokens
    
    def test_cached_morphology_adapter(self):
        """Test cached morphology adapter."""
        cache = LruTtlCache(maxsize=10, ttl_seconds=60)
        adapter = MorphologyAdapter(cache_size=10, cache=cache)
        
        # Test parsing
        parses = adapter.parse("Test", "en")
        assert parses is not None
        
        # Test nominative
        nominative = adapter.to_nominative("Test", "en")
        assert nominative is not None


if __name__ == "__main__":
    pytest.main([__file__])
