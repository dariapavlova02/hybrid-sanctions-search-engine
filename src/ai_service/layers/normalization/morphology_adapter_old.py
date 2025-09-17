"""
Unified morphology adapter with caching and UK dictionary support.

This module provides a centralized interface for morphological analysis
using pymorphy3 with proper caching and fallback behavior for Ukrainian.
"""

from __future__ import annotations

import threading
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, Any

from ...utils.logging_config import get_logger


@dataclass(frozen=True)
class MorphParse:
    """Lightweight representation of a morphology parse."""

    normal: str
    tag: str
    score: float
    case: Optional[str] = None
    gender: Optional[str] = None
    nominative: Optional[str] = None


class MorphologyAdapter:
    """
    Thread-safe morphology adapter with LRU caching and UK dictionary support.
    
    Features:
    - LRU caching for parse results (configurable size)
    - Thread-safe operations
    - Fallback behavior for missing UK dictionary
    - Warmup functionality for common names
    - Graceful degradation when pymorphy3 is unavailable
    """

    def __init__(self, cache_size: int = 50000):
        """
        Initialize morphology adapter.
        
        Args:
            cache_size: Maximum number of cached parse results
        """
        self._logger = get_logger(__name__)
        self._cache_size = cache_size
        self._lock = threading.RLock()
        
        # Analyzers for each language
        self._analyzers: Dict[str, Any] = {}
        self._uk_available = False
        
        # Initialize analyzers
        self._initialize_analyzers()
        
        # Create cached methods
        self._parse_cached = lru_cache(maxsize=cache_size)(self._parse_uncached)
        self._to_nominative_cached = lru_cache(maxsize=cache_size)(self._to_nominative_uncached)
        self._detect_gender_cached = lru_cache(maxsize=cache_size)(self._detect_gender_uncached)

    def parse(self, token: str, lang: str) -> List[MorphParse]:
        """
        Parse token and return morphological analysis results.
        
        Args:
            token: Token to analyze
            lang: Language code ('ru' or 'uk')
            
        Returns:
            List of morphological parse results
        """
        if not token or not token.strip() or lang not in {"ru", "uk"}:
            return []
            
        normalized = unicodedata.normalize("NFKC", token)
        return self._parse_cached(normalized, lang)

    def to_nominative(self, token: str, lang: str) -> str:
        """
        Convert token to nominative case.
        
        Args:
            token: Token to convert
            lang: Language code ('ru' or 'uk')
            
        Returns:
            Nominative form of the token
        """
        if not token or not token.strip() or lang not in {"ru", "uk"}:
            return token
            
        normalized = unicodedata.normalize("NFKC", token)
        return self._to_nominative_cached(normalized, lang)

    def detect_gender(self, token: str, lang: str) -> str:
        """
        Detect grammatical gender of token.
        
        Args:
            token: Token to analyze
            lang: Language code ('ru' or 'uk')
            
        Returns:
            Gender: 'masc', 'femn', or 'unknown'
        """
        if not token or lang not in {"ru", "uk"}:
            return "unknown"
            
        normalized = unicodedata.normalize("NFKC", token)
        return self._detect_gender_cached(normalized, lang)

    def warmup(self, samples: List[Tuple[str, str]] = None) -> None:
        """
        Warm up cache with common names and surnames.
        
        Args:
            samples: List of (token, language) tuples to pre-cache. If None, uses default samples.
        """
        if samples is None:
            samples = []
        
        self._logger.info(f"Warming up morphology cache with {len(samples)} samples")
        
        for token, lang in samples:
            if token and lang in {"ru", "uk"}:
                try:
                    # Pre-cache parse results
                    self.parse(token, lang)
                    # Pre-cache nominative forms
                    self.to_nominative(token, lang)
                    # Pre-cache gender detection
                    self.detect_gender(token, lang)
                except Exception as e:
                    self._logger.debug(f"Warmup failed for {token} ({lang}): {e}")
        
        self._logger.info("Morphology cache warmup completed")
    
    def clear_cache(self) -> None:
        """Clear all cached results (useful for testing)."""
        with self._lock:
            self._parse_cached.cache_clear()
            self._to_nominative_cached.cache_clear()
            self._detect_gender_cached.cache_clear()
        self._logger.info("Morphology cache cleared")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "parse_cache_size": self._parse_cached.cache_info().currsize,
            "parse_cache_hits": self._parse_cached.cache_info().hits,
            "parse_cache_misses": self._parse_cached.cache_info().misses,
            "nominative_cache_size": self._to_nominative_cached.cache_info().currsize,
            "gender_cache_size": self._detect_gender_cached.cache_info().currsize,
        }

    def is_uk_available(self) -> bool:
        """Check if Ukrainian dictionary is available."""
        return self._uk_available

    def _initialize_analyzers(self) -> None:
        """Initialize pymorphy3 analyzers for supported languages."""
        # Initialize Russian analyzer
        self._analyzers["ru"] = self._create_analyzer("ru")
        
        # Initialize Ukrainian analyzer with fallback
        self._analyzers["uk"] = self._create_analyzer("uk")
        
        if not self._uk_available:
            self._logger.warning(
                "Ukrainian dictionary not available. Ukrainian morphology will use fallback behavior."
            )

    def _create_analyzer(self, lang: str) -> Optional[Any]:
        """Create pymorphy3 analyzer for given language."""
        try:
            import pymorphy3
            
            if lang == "uk":
                # Try to use Ukrainian dictionary
                try:
                    analyzer = pymorphy3.MorphAnalyzer(lang="uk")
                    self._uk_available = True
                    self._logger.info("Ukrainian dictionary loaded successfully")
                    return analyzer
                except Exception as e:
                    self._logger.warning(f"Failed to load Ukrainian dictionary: {e}")
                    # Fallback to Russian analyzer for Ukrainian
                    analyzer = pymorphy3.MorphAnalyzer(lang="ru")
                    self._uk_available = False
                    return analyzer
            else:
                # Russian analyzer
                analyzer = pymorphy3.MorphAnalyzer(lang=lang)
                return analyzer
                
        except ImportError:
            self._logger.error("pymorphy3 not available. Morphology features disabled.")
            return None
        except Exception as e:
            self._logger.error(f"Failed to initialize {lang} analyzer: {e}")
            return None

    def _get_analyzer(self, lang: str) -> Optional[Any]:
        """Get analyzer for language with thread safety."""
        with self._lock:
            return self._analyzers.get(lang)

    def _parse_uncached(self, token: str, lang: str) -> List[MorphParse]:
        """Uncached parse implementation."""
        analyzer = self._get_analyzer(lang)
        if not analyzer:
            return []

        try:
            pymorph_parses = analyzer.parse(token)
        except Exception as e:
            self._logger.debug(f"Parse failed for '{token}' ({lang}): {e}")
            return []

        results = []
        for parse_obj in pymorph_parses:
            try:
                # Get nominative form
                nominative = None
                try:
                    inflected = parse_obj.inflect({"nomn"})
                    nominative = inflected.word if inflected else parse_obj.normal_form
                except Exception:
                    nominative = parse_obj.normal_form

                # Extract tag information
                tag = str(parse_obj.tag)
                gender = getattr(parse_obj.tag, "gender", None)
                case = getattr(parse_obj.tag, "case", None)
                score = getattr(parse_obj, "score", 0.0)

                # Normalize gender and case
                gender = gender.lower() if isinstance(gender, str) else None
                case = case.lower() if isinstance(case, str) else None

                results.append(MorphParse(
                    normal=parse_obj.normal_form,
                    tag=tag,
                    score=float(score) if score is not None else 0.0,
                    case=case,
                    gender=gender,
                    nominative=nominative
                ))

            except Exception as e:
                self._logger.debug(f"Failed to process parse for '{token}': {e}")
                continue

        return results

    def _to_nominative_uncached(self, token: str, lang: str) -> str:
        """Uncached nominative conversion."""
        parses = self._parse_uncached(token, lang)
        
        # Look for explicit nominative case first
        for parse in parses:
            if parse.case == "nomn" and parse.nominative:
                return self._preserve_case(token, parse.nominative)
        
        # Fallback to any nominative form
        for parse in parses:
            if parse.nominative:
                return self._preserve_case(token, parse.nominative)
        
        # Fallback to normal form
        for parse in parses:
            if parse.normal:
                return self._preserve_case(token, parse.normal)
        
        return token

    def _detect_gender_uncached(self, token: str, lang: str) -> str:
        """Uncached gender detection."""
        parses = self._parse_uncached(token, lang)
        
        # Find best parse by score
        best_parse = self._best_parse(parses)
        if best_parse and best_parse.gender in {"masc", "femn"}:
            return best_parse.gender
        
        return "unknown"

    def _best_parse(self, parses: List[MorphParse]) -> Optional[MorphParse]:
        """
        Select best parse from list based on score and priority rules.
        
        Args:
            parses: List of morphological parses
            
        Returns:
            Best parse or None if empty list
        """
        if not parses:
            return None
        
        # Sort by score (descending) and prefer proper nouns
        def parse_priority(parse: MorphParse) -> Tuple[float, bool]:
            # Higher score is better
            score = parse.score
            
            # Prefer proper nouns (names) - check if tag contains proper noun indicators
            is_proper = any(indicator in parse.tag.lower() for indicator in [
                "name", "surn", "patr", "geox", "org"
            ])
            
            return (score, is_proper)
        
        return max(parses, key=parse_priority)

    @staticmethod
    def _preserve_case(source: str, target: str) -> str:
        """Preserve case pattern from source to target."""
        if not target:
            return target
        
        if source.isupper():
            return target.upper()
        elif source.istitle():
            return "-".join(part.capitalize() for part in target.split("-"))
        elif source.islower():
            return target.lower()
        else:
            # Mixed case: preserve first character casing
            first = target[0].upper() if source[0].isupper() else target[0].lower()
            return first + target[1:]


# Global adapter instance for sharing across requests
_global_adapter: Optional[MorphologyAdapter] = None
_adapter_lock = threading.Lock()


def get_global_adapter(cache_size: int = 50000) -> MorphologyAdapter:
    """Get global morphology adapter instance."""
    global _global_adapter
    
    if _global_adapter is None:
        with _adapter_lock:
            if _global_adapter is None:
                _global_adapter = MorphologyAdapter(cache_size)
    else:
        # If adapter exists but with different cache size, recreate it
        if _global_adapter._cache_size != cache_size:
            with _adapter_lock:
                if _global_adapter._cache_size != cache_size:
                    _global_adapter = MorphologyAdapter(cache_size)
    
    return _global_adapter


def clear_global_cache() -> None:
    """Clear global adapter cache."""
    global _global_adapter
    if _global_adapter:
        _global_adapter.clear_cache()


__all__ = ["MorphologyAdapter", "MorphParse", "get_global_adapter", "clear_global_cache"]