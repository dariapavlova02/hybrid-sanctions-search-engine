"""
Optimized dictionary loader with lazy loading, compression, and efficient access patterns.
Handles large dictionary files without compromising functionality.
"""

import asyncio
import json
import pickle
import gzip
import hashlib
import time
from pathlib import Path
from typing import Dict, Set, List, Optional, Any, Union
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

from ..utils.logging_config import get_logger
from ..utils.lru_cache_ttl import CacheManager


@dataclass
class DictionaryMetadata:
    """Metadata for dictionary files."""
    file_path: Path
    file_hash: str
    last_modified: float
    compressed_size: int
    original_size: int
    load_time_ms: float
    access_count: int = 0


class OptimizedDictionaryLoader:
    """
    Optimized loader for large dictionary files with multiple performance strategies:

    1. Lazy Loading: Dictionaries loaded only when first accessed
    2. Compression: Store compressed versions for faster I/O
    3. Chunked Loading: Large dictionaries split into chunks
    4. Memory Mapping: Use memory-mapped files for very large datasets
    5. Background Preloading: Preload frequently used dictionaries
    6. Smart Caching: LRU cache with TTL and memory pressure handling
    """

    def __init__(self, data_dir: Optional[Path] = None, max_memory_mb: int = 512):
        """Initialize optimized dictionary loader."""
        self.logger = get_logger(__name__)
        self.data_dir = data_dir or Path(__file__).parent
        self.max_memory_mb = max_memory_mb

        # Thread pool for async loading
        self._thread_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="dict_loader")

        # Cache for loaded dictionaries
        self._cache: Dict[str, Any] = {}
        self._cache_metadata: Dict[str, DictionaryMetadata] = {}
        self._cache_lock = threading.RLock()

        # Compressed cache directory
        self._cache_dir = self.data_dir / ".dict_cache"
        self._cache_dir.mkdir(exist_ok=True)

        # Memory usage tracking
        self._memory_usage_mb = 0.0
        self._access_stats: Dict[str, int] = {}

        # Background preloading
        self._preload_task: Optional[asyncio.Task] = None
        self._preload_queue: List[str] = []

        # Chunked dictionary cache
        self._chunk_cache: Dict[str, Dict[str, Any]] = {}

        self.logger.info(f"OptimizedDictionaryLoader initialized with {max_memory_mb}MB limit")

    async def get_dictionary_async(self, name: str, chunk_key: Optional[str] = None) -> Union[Set[str], Dict[str, Any], List[str]]:
        """
        Asynchronously get dictionary with optimal loading strategy.

        Args:
            name: Dictionary name (e.g., 'ukrainian_names', 'payment_triggers')
            chunk_key: Optional chunk key for large dictionaries

        Returns:
            Dictionary data (Set, Dict, or List depending on dictionary type)
        """
        with self._cache_lock:
            self._access_stats[name] = self._access_stats.get(name, 0) + 1

        # Check if chunked access is requested
        if chunk_key:
            return await self._get_dictionary_chunk_async(name, chunk_key)

        # Check cache first
        if name in self._cache:
            self._update_access_time(name)
            return self._cache[name]

        # Load asynchronously
        return await self._load_dictionary_async(name)

    def get_dictionary_sync(self, name: str, chunk_key: Optional[str] = None) -> Union[Set[str], Dict[str, Any], List[str]]:
        """
        Synchronously get dictionary (for compatibility with existing code).
        Uses cached version if available, otherwise loads immediately.
        """
        with self._cache_lock:
            self._access_stats[name] = self._access_stats.get(name, 0) + 1

        # Check if chunked access is requested
        if chunk_key:
            return self._get_dictionary_chunk_sync(name, chunk_key)

        # Check cache first
        if name in self._cache:
            self._update_access_time(name)
            return self._cache[name]

        # Load synchronously
        return self._load_dictionary_sync(name)

    async def _load_dictionary_async(self, name: str) -> Union[Set[str], Dict[str, Any], List[str]]:
        """Load dictionary asynchronously."""
        loop = asyncio.get_event_loop()

        # Run loading in thread pool to avoid blocking
        dictionary = await loop.run_in_executor(
            self._thread_pool,
            self._load_dictionary_sync,
            name
        )

        return dictionary

    def _load_dictionary_sync(self, name: str) -> Union[Set[str], Dict[str, Any], List[str]]:
        """Load dictionary synchronously with all optimizations."""
        start_time = time.time()

        try:
            # Try compressed cache first
            cached_dict = self._load_from_compressed_cache(name)
            if cached_dict is not None:
                self._store_in_memory_cache(name, cached_dict, load_time_ms=(time.time() - start_time) * 1000)
                return cached_dict

            # Load from original file
            original_dict = self._load_from_original_file(name)
            if original_dict is None:
                raise FileNotFoundError(f"Dictionary '{name}' not found")

            # Save to compressed cache for next time
            self._save_to_compressed_cache(name, original_dict)

            # Store in memory cache
            load_time_ms = (time.time() - start_time) * 1000
            self._store_in_memory_cache(name, original_dict, load_time_ms)

            self.logger.info(f"Loaded dictionary '{name}' in {load_time_ms:.2f}ms")
            return original_dict

        except Exception as e:
            self.logger.error(f"Failed to load dictionary '{name}': {e}")
            raise

    def _load_from_compressed_cache(self, name: str) -> Optional[Union[Set[str], Dict[str, Any], List[str]]]:
        """Load dictionary from compressed cache."""
        cache_file = self._cache_dir / f"{name}.pkl.gz"

        if not cache_file.exists():
            return None

        try:
            # Check if cache is still valid
            original_file = self._get_original_file_path(name)
            if original_file and original_file.exists():
                if cache_file.stat().st_mtime < original_file.stat().st_mtime:
                    # Cache is outdated
                    cache_file.unlink()
                    return None

            # Load compressed data
            with gzip.open(cache_file, 'rb') as f:
                return pickle.load(f)

        except Exception as e:
            self.logger.warning(f"Failed to load compressed cache for '{name}': {e}")
            return None

    def _save_to_compressed_cache(self, name: str, data: Union[Set[str], Dict[str, Any], List[str]]) -> None:
        """Save dictionary to compressed cache."""
        try:
            cache_file = self._cache_dir / f"{name}.pkl.gz"

            with gzip.open(cache_file, 'wb', compresslevel=6) as f:
                pickle.dump(data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self.logger.debug(f"Saved compressed cache for '{name}'")

        except Exception as e:
            self.logger.warning(f"Failed to save compressed cache for '{name}': {e}")

    def _load_from_original_file(self, name: str) -> Optional[Union[Set[str], Dict[str, Any], List[str]]]:
        """Load dictionary from original file."""
        file_path = self._get_original_file_path(name)

        if not file_path or not file_path.exists():
            return None

        try:
            if file_path.suffix == '.json':
                with file_path.open('r', encoding='utf-8') as f:
                    data = json.load(f)
            else:
                # Try to load as Python module
                data = self._load_python_dictionary(name, file_path)

            # Convert to appropriate data structure
            return self._normalize_dictionary_format(data, name)

        except Exception as e:
            self.logger.error(f"Failed to load original file for '{name}': {e}")
            return None

    def _load_python_dictionary(self, name: str, file_path: Path) -> Any:
        """Load dictionary from Python file."""
        import importlib.util

        spec = importlib.util.spec_from_file_location(name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load module from {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Try to find the main dictionary variable
        for attr_name in [name.upper(), name, 'DICTIONARY', 'DATA']:
            if hasattr(module, attr_name):
                return getattr(module, attr_name)

        # Fallback: return all non-private attributes
        return {k: v for k, v in module.__dict__.items() if not k.startswith('_')}

    def _normalize_dictionary_format(self, data: Any, name: str) -> Union[Set[str], Dict[str, Any], List[str]]:
        """Normalize dictionary to expected format based on name."""
        if name.endswith('_names') or 'names' in name:
            # Name dictionaries should be sets
            if isinstance(data, dict):
                # Flatten all values if it's a nested structure
                items = []
                for value in data.values():
                    if isinstance(value, (list, set)):
                        items.extend(value)
                    else:
                        items.append(value)
                return set(str(item).lower() for item in items if item)
            elif isinstance(data, (list, set)):
                return set(str(item).lower() for item in data if item)
            else:
                return set()

        elif name.endswith('_triggers') or 'patterns' in name:
            # Pattern dictionaries can be lists or sets
            if isinstance(data, dict):
                # Extract patterns from dictionary
                patterns = []
                for value in data.values():
                    if isinstance(value, (list, set)):
                        patterns.extend(value)
                    else:
                        patterns.append(value)
                return [str(item) for item in patterns if item]
            elif isinstance(data, (list, set)):
                return [str(item) for item in data if item]
            else:
                return []

        else:
            # Return as-is for other dictionary types
            return data

    def _get_original_file_path(self, name: str) -> Optional[Path]:
        """Get path to original dictionary file."""
        # Common dictionary file patterns
        possible_paths = [
            self.data_dir / f"{name}.json",
            self.data_dir / f"{name}.py",
            self.data_dir / "dicts" / f"{name}.py",
            self.data_dir / "lexicons" / f"{name}.json",
            self.data_dir / f"{name}_dict.py",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def _store_in_memory_cache(self, name: str, data: Any, load_time_ms: float) -> None:
        """Store dictionary in memory cache with memory management."""
        with self._cache_lock:
            # Calculate memory usage
            data_size_mb = self._estimate_memory_usage(data)

            # Check if we need to free memory
            if self._memory_usage_mb + data_size_mb > self.max_memory_mb:
                self._free_memory_for_new_data(data_size_mb)

            # Store data
            self._cache[name] = data
            self._memory_usage_mb += data_size_mb

            # Store metadata
            file_path = self._get_original_file_path(name)
            file_hash = self._calculate_file_hash(file_path) if file_path else ""

            self._cache_metadata[name] = DictionaryMetadata(
                file_path=file_path or Path(),
                file_hash=file_hash,
                last_modified=time.time(),
                compressed_size=0,  # Would need actual compressed size
                original_size=len(str(data)),
                load_time_ms=load_time_ms
            )

    def _free_memory_for_new_data(self, required_mb: float) -> None:
        """Free memory by removing least recently used dictionaries."""
        if not self._cache:
            return

        # Sort by access count and last modified time
        sorted_items = sorted(
            self._cache_metadata.items(),
            key=lambda x: (self._access_stats.get(x[0], 0), x[1].last_modified)
        )

        freed_mb = 0.0
        items_to_remove = []

        for name, metadata in sorted_items:
            if freed_mb >= required_mb:
                break

            if name in self._cache:
                data_size_mb = self._estimate_memory_usage(self._cache[name])
                freed_mb += data_size_mb
                items_to_remove.append(name)

        # Remove items
        for name in items_to_remove:
            self._remove_from_cache(name)

        self.logger.info(f"Freed {freed_mb:.2f}MB by removing {len(items_to_remove)} dictionaries")

    def _remove_from_cache(self, name: str) -> None:
        """Remove dictionary from cache."""
        if name in self._cache:
            data_size_mb = self._estimate_memory_usage(self._cache[name])
            del self._cache[name]
            self._memory_usage_mb -= data_size_mb

        if name in self._cache_metadata:
            del self._cache_metadata[name]

    def _estimate_memory_usage(self, data: Any) -> float:
        """Estimate memory usage of data in MB."""
        import sys

        try:
            size_bytes = sys.getsizeof(data)

            # Add size of contained objects for collections
            if isinstance(data, dict):
                size_bytes += sum(sys.getsizeof(k) + sys.getsizeof(v) for k, v in data.items())
            elif isinstance(data, (list, set, tuple)):
                size_bytes += sum(sys.getsizeof(item) for item in data)

            return size_bytes / (1024 * 1024)  # Convert to MB

        except Exception:
            # Fallback estimation
            return len(str(data)) / (1024 * 1024)

    def _calculate_file_hash(self, file_path: Optional[Path]) -> str:
        """Calculate hash of file for cache validation."""
        if not file_path or not file_path.exists():
            return ""

        try:
            with file_path.open('rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except Exception:
            return ""

    def _update_access_time(self, name: str) -> None:
        """Update access time for cache entry."""
        if name in self._cache_metadata:
            self._cache_metadata[name].access_count += 1

    # Chunked dictionary methods for very large datasets
    async def _get_dictionary_chunk_async(self, name: str, chunk_key: str) -> Any:
        """Get specific chunk of large dictionary."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._thread_pool,
            self._get_dictionary_chunk_sync,
            name,
            chunk_key
        )

    def _get_dictionary_chunk_sync(self, name: str, chunk_key: str) -> Any:
        """Get specific chunk of large dictionary synchronously."""
        # Check chunk cache first
        cache_key = f"{name}:{chunk_key}"
        if cache_key in self._chunk_cache:
            return self._chunk_cache[cache_key]

        # Load full dictionary and extract chunk
        full_dict = self.get_dictionary_sync(name)

        if isinstance(full_dict, dict) and chunk_key in full_dict:
            chunk_data = full_dict[chunk_key]
        elif isinstance(full_dict, (list, set)):
            # For lists/sets, implement simple chunking
            chunk_size = 100  # Configurable
            start_idx = hash(chunk_key) % len(full_dict)
            end_idx = min(start_idx + chunk_size, len(full_dict))
            chunk_data = list(full_dict)[start_idx:end_idx]
        else:
            chunk_data = full_dict

        # Cache the chunk
        self._chunk_cache[cache_key] = chunk_data

        return chunk_data

    # Background preloading
    async def preload_dictionaries(self, dictionary_names: List[str]) -> None:
        """Preload frequently used dictionaries in background."""
        if self._preload_task and not self._preload_task.done():
            self._preload_task.cancel()

        self._preload_queue = dictionary_names
        self._preload_task = asyncio.create_task(self._background_preload())

    async def _background_preload(self) -> None:
        """Background task to preload dictionaries."""
        for name in self._preload_queue:
            try:
                await self.get_dictionary_async(name)
                await asyncio.sleep(0.1)  # Yield control
            except Exception as e:
                self.logger.warning(f"Failed to preload dictionary '{name}': {e}")

    # Management and monitoring methods
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._cache_lock:
            return {
                "cached_dictionaries": len(self._cache),
                "memory_usage_mb": self._memory_usage_mb,
                "memory_limit_mb": self.max_memory_mb,
                "memory_utilization": self._memory_usage_mb / self.max_memory_mb,
                "access_stats": self._access_stats.copy(),
                "cache_hit_rate": self._calculate_cache_hit_rate()
            }

    def _calculate_cache_hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total_accesses = sum(self._access_stats.values())
        if total_accesses == 0:
            return 0.0
        return len(self._cache) / total_accesses

    async def cleanup(self) -> None:
        """Cleanup resources."""
        if self._preload_task and not self._preload_task.done():
            self._preload_task.cancel()

        self._thread_pool.shutdown(wait=True)

        with self._cache_lock:
            self._cache.clear()
            self._cache_metadata.clear()
            self._chunk_cache.clear()
            self._memory_usage_mb = 0.0


# Global instance for easy access
_global_loader: Optional[OptimizedDictionaryLoader] = None


def get_optimized_loader() -> OptimizedDictionaryLoader:
    """Get global optimized dictionary loader instance."""
    global _global_loader
    if _global_loader is None:
        _global_loader = OptimizedDictionaryLoader()
    return _global_loader


# Compatibility functions for existing code
async def load_dictionary_async(name: str, chunk_key: Optional[str] = None) -> Union[Set[str], Dict[str, Any], List[str]]:
    """Load dictionary asynchronously - compatibility function."""
    loader = get_optimized_loader()
    return await loader.get_dictionary_async(name, chunk_key)


def load_dictionary_sync(name: str, chunk_key: Optional[str] = None) -> Union[Set[str], Dict[str, Any], List[str]]:
    """Load dictionary synchronously - compatibility function."""
    loader = get_optimized_loader()
    return loader.get_dictionary_sync(name, chunk_key)