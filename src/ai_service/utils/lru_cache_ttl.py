#!/usr/bin/env python3
"""
Thread-safe LRU cache with TTL (Time To Live) support.

This module provides a high-performance caching solution for the normalization pipeline
with automatic expiration and LRU eviction policies.
"""

import hashlib
import threading
import time
from typing import Any, Dict, Optional, Tuple, Union
from collections import OrderedDict


class LruTtlCache:
    """
    Thread-safe LRU cache with TTL support.
    
    Features:
    - LRU eviction when maxsize is reached
    - TTL expiration for automatic cleanup
    - Thread-safe operations with RLock
    - Hit/miss counters for metrics
    - Memory-efficient storage
    """
    
    def __init__(self, maxsize: int = 2048, ttl_seconds: int = 600):
        """
        Initialize LRU TTL cache.
        
        Args:
            maxsize: Maximum number of items to store
            ttl_seconds: Time to live for cached items in seconds
        """
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        
        # Thread-safe storage
        self._lock = threading.RLock()
        self._cache: OrderedDict = OrderedDict()
        self._timestamps: Dict[Any, float] = {}
        
        # Metrics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0
        
        # Configuration
        self._enabled = True
    
    def __bool__(self) -> bool:
        """Return True if cache is enabled."""
        return self._enabled
    
    def get(self, key: Any) -> Tuple[bool, Optional[Any]]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Tuple of (hit, value) where hit is boolean and value is the cached value or None
        """
        if not self._enabled:
            return False, None
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return False, None
            
            # Check TTL
            if self._is_expired(key):
                del self._cache[key]
                del self._timestamps[key]
                self._expirations += 1
                self._misses += 1
                return False, None
            
            # Move to end (most recently used)
            value = self._cache.pop(key)
            self._cache[key] = value
            
            self._hits += 1
            return True, value
    
    def set(self, key: Any, value: Any) -> None:
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
        """
        if not self._enabled:
            return
        
        with self._lock:
            current_time = time.time()
            
            # Remove existing entry if present
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
            
            # Check if we need to evict
            while len(self._cache) >= self.maxsize:
                # Remove least recently used item
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                del self._timestamps[oldest_key]
                self._evictions += 1
            
            # Add new entry
            self._cache[key] = value
            self._timestamps[key] = current_time
    
    def delete(self, key: Any) -> bool:
        """
        Delete key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if not found
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._timestamps[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all entries from cache."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._hits = 0
            self._misses = 0
            self._evictions = 0
            self._expirations = 0
    
    def purge_expired(self) -> int:
        """
        Remove all expired entries.
        
        Returns:
            Number of entries removed
        """
        if not self._enabled:
            return 0
        
        with self._lock:
            current_time = time.time()
            expired_keys = []
            
            for key, timestamp in self._timestamps.items():
                if current_time - timestamp > self.ttl_seconds:
                    expired_keys.append(key)
            
            for key in expired_keys:
                if key in self._cache:
                    del self._cache[key]
                    del self._timestamps[key]
                    self._expirations += 1
            
            return len(expired_keys)
    
    def _is_expired(self, key: Any) -> bool:
        """Check if key is expired."""
        if key not in self._timestamps:
            return True
        
        current_time = time.time()
        return current_time - self._timestamps[key] > self.ttl_seconds
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0.0
            
            return {
                'size': len(self._cache),
                'maxsize': self.maxsize,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'evictions': self._evictions,
                'expirations': self._expirations,
                'enabled': self._enabled
            }
    
    def enable(self) -> None:
        """Enable cache."""
        self._enabled = True
    
    def disable(self) -> None:
        """Disable cache and clear all entries."""
        with self._lock:
            self._enabled = False
            self.clear()
    
    def __len__(self) -> int:
        """Get current cache size."""
        with self._lock:
            return len(self._cache)
    
    def __contains__(self, key: Any) -> bool:
        """Check if key exists in cache and is not expired."""
        if not self._enabled:
            return False
        
        with self._lock:
            if key not in self._cache:
                return False
            return not self._is_expired(key)


def create_cache_key(language: str, text: str, flags_hash: str) -> Tuple[str, str, str]:
    """
    Create a cache key for normalization operations.
    
    Args:
        language: Language code
        text: Input text (should be sanitized)
        flags_hash: Hash of feature flags
        
    Returns:
        Tuple suitable as cache key
    """
    return (language, text, flags_hash)


def create_flags_hash(flags: Dict[str, Any]) -> str:
    """
    Create a hash of feature flags for cache key.
    
    Args:
        flags: Dictionary of feature flags
        
    Returns:
        Short hash string (8-12 characters)
    """
    # Sort flags for consistent hashing
    sorted_flags = sorted(flags.items())
    flags_str = str(sorted_flags)
    
    # Create short hash
    hash_obj = hashlib.sha1(flags_str.encode('utf-8'))
    return hash_obj.hexdigest()[:10]  # 10 characters should be enough


def create_text_hash(text: str) -> str:
    """
    Create a hash of text for cache key (privacy-safe).
    
    Args:
        text: Input text
        
    Returns:
        Hash string for the text
    """
    # Normalize text for consistent hashing
    normalized_text = text.strip().lower()
    hash_obj = hashlib.sha1(normalized_text.encode('utf-8'))
    return hash_obj.hexdigest()[:12]  # 12 characters for text hash


class CacheManager:
    """
    Manager for multiple caches in the normalization pipeline.
    
    Provides centralized management of caches for different layers
    with unified configuration and metrics collection.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize cache manager.
        
        Args:
            config: Cache configuration dictionary
        """
        self.config = config or {}
        
        # Default configuration
        self.maxsize = self.config.get('max_size', 2048)
        self.ttl_seconds = self.config.get('ttl_sec', 600)
        self.enabled = self.config.get('enable_cache', True)
        
        # Create caches for different layers
        self.tokenizer_cache = LruTtlCache(
            maxsize=self.maxsize,
            ttl_seconds=self.ttl_seconds
        )
        
        self.morphology_cache = LruTtlCache(
            maxsize=self.maxsize,
            ttl_seconds=self.ttl_seconds
        )
        
        # Disable if not enabled
        if not self.enabled:
            self.tokenizer_cache.disable()
            self.morphology_cache.disable()
    
    def get_tokenizer_cache(self) -> LruTtlCache:
        """Get tokenizer cache."""
        return self.tokenizer_cache
    
    def get_morphology_cache(self) -> LruTtlCache:
        """Get morphology cache."""
        return self.morphology_cache
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all caches."""
        return {
            'tokenizer': self.tokenizer_cache.get_stats(),
            'morphology': self.morphology_cache.get_stats(),
            'config': {
                'maxsize': self.maxsize,
                'ttl_seconds': self.ttl_seconds,
                'enabled': self.enabled
            }
        }
    
    def purge_all_expired(self) -> Dict[str, int]:
        """Purge expired entries from all caches."""
        return {
            'tokenizer': self.tokenizer_cache.purge_expired(),
            'morphology': self.morphology_cache.purge_expired()
        }
    
    def clear_all(self) -> None:
        """Clear all caches."""
        self.tokenizer_cache.clear()
        self.morphology_cache.clear()
    
    def enable_all(self) -> None:
        """Enable all caches."""
        self.tokenizer_cache.enable()
        self.morphology_cache.enable()
        self.enabled = True
    
    def disable_all(self) -> None:
        """Disable all caches."""
        self.tokenizer_cache.disable()
        self.morphology_cache.disable()
        self.enabled = False
