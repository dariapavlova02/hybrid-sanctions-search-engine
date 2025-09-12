"""
Simplified Name Detector

This detector provides a fallback mechanism for name extraction when NER fails.
It uses simple heuristics like capitalization and dictionary lookups.
"""

import re
from typing import List, Dict, Set

from ...utils.logging_config import get_logger

from ...data.dicts.english_nicknames import ENGLISH_NICKNAMES
from ...data.dicts.ukrainian_diminutives import UKRAINIAN_DIMINUTIVES
from ...data.dicts.russian_diminutives import RUSSIAN_DIMINUTIVES


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
        tokens = re.findall(r'\b\w[\w\.\-]+\b', text)
        
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
            elif re.fullmatch(r'([A-ZА-ЯІЇЄҐ]\.)+', token):
                 potential_names.append(token)

        self.logger.debug(f"Detected potential names in fallback: {potential_names}")
        return potential_names
