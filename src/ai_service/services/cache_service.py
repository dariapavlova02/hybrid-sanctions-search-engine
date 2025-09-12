"""
Simple cache service for MVP
"""

import time
import json
import hashlib
import logging
from typing import Dict, List, Optional, Union, Any, Callable
from collections import OrderedDict

from ..utils import get_logger


class CacheService:
    """Simple cache service with TTL and LRU eviction"""
    
    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Initialize cache service
        
        Args:
            max_size: Maximum number of elements
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        
        # LRU cache with TTL
        self.cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()
        
        # Statistics
        self.stats = {
            'hits': 0,
            'misses': 0,
            'sets': 0,
            'evictions': 0,
            'expirations': 0
        }
        
        self.logger = get_logger(__name__)
        self.logger.info(f"CacheService initialized with max_size={max_size}, default_ttl={default_ttl}")
    
    def _generate_cache_key(self, *args, **kwargs) -> str:
        """Generate cache key"""
        # Create unique key from arguments
        key_data = {
            'args': args,
            'kwargs': sorted(kwargs.items())
        }
        
        # JSON serialization + hash
        key_string = json.dumps(key_data, sort_keys=True, default=str)
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _generate_key(self, *args, **kwargs) -> str:
        """Alias for _generate_cache_key method"""
        return self._generate_cache_key(*args, **kwargs)
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache
        
        Args:
            key: Cache key
            
        Returns:
            Value or None if not found/expired
        """
        if not key:
            return None
        
        # Check if key exists in cache
        if key not in self.cache:
            self.stats['misses'] += 1
            return None
        
        # Check TTL
        cache_entry = self.cache[key]
        if self._is_expired(cache_entry):
            del self.cache[key]
            self.stats['expirations'] += 1
            self.stats['misses'] += 1
            return None
        
        # Update position in LRU
        self.cache.move_to_end(key)
        
        self.stats['hits'] += 1
        return cache_entry['value']
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Save value to cache
        
        Args:
            key: Cache key
            value: Value to save
            ttl: TTL in seconds (None = default)
            
        Returns:
            True if successfully saved
        """
        if not key:
            return False
        
        # Check if cache needs cleaning
        if len(self.cache) >= self.max_size:
            self._evict_lru()
        
        # Save value
        ttl_seconds = ttl if ttl is not None else self.default_ttl
        self.cache[key] = {
            'value': value,
            'timestamp': time.time(),
            'ttl': ttl_seconds
        }
        
        # Update position in LRU
        self.cache.move_to_end(key)
        
        self.stats['sets'] += 1
        return True
    
    def get_or_set(self, key: str, default_func: Callable, ttl: Optional[int] = None, *args, **kwargs) -> Any:
        """
        Get from cache or set default value
        
        Args:
            key: Cache key
            default_func: Function to generate default value
            ttl: TTL in seconds
            *args, **kwargs: Arguments for default_func
            
        Returns:
            Value from cache or new value
        """
        # Try to get from cache
        cached_value = self.get(key)
        if cached_value is not None:
            return cached_value
        
        # Generate new value
        new_value = default_func(*args, **kwargs)
        self.set(key, new_value, ttl)
        return new_value
    
    def _is_expired(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if value is expired"""
        if 'timestamp' not in cache_entry or 'ttl' not in cache_entry:
            return True
        
        current_time = time.time()
        return current_time - cache_entry['timestamp'] > cache_entry['ttl']
    
    def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if key in self.cache:
            del self.cache[key]
            return True
        return False
    
    def _evict_lru(self) -> None:
        """Evict least recently used element"""
        if not self.cache:
            return
        
        # Remove first element (oldest)
        oldest_key = next(iter(self.cache))
        del self.cache[oldest_key]
        self.stats['evictions'] += 1
    
    def clear(self) -> None:
        """Clear entire cache"""
        self.cache.clear()
        self.logger.info("Cache cleared")
    
    def cleanup_expired(self) -> int:
        """Clean up expired elements"""
        expired_keys = []
        
        for key, entry in self.cache.items():
            if self._is_expired(entry):
                expired_keys.append(key)
        
        for key in expired_keys:
            del self.cache[key]
            self.stats['expirations'] += 1
        
        if expired_keys:
            self.logger.info(f"Cleaned up {len(expired_keys)} expired entries")
        
        return len(expired_keys)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        stats = self.stats.copy()
        
        # Add current information
        stats.update({
            'current_size': len(self.cache),
            'max_size': self.max_size,
            'total_requests': stats['hits'] + stats['misses'],
            'hit_rate': stats['hits'] / max(stats['hits'] + stats['misses'], 1),
            'memory_usage_mb': self._estimate_memory_usage(),
            'oldest_entry_age': self._get_oldest_entry_age(),
            'newest_entry_age': self._get_newest_entry_age()
        })
        
        return stats
    
    def _estimate_memory_usage(self) -> float:
        """Estimate memory usage in MB"""
        total_bytes = 0
        
        for key, entry in self.cache.items():
            # Estimate key and value size
            total_bytes += len(key.encode('utf-8'))
            
            # Try to serialize value to JSON, fallback to string representation
            try:
                value_bytes = len(json.dumps(entry['value']).encode('utf-8'))
            except (TypeError, ValueError):
                # If JSON serialization fails, use string representation
                value_bytes = len(str(entry['value']).encode('utf-8'))
            
            total_bytes += value_bytes
        
        # Convert to MB
        return total_bytes / (1024 * 1024)
    
    def _get_oldest_entry_age(self) -> float:
        """Get age of oldest entry in seconds"""
        if not self.cache:
            return 0.0
        
        oldest_timestamp = min(entry['timestamp'] for entry in self.cache.values())
        return time.time() - oldest_timestamp
    
    def _get_newest_entry_age(self) -> float:
        """Get age of newest entry in seconds"""
        if not self.cache:
            return 0.0
        
        newest_timestamp = max(entry['timestamp'] for entry in self.cache.values())
        return time.time() - newest_timestamp
    
    def resize(self, new_max_size: int) -> None:
        """Change maximum cache size"""
        if new_max_size <= 0:
            raise ValueError("Cache size must be positive")
        
        self.max_size = new_max_size
        
        # If new size is smaller, evict excess elements
        while len(self.cache) > self.max_size:
            self._evict_lru()
        
        self.logger.info(f"Cache resized to {new_max_size}")
    
    def set_max_size(self, new_max_size: int) -> None:
        """Alias for resize method"""
        self.resize(new_max_size)
    
    def keys(self) -> List[str]:
        """Get list of all keys"""
        return list(self.cache.keys())
    
    def get_keys(self) -> List[str]:
        """Alias for keys method"""
        return self.keys()
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        if key not in self.cache:
            return False
        
        # Check if not expired
        return not self._is_expired(self.cache[key])
    
    def touch(self, key: str) -> bool:
        """Update TTL for key"""
        if key not in self.cache:
            return False
        
        # Update timestamp
        self.cache[key]['timestamp'] = time.time()
        
        # Move to end of LRU
        self.cache.move_to_end(key)
        
        return True
