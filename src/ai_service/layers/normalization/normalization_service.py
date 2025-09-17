#!/usr/bin/env python3
"""
Text normalization service - thin facade over NormalizationFactory.

This module provides a clean interface for normalizing person names
from Ukrainian, Russian, and English texts. The heavy lifting is done
by the NormalizationFactory and its processors.
"""

import json
import time
import unicodedata
from pathlib import Path
from typing import Dict, Optional, Set, List, Tuple

from ...config import LANGUAGE_CONFIG
from ...contracts.base_contracts import NormalizationResult
from ...data.patterns.identifiers import (
    get_validation_function,
    normalize_identifier,
)
from ...utils.logging_config import get_logger
from ...utils.feature_flags import get_feature_flag_manager, FeatureFlags
from ..language.language_detection_service import LanguageDetectionService
from ..unicode.unicode_service import UnicodeService
from .morphology.gender_rules import prefer_feminine_form
from .morphology_adapter import MorphologyAdapter, get_global_adapter
from .processors.normalization_factory import NormalizationFactory, NormalizationConfig
from .lexicon_loader import get_lexicons
from .role_tagger import RoleTagger, TokenRole

# Check for optional dependencies
try:
    from ...data.dicts import russian_names, ukrainian_names
    DICTIONARIES_AVAILABLE = True
except ImportError:  # pragma: no cover - optional heavy dependency
    DICTIONARIES_AVAILABLE = False
    russian_names = None  # type: ignore
    ukrainian_names = None  # type: ignore


