"""
Text normalization utilities for high-recall pattern generation.
"""

import re
import unicodedata
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...unicode.unicode_service import UnicodeService


class TextNormalizer:
    """Text normalization for Aho-Corasick pattern matching."""

    def __init__(self, unicode_service: "UnicodeService" = None):
        """Initialize normalizer with optional unicode service."""
        self.unicode_service = unicode_service

    def normalize_for_ac(self, text: str) -> str:
        """
        Нормализация текста для Aho-Corasick
        Только NFKC, casefold, унификация символов - БЕЗ транслитерации

        Args:
            text: Входная строка для нормализации

        Returns:
            Нормализованная строка для использования в AC
        """
        if not text:
            return ""

        # Graceful fallback: если UnicodeService недоступен, используем локальную нормализацию
        try:
            if hasattr(self, 'unicode_service') and self.unicode_service:
                result = self.unicode_service.normalize_text(
                    text,
                    aggressive=True,
                    normalize_homoglyphs=False
                )
                normalized = result["normalized"]
            else:
                normalized = text
        except Exception:
            normalized = text

        # NFKC нормализация
        normalized = unicodedata.normalize('NFKC', normalized)

        # Casefold для унификации регистра
        normalized = normalized.casefold()

        # Дополнительная нормализация для AC
        # Заменяем двойные кавычки на одинарные для унификации
        normalized = normalized.replace('"', "'")

        # Заменяем оставшиеся дефисы
        hyphen_variants = ['‐', '–', '—', '―', '‒', '‑', '‗', '⁃', '⁻', '₋']
        for variant in hyphen_variants:
            normalized = normalized.replace(variant, '-')

        # Коллапс кратных пробелов
        normalized = re.sub(r'\s+', ' ', normalized)

        # Обрезка крайних пробелов
        normalized = normalized.strip()

        return normalized

    def detect_language(self, text: str) -> str:
        """
        Determine language for variant generation.

        Args:
            text: Text to analyze

        Returns:
            Language code ('ru', 'uk', 'en', or 'auto')
        """
        if not text:
            return "auto"

        # Simple heuristics for language detection
        cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        latin_chars = sum(1 for c in text if 'A' <= c <= 'Z' or 'a' <= c <= 'z')
        total_chars = len([c for c in text if c.isalpha()])

        if total_chars == 0:
            return "auto"

        cyrillic_ratio = cyrillic_chars / total_chars

        # Strong Russian indicators
        if any(char in text for char in ['ё', 'ы', 'э', 'Ё', 'Ы', 'Э']):
            return "ru"

        # Strong Ukrainian indicators
        if any(char in text for char in ['ї', 'і', 'є', 'ґ', 'Ї', 'І', 'Є', 'Ґ']):
            return "uk"

        # General Cyrillic vs Latin
        if cyrillic_ratio > 0.7:
            return "ru"  # Default to Russian for generic Cyrillic
        elif cyrillic_ratio < 0.3:
            return "en"
        else:
            return "auto"  # Mixed script

    def is_cyrillic(self, text: str) -> bool:
        """Check if text contains primarily Cyrillic characters."""
        if not text:
            return False

        cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        total_chars = len([c for c in text if c.isalpha()])

        return total_chars > 0 and (cyrillic_chars / total_chars) > 0.5