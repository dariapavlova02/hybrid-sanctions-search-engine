"""Unified wrapper around pymorphy analyzers for nominative enforcement."""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import List, Optional

from ....utils.logging_config import get_logger


@dataclass(frozen=True)
class MorphParse:
    """Lightweight representation of a morphology parse."""

    nominative_form: str
    normal_form: str
    score: float
    tag: str
    gender: Optional[str]
    case: Optional[str]


class MorphologyAdapter:
    """Cache-friendly adapter that exposes nominative and gender helpers."""

    def __init__(self) -> None:
        self._logger = get_logger(__name__)
        self._analyzers = {}
        for lang in ("ru", "uk"):
            self._initialise_analyzer(lang)

    def parse(self, token: str, lang: str) -> List[MorphParse]:
        """Return cached parses for ``token`` in the requested language."""
        if not token:
            return []
        normalized = unicodedata.normalize("NFKC", token)
        cached = self._parse_cached(normalized, lang)
        return [MorphParse(*entry) for entry in cached]

    def to_nominative(self, token: str, lang: str) -> str:
        """Convert ``token`` to nominative case when possible."""
        if not token:
            return token

        normalized = unicodedata.normalize("NFKC", token)
        parses = self.parse(normalized, lang)
        
        # Look for explicit nominative case first
        for morph in parses:
            if morph.case == "nomn" and morph.nominative_form:
                return _preserve_case(token, morph.nominative_form)
        
        # Fallback to any nominative form
        for morph in parses:
            candidate = morph.nominative_form or morph.normal_form
            if candidate:
                return _preserve_case(token, candidate)
        return token

    def detect_gender(self, token: str, lang: str) -> str:
        """Infer grammatical gender from the best parse."""
        parses = self.parse(token, lang)
        for morph in parses:
            gender = (morph.gender or "").lower()
            if gender in {"femn", "masc"}:
                return gender
        return "unknown"

    def clear_cache(self) -> None:
        """Clear cached parse entries (useful for tests)."""
        self._parse_cached.cache_clear()

    def _initialise_analyzer(self, lang: str) -> None:
        if lang in self._analyzers:
            return
        try:
            import pymorphy3

            self._analyzers[lang] = pymorphy3.MorphAnalyzer(lang=lang)
        except Exception as exc:  # pragma: no cover - optional dependency
            self._logger.warning("Morphology analyzer unavailable for %s: %s", lang, exc)
            self._analyzers[lang] = None

    def _get_analyzer(self, lang: str):
        analyzer = self._analyzers.get(lang)
        if analyzer is None and lang in {"ru", "uk"}:
            self._initialise_analyzer(lang)
            analyzer = self._analyzers.get(lang)
        return analyzer

    @lru_cache(maxsize=50_000)
    def _parse_cached(self, token: str, lang: str):
        analyzer = self._get_analyzer(lang)
        if not analyzer:
            return tuple()

        try:
            pymorph_parses = analyzer.parse(token)
        except Exception as exc:  # pragma: no cover - analyzer specific
            self._logger.debug("Morphology parse failed for '%s' (%s): %s", token, lang, exc)
            return tuple()

        results = []
        for parse_obj in pymorph_parses:
            try:
                inflected = parse_obj.inflect({"nomn"})
                nominative = inflected.word if inflected else parse_obj.normal_form
            except Exception:  # pragma: no cover - inflection edge cases
                nominative = parse_obj.normal_form

            tag = str(parse_obj.tag)
            gender = getattr(parse_obj.tag, "gender", None)
            case = getattr(parse_obj.tag, "case", None)
            score = getattr(parse_obj, "score", 0.0)

            results.append((
                nominative,
                parse_obj.normal_form,
                float(score) if score is not None else 0.0,
                tag,
                gender.lower() if isinstance(gender, str) else gender,
                case.lower() if isinstance(case, str) else case,
            ))

        return tuple(results)


def _preserve_case(source: str, target: str) -> str:
    if not target:
        return target
    if source.isupper():
        return target.upper()
    if source.istitle():
        return "-".join(part.capitalize() for part in target.split("-"))
    if source.islower():
        return target.lower()
    # Fallback: mirror first character casing
    first = target[0].upper() if source[0].isupper() else target[0].lower()
    return first + target[1:]


__all__ = ["MorphologyAdapter", "MorphParse"]
