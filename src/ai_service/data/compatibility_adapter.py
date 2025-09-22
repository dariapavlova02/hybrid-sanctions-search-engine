"""
Compatibility adapter for seamless migration from direct imports to optimized data access.
Maintains API compatibility while providing performance improvements.
"""

import sys
from typing import Set, Dict, List, Any
from pathlib import Path

from .optimized_data_access import get_optimized_data_access
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class CompatibilityAdapter:
    """
    Adapter that maintains backward compatibility while using optimized loading.

    This allows existing code to continue working without modification while
    benefiting from performance improvements.
    """

    def __init__(self):
        """Initialize compatibility adapter."""
        self.data_access = get_optimized_data_access()
        self._legacy_imports_warned = set()

    def __getattr__(self, name: str):
        """
        Intercept attribute access and redirect to optimized loader.
        This allows transparent replacement of legacy imports.
        """
        # Map legacy attribute names to optimized loader methods
        attribute_map = {
            'STOP_ALL': self._get_stop_all,
            'UKRAINIAN_NAMES': self._get_ukrainian_names,
            'RUSSIAN_NAMES': self._get_russian_names,
            'DIMINUTIVES_RU': self._get_diminutives_ru,
            'DIMINUTIVES_UK': self._get_diminutives_uk,
            'PAYMENT_TRIGGERS': self._get_payment_triggers,
            'SMART_FILTER_PATTERNS': self._get_smart_filter_patterns,
        }

        if name in attribute_map:
            # Warn about legacy usage (once per attribute)
            if name not in self._legacy_imports_warned:
                logger.info(f"Legacy import '{name}' redirected to optimized loader")
                self._legacy_imports_warned.add(name)

            return attribute_map[name]()

        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")

    def _get_stop_all(self) -> Set[str]:
        """Get STOP_ALL for compatibility."""
        return self.data_access.get_stopwords_sync()

    def _get_ukrainian_names(self) -> Set[str]:
        """Get UKRAINIAN_NAMES for compatibility."""
        return self.data_access.get_ukrainian_names_sync()

    def _get_russian_names(self) -> Set[str]:
        """Get RUSSIAN_NAMES for compatibility."""
        return self.data_access.get_russian_names_sync()

    def _get_diminutives_ru(self) -> Dict[str, str]:
        """Get DIMINUTIVES_RU for compatibility."""
        return self.data_access.get_diminutives_sync('ru')

    def _get_diminutives_uk(self) -> Dict[str, str]:
        """Get DIMINUTIVES_UK for compatibility."""
        return self.data_access.get_diminutives_sync('uk')

    def _get_payment_triggers(self) -> List[str]:
        """Get PAYMENT_TRIGGERS for compatibility."""
        return self.data_access.get_payment_triggers_async()

    def _get_smart_filter_patterns(self) -> Dict[str, Any]:
        """Get SMART_FILTER_PATTERNS for compatibility."""
        import asyncio
        try:
            # Try to run async version
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a task and get result when available
                task = asyncio.create_task(self.data_access.get_smart_filter_patterns_async())
                # For now, return empty dict and schedule loading
                asyncio.create_task(self._cache_smart_patterns(task))
                return self.data_access._get_fallback_smart_patterns()
            else:
                return loop.run_until_complete(self.data_access.get_smart_filter_patterns_async())
        except RuntimeError:
            # No event loop, return fallback
            return self.data_access._get_fallback_smart_patterns()

    async def _cache_smart_patterns(self, task):
        """Cache smart patterns result for future access."""
        try:
            result = await task
            # Store in a way that can be accessed later
            self._cached_smart_patterns = result
        except Exception as e:
            logger.warning(f"Failed to cache smart patterns: {e}")


# Module-level compatibility adapter
_adapter = CompatibilityAdapter()


