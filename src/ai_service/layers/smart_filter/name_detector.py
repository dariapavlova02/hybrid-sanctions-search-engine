"""
Simplified Name Detector

This detector provides a fallback mechanism for name extraction when NER fails.
It uses simple heuristics like capitalization and dictionary lookups.
"""

import re
from typing import Any, Dict, List, Set

import json
from pathlib import Path

from ...data.dicts.smart_filter_patterns import SERVICE_WORDS

# Load data from root data directory
_data_dir = Path(__file__).parent.parent.parent.parent.parent / "data"

# Load English nicknames
with open(_data_dir / "lexicons" / "en_nicknames.json", "r", encoding="utf-8") as f:
    ENGLISH_NICKNAMES = json.load(f)

# Load Russian diminutives
with open(_data_dir / "diminutives_ru.json", "r", encoding="utf-8") as f:
    RUSSIAN_DIMINUTIVES = json.load(f)

# Load Ukrainian diminutives  
with open(_data_dir / "diminutives_uk.json", "r", encoding="utf-8") as f:
    UKRAINIAN_DIMINUTIVES = json.load(f)
from ...utils.logging_config import get_logger


class NameDetector:
    """A simplified person name detector for fallback purposes."""

    def __init__(self, smart_filter_service=None):
        """Initialize detector."""
        self.logger = get_logger(__name__)
        self.name_dictionaries = self._load_name_dictionaries()
        self.smart_filter_service = smart_filter_service
        self.logger.info("Simplified NameDetector initialized.")

        # Create combined set of service words for fast lookup
        # Only include obvious service/payment terms, not general business words
        self._service_words = set()
        for lang_words in SERVICE_WORDS.values():
            self._service_words.update(word.lower() for word in lang_words)

        # Remove words that might be names to avoid false positives
        self._service_words.discard('анна')  # Common name
        self._service_words.discard('віра')  # Common name
        self._service_words.discard('дарья')  # Common name
        self._service_words.discard('віка')  # Common name

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
            token_lower = token.lower()

            # Skip if it's a service word (payment terms, services, etc.)
            # Now more selective - only obvious service words, not potential names
            if token_lower in self._service_words:
                self.logger.debug(f"Skipping service word: {token}")
                continue

            # Heuristic 1: Is it a capitalized word? (and not just a single letter)
            if token[0].isupper() and len(token) > 1:
                potential_names.append(token)
            # Heuristic 2: Is it in our name dictionaries?
            elif token_lower in all_names_dict:
                potential_names.append(token)
            # Heuristic 3: Does it look like an initial? (e.g., "A.", "B.C.")
            elif re.fullmatch(r"([A-ZА-ЯІЇЄҐ]\.)+", token):
                potential_names.append(token)

        self.logger.debug(f"Detected potential names in fallback: {potential_names}")
        return potential_names

    def _verify_names_with_ac(self, detected_names: List[str]) -> tuple[List[str], float]:
        """
        Verify detected names against AC dictionary.
        
        Args:
            detected_names: List of detected name tokens
            
        Returns:
            Tuple of (verified_names, confidence_bonus)
        """
        if not self.smart_filter_service:
            return [], 0.0
            
        try:
            # Create a text with just the detected names for AC search
            names_text = " ".join(detected_names)
            
            # Search for AC matches in the names text
            ac_result = self.smart_filter_service.search_aho_corasick(names_text)
            ac_matches = ac_result.get("matches", [])
            
            # Extract verified names from AC matches
            verified_names = []
            for match in ac_matches:
                matched_text = match.get("matched_text", "")
                if matched_text in detected_names:
                    verified_names.append(matched_text)
            
            # Calculate confidence bonus (0.2 per verified name, max 0.4)
            confidence_bonus = min(len(verified_names) * 0.2, 0.4)
            
            self.logger.debug(f"AC verification: {len(verified_names)} names verified out of {len(detected_names)}")
            return verified_names, confidence_bonus
            
        except Exception as e:
            self.logger.warning(f"AC verification failed: {e}")
            return [], 0.0

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

        # Simple confidence calculation - increased for better name detection
        if name_count == 0:
            confidence = 0.0
        elif name_count == 1:
            confidence = 0.8  # Increased from 0.3 to 0.8 for single names
        elif name_count >= 2:
            confidence = 0.9  # Increased from 0.7 to 0.9 for multiple names
        else:
            confidence = 0.0

        # Adjust confidence based on text length
        if text_length > 10 and name_count > 0:
            confidence *= 0.8  # Reduce confidence for long texts with few names

        # AC verification step: check detected names against AC dictionary
        ac_verified_names = []
        ac_confidence_bonus = 0.0
        
        if (detected_names and 
            self.smart_filter_service and 
            hasattr(self.smart_filter_service, 'aho_corasick_enabled') and
            self.smart_filter_service.aho_corasick_enabled):
            
            ac_verified_names, ac_confidence_bonus = self._verify_names_with_ac(detected_names)
            
            # Apply AC confidence bonus if names were verified
            if ac_verified_names:
                confidence = min(confidence + ac_confidence_bonus, 1.0)

        # Check for specific name patterns
        has_capitals = any(name[0].isupper() and len(name) > 1 for name in detected_names)
        has_initials = any(re.fullmatch(r"([A-ZА-ЯІЇЄҐ]\.)+", name) for name in detected_names)
        has_patronymic_endings = any(
            name.endswith(('ович', 'евич', 'йович', 'ич', 'івна', 'ївна', 'овна', 'евна', 'ична'))
            for name in detected_names
        )
        has_nicknames = any(
            name.lower() in self.name_dictionaries.get("all", set())
            for name in detected_names
        )

        return {
            "has_names": name_count > 0,
            "name_count": name_count,
            "names": detected_names,
            "confidence": min(confidence, 1.0),
            "ac_verified_names": ac_verified_names,
            "ac_confidence_bonus": ac_confidence_bonus,
            # Additional fields for compatibility
            "has_capitals": has_capitals,
            "has_initials": has_initials,
            "has_patronymic_endings": has_patronymic_endings,
            "has_nicknames": has_nicknames,
        }
