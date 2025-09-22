"""Thin wrapper around language-specific morphology analyzers."""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from ....utils.logging_config import get_logger
from ....utils.profiling import profile_function, profile_time
from ..morphology.gender_rules import (
    convert_given_name_to_nominative,
    convert_patronymic_to_nominative,
    convert_surname_to_nominative,
)
from ..morphology.russian_morphology import RussianMorphologyAnalyzer
from ..morphology.ukrainian_morphology import UkrainianMorphologyAnalyzer

PersonalRole = Optional[str]


class MorphologyProcessor:
    """Provide morphology-aware normalization for Slavic names."""

    def __init__(self, diminutive_maps: Optional[Dict[str, Dict[str, str]]] = None) -> None:
        self.logger = get_logger(__name__)
        self.dim2full_maps = diminutive_maps or {}
        self._analyzers: Dict[str, object] = {}
        self._cache: Dict[Tuple[str, str, PersonalRole], Tuple[str, bool, List[str]]] = {}
        self._initialise_analyzers()

    def _initialise_analyzers(self) -> None:
        try:
            self._analyzers["ru"] = RussianMorphologyAnalyzer()
        except Exception as exc:  # pragma: no cover - optional dependency failures
            self.logger.warning("RussianMorphologyAnalyzer unavailable: %s", exc)
        try:
            self._analyzers["uk"] = UkrainianMorphologyAnalyzer()
        except Exception as exc:  # pragma: no cover
            self.logger.warning("UkrainianMorphologyAnalyzer unavailable: %s", exc)

    @profile_function("morphology_processor.normalize_slavic_token")
    async def normalize_slavic_token(
        self,
        token: str,
        role: PersonalRole,
        language: str,
        enable_morphology: bool = True,
        preserve_feminine_suffix_uk: bool = False,
    ) -> Tuple[str, List[str]]:
        """Normalize a single token to nominative form using language analyzers."""
        if not token:
            return token, ["Empty token"]

        if not enable_morphology:
            return self._title_case(token) if role in {"given", "surname", "patronymic"} else token, [
                "Morphology disabled"
            ]

        cached = self._cache.get((token, language, role))
        if cached:
            normalized, _, trace = cached
            return normalized, trace.copy()

        normalized, fallback, trace = self._normalize_token(token, language, role, preserve_feminine_suffix_uk)
        if fallback and role in {"given", "surname", "patronymic"}:
            title = self._title_case(normalized)
            if title != normalized:
                trace.append(f"Capitalization fallback: '{normalized}' -> '{title}'")
                normalized = title

        self._cache[(token, language, role)] = (normalized, fallback, trace)
        return normalized, trace

    def _normalize_token(
        self,
        token: str,
        language: str,
        role: PersonalRole,
        preserve_feminine_suffix_uk: bool = False,
    ) -> Tuple[str, bool, List[str]]:
        trace: List[str] = []
        normalized = token
        fallback = True

        if role == "given":
            normalized, fallback, trace = self._normalize_given(token, language)
        elif role == "surname":
            normalized, fallback, trace = self._normalize_surname(token, language, preserve_feminine_suffix_uk)
        elif role == "patronymic":
            normalized, fallback, trace = self._normalize_patronymic(token, language)
        else:
            analyzer_norm = self._analyzer_normalize(token, language)
            if analyzer_norm and analyzer_norm.lower() != token.lower():
                trace.append(f"Analyzer normalized '{token}' -> '{analyzer_norm}'")
                normalized = analyzer_norm
                fallback = False
            else:
                normalized = token
                fallback = True

        return normalized, fallback, trace

    def _normalize_given(self, token: str, language: str) -> Tuple[str, bool, List[str]]:
        trace: List[str] = []
        fallback = True
        normalized = token

        full = self.dim2full_maps.get(language, {}).get(token.lower())
        if full:
            normalized = self._title_case(full)
            trace.append(f"Diminutive expansion: '{token}' -> '{normalized}'")
            fallback = False

        converted = convert_given_name_to_nominative(normalized, language)
        if converted != normalized:
            normalized = self._title_case(converted)
            trace.append(f"Given name to nominative: '{token}' -> '{normalized}'")
            fallback = False

        analyzer_norm = self._analyzer_normalize(normalized, language)
        if analyzer_norm and analyzer_norm.lower() != normalized.lower():
            trace.append(f"Analyzer normalized given name '{normalized}' -> '{analyzer_norm}'")
            normalized = analyzer_norm
            fallback = False

        return normalized, fallback, trace

    def _normalize_surname(self, token: str, language: str, preserve_feminine_suffix_uk: bool = False) -> Tuple[str, bool, List[str]]:
        trace: List[str] = []
        normalized = convert_surname_to_nominative(token, language, preserve_feminine_suffix_uk)
        fallback = normalized.lower() == token.lower()
        if not fallback:
            normalized = self._title_case(normalized)
            if preserve_feminine_suffix_uk and language == "uk":
                trace.append(f"Ukrainian surname to nominative (preserving feminine suffix): '{token}' -> '{normalized}'")
            else:
                trace.append(f"Surname to nominative: '{token}' -> '{normalized}'")

        # Skip analyzer normalization for surnames to avoid corruption
        # Surnames are already properly normalized by convert_surname_to_nominative
        # analyzer_norm = self._analyzer_normalize(normalized, language)
        # if analyzer_norm and analyzer_norm.lower() != normalized.lower():
        #     trace.append(f"Analyzer normalized surname '{normalized}' -> '{analyzer_norm}'")
        #     normalized = analyzer_norm
        #     fallback = False

        return normalized, fallback, trace

    def _normalize_patronymic(self, token: str, language: str) -> Tuple[str, bool, List[str]]:
        trace: List[str] = []
        normalized = convert_patronymic_to_nominative(token, language)
        fallback = normalized.lower() == token.lower()
        if not fallback:
            normalized = self._title_case(normalized)
            trace.append(f"Patronymic to nominative: '{token}' -> '{normalized}'")

        analyzer_norm = self._analyzer_normalize(normalized, language)
        if analyzer_norm and analyzer_norm.lower() != normalized.lower():
            trace.append(f"Analyzer normalized patronymic '{normalized}' -> '{analyzer_norm}'")
            normalized = analyzer_norm
            fallback = False

        return normalized, fallback, trace

    def _analyzer_normalize(self, token: str, language: str) -> Optional[str]:
        analyzer = self._analyzers.get(language)
        if not analyzer or not token:
            return None

        try:
            if hasattr(analyzer, "analyze_name"):
                normalized = analyzer.analyze_name(token)
                if normalized:
                    return normalized

            morph = getattr(analyzer, "morph_analyzer", None)
            pick_best = getattr(analyzer, "pick_best_parse", None)
            if morph and pick_best:
                parses = morph.parse(token)
                if parses:
                    best = pick_best(parses)
                    if best and getattr(best, "normal_form", None):
                        normal_form = best.normal_form
                        if normal_form:
                            return self._title_case(normal_form)
        except Exception as exc:  # pragma: no cover - analyzer specific failures
            self.logger.debug("Analyzer normalization failed for '%s': %s", token, exc)

        return None

    def _title_case(self, token: str) -> str:
        if not token:
            return token
        return token[0].upper() + token[1:].lower()

    def clear_cache(self) -> None:
        self._cache.clear()
        self.logger.info("Morphology cache cleared")

