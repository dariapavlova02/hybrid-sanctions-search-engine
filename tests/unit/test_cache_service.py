"""
Unit тесты для CacheService
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, patch

from src.ai_service.services.cache_service import CacheService


class TestCacheService:
    """Tests for CacheService"""
    
    def test_basic_set_get(self, cache_service):
        """Test basic set/get operations"""
        # Arrange
        key = "test_key"
        value = "test_value"
        
        # Act
        result_set = cache_service.set(key, value)
        result_get = cache_service.get(key)
        
        # Assert
        assert result_set is True
        assert result_get == value
    
    def test_get_nonexistent_key(self, cache_service):
        """Test getting non-existent key"""
        # Act
        result = cache_service.get("nonexistent_key")
        
        # Assert
        assert result is None
    
    def test_lru_eviction(self, cache_service):
        """Test LRU eviction: add max_size + 1 elements"""
        # Arrange
        items = [("key1", "value1"), ("key2", "value2"), ("key3", "value3")]
        
        # Act - fill cache to maximum
        for key, value in items:
            cache_service.set(key, value)
        
        # Check that all elements are in place
        for key, value in items:
            assert cache_service.get(key) == value
        
        # Add one more element - should evict the oldest (key1)
        cache_service.set("key4", "value4")
        
        # Assert
        assert cache_service.get("key1") is None  # Oldest element removed
        assert cache_service.get("key2") == "value2"
        assert cache_service.get("key3") == "value3"
        assert cache_service.get("key4") == "value4"
    
    @pytest.mark.asyncio
    async def test_ttl_expiration(self, cache_service):
        """Test TTL: save element with TTL=1 second"""
        # Arrange
        key = "ttl_key"
        value = "ttl_value"
        ttl = 1
        
        # Act
        cache_service.set(key, value, ttl=ttl)
        
        # Check that element exists immediately
        assert cache_service.get(key) == value
        
        # Wait longer than TTL
        await asyncio.sleep(1.1)
        
        # Assert
        assert cache_service.get(key) is None
    
    def test_statistics(self, cache_service):
        """Test statistics: hits, misses, current_size"""
        # Arrange
        key1, value1 = "key1", "value1"
        key2, value2 = "key2", "value2"
        
        # Act - perform operations for statistics
        # 1 miss (key doesn't exist)
        cache_service.get("nonexistent")
        
        # 1 set
        cache_service.set(key1, value1)
        
        # 1 hit
        cache_service.get(key1)
        
        # 1 miss (another key doesn't exist)
        cache_service.get("another_nonexistent")
        
        # 1 set
        cache_service.set(key2, value2)
        
        # 1 hit
        cache_service.get(key2)
        
        # Assert
        stats = cache_service.get_stats()
        assert stats['hits'] == 2
        assert stats['misses'] == 2
        assert stats['current_size'] == 2
        assert stats['total_requests'] == 4  # 2 hits + 2 misses
        assert stats['hit_rate'] == 0.5  # 2 hits / 4 requests
    
    def test_get_or_set_cache_hit(self, cache_service):
        """Test get_or_set on cache hit"""
        # Arrange
        key = "test_key"
        cached_value = "cached_value"
        cache_service.set(key, cached_value)
        
        # Mock function should not be called
        mock_func = Mock(return_value="new_value")
        
        # Act
        result = cache_service.get_or_set(key, mock_func)
        
        # Assert
        assert result == cached_value
        mock_func.assert_not_called()
    
    def test_get_or_set_cache_miss(self, cache_service):
        """Test get_or_set on cache miss"""
        # Arrange
        key = "test_key"
        new_value = "new_value"
        mock_func = Mock(return_value=new_value)
        
        # Act
        result = cache_service.get_or_set(key, mock_func, ttl=10)
        
        # Assert
        assert result == new_value
        mock_func.assert_called_once()
        assert cache_service.get(key) == new_value
    
    def test_clear_cache(self, cache_service):
        """Test cache clearing"""
        # Arrange
        cache_service.set("key1", "value1")
        cache_service.set("key2", "value2")
        
        # Act
        cache_service.clear()
        
        # Assert
        assert cache_service.get("key1") is None
        assert cache_service.get("key2") is None
        assert cache_service.get_stats()['current_size'] == 0
    
    def test_exists_method(self, cache_service):
        """Test exists method"""
        # Arrange
        key = "test_key"
        value = "test_value"
        
        # Act & Assert
        assert cache_service.exists(key) is False
        
        cache_service.set(key, value)
        assert cache_service.exists(key) is True
        
        cache_service.clear()
        assert cache_service.exists(key) is False
    
    @pytest.mark.asyncio
    async def test_exists_with_expired_key(self, cache_service):
        """Test exists with expired key"""
        # Arrange
        key = "ttl_key"
        value = "ttl_value"
        
        # Act
        cache_service.set(key, value, ttl=1)
        assert cache_service.exists(key) is True
        
        # Wait for TTL expiration
        await asyncio.sleep(1.1)
        
        # Assert
        assert cache_service.exists(key) is False
    
    def test_touch_method(self, cache_service):
        """Test touch method for TTL update"""
        # Arrange
        key = "test_key"
        value = "test_value"
        cache_service.set(key, value)
        
        # Act
        result = cache_service.touch(key)
        
        # Assert
        assert result is True
        assert cache_service.get(key) == value
    
    def test_touch_nonexistent_key(self, cache_service):
        """Test touch for non-existent key"""
        # Act
        result = cache_service.touch("nonexistent")
        
        # Assert
        assert result is False
    
    def test_cleanup_expired(self, cache_service):
        """Test cleanup of expired elements"""
        # Arrange
        cache = CacheService(max_size=10, default_ttl=1)
        
        # Add elements with different TTL
        cache.set("key1", "value1", ttl=1)
        cache.set("key2", "value2", ttl=10)  # Won't expire
        
        # Wait for first element expiration
        time.sleep(1.1)
        
        # Act
        cleaned_count = cache.cleanup_expired()
        
        # Assert
        assert cleaned_count == 1
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
    
    def test_set_max_size(self, cache_service):
        """Test changing maximum cache size"""
        # Arrange
        # Fill cache
        for i in range(3):
            cache_service.set(f"key{i}", f"value{i}")
        
        # Act - reduce size
        cache_service.set_max_size(2)
        
        # Assert
        stats = cache_service.get_stats()
        assert stats['current_size'] == 2
        assert stats['max_size'] == 2
        # Last element should remain (LRU)
        assert cache_service.get("key2") == "value2"
        assert cache_service.get("key1") == "value1"
        assert cache_service.get("key0") is None  # Oldest removed
    
    def test_get_keys(self, cache_service):
        """Test getting list of keys"""
        # Arrange
        keys = ["key1", "key2", "key3"]
        for key in keys:
            cache_service.set(key, f"value_{key}")
        
        # Act
        cache_keys = cache_service.get_keys()
        
        # Assert
        assert set(cache_keys) == set(keys)
        assert len(cache_keys) == 3
    
    def test_memory_usage_estimation(self, cache_service):
        """Test memory usage estimation"""
        # Arrange
        cache_service.set("key1", "value1")
        cache_service.set("key2", "value2")
        
        # Act
        stats = cache_service.get_stats()
        
        # Assert
        assert 'memory_usage_mb' in stats
        assert isinstance(stats['memory_usage_mb'], (int, float))
        assert stats['memory_usage_mb'] >= 0
    
    def test_generate_key_method(self, cache_service):
        """Test cache key generation"""
        # Arrange & Act
        key1 = cache_service._generate_key("arg1", "arg2", kwarg1="value1")
        key2 = cache_service._generate_key("arg1", "arg2", kwarg1="value1")
        key3 = cache_service._generate_key("arg1", "arg3", kwarg1="value1")
        
        # Assert
        assert key1 == key2  # Same arguments -> same keys
        assert key1 != key3  # Different arguments -> different keys
        assert len(key1) == 32  # MD5 hash length
    
    def test_lru_logic_with_access(self, cache_service):
        """Test LRU logic: accessing element updates its position"""
        # Arrange - fill cache
        cache_service.set("key1", "value1")
        cache_service.set("key2", "value2")
        cache_service.set("key3", "value3")
        
        # Act - access old element (key1), which should update its position
        cache_service.get("key1")
        
        # Add new element - should evict key2 (now oldest)
        cache_service.set("key4", "value4")
        
        # Assert
        assert cache_service.get("key1") == "value1"  # Remained (was updated)
        assert cache_service.get("key2") is None      # Was evicted (became oldest)
        assert cache_service.get("key3") == "value3"  # Remained
        assert cache_service.get("key4") == "value4"  # New element
        
        # Check statistics
        stats = cache_service.get_stats()
        assert stats['current_size'] == 3
        assert stats['evictions'] == 1
