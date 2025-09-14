"""
Simplified Name Detector

This detector provides a fallback mechanism for name extraction when NER fails.
It uses simple heuristics like capitalization and dictionary lookups.
"""

import re
from typing import Any, Dict, List, Set

from ...data.dicts.english_nicknames import ENGLISH_NICKNAMES
from ...data.dicts.russian_diminutives import RUSSIAN_DIMINUTIVES
from ...data.dicts.ukrainian_diminutives import UKRAINIAN_DIMINUTIVES
from ...utils.logging_config import get_logger


class NameDetector:
    """A simplified person name detector for fallback purposes."""

    def __init__(self):
        """Initialize detector."""
        self.logger = get_logger(__name__)
        self.name_dictionaries = self._load_name_dictionaries()
        self.logger.info("Simplified NameDetector initialized.")

    def _load_name_dictionaries(self) -> Dict[str, Set[str]]:
        """Loads a combined set of names from the new flat dictionaries."""
        all_names = set()

        # Add both keys (diminutives) and values (canonical names)
        all_names.update(UKRAINIAN_DIMINUTIVES.keys())
        all_names.update(UKRAINIAN_DIMINUTIVES.values())

        all_names.update(RUSSIAN_DIMINUTIVES.keys())
        all_names.update(RUSSIAN_DIMINUTIVES.values())

        all_names.update(ENGLISH_NICKNAMES.keys())
        all_names.update(ENGLISH_NICKNAMES.values())

        self.logger.info(f"Loaded {len(all_names)} unique names into the dictionary.")
        return {"all": all_names}

    def detect_names(self, text: str) -> List[str]:
        """
        Detects potential names in a text string.
        This is a fallback method that uses simple heuristics.
        """
        if not text:
            return []

        # Simple tokenization
        tokens = re.findall(r"\b\w[\w\.\-]+\b", text)

        potential_names = []
        all_names_dict = self.name_dictionaries.get("all", set())

        for token in tokens:
            # Heuristic 1: Is it a capitalized word? (and not just a single letter)
            if token[0].isupper() and len(token) > 1:
                potential_names.append(token)
            # Heuristic 2: Is it in our name dictionaries?
            elif token.lower() in all_names_dict:
                potential_names.append(token)
            # Heuristic 3: Does it look like an initial? (e.g., "A.", "B.C.")
            elif re.fullmatch(r"([A-ZА-ЯІЇЄҐ]\.)+", token):
                potential_names.append(token)

        self.logger.debug(f"Detected potential names in fallback: {potential_names}")
        return potential_names

    def detect_name_signals(self, text: str) -> Dict[str, Any]:
        """
        Detects name-related signals in text for smart filtering.
        Returns a dictionary with signal information.
        """
        if not text:
            return {"has_names": False, "name_count": 0, "names": [], "confidence": 0.0}

        # Detect names using existing method
        detected_names = self.detect_names(text)

        # Calculate confidence based on name count and text length
        name_count = len(detected_names)
        text_length = len(text.split())

        # Simple confidence calculation
        if name_count == 0:
            confidence = 0.0
        elif name_count == 1:
            confidence = 0.3
        elif name_count >= 2:
            confidence = 0.7
        else:
            confidence = 0.0

        # Adjust confidence based on text length
        if text_length > 10 and name_count > 0:
            confidence *= 0.8  # Reduce confidence for long texts with few names

        return {
            "has_names": name_count > 0,
            "name_count": name_count,
            "names": detected_names,
            "confidence": min(confidence, 1.0),
        }
