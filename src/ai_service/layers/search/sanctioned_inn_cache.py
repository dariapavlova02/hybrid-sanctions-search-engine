"""
Fast lookup cache for sanctioned INNs.

Provides O(1) lookup for INN -> sanctioned person/organization mapping.
Much faster than AC search or Elasticsearch for INN-specific queries.
"""

import json
import time
from pathlib import Path
from typing import Dict, Optional, Any
from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class SanctionedINNCache:
    """Fast in-memory cache for sanctioned INNs."""

    def __init__(self):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.loaded_at: Optional[float] = None
        self.cache_file = Path(__file__).parent.parent.parent / "data" / "sanctioned_inns_cache.json"
        self.stats = {
            "total_inns": 0,
            "persons": 0,
            "organizations": 0,
            "lookups": 0,
            "hits": 0,
            "misses": 0
        }

    def load_cache(self) -> bool:
        """Load sanctioned INNs cache from file."""
        try:
            if not self.cache_file.exists():
                logger.warning(f"INN cache file not found: {self.cache_file}")
                return False

            start_time = time.time()
            with open(self.cache_file, 'r', encoding='utf-8') as f:
                self.cache = json.load(f)

            self.loaded_at = time.time()
            load_time = (self.loaded_at - start_time) * 1000

            # Update statistics
            self.stats["total_inns"] = len(self.cache)
            for inn_data in self.cache.values():
                if inn_data.get("type") == "person":
                    self.stats["persons"] += 1
                elif inn_data.get("type") == "organization":
                    self.stats["organizations"] += 1

            logger.info(
                f"[OK] Loaded {self.stats['total_inns']} sanctioned INNs "
                f"({self.stats['persons']} persons, {self.stats['organizations']} orgs) "
                f"in {load_time:.2f}ms"
            )
            return True

        except Exception as e:
            logger.error(f"[ERROR] Failed to load INN cache: {e}")
            return False

    def lookup(self, inn: str) -> Optional[Dict[str, Any]]:
        """
        Fast lookup for sanctioned INN.

        Args:
            inn: INN to check

        Returns:
            Dict with sanctioned person/organization data if found, None otherwise
        """
        self.stats["lookups"] += 1

        if not self.cache and not self.load_cache():
            self.stats["misses"] += 1
            return None

        inn_normalized = str(inn).strip()
        result = self.cache.get(inn_normalized)

        if result:
            self.stats["hits"] += 1
            logger.debug(f"🚨 SANCTIONED INN FOUND: {inn_normalized} -> {result.get('name', 'Unknown')}")
            return result.copy()  # Return copy to prevent modification
        else:
            self.stats["misses"] += 1
            return None

    def is_sanctioned(self, inn: str) -> bool:
        """Check if INN is sanctioned."""
        return self.lookup(inn) is not None

    def get_sanctioned_person(self, inn: str) -> Optional[Dict[str, Any]]:
        """Get sanctioned person data by INN."""
        result = self.lookup(inn)
        if result and result.get("type") == "person":
            return result
        return None

    def get_sanctioned_organization(self, inn: str) -> Optional[Dict[str, Any]]:
        """Get sanctioned organization data by INN."""
        result = self.lookup(inn)
        if result and result.get("type") == "organization":
            return result
        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        hit_rate = (self.stats["hits"] / max(1, self.stats["lookups"])) * 100
        return {
            **self.stats,
            "hit_rate_percent": round(hit_rate, 2),
            "loaded_at": self.loaded_at,
            "cache_age_seconds": time.time() - self.loaded_at if self.loaded_at else None
        }

    def reload_cache(self) -> bool:
        """Force reload cache from file."""
        self.cache.clear()
        self.loaded_at = None
        # Reset lookup stats (but keep total counts)
        self.stats["lookups"] = 0
        self.stats["hits"] = 0
        self.stats["misses"] = 0

        return self.load_cache()


# Global cache instance
_inn_cache_instance: Optional[SanctionedINNCache] = None


def get_inn_cache() -> SanctionedINNCache:
    """Get global INN cache instance."""
    global _inn_cache_instance
    if _inn_cache_instance is None:
        _inn_cache_instance = SanctionedINNCache()
        _inn_cache_instance.load_cache()
    return _inn_cache_instance


def lookup_sanctioned_inn(inn: str) -> Optional[Dict[str, Any]]:
    """Fast lookup for sanctioned INN (convenience function)."""
    return get_inn_cache().lookup(inn)


def is_inn_sanctioned(inn: str) -> bool:
    """Check if INN is sanctioned (convenience function)."""
    return get_inn_cache().is_sanctioned(inn)