class NormalizationService:
    """
    Thin facade for name normalization.

    Responsibilities:
    - Input validation and sanitization
    - Language detection
    - Configuration management
    - Factory orchestration
    - Statistics aggregation
    """

    def __init__(self):
        """Initialize normalization service with minimal dependencies."""
        self.logger = get_logger(__name__)

        # Feature flag manager
        self.feature_flags = get_feature_flag_manager()

        # Core services
        self.language_service = LanguageDetectionService()
        self.unicode_service = UnicodeService()
        # Use global adapter for better caching across requests
        self.morphology_adapter = get_global_adapter()

        # Load resources for factory
        name_dictionaries = self._load_name_dictionaries()
        diminutive_maps = self._load_diminutive_maps()

        # Initialize the processor factory
        self.normalization_factory = NormalizationFactory(
            name_dictionaries,
            diminutive_maps,
        )

        # Initialize role tagger for stopword and organization filtering
        lexicons = get_lexicons()
        self.role_tagger = RoleTagger(window=3)

        # Initialize legacy service for fallback
        self._legacy_service = None

        # Statistics tracking
        self._stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'avg_processing_time': 0.0,
            'languages_detected': {'ru': 0, 'uk': 0, 'en': 0, 'unknown': 0},
            'implementation_usage': {'factory': 0, 'legacy': 0, 'dual': 0}
        }

        self.logger.info("NormalizationService initialized as thin facade with feature flags")

    def _to_title(self, word: str) -> str:
        """
        Convert word to title case while preserving apostrophes and hyphens.
        
        Args:
            word: Input word to convert
            
        Returns:
            Word in title case (first letter uppercase, rest lowercase)
        """
        if not word:
            return word
        
        # Handle hyphenated words - apply titlecase to each segment
        if '-' in word:
            segments = word.split('-')
            return '-'.join(self._to_title(segment) for segment in segments)
        
        # Handle single word - first letter uppercase, rest lowercase
        if len(word) == 1:
            return word.upper()
        
        # Handle apostrophes - capitalize letter after apostrophe
        result = word[0].upper()
        i = 1
        while i < len(word):
            if word[i] == "'" and i + 1 < len(word):
                result += "'" + word[i + 1].upper()
                i += 2
            else:
                result += word[i].lower()
                i += 1
        
        return result

    def _apply_role_filtering(self, text: str, language: str, feature_flags: Optional[FeatureFlags] = None) -> Tuple[str, List[Dict]]:
        """
        Apply role-based filtering to remove stopwords and organizations.
        
        Args:
            text: Input text
            language: Language code
            feature_flags: Feature flags for configuration
            
        Returns:
            Tuple of (filtered_text, trace_entries)
        """
        # Simple tokenization for role tagging
        import re
        tokens = re.findall(r'\S+', text)
        
        if not tokens:
            return text, []
        
        # Tag tokens with roles
        role_tags = self.role_tagger.tag(tokens, language)
        
        # Get person candidates (exclude stopwords and organizations)
        person_candidates = self.role_tagger.get_person_candidates(role_tags)
        
        # Get organization spans for trace
        org_spans = self.role_tagger.get_organization_spans(role_tags)
        
        # Count filtered tokens
        stopword_count = self.role_tagger.get_stopword_count(role_tags)
        org_count = self.role_tagger.get_organization_count(role_tags)
        
        # Build trace entries
        trace_entries = []
        
        if stopword_count > 0:
            trace_entries.append({
                "type": "role",
                "action": "stopword_filtered",
                "count": stopword_count
            })
        
        for start_idx, end_idx, span_text in org_spans:
            trace_entries.append({
                "type": "role",
                "action": "org_span",
                "form": tokens[start_idx] if start_idx < len(tokens) else "",
                "span": span_text
            })
        
        # If strict_stopwords is enabled, filter out stopwords and organizations
        if feature_flags and feature_flags.strict_stopwords:
            filtered_tokens = person_candidates
            filtered_text = " ".join(filtered_tokens)
        else:
            # Keep all tokens but mark roles in trace
            filtered_text = text
        
        return filtered_text, trace_entries

    async def normalize_async(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        user_id: Optional[str] = None,
        request_context: Optional[Dict] = None,
        # Ukrainian-specific flags
        strict_stopwords: bool = False,
        preserve_feminine_suffix_uk: bool = False,
        enable_spacy_uk_ner: bool = False,
        # English-specific flags
        en_use_nameparser: bool = True,
        enable_en_nickname_expansion: bool = True,
        enable_spacy_en_ner: bool = False,
        # Russian-specific flags
        ru_yo_strategy: str = "preserve",
        enable_ru_nickname_expansion: bool = True,
        enable_spacy_ru_ner: bool = False,
        # Feature flags for safe rollout
        feature_flags: Optional[FeatureFlags] = None,
    ) -> NormalizationResult:
        """
        Async normalization entrypoint.

        Args:
            text: Input text to normalize
            language: Language code or 'auto' for detection
            remove_stop_words: Remove stop words during tokenization
            preserve_names: Preserve name-specific punctuation
            enable_advanced_features: Enable morphology and advanced processing
            user_id: User ID for consistent feature flag rollout
            request_context: Additional context for implementation selection
            strict_stopwords: Use strict stopword filtering for initials (Ukrainian)
            preserve_feminine_suffix_uk: Preserve Ukrainian feminine suffixes (-ська/-цька)
            enable_spacy_uk_ner: Enable spaCy Ukrainian NER
            en_use_nameparser: Use nameparser for English names
            enable_en_nickname_expansion: Expand English nicknames
            enable_spacy_en_ner: Enable spaCy English NER
            ru_yo_strategy: Russian 'ё' policy ('preserve' or 'fold')
            enable_ru_nickname_expansion: Expand Russian nicknames
            enable_spacy_ru_ner: Enable spaCy Russian NER

        Returns:
            NormalizationResult with normalized text and metadata
        """
        start_time = time.time()
        self._stats['total_requests'] += 1

        try:
            # Input validation
            validation_result = self._validate_input(text)
            if validation_result:
                self._stats['failed_requests'] += 1
                return validation_result

            # Language detection
            detected_language = self._detect_language(text, language)
            self._stats['languages_detected'][detected_language] += 1

            # Use passed feature flags or fall back to global flags
            effective_flags = feature_flags or self.feature_flags._flags
            
            # Apply role-based filtering (stopwords and organizations)
            filtered_text, role_trace_entries = self._apply_role_filtering(text, detected_language, effective_flags)
            
            # Determine implementation based on feature flags
            use_factory = effective_flags.use_factory_normalizer or self.feature_flags.should_use_factory(
                language=detected_language,
                user_id=user_id,
                request_context=request_context
            )

            monitoring_config = self.feature_flags.get_monitoring_config()

            # Log implementation choice if enabled
            if monitoring_config['log_implementation_choice']:
                self.logger.info(f"Using {'factory' if use_factory else 'legacy'} implementation for language={detected_language}")

            # Dual processing mode for comparison
            if monitoring_config['enable_dual_processing']:
                result = await self._dual_process(
                    filtered_text, detected_language, remove_stop_words,
                    preserve_names, enable_advanced_features,
                    strict_stopwords, preserve_feminine_suffix_uk, enable_spacy_uk_ner,
                    en_use_nameparser, enable_en_nickname_expansion, enable_spacy_en_ner,
                    ru_yo_strategy, enable_ru_nickname_expansion, enable_spacy_ru_ner,
                    effective_flags
                )
                self._stats['implementation_usage']['dual'] += 1
            elif use_factory:
                result = await self._process_with_factory(
                    filtered_text, detected_language, remove_stop_words,
                    preserve_names, enable_advanced_features,
                    strict_stopwords, preserve_feminine_suffix_uk, enable_spacy_uk_ner,
                    en_use_nameparser, enable_en_nickname_expansion, enable_spacy_en_ner,
                    ru_yo_strategy, enable_ru_nickname_expansion, enable_spacy_ru_ner,
                    effective_flags
                )
                self._stats['implementation_usage']['factory'] += 1
            else:
                result = await self._process_with_legacy(
                    filtered_text, detected_language, remove_stop_words,
                    preserve_names, enable_advanced_features,
                    effective_flags
                )
                self._stats['implementation_usage']['legacy'] += 1

            # Add role filtering trace entries to result
            if role_trace_entries and hasattr(result, 'trace') and result.trace:
                result.trace.extend(role_trace_entries)
            elif role_trace_entries:
                result.trace = role_trace_entries

            # Update statistics
            processing_time = time.time() - start_time
            self._update_stats(processing_time, success=result.success)

            return result

        except Exception as e:
            self.logger.error(f"Normalization failed: {e}")
            processing_time = time.time() - start_time
            self._update_stats(processing_time, success=False)
            self._stats['failed_requests'] += 1

            return NormalizationResult(
                normalized="",
                tokens=[],
                trace=[],
                errors=[str(e)],
                language=language or "unknown",
                confidence=0.0,
                original_length=len(text),
                normalized_length=0,
                token_count=0,
                processing_time=processing_time,
                success=False,
                original_text=text,
                token_variants={},
                total_variants=0,
                persons_core=[],
                organizations_core=[],
                persons=[],
            )

    def normalize_sync(
        self,
        text: str,
        *,
        language: Optional[str] = None,
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        strict_stopwords: bool = False,
        preserve_feminine_suffix_uk: bool = False,
        enable_spacy_uk_ner: bool = False,
    ) -> NormalizationResult:
        """
        Synchronous normalization entrypoint.

        This is a convenience wrapper that runs the async implementation
        in a new event loop if needed.
        """
        import asyncio

        try:
            # Try to get current event loop
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If loop is running, we need to use run_in_executor
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.normalize_async(
                        text,
                        language=language,
                        remove_stop_words=remove_stop_words,
                        preserve_names=preserve_names,
                        enable_advanced_features=enable_advanced_features,
                        strict_stopwords=strict_stopwords,
                        preserve_feminine_suffix_uk=preserve_feminine_suffix_uk,
                        enable_spacy_uk_ner=enable_spacy_uk_ner,
                    ))
                    return future.result()
            else:
                # No running loop, we can use asyncio.run
                return asyncio.run(self.normalize_async(
                    text,
                    language=language,
                    remove_stop_words=remove_stop_words,
                    preserve_names=preserve_names,
                    enable_advanced_features=enable_advanced_features,
                    strict_stopwords=strict_stopwords,
                    preserve_feminine_suffix_uk=preserve_feminine_suffix_uk,
                    enable_spacy_uk_ner=enable_spacy_uk_ner,
                ))
        except RuntimeError:
            # No event loop, create one
            return asyncio.run(self.normalize_async(
                text,
                language=language,
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names,
                enable_advanced_features=enable_advanced_features,
                strict_stopwords=strict_stopwords,
                preserve_feminine_suffix_uk=preserve_feminine_suffix_uk,
                enable_spacy_uk_ner=enable_spacy_uk_ner,
            ))

    def normalize(
        self,
        text: str,
        language: Optional[str] = None,
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        strict_stopwords: bool = False,
        preserve_feminine_suffix_uk: bool = False,
        enable_spacy_uk_ner: bool = False,
    ) -> NormalizationResult:
        """Legacy compatibility method."""
        return self.normalize_sync(
            text,
            language=language,
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            enable_advanced_features=enable_advanced_features,
            strict_stopwords=strict_stopwords,
            preserve_feminine_suffix_uk=preserve_feminine_suffix_uk,
            enable_spacy_uk_ner=enable_spacy_uk_ner,
        )

    def validate_identifier(self, identifier: str, identifier_type: str) -> bool:
        """Validate identifier value using checksum-aware validators."""
        validator = get_validation_function(identifier_type)
        if validator is None:
            raise ValueError(f"Unsupported identifier type: {identifier_type}")

        normalized_value = normalize_identifier(identifier, identifier_type)
        if not normalized_value:
            return False

        return validator(normalized_value)

    def _validate_input(self, text: str) -> Optional[NormalizationResult]:
        """Validate input text and return error result if invalid."""
        if not isinstance(text, str):
            return NormalizationResult(
                normalized="",
                tokens=[],
                trace=[],
                errors=["Input must be a string"],
                language="unknown",
                confidence=0.0,
                original_length=0,
                normalized_length=0,
                token_count=0,
                processing_time=0.0,
                success=False,
                original_text=str(text),
                token_variants={},
                total_variants=0,
                persons_core=[],
                organizations_core=[],
                persons=[],
            )

        if len(text) > 10000:
            return NormalizationResult(
                normalized="",
                tokens=[],
                trace=[],
                errors=[f"Input too long: {len(text)} characters (max 10,000)"],
                language="unknown",
                confidence=0.0,
                original_length=len(text),
                normalized_length=0,
                token_count=0,
                processing_time=0.0,
                success=False,
                original_text=text,
                token_variants={},
                total_variants=0,
                persons_core=[],
                organizations_core=[],
                persons=[],
            )

        try:
            unicodedata.normalize("NFC", text)
        except Exception as e:
            return NormalizationResult(
                normalized="",
                tokens=[],
                trace=[],
                errors=[f"Invalid Unicode input: {e}"],
                language="unknown",
                confidence=0.0,
                original_length=len(text),
                normalized_length=0,
                token_count=0,
                processing_time=0.0,
                success=False,
                original_text=text,
                token_variants={},
                total_variants=0,
                persons_core=[],
                organizations_core=[],
                persons=[],
            )

        return None  # Valid input

    def _detect_language(self, text: str, language: Optional[str]) -> str:
        """Detect language or use provided language."""
        if language and language != "auto":
            return language

        try:
            lang_result = self.language_service.detect_language_config_driven(text, LANGUAGE_CONFIG)
            return lang_result.language
        except Exception as e:
            self.logger.warning(f"Language detection failed: {e}")
            return "ru"  # Default fallback

    def _update_stats(self, processing_time: float, success: bool):
        """Update processing statistics."""
        if success:
            self._stats['successful_requests'] += 1
        else:
            self._stats['failed_requests'] += 1

        # Update average processing time
        total = self._stats['total_requests']
        current_avg = self._stats['avg_processing_time']
        self._stats['avg_processing_time'] = (current_avg * (total - 1) + processing_time) / total

    def get_statistics(self) -> Dict:
        """Get service statistics."""
        return {
            **self._stats,
            'factory_stats': self.normalization_factory.get_statistics()
        }

    def clear_caches(self):
        """Clear all caches."""
        self.normalization_factory.clear_caches()
        self.morphology_adapter.clear_cache()
        self.logger.info("All caches cleared")

    def warmup_morphology_cache(self, samples: List[Tuple[str, str]] = None):
        """
        Warm up morphology cache with common names.
        
        Args:
            samples: List of (token, language) tuples. If None, uses default samples.
        """
        if samples is None:
            # Default common names for warmup
            samples = [
                # Russian names
                ("Анна", "ru"), ("Мария", "ru"), ("Иван", "ru"), ("Сергей", "ru"),
                ("Иванова", "ru"), ("Петрова", "ru"), ("Сидоров", "ru"), ("Кузнецов", "ru"),
                # Ukrainian names
                ("Олена", "uk"), ("Ірина", "uk"), ("Марія", "uk"), ("Іван", "uk"),
                ("Ковальська", "uk"), ("Шевченко", "uk"), ("Петренко", "uk"), ("Кравцівська", "uk"),
            ]
        
        self.morphology_adapter.warmup(samples)
        self.logger.info(f"Morphology cache warmed up with {len(samples)} samples")

    def _load_name_dictionaries(self) -> Dict[str, Set[str]]:
        """Load name dictionaries for processors."""
        dictionaries = {}

        if DICTIONARIES_AVAILABLE:
            try:
                # Load Russian names
                if hasattr(russian_names, 'RUSSIAN_NAMES'):
                    # Extract given names from RUSSIAN_NAMES
                    given_names = set()
                    surnames = set()
                    diminutives = set()
                    
                    for name, props in russian_names.RUSSIAN_NAMES.items():
                        given_names.add(name)
                        if 'variants' in props:
                            given_names.update(props['variants'])
                        if 'diminutives' in props:
                            diminutives.update(props['diminutives'])
                        if 'declensions' in props:
                            given_names.update(props['declensions'])
                    
                    dictionaries['given_names_ru'] = given_names
                    dictionaries['diminutives_ru'] = diminutives
                    dictionaries['surnames_ru'] = surnames

                # Load Ukrainian names
                if hasattr(ukrainian_names, 'UKRAINIAN_NAMES'):
                    # Extract given names from UKRAINIAN_NAMES
                    given_names = set()
                    surnames = set()
                    diminutives = set()
                    
                    for name, props in ukrainian_names.UKRAINIAN_NAMES.items():
                        given_names.add(name)
                        if 'variants' in props:
                            given_names.update(props['variants'])
                        if 'diminutives' in props:
                            diminutives.update(props['diminutives'])
                        if 'declensions' in props:
                            given_names.update(props['declensions'])
                    
                    dictionaries['given_names_uk'] = given_names
                    dictionaries['diminutives_uk'] = diminutives
                    dictionaries['surnames_uk'] = surnames

                self.logger.info(f"Loaded {len(dictionaries)} name dictionaries")
            except Exception as e:
                self.logger.warning(f"Failed to load name dictionaries: {e}")

        return dictionaries

    def _load_diminutive_maps(self) -> Dict[str, Dict[str, str]]:
        """Load diminutive to full name mappings from JSON dictionaries."""
        maps: Dict[str, Dict[str, str]] = {}

        base_path = Path(__file__).resolve().parents[4]
        data_dir = base_path / "data"

        for lang in ("ru", "uk"):
            path = data_dir / f"diminutives_{lang}.json"
            if not path.exists():
                self.logger.warning("Diminutive dictionary missing for %s: %s", lang, path)
                continue

            try:
                with path.open("r", encoding="utf-8") as handle:
                    raw = json.load(handle)
                maps[lang] = {
                    unicodedata.normalize("NFKC", key).lower(): unicodedata.normalize("NFKC", value).lower()
                    for key, value in raw.items()
                }
            except json.JSONDecodeError as exc:
                self.logger.error("Invalid JSON in diminutive dictionary %s: %s", lang, exc)
            except Exception as exc:  # pragma: no cover - IO errors logged
                self.logger.error("Failed to load diminutive dictionary %s: %s", lang, exc)

        # Preserve English nicknames behaviour if available
        if DICTIONARIES_AVAILABLE:
            try:
                from ...data.dicts.english_names import NICKNAMES_EN
                maps['en'] = {
                    unicodedata.normalize("NFKC", key).lower(): unicodedata.normalize("NFKC", value).lower()
                    for key, value in NICKNAMES_EN.items()
                }
            except ImportError:
                pass
            except Exception as exc:
                self.logger.warning("Failed to load English nicknames: %s", exc)

        self.logger.info(f"Loaded diminutive maps for {len(maps)} languages")
        return maps

    async def _process_with_factory(
        self,
        text: str,
        language: str,
        remove_stop_words: bool,
        preserve_names: bool,
        enable_advanced_features: bool,
        strict_stopwords: bool = False,
        preserve_feminine_suffix_uk: bool = False,
        enable_spacy_uk_ner: bool = False,
        en_use_nameparser: bool = True,
        enable_en_nickname_expansion: bool = True,
        enable_spacy_en_ner: bool = False,
        ru_yo_strategy: str = "preserve",
        enable_ru_nickname_expansion: bool = True,
        enable_spacy_ru_ner: bool = False,
        feature_flags: Optional[FeatureFlags] = None,
    ) -> NormalizationResult:
        """Process with factory implementation."""
        config = NormalizationConfig(
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            enable_advanced_features=enable_advanced_features,
            language=language,
            strict_stopwords=strict_stopwords,
            preserve_feminine_suffix_uk=preserve_feminine_suffix_uk,
            enable_spacy_uk_ner=enable_spacy_uk_ner,
            en_use_nameparser=en_use_nameparser,
            enable_en_nickname_expansion=enable_en_nickname_expansion,
            enable_spacy_en_ner=enable_spacy_en_ner,
            ru_yo_strategy=ru_yo_strategy,
            enable_ru_nickname_expansion=enable_ru_nickname_expansion,
            enable_spacy_ru_ner=enable_spacy_ru_ner,
        )
        result = await self.normalization_factory.normalize_text(text, config, feature_flags)
        return self._enforce_nominative_and_gender(result, language)

    async def _process_with_legacy(
        self,
        text: str,
        language: str,
        remove_stop_words: bool,
        preserve_names: bool,
        enable_advanced_features: bool,
        feature_flags: Optional[FeatureFlags] = None,
    ) -> NormalizationResult:
        """Process with legacy implementation."""
        if self._legacy_service is None:
            from .normalization_service_legacy import NormalizationService as LegacyService
            self._legacy_service = LegacyService()

        # Legacy service is synchronous, so we run it in executor
        import asyncio
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            self._legacy_service.normalize,
            text,
            language,
            remove_stop_words,
            preserve_names,
            enable_advanced_features,
        )
        return self._enforce_nominative_and_gender(result, language)

    async def _dual_process(
        self,
        text: str,
        language: str,
        remove_stop_words: bool,
        preserve_names: bool,
        enable_advanced_features: bool,
        strict_stopwords: bool = False,
        preserve_feminine_suffix_uk: bool = False,
        enable_spacy_uk_ner: bool = False,
        en_use_nameparser: bool = True,
        enable_en_nickname_expansion: bool = True,
        enable_spacy_en_ner: bool = False,
        ru_yo_strategy: str = "preserve",
        enable_ru_nickname_expansion: bool = True,
        enable_spacy_ru_ner: bool = False,
        feature_flags: Optional[FeatureFlags] = None,
    ) -> NormalizationResult:
        """Process with both implementations for comparison."""
        import asyncio

        # Run both implementations concurrently
        factory_task = asyncio.create_task(
            self._process_with_factory(text, language, remove_stop_words, preserve_names, enable_advanced_features,
                                     strict_stopwords, preserve_feminine_suffix_uk, enable_spacy_uk_ner,
                                     en_use_nameparser, enable_en_nickname_expansion, enable_spacy_en_ner,
                                     ru_yo_strategy, enable_ru_nickname_expansion, enable_spacy_ru_ner, feature_flags)
        )
        legacy_task = asyncio.create_task(
            self._process_with_legacy(text, language, remove_stop_words, preserve_names, enable_advanced_features, feature_flags)
        )

        factory_result, legacy_result = await asyncio.gather(factory_task, legacy_task, return_exceptions=True)

        # Log comparison results
        if not isinstance(factory_result, Exception) and not isinstance(legacy_result, Exception):
            parity_match = factory_result.normalized == legacy_result.normalized
            self.logger.info(
                f"Dual processing comparison: parity={parity_match}, "
                f"factory='{factory_result.normalized}', legacy='{legacy_result.normalized}'"
            )

        # Return factory result by default, fallback to legacy on error
        if isinstance(factory_result, Exception):
            self.logger.warning(f"Factory failed in dual mode: {factory_result}")
            return legacy_result if not isinstance(legacy_result, Exception) else self._build_error_result(text, str(factory_result))

        return factory_result

    def _enforce_nominative_and_gender(
        self,
        result: NormalizationResult,
        language: Optional[str],
    ) -> NormalizationResult:
        """Force nominative outputs and retain feminine surname endings when needed."""

        if not self.feature_flags.enforce_nominative():
            return result

        if not result.trace:
            return result

        lang = (language or result.language or "ru").lower()
        if lang not in {"ru", "uk", "en"}:
            return result

        adapter = self.morphology_adapter
        preserve_feminine = self.feature_flags.preserve_feminine_surnames()
        personal_roles = {"given", "patronymic", "surname", "initial"}

        given_gender = "unknown"
        personal_sequence = []

        for trace in result.trace:
            role = trace.role
            if role in {"given", "patronymic", "surname"}:
                original_output = trace.output
                nominative = adapter.to_nominative(original_output, lang)
                if nominative and nominative != original_output:
                    # Apply titlecase to nominative result
                    titlecased_nominative = self._to_title(nominative)
                    trace.notes = self._append_trace_note(
                        trace.notes,
                        {
                            "type": "morph",
                            "action": "to_nominative",
                            "token": original_output,
                            "result": titlecased_nominative,
                        },
                    )
                    trace.output = titlecased_nominative

                if role == "given" and given_gender == "unknown":
                    detected_gender = adapter.detect_gender(trace.output, lang)
                    if detected_gender in {"femn", "masc"}:
                        given_gender = detected_gender

            if role == "surname" and preserve_feminine:
                before_preserve = trace.output
                preferred = prefer_feminine_form(before_preserve, given_gender, lang)
                payload = {
                    "type": "morph",
                    "action": "preserve_feminine",
                    "token": before_preserve,
                }
                if preferred != before_preserve:
                    trace.output = preferred
                    payload["result"] = preferred
                trace.notes = self._append_trace_note(trace.notes, payload)

            # Don't collect personal sequence here to avoid duplicates

        # Remove duplicate traces and collect personal sequence, but allow duplicate initials
        seen_tokens = set()
        unique_traces = []
        for trace in result.trace:
            # For initials, allow duplicates (И. И. Петров)
            # For other roles, check for duplicates
            if trace.role != 'initial':
                token_key = (trace.token, trace.role)
                if token_key not in seen_tokens:
                    seen_tokens.add(token_key)
                    unique_traces.append(trace)
                else:
                    # Update existing trace with new output
                    for existing_trace in unique_traces:
                        if existing_trace.token == trace.token and existing_trace.role == trace.role:
                            existing_trace.output = trace.output
                            break
            else:
                # For initials, always add (allow duplicates)
                unique_traces.append(trace)
        
        # Update result.trace with unique traces
        result.trace = unique_traces
        
        # Collect personal sequence from unique traces
        for trace in result.trace:
            role = trace.role
            if role in personal_roles:
                personal_sequence.append((role, trace.output))

        person_tokens = [token for _, token in personal_sequence]

        if person_tokens:
            # Remove duplicates while preserving order, but allow duplicate initials
            seen = set()
            unique_person_tokens = []
            for i, (role, token) in enumerate(personal_sequence):
                # For initials, allow duplicates (И. И. Петров)
                # For other roles, skip if we've already processed this token
                if role != 'initial' and token.lower() in seen:
                    continue
                    
                if role != 'initial':
                    seen.add(token.lower())
                    
                unique_person_tokens.append(token)
            
            # Apply titlecase to person tokens
            titlecased_tokens = []
            for token in unique_person_tokens:
                titlecased_token = self._to_title(token)
                titlecased_tokens.append(titlecased_token)
            
            result.normalized = " ".join(titlecased_tokens)
            person_tokens = titlecased_tokens  # Update person_tokens for tokens field

        organization_tokens = list(result.organizations_core or [])
        if not organization_tokens:
            organization_tokens = [trace.output for trace in result.trace if trace.role == "org"]

        result.tokens = person_tokens + organization_tokens

        if result.persons:
            seq_index = 0
            for person in result.persons:
                roles = person.get("roles", [])
                new_tokens = []
                for _ in roles:
                    if seq_index >= len(personal_sequence):
                        break
                    _, token_value = personal_sequence[seq_index]
                    new_tokens.append(token_value)
                    seq_index += 1
                if new_tokens:
                    person["tokens"] = new_tokens
            result.persons_core = [person.get("tokens", []) for person in result.persons]
        else:
            result.persons_core = [person_tokens] if person_tokens else []

        if given_gender in {"femn", "masc"}:
            result.person_gender = given_gender

        return result

    @staticmethod
    def _append_trace_note(existing: Optional[str], payload: Dict[str, str]) -> str:
        serialized = json.dumps(payload, ensure_ascii=False)
        if existing:
            return f"{existing}; {serialized}"
        return serialized

    def _build_error_result(self, text: str, error_msg: str) -> NormalizationResult:
        """Build error result for failed processing."""
        return NormalizationResult(
            normalized="",
            tokens=[],
            trace=[],
            errors=[error_msg],
            language="unknown",
            confidence=0.0,
            original_length=len(text),
            normalized_length=0,
            token_count=0,
            processing_time=0.0,
            success=False,
            original_text=text,
            token_variants={},
            total_variants=0,
            persons_core=[],
            organizations_core=[],
            persons=[],
        )
