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
from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING

from ...utils.logging_config import get_logger

if TYPE_CHECKING:
    from ...utils.lru_cache_ttl import LruTtlCache
    from ...utils.feature_flags import FeatureFlags


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

    def __init__(self, cache_size: int = 50000, cache: Optional[LruTtlCache] = None):
        """
        Initialize morphology adapter.
        
        Args:
            cache_size: Maximum number of cached parse results
            cache: Optional external cache instance
        """
        self._logger = get_logger(__name__)
        self._cache_size = cache_size
        self._lock = threading.RLock()
        self.cache = cache
        
        # Analyzers for each language
        self._analyzers: Dict[str, Any] = {}
        self._uk_available = False
        self._uk_declension_index: Optional[Dict[str, str]] = None
        
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
            
        normalized = unicodedata.normalize("NFC", token)
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
            
        normalized = unicodedata.normalize("NFC", token)
        return self._to_nominative_cached(normalized, lang)

    def to_nominative_cached(self, token: str, lang: str, flags: 'FeatureFlags', role: str = 'unknown') -> Tuple[str, str]:
        """
        Convert token to nominative case with caching and feature flags support.
        
        Args:
            token: Token to convert
            lang: Language code ('ru' or 'uk')
            flags: Feature flags object
            role: Token role (given, surname, patronymic, etc.)
            
        Returns:
            Tuple of (nominative_form, trace_note)
        """
        if not token or not token.strip() or lang not in {"ru", "uk"}:
            return token, "morph.nominal_noop"
        
        # Create cache key with flags
        cache_key = (
            lang, 
            token.lower(), 
            getattr(flags, 'enforce_nominative', True),
            getattr(flags, 'preserve_feminine_surnames', True)
        )

        # Check cache first
        if hasattr(self, '_to_nominative_cached_with_flags'):
            cached_result = self._to_nominative_cached_with_flags.get(cache_key)
            if cached_result is not None:
                return cached_result

        # Process token
        normalized = unicodedata.normalize("NFC", token)
        result, trace_note = self._to_nominative_uncached_with_flags(
            normalized, lang, flags, role
        )
        
        # Cache result
        if not hasattr(self, '_to_nominative_cached_with_flags'):
            self._to_nominative_cached_with_flags = {}
        self._to_nominative_cached_with_flags[cache_key] = (result, trace_note)
        
        return result, trace_note

    def detect_gender(self, token: str, lang: str) -> str:
        """
        Detect grammatical gender of token.
        
        Args:
            token: Token to analyze
            lang: Language code ('ru' or 'uk')
            
        Returns:
            Gender: 'masc', 'femn', or 'unknown'
        """
        if not token or not token.strip() or lang not in {"ru", "uk"}:
            return "unknown"
            
        normalized = unicodedata.normalize("NFC", token)
        return self._detect_gender_cached(normalized, lang)

    def apply_yo_strategy(self, token: str, strategy: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Apply Russian 'ё' strategy (preserve or fold).
        
        Args:
            token: Token to process
            strategy: 'preserve' or 'fold'
            
        Returns:
            Tuple of (processed_token, trace_entries)
        """
        if not token or strategy not in {"preserve", "fold"}:
            return token, []
        
        trace_entries = []
        
        if strategy == "fold":
            # Convert 'ё' to 'е' and 'Ё' to 'Е'
            if 'ё' in token or 'Ё' in token:
                original = token
                processed = token.replace('ё', 'е').replace('Ё', 'Е')
                trace_entries.append({
                    "type": "yo",
                    "action": "fold",
                    "from": original,
                    "to": processed
                })
                return processed, trace_entries
        
        # For "preserve" strategy, keep as is but add trace
        if 'ё' in token or 'Ё' in token:
            trace_entries.append({
                "type": "yo",
                "action": "preserve",
                "from": token,
                "to": token
            })
        
        return token, trace_entries

    def detect_patronymic(self, token: str, lang: str) -> bool:
        """
        Detect if a token is a patronymic based on suffix patterns.
        
        Args:
            token: Token to analyze
            lang: Language code ('ru' or 'uk')
            
        Returns:
            True if token appears to be a patronymic
        """
        if not token or lang not in {"ru", "uk"}:
            return False
        
        token_lower = token.lower()
        
        # Russian patronymic patterns
        if lang == "ru":
            patronymic_suffixes = {
                "ович", "евич", "йович", "ич",  # Masculine
                "овна", "евна", "ична",  # Feminine
                "овича", "евича", "йовича", "ича",  # Genitive masculine
                "івни", "овни", "евни", "ични",  # Genitive feminine
                "овичу", "евичу", "йовичу", "ичу",  # Dative masculine
                "овні", "евні", "ичні",  # Dative feminine
                "овичем", "евичем", "йовичем", "ичем",  # Instrumental masculine
                "овною", "евною", "ичною",  # Instrumental feminine
                "овиче", "евиче", "йовиче", "иче",  # Vocative masculine
                "овно", "евно", "ично"  # Vocative feminine
            }
            return any(token_lower.endswith(suffix) for suffix in patronymic_suffixes)
        
        # Ukrainian patronymic patterns
        elif lang == "uk":
            patronymic_suffixes = {
                "ович", "евич", "йович", "ич",  # Masculine
                "івна", "ївна", "овна", "евна", "ична",  # Feminine
                "овича", "евича", "йовича", "ича",  # Genitive masculine
                "івни", "ївни", "овни", "евни", "ични",  # Genitive feminine
                "овичу", "евичу", "йовичу", "ичу",  # Dative masculine
                "івні", "ївні", "овні", "евні", "ичні",  # Dative feminine
                "овичем", "евичем", "йовичем", "ичем",  # Instrumental masculine
                "івною", "ївною", "овною", "евною", "ичною",  # Instrumental feminine
                "овиче", "евиче", "йовиче", "иче",  # Vocative masculine
                "івно", "ївно", "овно", "евно", "ично"  # Vocative feminine
            }
            return any(token_lower.endswith(suffix) for suffix in patronymic_suffixes)
        
        return False

    def normalize_patronymic_to_nominative(self, token: str, lang: str) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Normalize a patronymic token to nominative case.
        
        Args:
            token: Patronymic token to normalize
            lang: Language code ('ru' or 'uk')
            
        Returns:
            Tuple of (normalized_token, trace_entries)
        """
        if not token or lang not in {"ru", "uk"}:
            return token, []
        
        trace_entries = []
        
        # First try morphological analysis
        try:
            if lang == "ru" and hasattr(self, '_analyzers') and 'ru' in self._analyzers:
                analyzer = self._analyzers['ru']
                parses = analyzer.parse(token)
                if parses:
                    # Find the best parse that looks like a patronymic
                    for parse in parses:
                        if 'Name' in parse.tag and ('Patr' in parse.tag or 'Abbr' in parse.tag):
                            nominative = parse.normal_form
                            if nominative != token:
                                trace_entries.append({
                                    "type": "patronymic_nominalized",
                                    "action": "morphology",
                                    "from": token,
                                    "to": nominative,
                                    "reason": "patronymic_nominalized"
                                })
                                return nominative, trace_entries
            
            elif lang == "uk" and hasattr(self, '_analyzers') and 'uk' in self._analyzers:
                analyzer = self._analyzers['uk']
                parses = analyzer.parse(token)
                if parses:
                    # Find the best parse that looks like a patronymic
                    for parse in parses:
                        if 'Name' in parse.tag and ('Patr' in parse.tag or 'Abbr' in parse.tag):
                            nominative = parse.normal_form
                            if nominative != token:
                                trace_entries.append({
                                    "type": "patronymic_nominalized",
                                    "action": "morphology",
                                    "from": token,
                                    "to": nominative,
                                    "reason": "patronymic_nominalized"
                                })
                                return nominative, trace_entries
        except Exception as e:
            # Fall back to rule-based normalization
            pass
        
        # Rule-based fallback for common patronymic patterns
        token_lower = token.lower()
        
        # Russian patterns
        if lang == "ru":
            if token_lower.endswith("овича"):
                nominative = token[:-1]  # овича -> ович
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("евича"):
                nominative = token[:-1]  # евича -> евич
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("овичу"):
                nominative = token[:-1]  # овичу -> ович
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("овны"):
                nominative = token[:-1] + "а"  # овны -> овна
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("овни"):
                nominative = token[:-1] + "а"  # овни -> овна
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("евни"):
                nominative = token[:-1] + "а"  # евни -> евна
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
        
        # Ukrainian patterns
        elif lang == "uk":
            if token_lower.endswith("овича"):
                nominative = token[:-1]  # овича -> ович
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("евича"):
                nominative = token[:-1]  # евича -> евич
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("івни"):
                nominative = token[:-1]  # івни -> івна
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
            elif token_lower.endswith("ївни"):
                nominative = token[:-1]  # ївни -> ївна
                trace_entries.append({
                    "type": "patronymic_nominalized",
                    "action": "rule_based",
                    "from": token,
                    "to": nominative,
                    "reason": "patronymic_nominalized"
                })
                return nominative, trace_entries
        
        # No normalization needed
        return token, trace_entries

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
    
    def get_stats(self) -> Dict[str, int]:
        """Get adapter statistics (alias for get_cache_stats)."""
        return self.get_cache_stats()

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

    def _is_mixed_script(self, token: str) -> bool:
        """Check if token contains characters from multiple scripts."""
        if not token or len(token) < 2:
            return False

        scripts = set()
        for char in token:
            if ord(char) < 128:  # ASCII
                scripts.add('Latin')
            elif '\u0400' <= char <= '\u04FF':  # Cyrillic
                scripts.add('Cyrillic')
            elif '\u0100' <= char <= '\u017F':  # Latin Extended-A (includes Turkish İ)
                scripts.add('Latin')
            elif char.isalpha():  # Other alphabetic scripts
                scripts.add('Other')

        return len(scripts) > 1

    def _apply_pre_canon_rules(self, token: str, lang: str, flags: 'FeatureFlags', role: str = 'unknown') -> str:
        """Apply pre-canonicalization rules: diminutive mapping and gender rules."""
        if lang not in {"ru", "uk"}:
            return token
        
        # Check if custom rules are enabled
        if not getattr(flags, 'morphology_custom_rules_first', True):
            return token
        
        # Load diminutive dictionaries if not already done
        if not hasattr(self, '_diminutive_dicts'):
            self._diminutive_dicts = {}
            try:
                import json
                from pathlib import Path
                
                # Load Russian diminutives
                ru_path = Path(__file__).resolve().parents[4] / "data" / "diminutives_ru.json"
                self._logger.debug(f"Loading Russian diminutives from: {ru_path}")
                with open(ru_path, 'r', encoding='utf-8') as f:
                    self._diminutive_dicts['ru'] = json.load(f)
                self._logger.debug(f"Loaded {len(self._diminutive_dicts['ru'])} Russian diminutives")
                if 'вика' in self._diminutive_dicts['ru']:
                    self._logger.debug(f"Found 'вика' -> '{self._diminutive_dicts['ru']['вика']}'")
                else:
                    self._logger.debug("'вика' not found in Russian diminutives")
                
                # Load Ukrainian diminutives
                uk_path = Path(__file__).resolve().parents[4] / "data" / "diminutives_uk.json"
                with open(uk_path, 'r', encoding='utf-8') as f:
                    self._diminutive_dicts['uk'] = json.load(f)
            except Exception as e:
                self._logger.debug(f"Failed to load diminutive dictionaries: {e}")
                return token
        
        # Step 1: Check diminutive dictionary for original token FIRST
        canonical = self._diminutive_dicts.get(lang, {}).get(token.lower())
        if canonical:
            self._logger.debug(f"Diminutive mapping: '{token}' -> '{canonical}'")
            return canonical
        
        # Step 2: Apply gender rules only for given names (for case-sensitive rules like "Вики" -> "Вика")
        if role == 'given':
            try:
                from .morphology.gender_rules import convert_given_name_to_nominative
                converted = convert_given_name_to_nominative(token, lang)
                self._logger.debug(f"Gender rules: '{token}' -> '{converted}'")
                if converted != token:
                    return converted
            except Exception as e:
                self._logger.debug(f"Gender rules failed for '{token}': {e}")
        
        return token

    def _to_nominative_uncached_with_flags(self, token: str, lang: str, flags: 'FeatureFlags', role: str = 'unknown') -> Tuple[str, str]:
        """Uncached nominative conversion with feature flags support."""
        # Check if nominative enforcement is disabled
        if not getattr(flags, 'enforce_nominative', True):
            return token, "morph.nominal_noop"

        # Skip morphology for mixed-script tokens to ensure idempotency
        # Mixed-script tokens (e.g., Turkish İ + Cyrillic) confuse morphological analysis
        if self._is_mixed_script(token):
            return token, "morph.nominal_noop"

        # PRE-CANON STEP: Apply our custom rules before pymorphy3
        canonical_base = self._apply_pre_canon_rules(token, lang, flags, role)
        self._logger.debug(f"Pre-canon: '{token}' -> '{canonical_base}'")
        if canonical_base != token:
            # If our rules changed the token, return it directly without pymorphy3
            # But preserve the case of the original token
            result = self._preserve_case(token, canonical_base)
            self._logger.debug(f"Returning canonical_base with preserved case: '{token}' -> '{canonical_base}' -> '{result}'")
            return result, "morph.pre_canon"
        else:
            base_token = token
            trace_note = None

        parses = self._parse_uncached(base_token, lang)
        if not parses:
            if lang == "uk":
                fallback = self._fallback_ukrainian_nominative(base_token)
                if fallback:
                    return fallback, trace_note or "morph.uk_fallback"
            return base_token, trace_note or "morph.nominal_noop"
        
        # Check for idempotency - if token is already in nominative case, don't change it
        best_parse = parses[0]
        self._logger.debug(f"Idempotency check: '{base_token}' -> normal='{best_parse.normal}', nominative='{best_parse.nominative}'")
        if best_parse.normal and best_parse.normal.lower() == base_token.lower():
            self._logger.debug(f"Idempotent: keeping '{base_token}' as is")
            return base_token, "morph.nominal_noop"

        if lang == "uk":
            preferred_parse = self._prefer_ukrainian_masculine_parse(base_token, parses)
            if preferred_parse and preferred_parse.nominative:
                result = self._preserve_case(base_token, preferred_parse.nominative)
                return result, trace_note or "morph.to_nominative"
        
        # Check for feminine/masculine surname preservation
        preserve_feminine = getattr(flags, 'preserve_feminine_surnames', True)

        # Special handling for surnames
        if role == "surname":
            # Check if this is already a proper surname form that should be preserved
            lower_token = base_token.lower()

            # Common Russian/Ukrainian masculine surname endings in nominative
            masculine_surname_endings = ('ов', 'ев', 'ин', 'ын', 'ич', 'енко', 'ский', 'цкий', 'ук', 'юк', 'ян', 'дзе')

            # If it looks like a masculine surname in nominative, preserve it
            if any(lower_token.endswith(ending) for ending in masculine_surname_endings):
                # Check if any parse recognizes it as a proper noun or if all parses are questionable
                has_proper_noun = any('Name' in str(parse.tag) for parse in parses)
                all_parses_are_common_noun = all(
                    'NOUN' in str(parse.tag) and 'inan' in str(parse.tag)
                    for parse in parses
                )

                # If it's likely a surname (no proper noun recognition but looks like surname),
                # or all parses treat it as inanimate noun (likely misclassification), preserve it
                if not has_proper_noun or all_parses_are_common_noun:
                    return base_token, "morph.preserve_surname"

            # Check for feminine surname preservation
            if preserve_feminine:
                # Check if this is already a nominative feminine form that should be preserved
                # Only preserve if it's singular nominative, not plural
                # TODO: Add context-aware gender checking to avoid preserving feminine forms for male names
                for parse in parses:
                    if parse.case == "nomn" and parse.gender == "femn":
                        # Check if it's singular by looking at the tag
                        if 'plur' not in parse.tag:
                            # For surnames that could have both masculine and feminine forms,
                            # don't auto-preserve the feminine form - let gender logic decide
                            if (lower_token.endswith(('ова', 'ева', 'ина', 'ская', 'цкая', 'ич', 'енко')) or
                                lower_token.endswith('ич') or lower_token.endswith('енко')):
                                # These endings are ambiguous, skip auto-preservation
                                continue
                            # This is already nominative feminine singular, preserve it
                            return base_token, trace_note or "morph.preserve_feminine"
        
        # Look for explicit nominative case first
        # If preservation is disabled, prefer masculine forms
        if not preserve_feminine:
            # Look for masculine forms first (any case)
            for parse in parses:
                if parse.gender == "masc" and parse.nominative:
                    result = self._preserve_case(base_token, parse.nominative)
                    return result, trace_note or "morph.to_nominative"
        
        # Look for best nominative form
        # Priority: 1) Non-plural nominative case, 2) Any nominative case, 3) Any parse with nominative form, 4) Normal form fallback
        best_parse = None
        
        # Prefer non-plural nominative case first
        for parse in parses:
            if parse.case == "nomn" and parse.nominative and 'plur' not in parse.tag:
                best_parse = parse
                break

        # Second priority: any nominative case (but skip plural for names)
        if not best_parse:
            for parse in parses:
                if parse.case == "nomn" and parse.nominative and 'plur' not in parse.tag:
                    best_parse = parse
                    break

        # Third priority: any parse with nominative form (prefer non-plural, prefer feminine for given names only)
        if not best_parse:
            # For given names, prefer feminine forms; for surnames, prefer masculine forms
            if role == 'given':
                # First try to find feminine forms (for given names)
                for parse in parses:
                    if parse.nominative and 'plur' not in parse.tag and parse.gender == "femn":
                        best_parse = parse
                        break
                # If no feminine found, try any non-plural
                if not best_parse:
                    for parse in parses:
                        if parse.nominative and 'plur' not in parse.tag:
                            best_parse = parse
                            break
            else:
                # For surnames and other roles, prefer masculine forms
                for parse in parses:
                    if parse.nominative and 'plur' not in parse.tag and parse.gender == "masc":
                        best_parse = parse
                        break
                # If no masculine found, try any non-plural
                if not best_parse:
                    for parse in parses:
                        if parse.nominative and 'plur' not in parse.tag:
                            best_parse = parse
                            break

        # Fourth priority: any parse with nominative form
        if not best_parse:
            for parse in parses:
                if parse.nominative:
                    best_parse = parse
                    break

        # Use the best parse found
        if best_parse:
            result = self._preserve_case(base_token, best_parse.nominative)
            # Check diminutive dictionary after pymorphy3
            diminutive_result = self._check_diminutive_dict(result, lang)
            if diminutive_result != result:
                result = self._preserve_case(base_token, diminutive_result)
                return result, trace_note or "morph.to_nominative_diminutive"
            return result, trace_note or "morph.to_nominative"
        
        # Fallback to normal form if no nominative found
        for parse in parses:
            if parse.normal:
                result = self._preserve_case(base_token, parse.normal)
                # Check diminutive dictionary after pymorphy3
                diminutive_result = self._check_diminutive_dict(result, lang)
                if diminutive_result != result:
                    result = self._preserve_case(base_token, diminutive_result)
                    return result, trace_note or "morph.to_nominative_diminutive"
                return result, trace_note or "morph.to_nominative"
        
        return base_token, trace_note or "morph.nominal_noop"

    def _check_diminutive_dict(self, token: str, lang: str) -> str:
        """Check if token exists in diminutive dictionary and return canonical form."""
        if not hasattr(self, '_diminutive_dicts'):
            self._load_diminutive_dicts()
        
        lang_dict = self._diminutive_dicts.get(lang, {})
        canonical = lang_dict.get(token.lower())
        if canonical:
            self._logger.debug(f"Diminutive dict: '{token}' -> '{canonical}'")
            return canonical
        return token

    def _prefer_ukrainian_masculine_parse(self, base_token: str, parses: List[MorphParse]) -> Optional[MorphParse]:
        """Prefer masculine nominative form for Ukrainian declensions when available."""
        base_lower = base_token.lower()
        candidates: List[Tuple[int, MorphParse]] = []

        for parse in parses:
            if not parse.nominative:
                continue
            if parse.nominative.lower() == base_lower:
                continue
            if parse.gender != "masc":
                continue

            tag_lower = parse.tag.lower()
            if not any(marker in tag_lower for marker in ("name", "surn", "patr")):
                continue
            if 'plur' in tag_lower:
                continue

            priority = 1
            if parse.case == "nomn":
                priority = 3
            elif parse.case in {"gent", "accs", "datv"}:
                priority = 2

            candidates.append((priority, parse))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        return candidates[0][1]

    def _fallback_ukrainian_nominative(self, token: str) -> Optional[str]:
        """Fallback to dictionary-based Ukrainian declension lookup."""
        if not token:
            return None

        index = self._get_uk_declension_index()
        if not index:
            return None

        canonical = index.get(token.lower())
        if canonical:
            return self._preserve_case(token, canonical)
        return None

    def _get_uk_declension_index(self) -> Dict[str, str]:
        if self._uk_declension_index is None:
            self._uk_declension_index = self._build_uk_declension_index()
        return self._uk_declension_index

    @staticmethod
    def _build_uk_declension_index() -> Dict[str, str]:
        try:
            from ...data.dicts.ukrainian_names import UKRAINIAN_NAMES
        except ImportError:
            return {}

        index: Dict[str, str] = {}
        for nominative, data in UKRAINIAN_NAMES.items():
            canonical = nominative
            index[nominative.lower()] = canonical
            for form in data.get('declensions', []) or []:
                index[form.lower()] = canonical
            for variant in data.get('variants', []) or []:
                index[variant.lower()] = canonical
            for diminutive in data.get('diminutives', []) or []:
                index[diminutive.lower()] = canonical

        return index

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


    async def normalize_slavic_token(
        self,
        token: str,
        role: Optional[str],
        language: str,
        enable_morphology: bool = True,
        preserve_feminine_suffix_uk: bool = False,
        feature_flags: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]]]:
        """
        Normalize a Slavic token using morphology.
        
        Args:
            token: Token to normalize
            role: Token role (given, surname, patronymic, etc.)
            language: Language code (ru/uk)
            enable_morphology: Whether to use morphological analysis
            preserve_feminine_suffix_uk: Whether to preserve feminine suffixes in Ukrainian
            feature_flags: Additional feature flags
            
        Returns:
            Tuple of (normalized_token, trace_info)
        """
        if not enable_morphology or not token.strip():
            return token, []
        
        try:
            # Parse the token
            parses = self.parse(token, language)
            if not parses:
                return token, []
            
            # Get the best parse
            best_parse = parses[0]
            
            # Get nominative form
            nominative = self.to_nominative(token, language)
            if nominative:
                return nominative, [{"rule": "morphology", "normal_form": nominative}]
            
            return token, []
            
        except Exception as e:
            self._logger.debug(f"Morphological normalization failed for '{token}': {e}")
            return token, []


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
