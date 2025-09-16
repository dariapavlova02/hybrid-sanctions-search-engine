"""
Morphological processing for name normalization.
Handles the complex morphological analysis extracted from the main service.
"""

import asyncio
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any
from ....utils.logging_config import get_logger


class MorphologyProcessor:
    """Handles morphological analysis for name normalization."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self._morphs = {}
        self._cache = {}
        self._initialize_morphology_analyzers()

    def _initialize_morphology_analyzers(self):
        """Initialize morphology analyzers for supported languages."""
        try:
            import pymorphy3
            self._morphs['ru'] = pymorphy3.MorphAnalyzer(lang='ru')
            self._morphs['uk'] = pymorphy3.MorphAnalyzer(lang='uk')
            self.logger.info("Morphology analyzers initialized for ru, uk")
        except ImportError:
            self.logger.warning("pymorphy3 not available, morphological analysis disabled")
        except Exception as e:
            self.logger.warning(f"Failed to initialize morphology analyzers: {e}")

    @lru_cache(maxsize=10000)
    def morph_nominal(
        self,
        token: str,
        language: str,
        role: str = None
    ) -> Tuple[str, bool, List[str]]:
        """
        Perform morphological normalization to nominative case.

        Args:
            token: Token to normalize
            language: Language code (ru, uk)
            role: Token role hint (given, surname, patronymic)

        Returns:
            Tuple of (normalized_token, fallback_used, trace)
        """
        if not token or language not in self._morphs:
            return token, True, ["No morphological analysis available"]

        try:
            return self._analyze_morphology(token, language, role)
        except Exception as e:
            self.logger.warning(f"Morphological analysis failed for '{token}': {e}")
            return token, True, [f"Morphological analysis error: {e}"]

    def _analyze_morphology(
        self,
        token: str,
        language: str,
        role: str = None
    ) -> Tuple[str, bool, List[str]]:
        """Core morphological analysis logic."""
        morph = self._morphs[language]
        trace = []

        # Parse the word
        parses = morph.parse(token)
        if not parses:
            trace.append("No morphological parses found")
            return token, True, trace

        # Find best parse based on role
        best_parse = self._select_best_parse(parses, role, token)
        trace.append(f"Selected parse: {best_parse.tag}")

        # Check if already nominative
        if 'nomn' in best_parse.tag:
            trace.append("Already in nominative case")
            return token, False, trace

        # Try to inflect to nominative
        try:
            nominative = best_parse.inflect({'nomn'})
            if nominative and nominative.word != token:
                trace.append(f"Inflected to nominative: '{token}' -> '{nominative.word}'")
                return nominative.word, False, trace
        except Exception as e:
            trace.append(f"Inflection failed: {e}")

        # Use normal form as fallback
        if best_parse.normal_form and best_parse.normal_form != token:
            trace.append(f"Using normal form: '{token}' -> '{best_parse.normal_form}'")
            return best_parse.normal_form, False, trace

        trace.append("No morphological changes applied")
        return token, True, trace

    def _select_best_parse(self, parses: List[Any], role: str, token: str) -> Any:
        """Select the best morphological parse based on role and context."""
        if not parses:
            return None

        # Score each parse
        scored_parses = []
        for parse in parses:
            score = self._score_parse(parse, role, token)
            scored_parses.append((score, parse))

        # Return highest scoring parse
        scored_parses.sort(key=lambda x: x[0], reverse=True)
        return scored_parses[0][1]

    def _score_parse(self, parse: Any, role: str, token: str) -> float:
        """Score a morphological parse based on role and token characteristics."""
        score = 0.0

        # Base score for having a part of speech
        if hasattr(parse, 'tag') and parse.tag.POS:
            score += 1.0

        # Role-specific scoring
        if role == 'given' and 'Name' in str(parse.tag):
            score += 3.0
        elif role == 'surname' and 'Surn' in str(parse.tag):
            score += 3.0
        elif role == 'patronymic' and 'Patr' in str(parse.tag):
            score += 3.0

        # Prefer proper nouns for names
        if 'NOUN' in str(parse.tag):
            score += 1.0

        # Prefer exact matches
        if hasattr(parse, 'word') and parse.word.lower() == token.lower():
            score += 2.0

        # Penalty for very short words that might be incorrectly analyzed
        if len(token) < 3:
            score -= 0.5

        return score

    async def normalize_slavic_token(
        self,
        token: str,
        role: str,
        language: str,
        enable_morphology: bool = True
    ) -> Tuple[str, List[str]]:
        """
        Normalize a Slavic language token.

        Args:
            token: Token to normalize
            role: Token role
            language: Language code
            enable_morphology: Whether to use morphological analysis

        Returns:
            Tuple of (normalized_token, trace)
        """
        trace = []

        if not enable_morphology:
            # Simple capitalization
            normalized = token.capitalize() if role in {'given', 'surname', 'patronymic'} else token
            trace.append(f"Simple normalization: '{token}' -> '{normalized}'")
            return normalized, trace

        # Use morphological analysis
        normalized, fallback_used, morph_trace = self.morph_nominal(token, language, role)
        trace.extend(morph_trace)

        # Apply case normalization if morphology didn't change anything
        if fallback_used and role in {'given', 'surname', 'patronymic'}:
            normalized = normalized.capitalize()
            trace.append(f"Applied capitalization fallback: '{normalized}'")

        return normalized, trace

    def handle_diminutives(
        self,
        token: str,
        language: str,
        diminutive_maps: Dict[str, Dict[str, str]] = None
    ) -> Tuple[str, bool, List[str]]:
        """
        Convert diminutive forms to full names.

        Args:
            token: Token to check
            language: Language code
            diminutive_maps: Diminutive to full name mappings

        Returns:
            Tuple of (normalized_token, was_diminutive, trace)
        """
        trace = []
        diminutive_maps = diminutive_maps or {}

        lang_map = diminutive_maps.get(language, {})
        token_lower = token.lower()

        if token_lower in lang_map:
            full_form = lang_map[token_lower]
            trace.append(f"Converted diminutive: '{token}' -> '{full_form}'")
            return full_form, True, trace

        trace.append("No diminutive conversion found")
        return token, False, trace

    def clear_cache(self):
        """Clear the morphological analysis cache."""
        self.morph_nominal.cache_clear()
        self._cache.clear()
        self.logger.info("Morphology cache cleared")