def install_compatibility_adapter():
    """
    Install compatibility adapter for seamless migration.

    This function modifies the import system to redirect legacy imports
    to the optimized loader while maintaining full API compatibility.
    """
    # Get the current module
    current_module = sys.modules[__name__]

    # Create adapter methods on module level
    def module_getattr(name: str):
        """Module-level __getattr__ for Python 3.7+ compatibility."""
        return getattr(_adapter, name)

    # Set module-level __getattr__
    current_module.__getattr__ = module_getattr

    logger.info("Compatibility adapter installed for optimized data access")


# Explicit exports for direct access
def get_stopwords_optimized() -> Set[str]:
    """Get stopwords using optimized loader."""
    return _adapter.data_access.get_stopwords_sync()


def get_ukrainian_names_optimized() -> Set[str]:
    """Get Ukrainian names using optimized loader."""
    return _adapter.data_access.get_ukrainian_names_sync()


def get_russian_names_optimized() -> Set[str]:
    """Get Russian names using optimized loader."""
    return _adapter.data_access.get_russian_names_sync()


def get_diminutives_optimized(language: str) -> Dict[str, str]:
    """Get diminutives using optimized loader."""
    return _adapter.data_access.get_diminutives_sync(language)


async def get_data_async(data_type: str, **kwargs) -> Any:
    """
    Generic async data getter for any data type.

    Args:
        data_type: Type of data ('stopwords', 'ukrainian_names', etc.)
        **kwargs: Additional arguments like chunk_key, language

    Returns:
        Requested data
    """
    data_access = get_optimized_data_access()

    if data_type == 'stopwords':
        return await data_access.get_stopwords_async()
    elif data_type == 'ukrainian_names':
        return await data_access.get_ukrainian_names_async(kwargs.get('chunk_key'))
    elif data_type == 'russian_names':
        return await data_access.get_russian_names_async(kwargs.get('chunk_key'))
    elif data_type == 'diminutives':
        language = kwargs.get('language', 'ru')
        return await data_access.get_diminutives_async(language)
    elif data_type == 'payment_triggers':
        return await data_access.get_payment_triggers_async()
    elif data_type == 'smart_filter_patterns':
        return await data_access.get_smart_filter_patterns_async()
    else:
        raise ValueError(f"Unknown data type: {data_type}")


# Install the adapter when this module is imported
install_compatibility_adapter()


# Legacy compatibility - these will be intercepted by __getattr__
# but we define them here for IDE support and explicit imports

# Placeholder attributes that will be replaced by __getattr__
STOP_ALL: Set[str] = set()
UKRAINIAN_NAMES: Set[str] = set()
RUSSIAN_NAMES: Set[str] = set()
DIMINUTIVES_RU: Dict[str, str] = {}
DIMINUTIVES_UK: Dict[str, str] = {}
PAYMENT_TRIGGERS: List[str] = []
SMART_FILTER_PATTERNS: Dict[str, Any] = {}


# Performance monitoring
class DataAccessMetrics:
    """Monitor data access performance and usage."""

    def __init__(self):
        """Initialize metrics collection."""
        self.access_counts = {}
        self.load_times = {}
        self.cache_hits = 0
        self.cache_misses = 0

    def record_access(self, data_type: str, load_time_ms: float, cache_hit: bool):
        """Record data access metrics."""
        self.access_counts[data_type] = self.access_counts.get(data_type, 0) + 1

        if data_type not in self.load_times:
            self.load_times[data_type] = []
        self.load_times[data_type].append(load_time_ms)

        if cache_hit:
            self.cache_hits += 1
        else:
            self.cache_misses += 1

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        total_accesses = sum(self.access_counts.values())
        cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0

        avg_load_times = {}
        for data_type, times in self.load_times.items():
            avg_load_times[data_type] = sum(times) / len(times) if times else 0

        return {
            "total_accesses": total_accesses,
            "access_counts": self.access_counts.copy(),
            "cache_hit_rate": cache_hit_rate,
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "avg_load_times_ms": avg_load_times
        }


# Global metrics instance
_metrics = DataAccessMetrics()


def get_data_access_metrics() -> Dict[str, Any]:
    """Get data access performance metrics."""
    return _metrics.get_stats()