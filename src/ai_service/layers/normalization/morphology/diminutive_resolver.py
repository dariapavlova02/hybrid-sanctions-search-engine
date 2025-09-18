"""Resolve diminutive tokens to canonical forms using dictionary data."""

from __future__ import annotations

import json
import unicodedata
from functools import lru_cache
from pathlib import Path
from typing import Dict, Optional

from ....utils.logging_config import get_logger


_SUPPORTED_LANGS = ("ru", "uk")


class DiminutiveResolver:
    """Map diminutive tokens to their canonical form using static dictionaries."""

    def __init__(self, base_path: Path) -> None:
        self._logger = get_logger(__name__)
        self._base_path = base_path
        self._maps: Dict[str, Dict[str, str]] = {}
        for lang in _SUPPORTED_LANGS:
            self._maps[lang] = self._load_dictionary(lang)

        # Bind cached resolver to the instance so the cache size is per resolver
        self._resolve_cached = lru_cache(maxsize=10_000)(self._resolve_internal)

    def resolve(self, token: str, lang: str, *, allow_cross_lang: bool = False) -> Optional[str]:
        """Return canonical form for diminutive token."""
        if not token:
            return None

        if lang not in _SUPPORTED_LANGS:
            self._logger.debug("Unsupported diminutive language requested: %s", lang)
            return None

        normalized_token = unicodedata.normalize("NFC", token).lower()
        return self._resolve_cached(normalized_token, lang, allow_cross_lang)

    def _resolve_internal(self, token: str, lang: str, allow_cross_lang: bool) -> Optional[str]:
        primary_map = self._maps.get(lang, {})
        canonical = primary_map.get(token)
        if canonical:
            return canonical

        if not allow_cross_lang:
            return None

        for neighbour in _SUPPORTED_LANGS:
            if neighbour == lang:
                continue
            alt_value = self._maps.get(neighbour, {}).get(token)
            if alt_value:
                return alt_value
        return None

    def _load_dictionary(self, lang: str) -> Dict[str, str]:
        path = self._get_data_path(lang)
        try:
            data = self._read_dictionary(path)
            return data
        except FileNotFoundError:
            self._logger.warning("Diminutive dictionary not found for %s at %s", lang, path)
            return {}
        except json.JSONDecodeError as exc:
            self._logger.error("Invalid JSON in diminutive dictionary %s: %s", lang, exc)
            return {}
        except Exception as exc:  # pragma: no cover - IO errors are rare
            self._logger.error("Failed to load diminutive dictionary %s: %s", lang, exc)
            return {}

    def _get_data_path(self, lang: str) -> Path:
        return self._base_path / "data" / f"diminutives_{lang}.json"

    def clear_cache(self) -> None:
        """Clear the resolver cache (primarily for tests)."""
        self._resolve_cached.cache_clear()

    @staticmethod
    @lru_cache(maxsize=8)
    def _read_dictionary(path: Path) -> Dict[str, str]:
        with path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        normalized: Dict[str, str] = {}
        for key, value in raw.items():
            norm_key = unicodedata.normalize("NFC", key).lower()
            norm_value = unicodedata.normalize("NFC", value).lower()
            normalized[norm_key] = norm_value
        return normalized

__all__ = ["DiminutiveResolver"]
