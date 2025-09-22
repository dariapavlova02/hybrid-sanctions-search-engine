"""
Optimized data access layer that replaces direct dictionary imports.
Provides memory-efficient access to large dictionary files.
"""

import asyncio
from typing import Set, Dict, List, Any, Optional
from pathlib import Path

from .optimized_dictionary_loader import get_optimized_loader, load_dictionary_async, load_dictionary_sync
from ..utils.async_sync_bridge import get_async_data_loader, async_safe
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


class OptimizedDataAccess:
    """
    Optimized access layer for all data dictionaries.
    Replaces direct imports with lazy loading and memory management.
    """

    def __init__(self):
        """Initialize optimized data access."""
        self.loader = get_optimized_loader()
        self.async_loader = get_async_data_loader()

        # Dictionary mapping for standardized access
        self.dictionary_map = {
            # Name dictionaries
            'ukrainian_names': 'data/ukrainian_names.json',
            'russian_names': 'data/russian_names.json',
            'english_names': 'data/english_names.json',
            'given_names_ru': 'data/dicts/given_names_ru.py',
            'given_names_uk': 'data/dicts/given_names_uk.py',
            'surnames_ru': 'data/dicts/surnames_ru.py',
            'surnames_uk': 'data/dicts/surnames_uk.py',

            # Diminutives and nicknames
            'diminutives_ru': 'data/diminutives_ru.json',
            'diminutives_uk': 'data/diminutives_uk.json',
            'diminutives_extra': 'data/dicts/diminutives_extra.py',
            'en_nicknames': 'data/lexicons/en_nicknames.json',

            # Stopwords and filters
            'stopwords': 'data/dicts/stopwords.py',
            'payment_triggers': 'data/payment_triggers.json',
            'smart_filter_patterns': 'data/smart_filter_patterns.json',

            # Organization data
            'legal_forms_ru': 'data/legal_forms_ru.json',
            'legal_forms_uk': 'data/legal_forms_uk.json',
            'legal_forms_en': 'data/legal_forms_en.json',
        }

        # Preload high-frequency dictionaries
        self._high_frequency_dicts = [
            'stopwords', 'diminutives_ru', 'diminutives_uk', 'given_names_ru', 'given_names_uk'
        ]

    async def initialize(self) -> None:
        """Initialize and preload frequently used dictionaries."""
        try:
            await self.loader.preload_dictionaries(self._high_frequency_dicts)
            logger.info("Optimized data access initialized with preloaded dictionaries")
        except Exception as e:
            logger.warning(f"Failed to preload dictionaries: {e}")

    # Stopwords access
    async def get_stopwords_async(self) -> Set[str]:
        """Get stopwords asynchronously."""
        try:
            stopwords_data = await self.async_loader.load_with_fallback(
                lambda: load_dictionary_sync('stopwords'),
                fallback_func=self._get_fallback_stopwords,
                cache_key='stopwords'
            )

            if isinstance(stopwords_data, dict) and 'STOP_ALL' in stopwords_data:
                return set(stopwords_data['STOP_ALL'])
            elif isinstance(stopwords_data, (set, list)):
                return set(stopwords_data)
            else:
                return self._get_fallback_stopwords()

        except Exception as e:
            logger.warning(f"Failed to load stopwords: {e}")
            return self._get_fallback_stopwords()

    def get_stopwords_sync(self) -> Set[str]:
        """Get stopwords synchronously (for compatibility)."""
        try:
            stopwords_data = load_dictionary_sync('stopwords')

            if isinstance(stopwords_data, dict) and 'STOP_ALL' in stopwords_data:
                return set(stopwords_data['STOP_ALL'])
            elif isinstance(stopwords_data, (set, list)):
                return set(stopwords_data)
            else:
                return self._get_fallback_stopwords()

        except Exception as e:
            logger.warning(f"Failed to load stopwords: {e}")
            return self._get_fallback_stopwords()

    def _get_fallback_stopwords(self) -> Set[str]:
        """Fallback stopwords if loading fails."""
        return {
            # Critical stopwords that must always be filtered
            "payment", "transfer", "invoice", "services", "refund", "charity",
            "corp", "company", "ltd", "inc", "llc", "from", "to", "for",
            "платеж", "перевод", "услуги", "оплата", "ооо", "зао", "ип",
            "платіж", "переказ", "послуги", "тов", "фоп"
        }

    # Ukrainian names access
    async def get_ukrainian_names_async(self, chunk_key: Optional[str] = None) -> Set[str]:
        """Get Ukrainian names asynchronously."""
        return await self._get_names_async('ukrainian_names', chunk_key)

    def get_ukrainian_names_sync(self, chunk_key: Optional[str] = None) -> Set[str]:
        """Get Ukrainian names synchronously."""
        return self._get_names_sync('ukrainian_names', chunk_key)

    # Russian names access
    async def get_russian_names_async(self, chunk_key: Optional[str] = None) -> Set[str]:
        """Get Russian names asynchronously."""
        return await self._get_names_async('russian_names', chunk_key)

    def get_russian_names_sync(self, chunk_key: Optional[str] = None) -> Set[str]:
        """Get Russian names synchronously."""
        return self._get_names_sync('russian_names', chunk_key)

    # Diminutives access
    async def get_diminutives_async(self, language: str) -> Dict[str, str]:
        """Get diminutives dictionary asynchronously."""
        dict_name = f'diminutives_{language}'
        try:
            diminutives_data = await self.async_loader.load_with_fallback(
                lambda: load_dictionary_sync(dict_name),
                fallback_func=lambda: self._get_fallback_diminutives(language),
                cache_key=dict_name
            )

            if isinstance(diminutives_data, dict):
                return diminutives_data
            else:
                return self._get_fallback_diminutives(language)

        except Exception as e:
            logger.warning(f"Failed to load {dict_name}: {e}")
            return self._get_fallback_diminutives(language)

    def get_diminutives_sync(self, language: str) -> Dict[str, str]:
        """Get diminutives dictionary synchronously."""
        dict_name = f'diminutives_{language}'
        try:
            diminutives_data = load_dictionary_sync(dict_name)

            if isinstance(diminutives_data, dict):
                return diminutives_data
            else:
                return self._get_fallback_diminutives(language)

        except Exception as e:
            logger.warning(f"Failed to load {dict_name}: {e}")
            return self._get_fallback_diminutives(language)

    def _get_fallback_diminutives(self, language: str) -> Dict[str, str]:
        """Fallback diminutives if loading fails."""
        if language == 'ru':
            return {
                "саша": "александр", "вова": "владимир", "катя": "екатерина",
                "дима": "дмитрий", "наташа": "наталья", "сергей": "сергей"
            }
        elif language == 'uk':
            return {
                "саша": "олександр", "вова": "володимир", "катя": "катерина",
                "дима": "дмитро", "наташа": "наталія"
            }
        else:
            return {}

    # Payment triggers access
    async def get_payment_triggers_async(self) -> List[str]:
        """Get payment triggers asynchronously."""
        try:
            triggers_data = await self.async_loader.load_with_fallback(
                lambda: load_dictionary_sync('payment_triggers'),
                fallback_func=self._get_fallback_payment_triggers,
                cache_key='payment_triggers'
            )

            if isinstance(triggers_data, (list, set)):
                return list(triggers_data)
            elif isinstance(triggers_data, dict):
                # Extract patterns from nested structure
                patterns = []
                for value in triggers_data.values():
                    if isinstance(value, (list, set)):
                        patterns.extend(value)
                    else:
                        patterns.append(str(value))
                return patterns
            else:
                return self._get_fallback_payment_triggers()

        except Exception as e:
            logger.warning(f"Failed to load payment triggers: {e}")
            return self._get_fallback_payment_triggers()

    def _get_fallback_payment_triggers(self) -> List[str]:
        """Fallback payment triggers if loading fails."""
        return [
            "payment", "transfer", "invoice", "bill", "refund",
            "платеж", "перевод", "счет", "оплата", "возврат",
            "платіж", "переказ", "рахунок", "оплата", "повернення"
        ]

    # Generic name access methods
    async def _get_names_async(self, dict_name: str, chunk_key: Optional[str] = None) -> Set[str]:
        """Generic async names getter."""
        try:
            names_data = await self.async_loader.load_with_fallback(
                lambda: load_dictionary_sync(dict_name, chunk_key),
                fallback_func=lambda: self._get_fallback_names(dict_name),
                cache_key=f'{dict_name}:{chunk_key}' if chunk_key else dict_name
            )

            if isinstance(names_data, (set, list)):
                return set(str(name).lower() for name in names_data if name)
            elif isinstance(names_data, dict):
                # Extract names from nested structure
                all_names = set()
                for value in names_data.values():
                    if isinstance(value, (list, set)):
                        all_names.update(str(name).lower() for name in value if name)
                    else:
                        all_names.add(str(value).lower())
                return all_names
            else:
                return self._get_fallback_names(dict_name)

        except Exception as e:
            logger.warning(f"Failed to load {dict_name}: {e}")
            return self._get_fallback_names(dict_name)

    def _get_names_sync(self, dict_name: str, chunk_key: Optional[str] = None) -> Set[str]:
        """Generic sync names getter."""
        try:
            names_data = load_dictionary_sync(dict_name, chunk_key)

            if isinstance(names_data, (set, list)):
                return set(str(name).lower() for name in names_data if name)
            elif isinstance(names_data, dict):
                # Extract names from nested structure
                all_names = set()
                for value in names_data.values():
                    if isinstance(value, (list, set)):
                        all_names.update(str(name).lower() for name in value if name)
                    else:
                        all_names.add(str(value).lower())
                return all_names
            else:
                return self._get_fallback_names(dict_name)

        except Exception as e:
            logger.warning(f"Failed to load {dict_name}: {e}")
            return self._get_fallback_names(dict_name)

    def _get_fallback_names(self, dict_name: str) -> Set[str]:
        """Fallback names if loading fails."""
        if 'ukrainian' in dict_name:
            return {"олександр", "володимир", "катерина", "наталія", "дмитро", "сергій"}
        elif 'russian' in dict_name:
            return {"александр", "владимир", "екатерина", "наталья", "дмитрий", "сергей"}
        elif 'english' in dict_name:
            return {"alexander", "vladimir", "catherine", "natalie", "dmitry", "sergey"}
        else:
            return set()

    # Smart filter patterns access
    async def get_smart_filter_patterns_async(self) -> Dict[str, Any]:
        """Get smart filter patterns asynchronously."""
        try:
            patterns_data = await self.async_loader.load_with_fallback(
                lambda: load_dictionary_sync('smart_filter_patterns'),
                fallback_func=self._get_fallback_smart_patterns,
                cache_key='smart_filter_patterns'
            )

            if isinstance(patterns_data, dict):
                return patterns_data
            else:
                return self._get_fallback_smart_patterns()

        except Exception as e:
            logger.warning(f"Failed to load smart filter patterns: {e}")
            return self._get_fallback_smart_patterns()

    def _get_fallback_smart_patterns(self) -> Dict[str, Any]:
        """Fallback smart filter patterns."""
        return {
            "name_indicators": ["mr", "ms", "mrs", "dr", "prof"],
            "organization_indicators": ["ltd", "inc", "corp", "llc", "ооо", "зао", "тов"],
            "payment_indicators": ["payment", "transfer", "платеж", "перевод", "платіж"]
        }

    # Cache management
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        loader_stats = self.loader.get_cache_stats()
        return {
            "dictionary_loader": loader_stats,
            "async_loader_cache": len(self.async_loader._loading_cache) if hasattr(self.async_loader, '_loading_cache') else 0
        }

    async def clear_caches(self) -> None:
        """Clear all caches."""
        # Clear dictionary loader cache
        with self.loader._cache_lock:
            self.loader._cache.clear()
            self.loader._cache_metadata.clear()
            self.loader._memory_usage_mb = 0.0

        # Clear async loader cache
        if hasattr(self.async_loader, '_loading_cache'):
            async with self.async_loader._cache_lock:
                self.async_loader._loading_cache.clear()

        logger.info("All data access caches cleared")

    async def cleanup(self) -> None:
        """Cleanup resources."""
        await self.loader.cleanup()


