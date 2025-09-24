"""
Person entity extractor.
"""

import re
from functools import lru_cache
from typing import Any, Dict, List

from .base_extractor import BaseExtractor


class PersonExtractor(BaseExtractor):
    """Extracts person names from text using pattern matching."""

    def __init__(self):
        super().__init__()

        # Patterns for different languages (as strings for caching)
        self._cyrillic_pattern_str = (
            r"\b[А-ЯЁЇІЄҐ][а-яёїієґ]+(?:\s+[А-ЯЁЇІЄҐ][а-яёїієґ]+){1,2}\b"
        )
        self._latin_pattern_str = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2}\b"

    @lru_cache(maxsize=4)
    def _get_compiled_pattern(self, pattern_type: str) -> re.Pattern:
        """Get compiled regex pattern with LRU caching."""
        if pattern_type == "cyrillic":
            return re.compile(self._cyrillic_pattern_str, re.IGNORECASE)
        elif pattern_type == "latin":
            return re.compile(self._latin_pattern_str, re.IGNORECASE)
        else:
            raise ValueError(f"Unknown pattern type: {pattern_type}")

    def extract(self, text: str, language: str = "uk", **kwargs) -> List[List[str]]:
        """
        Extract person name tokens from text.

        Args:
            text: Input text
            language: Text language

        Returns:
            List of person name token lists
        """
        if not self._is_valid_text(text):
            return []

        found_names = []

        # Extract Cyrillic names (Ukrainian/Russian) using cached pattern
        cyrillic_pattern = self._get_compiled_pattern("cyrillic")
        for match in cyrillic_pattern.finditer(text):
            name_tokens = match.group(0).split()
            if not self._contains_legal_form(name_tokens):
                # Filter out document markers from person names
                clean_tokens = self._filter_document_markers(name_tokens)
                if len(clean_tokens) >= 2:  # Need at least 2 tokens for a person name
                    found_names.append(clean_tokens)

        # Extract Latin names using cached pattern
        latin_pattern = self._get_compiled_pattern("latin")
        for match in latin_pattern.finditer(text):
            name_tokens = match.group(0).split()
            if not self._contains_legal_form(name_tokens):
                # Filter out document markers from person names
                clean_tokens = self._filter_document_markers(name_tokens)
                if len(clean_tokens) >= 2:  # Need at least 2 tokens for a person name
                    found_names.append(clean_tokens)

        self._log_extraction_result(text, len(found_names), "person")
        return found_names

    def _contains_legal_form(self, tokens: List[str]) -> bool:
        """Check if tokens contain legal form words."""
        from ....data.patterns.legal_forms import get_legal_forms_set

        try:
            legal_forms = get_legal_forms_set()
            return any(token.upper() in legal_forms for token in tokens)
        except ImportError:
            # Fallback if legal forms module not available
            common_legal_forms = {
                "ТОВ",
                "ООО",
                "ЗАО",
                "ПАО",
                "LLC",
                "INC",
                "LTD",
                "CORP",
            }
            return any(token.upper() in common_legal_forms for token in tokens)

    def _contains_document_marker(self, tokens: List[str]) -> bool:
        """Check if tokens contain business document markers."""
        try:
            from ....layers.normalization.processors.role_classifier import BUSINESS_DOCUMENT_MARKERS
            return any(token.lower() in BUSINESS_DOCUMENT_MARKERS for token in tokens)
        except ImportError:
            # Fallback with common document markers
            common_document_markers = {
                "іпн", "ипн", "inn", "inн", "tin", "edrpou", "едрпоу",
                "паспорт", "passport", "д.р.", "д/р", "dob", "born"
            }
            return any(token.lower() in common_document_markers for token in tokens)

    def _filter_document_markers(self, tokens: List[str]) -> List[str]:
        """Filter out document markers from tokens, keeping only person name parts."""
        try:
            from ....layers.normalization.processors.role_classifier import BUSINESS_DOCUMENT_MARKERS
            document_markers = BUSINESS_DOCUMENT_MARKERS
        except ImportError:
            # Fallback with common document markers
            document_markers = {
                "іпн", "ипн", "inn", "inн", "tin", "edrpou", "едрпоу",
                "паспорт", "passport", "д.р.", "д/р", "dob", "born"
            }

        return [token for token in tokens if token.lower() not in document_markers]
