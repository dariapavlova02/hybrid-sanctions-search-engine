"""
Embedding Preprocessor - normalizes text for embedding generation

This module provides text preprocessing specifically designed for embedding generation.
It follows the architectural principle of separation of concerns:

- NAMES/ORGANIZATIONS → Embeddings for semantic similarity
- DATES/IDs → Separate processing in Signals/Decision layers

Key Design Decisions:
1. Remove dates/IDs by default to focus on semantic content
2. Keep only names, organizations, and titles for vector generation
3. Future: include_attrs=True flag for attribute-aware embeddings

Usage:
    preprocessor = EmbeddingPreprocessor()
    clean_text = preprocessor.normalize_for_embedding("Ivan Petrov 1980-01-01 passport12345")
    # Result: "Ivan Petrov" (dates/IDs removed)
"""

import re
from typing import Optional

from ..utils.logging_config import get_logger


class EmbeddingPreprocessor:
    """Preprocessor for text normalization before embedding generation"""

    def __init__(self):
        """Initialize the preprocessor"""
        self.logger = get_logger(__name__)

        # Patterns for dates and IDs that should be removed by default
        self.date_patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",  # YYYY-MM-DD
            r"\b\d{2}\.\d{2}\.\d{4}\b",  # DD.MM.YYYY
            r"\b\d{2}/\d{2}/\d{4}\b",  # DD/MM/YYYY
            r"\b\d{1,2}\s+(?:января|февраля|марта|апреля|мая|июня|июля|августа|сентября|октября|ноября|декабря)\s+\d{4}\b",  # Russian dates
            r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",  # English dates
        ]

        self.id_patterns = [
            r"\bpassport\s*\d+\b",  # passport12345
            r"\bpassport\s*№\s*\d+\b",  # passport №12345
            r"\bID\s*\d+\b",  # ID12345
            r"\b№\s*\d+\b",  # №12345
            r"\bИНН\s*\d+\b",  # ИНН1234567890
            r"\bЄДРПОУ\s*\d+\b",  # ЄДРПОУ1234567890
            r"\bОГРН\s*\d+\b",  # ОГРН1234567890
            r"\bVAT\s*\d+\b",  # VAT1234567890
            r"\b\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",  # credit card numbers
            r"\b\d{3}-\d{3}-\d{3}\b",  # phone numbers
            r"№\s*\d+",  # №12345 (without word boundary for special character)
        ]

    def normalize_for_embedding(
        self, text: str, *, fold_spaces: bool = True, include_attrs: bool = False
    ) -> str:
        """
        Normalize text for embedding generation

        Args:
            text: Input text to normalize
            fold_spaces: Whether to collapse multiple spaces into single space
            include_attrs: Whether to include attributes (dates/IDs) - FUTURE FEATURE

        Returns:
            Normalized text with dates/IDs removed by default
        """
        if not text or not text.strip():
            return ""

        # TODO: Implement include_attrs=True mode for future use
        # This will allow including structured attributes in embeddings when needed
        if include_attrs:
            self.logger.warning(
                "include_attrs=True not yet implemented, using default behavior"
            )
            # For now, fall back to default behavior
            include_attrs = False

        # Start with the input text
        normalized = text.strip()

        if not include_attrs:
            # Remove dates
            for pattern in self.date_patterns:
                normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

            # Remove IDs
            for pattern in self.id_patterns:
                normalized = re.sub(pattern, "", normalized, flags=re.IGNORECASE)

        # Clean up the text
        if fold_spaces:
            # Collapse multiple whitespace into single space
            normalized = re.sub(r"\s+", " ", normalized)

        # Remove leading/trailing whitespace
        normalized = normalized.strip()

        self.logger.debug(
            f"Normalized '{text}' -> '{normalized}' (include_attrs={include_attrs})"
        )

        return normalized

    def extract_name_only(self, text: str) -> str:
        """
        Extract only the name/title part, removing all dates and IDs

        Args:
            text: Input text

        Returns:
            Text with only name/title content
        """
        return self.normalize_for_embedding(text, fold_spaces=True, include_attrs=False)

    def should_include_attrs(self) -> bool:
        """
        Check if attributes should be included (for future implementation)

        Returns:
            False by default, True when include_attrs mode is implemented
        """
        # TODO: This will be configurable in the future
        return False