# Global instance
_global_data_access: Optional[OptimizedDataAccess] = None


def get_optimized_data_access() -> OptimizedDataAccess:
    """Get global optimized data access instance."""
    global _global_data_access
    if _global_data_access is None:
        _global_data_access = OptimizedDataAccess()
    return _global_data_access


# Compatibility functions to replace direct imports
@async_safe
def get_stopwords() -> Set[str]:
    """Get stopwords - async-safe compatibility function."""
    data_access = get_optimized_data_access()
    return data_access.get_stopwords_sync()


@async_safe
def get_ukrainian_names() -> Set[str]:
    """Get Ukrainian names - async-safe compatibility function."""
    data_access = get_optimized_data_access()
    return data_access.get_ukrainian_names_sync()


@async_safe
def get_russian_names() -> Set[str]:
    """Get Russian names - async-safe compatibility function."""
    data_access = get_optimized_data_access()
    return data_access.get_russian_names_sync()


@async_safe
def get_diminutives(language: str) -> Dict[str, str]:
    """Get diminutives - async-safe compatibility function."""
    data_access = get_optimized_data_access()
    return data_access.get_diminutives_sync(language)


@async_safe
def get_payment_triggers() -> List[str]:
    """Get payment triggers - async-safe compatibility function."""
    data_access = get_optimized_data_access()
    return data_access.get_payment_triggers_async()