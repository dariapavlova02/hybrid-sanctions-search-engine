"""
Factory class for coordinating normalization processors.
Provides better error handling, logging, and orchestration of the refactored components.
"""

import json
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any, Literal
from dataclasses import dataclass
from ....utils.logging_config import get_logger
from ....utils.perf_timer import PerfTimer
from ....utils.feature_flags import get_feature_flag_manager, FeatureFlags
from ....utils.profiling import profile_function, profile_time, get_profiling_stats, print_profiling_report
from ....utils.lru_cache_ttl import CacheManager, create_flags_hash
from ..tokenizer_service import TokenizerService, CachedTokenizerService
from ..morphology_adapter import MorphologyAdapter
from ....monitoring.cache_metrics import CacheMetrics, MetricsCollector
from ....contracts.base_contracts import NormalizationResult, TokenTrace
from ..error_handling import ErrorReportingMixin

from .token_processor import TokenProcessor
from .role_classifier import RoleClassifier
from .morphology_processor import MorphologyProcessor
from .gender_processor import GenderProcessor
from ..token_ops import collapse_double_dots, collapse_double_dots_token, normalize_hyphenated_name, normalize_apostrophe_name, is_hyphenated_surname
from ..morphology.diminutive_resolver import DiminutiveResolver
from ..role_tagger import RoleTagger
from ..role_tagger_service import RoleTaggerService
from ..lexicon_loader import get_lexicons


def _to_title(word: str) -> str:
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
        return '-'.join(_to_title(segment) for segment in segments)
    
    # Handle single word - use title() for proper apostrophe handling
    if len(word) == 1:
        return word.upper()

    # Use title() method which handles apostrophes correctly (e.g., "o'neil" -> "O'Neil")
    return word.title()

try:
    from ....data.dicts import russian_names, ukrainian_names
    DICTIONARIES_AVAILABLE = True
except ImportError:  # pragma: no cover - optional heavy dependency
    DICTIONARIES_AVAILABLE = False
    russian_names = None  # type: ignore
    ukrainian_names = None  # type: ignore

PERSON_ROLES = {"given", "surname", "patronymic", "initial", "suffix", "other"}
SEPARATOR_TOKENS = {"и", "та", "and", ",", "|", ";", "та", "і", "и"}


@dataclass
class NormalizationConfig:
    """Configuration for normalization processing."""
    remove_stop_words: bool = True
    preserve_names: bool = True
    enable_advanced_features: bool = True
    enable_morphology: bool = True
    enable_ascii_fastpath: bool = False
    enable_gender_adjustment: bool = True
    language: str = 'ru'
    use_factory: bool = True  # Flag to use factory vs legacy implementation

    # Validation flags (default OFF, for validation only)
    enable_spacy_ner: bool = False
    enable_nameparser_en: bool = False
    enable_fsm_tuned_roles: bool = False
    enable_enhanced_diminutives: bool = True
    enable_enhanced_gender_rules: bool = False
    enable_ac_tier0: bool = False
    enable_vector_fallback: bool = False
    filter_titles_suffixes: bool = True  # Filter out titles and suffixes from EN names
    preserve_feminine_suffix_uk: bool = False  # Preserve Ukrainian feminine suffixes (-ська/-цька)
    enable_spacy_uk_ner: bool = False  # Enable spaCy Ukrainian NER
    # English-specific flags
    en_use_nameparser: bool = True  # Use nameparser for English names
    enable_en_nickname_expansion: bool = True  # Expand English nicknames
    enable_spacy_en_ner: bool = False  # Enable spaCy English NER
    enable_nameparser_en: bool = False  # Enable nameparser for English name parsing
    enable_en_nicknames: bool = False  # Enable English nickname resolution
    enable_en_rules: bool = False  # Enable English-specific normalization rules
    # Russian-specific flags
    ru_yo_strategy: str = "preserve"  # Russian 'ё' policy ('preserve' or 'fold')
    enable_ru_nickname_expansion: bool = True  # Expand Russian nicknames
    enable_spacy_ru_ner: bool = False  # Enable spaCy Russian NER
    # Unicode normalization flags
    normalize_homoglyphs: bool = False  # Normalize Cyrillic/Latin homoglyphs to dominant alphabet
    yo_strategy: Literal["fold", "preserve"] = "fold"  # Russian 'ё' strategy ('fold' or 'preserve')
    # Caching flags
    enable_cache: bool = True  # Enable caching
    debug_tracing: bool = False  # Enable debug tracing with cache info


class NormalizationFactory(ErrorReportingMixin):
    """Factory for coordinating all normalization processors."""

    def __init__(
        self,
        name_dictionaries: Optional[Dict[str, Set[str]]] = None,
        diminutive_maps: Optional[Dict[str, Dict[str, str]]] = None,
        cache_manager: Optional[CacheManager] = None,
        cache_metrics: Optional[CacheMetrics] = None,
    ):
        super().__init__()
        self.logger = get_logger(__name__)

        # Feature flags for tokenizer improvements
        self.feature_flags = get_feature_flag_manager()

        # Initialize caching
        self.cache_manager = cache_manager or CacheManager()
        self.cache_metrics = cache_metrics or CacheMetrics()
        self.metrics_collector = MetricsCollector(self.cache_metrics)

        # Initialize cached services
        self.tokenizer_service = TokenizerService(
            cache=self.cache_manager.get_tokenizer_cache(),
            fix_initials_double_dot=self.feature_flags._flags.fix_initials_double_dot,
            preserve_hyphenated_case=self.feature_flags._flags.preserve_hyphenated_case
        )
        self.morphology_adapter = MorphologyAdapter()

        # Initialize processors
        self.token_processor = TokenProcessor()
        self.role_classifier = RoleClassifier(name_dictionaries, diminutive_maps)
        self.morphology_processor = MorphologyProcessor(diminutive_maps)
        self.gender_processor = GenderProcessor()
        self.diminutive_resolver = DiminutiveResolver(Path(__file__).resolve().parents[5])

        # Initialize role taggers with unified lexicon and AC acceleration
        self.lexicons = get_lexicons()
        self.role_tagger = RoleTagger(window=3, enable_ac=False)  # Conservative: AC disabled for now
        self.role_tagger_service = RoleTaggerService(role_classifier=self.role_classifier)  # Pass role classifier to FSM tagger
        
        # Initialize NER gateways with graceful fallback
        self.ner_gateway_uk = None
        self.ner_gateway_en = None
        self.ner_gateway_ru = None
        self.ner_disabled = False
        
        try:
            from ..ner_gateways import get_spacy_uk_ner, get_spacy_en_ner, get_spacy_ru_ner
            self.ner_gateway_uk = get_spacy_uk_ner()
            self.ner_gateway_en = get_spacy_en_ner()
            self.ner_gateway_ru = get_spacy_ru_ner()
            
            # Check if any NER is available
            if not any([self.ner_gateway_uk, self.ner_gateway_en, self.ner_gateway_ru]):
                self.ner_disabled = True
                self.logger.warning("No NER models available, falling back to rules-only mode")
            else:
                self.logger.info("NER gateways initialized successfully")
        except ImportError as e:
            self.logger.warning(f"NER gateways not available: {e}")
            self.ner_disabled = True
        except Exception as e:
            self.logger.warning(f"Failed to initialize NER gateways: {e}")
            self.ner_disabled = True

        # Cache for performance
        self._normalization_cache = {}

        self.logger.info("NormalizationFactory initialized with all processors")

    @profile_function("normalization_factory.normalize_text")
    async def normalize_text(
        self,
        text: str,
        config: NormalizationConfig,
        feature_flags: Optional[Any] = None
    ) -> NormalizationResult:
        """Normalize text and return a complete NormalizationResult."""
        # Use passed feature flags or fall back to global flags
        effective_flags = feature_flags if feature_flags is not None else self.feature_flags
        with PerfTimer() as timer:
            try:
                # Propagate feature flags to config
                if feature_flags:
                    from ....utils.flag_propagation import create_flag_context, propagate_flags_to_layer
                    flag_context = create_flag_context(feature_flags, "normalization", config.debug_tracing)
                    config = propagate_flags_to_layer(flag_context, "normalization", config)
                
                # Check for ASCII fastpath
                if config.enable_ascii_fastpath and self._is_ascii_fastpath_eligible(text, config):
                    result = await self._ascii_fastpath_normalize(text, config)
                    result.processing_time = timer.elapsed
                    result.success = len(result.errors or []) == 0
                    return result
                
                result = await self._normalize_with_error_handling(text, config, effective_flags)
                result.processing_time = timer.elapsed
                result.success = len(result.errors or []) == 0
                return result
            except Exception as e:
                self.logger.error(f"Normalization failed for text '{text}': {e}")
                return self._build_error_result(text, str(e), timer.elapsed)

    async def _normalize_with_error_handling(
        self,
        text: str,
        config: NormalizationConfig,
        effective_flags
    ) -> NormalizationResult:
        """Core normalization logic with comprehensive error handling."""

        errors: List[str] = []

        # Apply English name filter preprocessing if language is English
        processed_text = text
        if config.language == "en":
            try:
                from ..filters.english_name_filter import english_name_filter
                if english_name_filter.should_apply_filter(config.language, text):
                    filtered_text, filter_rules = english_name_filter.filter_name(text)
                    if filtered_text != text:
                        processed_text = filtered_text
                        self.logger.debug(f"English name filter applied: '{text}' -> '{filtered_text}', rules: {filter_rules}")
            except ImportError:
                # English name filter not available, continue with original text
                pass

        # Step 1: Tokenization with caching
        try:
            if config.enable_cache:
                # Refresh tokenizer flags from effective_flags before tokenization
                if effective_flags:
                    self.tokenizer_service.fix_initials_double_dot = getattr(effective_flags, 'fix_initials_double_dot', self.feature_flags._flags.fix_initials_double_dot)
                    self.tokenizer_service.preserve_hyphenated_case = getattr(effective_flags, 'preserve_hyphenated_case', self.feature_flags._flags.preserve_hyphenated_case)
                
                # Use cached tokenizer service
                feature_flags = {
                    'remove_stop_words': config.remove_stop_words,
                    'preserve_names': config.preserve_names,
                    'enable_advanced_features': config.enable_advanced_features
                }
                
                tokenization_result = self.tokenizer_service.tokenize(
                    processed_text,
                    language=config.language,
                    remove_stop_words=config.remove_stop_words,
                    preserve_names=config.preserve_names,
                    feature_flags=feature_flags
                )
                
                tokens = tokenization_result.tokens
                tokenization_traces = tokenization_result.traces
                token_meta = tokenization_result.metadata
                tokenizer_token_traces = tokenization_result.token_traces or []
                
                # Record metrics
                self.metrics_collector.collect_tokenizer_metrics(
                    config.language,
                    self.tokenizer_service.get_stats()
                )
                
                self.logger.debug(f"Tokenized '{processed_text}' into {len(tokens)} tokens (cache: {'hit' if tokenization_result.cache_hit else 'miss'})")
            else:
                # Use direct tokenization
                tokens, tokenization_traces, token_meta = self.token_processor.strip_noise_and_tokenize(
                    processed_text,
                    language=config.language,
                    remove_stop_words=config.remove_stop_words,
                    preserve_names=config.preserve_names
                )
                self.logger.debug(f"Tokenized '{text}' into {len(tokens)} tokens")
        except Exception as e:
            self.logger.error(f"Tokenization failed: {e}")
            return self._build_error_result(text, f"Tokenization failed: {e}")

        # Step 1.5: Apply tokenizer improvements (pre-processing)
        tokens, improvement_traces_pre = self._apply_tokenizer_improvements(tokens, tokenization_traces, effective_flags)
        self.logger.debug(f"Applied pre-processing tokenizer improvements: {len(improvement_traces_pre)} improvements")

        # Step 1.6: Apply Russian 'ё' strategy if needed
        yo_traces = []
        if config.language == "ru" and config.yo_strategy in {"preserve", "fold"}:
            tokens, yo_traces = self._apply_yo_strategy(tokens, config.yo_strategy)
            self.logger.debug(f"Applied Russian 'ё' strategy '{config.yo_strategy}': {len(yo_traces)} changes")

        if not tokens:
            return self._build_empty_result(text, config.language, config.debug_tracing)

        quoted_segments = token_meta.get("quoted_segments", [])

        # Step 1.6: Role tagging with FSM-based service (skip for English nameparser or if disabled)
        if (config.language == "en" and config.enable_nameparser_en) or not getattr(effective_flags, 'enable_fsm_tuned_roles', False):
            # Skip FSM role tagger for English nameparser mode or if FSM is disabled
            role_tags = []
            role_tagger_traces = []
            org_spans = []
            if config.language == "en" and config.enable_nameparser_en:
                self.logger.debug("FSM role tagger skipped for English nameparser mode")
            else:
                self.logger.debug("FSM role tagger disabled by enable_fsm_tuned_roles=False")
        else:
            try:
                # Get NER hints if enabled
                ner_hints = None
                if config.language == "uk" and config.enable_spacy_uk_ner and self.ner_gateway_uk:
                    try:
                        ner_hints = self.ner_gateway_uk.extract_entities(text)
                        self.logger.debug(f"Ukrainian NER extracted {len(ner_hints.person_spans)} person spans and {len(ner_hints.org_spans)} org spans")
                    except Exception as e:
                        self.logger.warning(f"Ukrainian NER extraction failed: {e}")
                elif config.language == "en" and config.enable_spacy_en_ner and self.ner_gateway_en:
                    try:
                        ner_hints = self.ner_gateway_en.extract_entities(text)
                        self.logger.debug(f"English NER extracted {len(ner_hints.person_spans)} person spans and {len(ner_hints.org_spans)} org spans")
                    except Exception as e:
                        self.logger.warning(f"English NER extraction failed: {e}")
                elif config.language == "ru" and config.enable_spacy_ru_ner and self.ner_gateway_ru:
                    try:
                        ner_hints = self.ner_gateway_ru.extract_entities(text)
                        self.logger.debug(f"Russian NER extracted {len(ner_hints.person_spans)} person spans and {len(ner_hints.org_spans)} org spans")
                    except Exception as e:
                        self.logger.warning(f"Russian NER extraction failed: {e}")
                
                # Use new FSM-based role tagger service
                if not hasattr(self, 'role_tagger_service') or self.role_tagger_service is None:
                    # Initialize role tagger service
                    self.role_tagger_service = RoleTaggerService(role_classifier=self.role_classifier)
                
                role_tags = self.role_tagger_service.tag(tokens, config.language)
                role_tagger_traces = self._create_fsm_role_tagger_traces(role_tags, tokens)
                self.logger.debug(f"FSM role tagger classified: {[(tag.role.value, tag.reason) for tag in role_tags]}")

                # Extract organization spans for later use
                org_spans = self._extract_organization_spans_from_fsm_tags(role_tags)
                if org_spans:
                    for span in org_spans:
                        role_tagger_traces.append(f"FSM role tagger: organization span '{' '.join(span)}'")

            except Exception as e:
                self.logger.error(f"FSM role tagging failed: {e}")
                errors.append(f"FSM role tagging failed: {e}")
                role_tags = []
                role_tagger_traces = []
                org_spans = []

        # Step 2: Role classification (existing system)
        try:
            self.logger.debug(f"Before role classification: tokens={tokens}")
            classified_tokens, roles, role_traces, org_entities = await self._classify_token_roles(
                tokens, config, quoted_segments
            )
            self.logger.debug(f"After role classification: classified_tokens={classified_tokens}, roles={roles}")
            original_tagged_tokens = list(zip(classified_tokens, roles))
            self.logger.debug(f"Classified roles: {list(zip(classified_tokens, roles))}")
            
            # Override roles with FSM results if available (but not for English nameparser)
            if role_tags and not (config.language == "en" and config.enable_nameparser_en):
                roles = [tag.role.value for tag in role_tags]
                self.logger.debug(f"FSM overrode roles: {list(zip(classified_tokens, roles))}")
            elif role_tags and config.language == "en" and config.enable_nameparser_en:
                self.logger.debug(f"FSM role tagger skipped for English nameparser mode")
        except Exception as e:
            self.logger.error(f"Role classification failed: {e}")
            errors.append(f"Role classification failed: {e}")
            classified_tokens = tokens
            roles = ['unknown'] * len(tokens)
            role_traces = [f"Role classification failed: {e}"]
            org_entities = []
            original_tagged_tokens = list(zip(classified_tokens, roles))

        # Step 2.5: Filter tokens based on FSM role tagger results
        self.logger.debug(f"Filtering check: role_tags={len(role_tags) if role_tags else 0}, strict_stopwords={getattr(effective_flags, 'strict_stopwords', False)}")
        if role_tags and getattr(effective_flags, 'strict_stopwords', False):
            # Pass trace if debug tracing is enabled
            trace_steps = [] if getattr(effective_flags, 'debug_tracing', False) else None
            filtered_tokens, filtered_roles, filter_traces = self._apply_role_filtering(
                classified_tokens, roles, role_tags, effective_flags=effective_flags, language=config.language, trace=trace_steps
            )
            self.logger.debug(f"FSM role filtering removed {len(classified_tokens) - len(filtered_tokens)} tokens")
        else:
            filtered_tokens = classified_tokens
            filtered_roles = roles
            filter_traces = []

        diminutive_traces: List[str] = []
        unresolved_diminutive_indices: Set[int] = set()
        # Use filtered tokens and roles if filtering was applied
        if role_tags and getattr(effective_flags, 'strict_stopwords', False):
            tokens_for_morphology = filtered_tokens
            roles_for_morphology = filtered_roles
        else:
            tokens_for_morphology = classified_tokens
            # Use FSM-updated roles if available, otherwise fallback to classified roles
            roles_for_morphology = roles
        if (
            config.language in {"ru", "uk"}
            and getattr(effective_flags, "enable_enhanced_diminutives", True)
        ):
            (
                tokens_for_morphology,
                diminutive_traces,
                unresolved_diminutive_indices,
            ) = self._apply_diminutives(
                classified_tokens,
                roles_for_morphology,
                config.language,
                effective_flags,
            )

        # Step 3: Morphological normalization
        try:
            self.logger.debug(f"Morphology input: {len(tokens_for_morphology)} tokens")
            normalized_tokens, morph_traces = await self._normalize_morphology(
                tokens_for_morphology, roles_for_morphology, config, skip_indices=None, effective_flags=effective_flags
            )
            self.logger.debug(f"Morphology output: {len(normalized_tokens)} normalized tokens")
            
            # Apply yo_strategy again after morphology to ensure consistency
            if config.language == "ru" and config.yo_strategy in {"preserve", "fold"}:
                self.logger.debug(f"Before yo_strategy post-morphology: {normalized_tokens}")
                normalized_tokens, yo_traces_post = self._apply_yo_strategy(normalized_tokens, config.yo_strategy)
                self.logger.debug(f"After yo_strategy post-morphology: {normalized_tokens}")
                if yo_traces_post:
                    morph_traces.extend([trace.notes for trace in yo_traces_post])
                    self.logger.debug(f"Applied Russian 'ё' strategy '{config.yo_strategy}' post-morphology: {len(yo_traces_post)} changes")
                    
        except Exception as e:
            self.logger.error(f"Morphological normalization failed: {e}")
            errors.append(f"Morphological normalization failed: {e}")
            normalized_tokens = tokens_for_morphology
            morph_traces = [f"Morphological normalization failed: {e}"]

        # Step 3.5: Apply diminutives resolution AFTER morphology
        post_morph_diminutive_traces = []
        if (
            config.language in {"ru", "uk", "en"}
            and getattr(effective_flags, "enable_enhanced_diminutives", True)
            and normalized_tokens  # Only if we have successful morphology results
        ):
            try:
                # Apply diminutives to the morphologically normalized tokens
                normalized_tokens, post_morph_diminutive_traces, _ = self._apply_diminutives(
                    normalized_tokens,
                    roles,
                    config.language,
                    effective_flags,
                )
                self.logger.debug(f"Applied post-morphology diminutive resolution: {len(post_morph_diminutive_traces)} changes")
            except Exception as e:
                self.logger.error(f"Post-morphology diminutive resolution failed: {e}")
                post_morph_diminutive_traces = [f"Post-morphology diminutive resolution failed: {e}"]

        # Step 4: Gender processing
        try:
            self.logger.debug(f"Gender processing input: {len(normalized_tokens)} tokens")
            final_tokens, gender_traces, gender_info = await self._process_gender(
                normalized_tokens, roles, config
            )
            self.logger.debug(f"Gender processing output: {len(final_tokens)} tokens")
        except Exception as e:
            self.logger.error(f"Gender processing failed: {e}")
            errors.append(f"Gender processing failed: {e}")
            final_tokens = normalized_tokens
            gender_traces = [f"Gender processing failed: {e}"]
            gender_info = {}

        # Step 4.5: Apply tokenizer improvements (post-processing)
        self.logger.debug(f"Post-processing input: {len(final_tokens)} tokens")
        final_tokens, improvement_traces_post = self._apply_tokenizer_improvements_post(final_tokens, roles, effective_flags)
        self.logger.debug(f"Post-processing output: {len(final_tokens)} tokens")
        self.logger.debug(f"Applied post-processing tokenizer improvements: {len(improvement_traces_post)} improvements")
        
        # Step 4.6: Apply double dot collapse to final tokens
        final_tokens = collapse_double_dots(final_tokens, [])

        # Step 5: Build trace
        processing_traces: List[str] = []
        cache_info = None
        
        # Always include improvement traces for collapse_double_dots rule
        processing_traces = (
            [str(trace) for trace in improvement_traces_pre]
            + [str(trace) for trace in yo_traces]
            + [str(trace) for trace in role_tagger_traces]
            + filter_traces
            + diminutive_traces
            + role_traces
            + morph_traces
            + post_morph_diminutive_traces  # Add post-morphology diminutive traces
            + gender_traces
            + [str(trace) for trace in improvement_traces_post]
        )
        
        if config.debug_tracing:
            # Add FSM role traces to the trace
            if role_tags:
                fsm_trace_entries = self.role_tagger_service.get_trace_entries(tokens, role_tags)
                for fsm_entry in fsm_trace_entries:
                    processing_traces.append(f"FSM role trace: {fsm_entry}")
            
            # Get cache info for debug tracing
            cache_info = getattr(self, '_debug_cache_info', None)
        
        # Update trace with FSM roles if available
        if role_tags:
            # Rebuild trace with FSM roles
            fsm_roles = [tag.role.value for tag in role_tags]
            # Use final_tokens to include morphology and gender processing
            trace = self._build_token_trace(
                classified_tokens,
                fsm_roles,
                final_tokens,  # Use tokens after full processing pipeline
                processing_traces,
                cache_info
            )
            
            # Add tokenizer improvement traces to final trace
            for improvement_trace in improvement_traces_post:
                if isinstance(improvement_trace, TokenTrace):
                    trace.append(improvement_trace)
            
            # Add tokenizer token traces to final trace
            for tokenizer_trace in tokenizer_token_traces:
                if isinstance(tokenizer_trace, TokenTrace):
                    trace.append(tokenizer_trace)
            
            # Add tokenization traces (like collapse_double_dots) to the final trace
            for tokenization_trace in tokenization_traces:
                if isinstance(tokenization_trace, dict) and tokenization_trace.get('rule') == 'collapse_double_dots':
                    trace.append(TokenTrace(
                        token=tokenization_trace.get('before', ''),
                        role='tokenizer',
                        rule='collapse_double_dots',
                        output=tokenization_trace.get('after', ''),
                        fallback=False,
                        notes=f"Evidence: {tokenization_trace.get('evidence', '')}",
                        is_hyphenated_surname=False
                    ))
            
            # Add improvement traces post (like normalize_hyphen_post) to the final trace
            for improvement_trace in improvement_traces_post:
                trace.append(improvement_trace)
                if isinstance(improvement_trace, TokenTrace):
                    self.logger.debug(f"Added improvement trace: {improvement_trace.rule} - {improvement_trace.token} -> {improvement_trace.output}")
                else:
                    self.logger.debug(f"Added improvement trace: {improvement_trace}")
        else:
            trace = self._build_token_trace(
                classified_tokens,
                roles,
                final_tokens,
                processing_traces,
                cache_info
            )
            
            # Add improvement traces post (like normalize_hyphen_post) to the final trace
            for improvement_trace in improvement_traces_post:
                trace.append(improvement_trace)
                if isinstance(improvement_trace, TokenTrace):
                    self.logger.debug(f"Added improvement trace: {improvement_trace.rule} - {improvement_trace.token} -> {improvement_trace.output}")
                else:
                    self.logger.debug(f"Added improvement trace: {improvement_trace}")
            
            # Add tokenizer token traces to final trace
            for tokenizer_trace in tokenizer_token_traces:
                if isinstance(tokenizer_trace, TokenTrace):
                    trace.append(tokenizer_trace)

        # Step 6: Separate personal/org tokens
        personal_tokens = [
            tok for tok, role in zip(final_tokens, roles) if role in PERSON_ROLES
        ]
        # Use final roles to determine organizations, not the original org_entities
        organizations = [
            tok for tok, role in zip(final_tokens, roles) if role == 'org'
        ]

        # Ensure trace is a list of TokenTrace objects
        if isinstance(trace, list) and trace and isinstance(trace[0], TokenTrace):
            filtered_person_tokens = self._filter_person_tokens(trace, config.preserve_names, roles, config.language)
        else:
            # If trace is not TokenTrace objects, create a simple trace
            filtered_person_tokens = final_tokens
        final_normalized_text = " ".join(filtered_person_tokens)

        self.logger.debug(f"Final normalized text: '{final_normalized_text}'")
        self.logger.debug(f"Filtered person tokens: {filtered_person_tokens}")
        self.logger.debug(f"Final normalized text length: {len(final_normalized_text)}")
        self.logger.debug(f"Filtered person tokens count: {len(filtered_person_tokens)}")

        # Add trace step for final assembly if debug tracing is enabled
        if getattr(effective_flags, 'debug_tracing', False) and filtered_person_tokens:
            # Add assembly trace to the main trace
            assembly_trace = TokenTrace(
                token="[assembly]",
                role="assembly",
                rule="assemble_done",
                output=final_normalized_text,
                fallback=False,
                notes=f"Assembled {len(filtered_person_tokens)} person tokens into final normalized text",
                is_hyphenated_surname=False  # Assembly trace is not a hyphenated surname
            )
            trace.append(assembly_trace)

        persons = self._extract_persons(
            original_tagged_tokens,
            final_tokens,
            roles,
            config.language,
        )
        persons_core = [person["tokens"] for person in persons] if persons else ([] if not filtered_person_tokens else [filtered_person_tokens])

        # Include ALL processed tokens for Signals Service (person tokens + organizations + business signals)
        all_processed_tokens = []

        # Add personal name tokens for normalized text
        all_processed_tokens.extend(filtered_person_tokens)

        # Add organization tokens
        all_processed_tokens.extend(organizations)

        # Add business signals (document markers and business IDs) from traces
        for token_trace in trace:
            if isinstance(token_trace, TokenTrace) and token_trace.role in {"document", "candidate:identifier"}:
                if token_trace.output and token_trace.output not in all_processed_tokens:
                    all_processed_tokens.append(token_trace.output)

        output_tokens = all_processed_tokens

        result = NormalizationResult(
            normalized=final_normalized_text,
            tokens=output_tokens,
            trace=trace,
            errors=errors,
            language=config.language,
            confidence=None,
            original_length=len(text),
            normalized_length=len(final_normalized_text),
            token_count=len(output_tokens),  # Count all output tokens
            processing_time=0.0,
            success=len(errors) == 0,
            original_text=text,
            token_variants={},
            total_variants=0,
            persons_core=persons_core,
            organizations_core=organizations,
            persons=persons,
            ner_disabled=self.ner_disabled,
        )
        
        # Debug logging after result creation
        self.logger.debug(f"Result normalized: '{result.normalized}'")
        self.logger.debug(f"Result tokens: {result.tokens}")
        self.logger.debug(f"Result normalized length: {len(result.normalized)}")
        self.logger.debug(f"Result token count: {len(result.tokens)}")

        # Set gender information for single person cases
        if persons and len(persons) == 1:
            person = persons[0]
            result.person_gender = person.get("gender")
            result.gender_confidence = person.get("confidence", {}).get("gap", 0.0)

        # Add any additional gender info from processing
        for key, value in gender_info.items():
            setattr(result, key, value)

        return result

    def _build_error_result(self, text: str, error_msg: str, processing_time: float = 0.0) -> NormalizationResult:
        """Build error result for failed normalization."""
        text = text or ""  # Handle None input
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
            processing_time=processing_time,
            success=False,
            original_text=text,
            token_variants={},
            total_variants=0,
            persons_core=[],
            organizations_core=[],
            persons=[],
        )

    def _build_empty_result(self, text: str, language: str, debug_tracing: bool = False) -> NormalizationResult:
        """Build empty result for texts with no tokens."""
        from ....contracts.base_contracts import TokenTrace
        
        text = text or ""  # Handle None input
        
        # Generate trace entries when debug_tracing is enabled
        trace = []
        if debug_tracing:
            trace.append(TokenTrace(
                token=text,
                role="system",
                rule="empty_result",
                output="",
                fallback=False,
                notes="No tokens found after tokenization"
            ))
            if text.strip():
                trace.append(TokenTrace(
                    token=text,
                    role="system",
                    rule="filtered_out",
                    output="",
                    fallback=False,
                    notes=f"Input text '{text}' was completely filtered out"
                ))
            else:
                trace.append(TokenTrace(
                    token=text,
                    role="system",
                    rule="empty_input",
                    output="",
                    fallback=False,
                    notes="Input text was empty or whitespace only"
                ))
        
        return NormalizationResult(
            normalized="",
            tokens=[],
            trace=trace,
            errors=[],
            language=language,
            confidence=None,
            original_length=len(text),
            normalized_length=0,
            token_count=0,
            processing_time=0.0,
            success=True,
            original_text=text,
            token_variants={},
            total_variants=0,
            persons_core=[],
            organizations_core=[],
            persons=[],
        )

    def _filter_person_tokens(self, trace: List[TokenTrace], preserve_names: bool, roles: List[str], language: str = "auto") -> List[str]:
        """Filter tokens to include only person-related tokens from trace with proper titlecase.

        Excludes ORG-спаны (organization spans) from person concatenation.
        Also filters Latin tokens in Cyrillic languages (ru/uk).
        """
        self.logger.debug(f"Filtering person tokens from {len(trace)} trace entries")
        filtered_tokens = []
        processed_tokens = set()  # Track processed tokens to avoid duplicates
        for i, token_trace in enumerate(trace):
            # Skip non-TokenTrace objects
            if not isinstance(token_trace, TokenTrace):
                self.logger.debug(f"  {i}: Skipping non-TokenTrace object: {type(token_trace)}")
                continue
                
            self.logger.debug(f"  {i}: token='{token_trace.token}' role='{token_trace.role}' output='{token_trace.output}'")
            
            # Skip ORG-спаны (organization spans) - they should not be included in person-concat
            if token_trace.role == 'org':
                self.logger.debug(f"  Skipping ORG-спан: {token_trace.token} -> {token_trace.output}")
                continue

            # Skip Latin tokens in Cyrillic languages (mixed script filtering)
            if language in ("ru", "uk") and self._is_latin_token(token_trace.output):
                self.logger.debug(f"  SCRIPT FILTER: Skipping Latin token '{token_trace.output}' in {language} context")
                continue

            if token_trace.role in PERSON_ROLES:
                # For initials, allow duplicates (И. И. Петров)
                # For other roles, skip if we've already processed this token
                if token_trace.role != 'initial' and token_trace.output in processed_tokens:
                    continue
                    
                if token_trace.role != 'initial':
                    processed_tokens.add(token_trace.output)
                
                # Apply titlecase to person tokens
                original_token = token_trace.token
                normalized_token = token_trace.output

                # CRITICAL FIX: For initials and patronymics with empty output, use original token
                if token_trace.role in ('initial', 'patronymic') and not normalized_token.strip():
                    normalized_token = original_token
                    self.logger.debug(f"INIT/PAT FIX: Using original token '{original_token}' for empty output {token_trace.role}")

                # Check if token is already properly cased (avoid double processing)
                already_cased = getattr(token_trace, 'already_cased', False)
                
                if not already_cased and token_trace.role != 'suffix':
                    # Check for apostrophes first (for names like O'Brien)
                    if "'" in normalized_token:
                        # Apply apostrophe normalization with titlecase
                        titlecased_token = normalize_apostrophe_name(normalized_token, titlecase=True)
                        
                        # Apply apostrophe normalization (don't add to trace to avoid duplication)
                        if titlecased_token != normalized_token:
                            self.logger.debug(f"Applied apostrophe normalization: {normalized_token} -> {titlecased_token}")
                    # For hyphenated surnames, apply special titlecase handling
                    elif getattr(token_trace, 'is_hyphenated_surname', False) or is_hyphenated_surname(normalized_token):
                        # Use the hyphenated normalization with titlecase for proper handling
                        titlecased_token = normalize_hyphenated_name(normalized_token, titlecase=True)

                        # Apply hyphenated surname titlecase (don't add to trace to avoid duplication)
                        if titlecased_token != normalized_token:
                            self.logger.debug(f"Applied hyphenated surname titlecase: {normalized_token} -> {titlecased_token}")
                    else:
                        # Apply regular titlecase to person tokens (except suffixes)
                        if token_trace.role == 'suffix':
                            titlecased_token = normalized_token  # Keep suffixes as-is
                        else:
                            titlecased_token = _to_title(normalized_token)

                        # Apply titlecase transformation (don't add to trace to avoid duplication)
                        if titlecased_token != normalized_token:
                            self.logger.debug(f"Applied titlecase: {normalized_token} -> {titlecased_token}")

                    filtered_tokens.append(titlecased_token)
                    self.logger.debug(f"Added titlecased token: {titlecased_token}")
                else:
                    filtered_tokens.append(normalized_token)
                    self.logger.debug(f"Added normalized token (already_cased): {normalized_token}")
        
        # Apply deduplication of consecutive identical person tokens
        deduplicated_tokens = self._deduplicate_consecutive_person_tokens(filtered_tokens, trace)
        
        # Sort tokens by role: given, surname, patronymic, initial
        # Create a mapping from token to role for sorting
        token_to_role = {}
        for token_trace in trace:
            if token_trace.role in PERSON_ROLES:
                # Find matching token in deduplicated_tokens (handle apostrophe variations)
                matching_token = None
                for dedup_token in deduplicated_tokens:
                    # Normalize apostrophes for comparison (handle all apostrophe types)
                    trace_normalized = token_trace.output.replace("'", "'").replace("'", "'").replace("ʼ", "'")
                    dedup_normalized = dedup_token.replace("'", "'").replace("'", "'").replace("ʼ", "'")
                    if trace_normalized.lower() == dedup_normalized.lower():
                        matching_token = dedup_token
                        break

                if matching_token:
                    token_to_role[matching_token] = token_trace.role
                    self.logger.debug(f"Mapped token role: {matching_token} → {token_trace.role}")
                else:
                    self.logger.warning(f"Could not find role for trace.output='{token_trace.output}' in {deduplicated_tokens}")

        # Role order depends on language
        if language == "uk":
            # Ukrainian order: surname given patronymic
            role_order = {'surname': 0, 'given': 1, 'patronymic': 2, 'initial': 3}
        else:
            # Default order: given surname patronymic
            role_order = {'given': 0, 'surname': 1, 'patronymic': 2, 'initial': 3}
        self.logger.debug(f"Sorting tokens by role order: {role_order}")
        self.logger.debug(f"Token to role mapping: {token_to_role}")
        deduplicated_tokens.sort(key=lambda x: role_order.get(token_to_role.get(x, ''), 999))
        self.logger.debug(f"Sorted tokens: {deduplicated_tokens}")
        
        self.logger.debug(f"Filtered person tokens: {filtered_tokens}")
        self.logger.debug(f"Deduplicated person tokens: {deduplicated_tokens}")
        self.logger.debug(f"Sorted person tokens: {deduplicated_tokens}")
        
        
        return deduplicated_tokens

    def _deduplicate_consecutive_person_tokens(self, tokens: List[str], trace: List[TokenTrace]) -> List[str]:
        """
        Deduplicate identical person tokens using casefold() comparison.
        
        Args:
            tokens: List of person tokens
            trace: List of TokenTrace objects to add deduplication trace
            
        Returns:
            List of deduplicated tokens
        """
        if not tokens:
            return tokens
            
        deduplicated = []
        seen_tokens = set()
        skipped_tokens = []
        
        for token in tokens:
            # Check if this is an initial (single letter followed by dot)
            is_initial = len(token) == 2 and token[1] == '.' and token[0].isalpha()
            
            if is_initial:
                # Always allow initials, even if they're duplicates
                deduplicated.append(token)
            else:
                # For non-initials, apply normal deduplication
                token_key = token.casefold()
                if token_key not in seen_tokens:
                    deduplicated.append(token)
                    seen_tokens.add(token_key)
                else:
                    # Add trace for skipped duplicate
                    trace.append(TokenTrace(
                        token=token,
                        role="deduplication",
                        rule="dedup_consecutive_person_tokens",
                        output="[skipped]",
                        fallback=False,
                        notes=f"Skipped duplicate token: '{token}' (already seen)",
                        is_hyphenated_surname=False
                    ))
                    skipped_tokens.append(token)
        
        # Add trace for deduplication if any tokens were removed
        if skipped_tokens:
            removed_count = len(skipped_tokens)
            trace.append(TokenTrace(
                token="[deduplication]",
                role="deduplication",
                rule="dedup_consecutive_person_tokens",
                output=f"removed {removed_count} duplicate tokens",
                fallback=False,
                notes=f"Original: {tokens}, Deduplicated: {deduplicated}",
                is_hyphenated_surname=False
            ))
        
        return deduplicated

    def _extract_persons(
        self,
        original_tagged_tokens: List[Tuple[str, str]],
        normalized_tokens: List[str],
        roles: List[str],
        language: str
    ) -> List[Dict[str, Any]]:
        """Extract person groups from tokens using legacy logic."""
        persons = []
        current_person = []
        current_normalized = []

        # Create a mapping from original tokens to normalized tokens
        token_to_normalized = {}
        normalized_index = 0
        for i, (original_token, role) in enumerate(original_tagged_tokens):
            if role in PERSON_ROLES:
                if normalized_index < len(normalized_tokens):
                    token_to_normalized[i] = normalized_tokens[normalized_index]
                    normalized_index += 1

        # Separators that indicate person boundaries
        for i, (token, role) in enumerate(original_tagged_tokens):
            token_lower = token.lower().strip()

            # Skip empty tokens
            if not token_lower:
                continue

            # Check if this is a separator
            if token_lower in SEPARATOR_TOKENS or role == "unknown":
                # If we have a current person, finalize it
                if current_person:
                    person_data = self._finalize_person(current_person, current_normalized, language)
                    if person_data:
                        persons.append(person_data)
                    current_person = []
                    current_normalized = []
                continue

            # Check if this token belongs to a person
            if role in PERSON_ROLES:
                current_person.append((token, role))
                # Add corresponding normalized token
                if i in token_to_normalized:
                    current_normalized.append(token_to_normalized[i])
                else:
                    current_normalized.append(token)
            else:
                # If we have a current person and encounter non-person token, finalize it
                if current_person:
                    person_data = self._finalize_person(current_person, current_normalized, language)
                    if person_data:
                        persons.append(person_data)
                    current_person = []
                    current_normalized = []

        # Don't forget the last person
        if current_person:
            person_data = self._finalize_person(current_person, current_normalized, language)
            if person_data:
                persons.append(person_data)

        return persons

    def _finalize_person(
        self,
        person_tokens: List[Tuple[str, str]],
        normalized_tokens: List[str],
        language: str
    ) -> Optional[Dict[str, Any]]:
        """Finalize a person group by determining gender and building final structure."""
        if not person_tokens:
            return None

        # Extract tokens and roles
        tokens = [token for token, role in person_tokens]
        roles = [role for token, role in person_tokens]

        # Use normalized tokens if available
        final_tokens = normalized_tokens if normalized_tokens else tokens

        # Simple gender inference (can be enhanced)
        gender = self._infer_simple_gender(final_tokens, roles, language)

        return {
            "tokens": final_tokens,
            "original_tokens": tokens,
            "roles": roles,
            "gender": gender,
            "confidence": {
                "score_female": 0.0,
                "score_male": 0.0,
                "gap": 0.0
            }
        }

    def _infer_simple_gender(self, tokens: List[str], roles: List[str], language: str) -> Optional[str]:
        """Simple gender inference based on surname patterns."""
        for token, role in zip(tokens, roles):
            if role == "surname" and language in ["ru", "uk"]:
                if token.endswith(("а", "на", "ська", "цька")):
                    return "female"
                elif token.endswith(("ський", "цький", "ов", "ин", "енко")):
                    return "male"
        return None

    async def _classify_token_roles(
        self,
        tokens: List[str],
        config: NormalizationConfig,
        quoted_segments: List[str]
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Classify the role of each token, returning possibly expanded tokens."""
        
        # Handle English names with nameparser if enabled
        if config.language == "en":
            return await self._classify_english_names(tokens, config, quoted_segments)
        
        # Default classification for other languages
        tagged_tokens, traces, organizations = self.role_classifier.tag_tokens(
            tokens, config.language, quoted_segments
        )
        classified_tokens = [token for token, _ in tagged_tokens]
        roles = [role for _, role in tagged_tokens]
        if not classified_tokens:
            return tokens, ['unknown'] * len(tokens), traces, []
        return classified_tokens, roles, traces, organizations

    async def _classify_english_names(
        self,
        tokens: List[str],
        config: NormalizationConfig,
        quoted_segments: List[str]
    ) -> Tuple[List[str], List[str], List[str], List[str]]:
        """Classify English names using nameparser."""
        try:
            from ..nameparser_adapter import get_nameparser_adapter, NAMEPARSER_AVAILABLE

            # Check if we have initials - if so, use role_classifier instead of nameparser
            # to preserve individual initials (e.g., "J.. J. Smith" -> "J. J. Smith")
            has_initials = any(
                len(token) <= 2 and token.endswith('.') and token[0].isalpha()
                for token in tokens
            )

            # Check if we likely have multiple persons (3+ tokens suggests multiple names)
            # This prevents nameparser from merging multiple persons into one
            likely_multiple_persons = len(tokens) >= 3

            if has_initials or likely_multiple_persons:
                # Use role_classifier for proper initial handling
                tagged_tokens, traces, organizations = self.role_classifier.tag_tokens(
                    tokens, config.language, quoted_segments
                )
                classified_tokens = [token for token, _ in tagged_tokens]
                roles = [role for _, role in tagged_tokens]
                return classified_tokens, roles, traces, organizations

            # Get nameparser adapter
            nameparser = get_nameparser_adapter()
            
            # Check for comma reversal pattern: ["Surname", ",", "Given"] or ["Surname,", "Given"]
            if len(tokens) == 3 and tokens[1] == ',':
                # Comma reversal case: ["O'Connor", ",", "Sean"] -> ["Sean", "O'Connor"]
                surname = tokens[0]
                given = tokens[2]
                processed_tokens = [given, surname]
            elif len(tokens) == 2 and tokens[0].endswith(','):
                # Comma reversal case: ["O'Connor,", "Sean"] -> ["Sean", "O'Connor"]
                surname = tokens[0].rstrip(',')
                given = tokens[1]
                processed_tokens = [given, surname]
            else:
                # Normal processing for other cases
                processed_tokens = []
                for token in tokens:
                    if '-' in token and not token.startswith('-') and not token.endswith('-'):
                        # Only split hyphens if nameparser is available, otherwise preserve hyphenated surnames
                        if NAMEPARSER_AVAILABLE:
                            parts = token.split('-')
                            processed_tokens.extend(parts)
                        else:
                            processed_tokens.append(token)
                    elif "'" in token and not token.startswith("'") and not token.endswith("'"):
                        # For apostrophes, preserve the token but normalize the apostrophe
                        normalized_token = token.replace("'", "'")
                        processed_tokens.append(normalized_token)
                    elif ',' in token:
                        # Handle comma-separated names within a single token
                        parts = [part.strip() for part in token.split(',')]
                        if len(parts) == 2 and parts[0] and parts[1]:
                            # Reverse order for comma-separated names: Last, First -> First Last
                            processed_tokens.extend([parts[1], parts[0]])
                        else:
                            # Remove comma and use as single token
                            processed_tokens.append(token.rstrip(','))
                    else:
                        processed_tokens.append(token)
            
            # Join tokens to form full name for parsing
            full_name = " ".join(processed_tokens)
            
            # Parse the name
            parsed = nameparser.parse_en_name(full_name, enable_nicknames=config.enable_en_nicknames, filter_titles_suffixes=config.filter_titles_suffixes)
            
            if parsed.confidence < 0.3:
                # Low confidence, try nickname resolution for single names
                if len(tokens) == 1 and config.enable_en_nicknames:
                    # Try to resolve single name as nickname
                    resolved_name, nickname_traces = self._resolve_english_nickname(tokens[0], config)
                    if resolved_name != tokens[0]:
                        # Nickname was resolved, treat as given name
                        return [resolved_name], ["given"], nickname_traces, []
                
                # Fall back to default classification using processed tokens (comma-reversed, etc.)
                tagged_tokens, traces, organizations = self.role_classifier.tag_tokens(
                    processed_tokens, config.language, quoted_segments
                )
                classified_tokens = [token for token, _ in tagged_tokens]
                roles = [role for _, role in tagged_tokens]
                return classified_tokens, roles, traces, organizations
            
            # Build classified tokens and roles from parsed name
            classified_tokens = []
            roles = []
            traces = []
            organizations = []
            
            # Add first name with nickname resolution
            if parsed.first:
                # Apply nickname resolution if enabled
                if config.enable_en_nicknames:
                    resolved_first, nickname_traces = self._resolve_english_nickname(parsed.first, config)
                    traces.extend(nickname_traces)
                    classified_tokens.append(resolved_first)
                else:
                    classified_tokens.append(parsed.first)
                
                roles.append("given")
                if parsed.nickname and config.enable_en_nicknames:
                    traces.append(f"Nickname expansion: '{parsed.nickname}' -> '{parsed.first}'")
                else:
                    traces.append(f"First name: '{parsed.first}'")
            
            # Skip middle names for normalization (remove them from output)
            # Add trace for debugging but don't include in tokens
            for middle in parsed.middles:
                traces.append(f"Middle name '{middle}' removed for normalization")
            
            # Add last name with particles
            if parsed.last:
                if parsed.particles:
                    # Reconstruct last name with particles
                    last_with_particles = " ".join(parsed.particles + [parsed.last])
                    classified_tokens.append(last_with_particles)
                    roles.append("surname")
                    traces.append(f"Surname with particles: '{last_with_particles}'")
                else:
                    classified_tokens.append(parsed.last)
                    roles.append("surname")
                    traces.append(f"Surname: '{parsed.last}'")
            
            # Add title (only if title/suffix filtering is disabled)
            if parsed.title and not config.filter_titles_suffixes:
                classified_tokens.append(parsed.title)
                roles.append("title")
                traces.append(f"Title: '{parsed.title}'")
            elif parsed.title:
                traces.append(f"Title filtered out: '{parsed.title}'")
            
            # Add suffix (only if title/suffix filtering is disabled)
            if parsed.suffix and not config.filter_titles_suffixes:
                classified_tokens.append(parsed.suffix)
                roles.append("suffix")
                traces.append(f"Suffix: '{parsed.suffix}'")
            elif parsed.suffix:
                traces.append(f"Suffix filtered out: '{parsed.suffix}'")
            
            # If no valid components found, fall back to original tokens
            if not classified_tokens:
                return tokens, ['unknown'] * len(tokens), ["No valid name components found"], []
            
            # For now, return the classified tokens as-is
            # TODO: Implement proper hyphen/apostrophe handling
            return classified_tokens, roles, traces, organizations
            
        except Exception as e:
            self.logger.warning(f"English name parsing failed: {e}")
            # Fall back to default classification
            tagged_tokens, traces, organizations = self.role_classifier.tag_tokens(
                tokens, config.language, quoted_segments
            )
            classified_tokens = [token for token, _ in tagged_tokens]
            roles = [role for _, role in tagged_tokens]
            return classified_tokens, roles, traces, organizations

    async def _normalize_english_morphology(
        self,
        tokens: List[str],
        roles: List[str],
        config: NormalizationConfig
    ) -> Tuple[List[str], List[str]]:
        """Apply English-specific morphological normalization."""
        normalized_tokens = []
        traces = []
        
        for token, role in zip(tokens, roles):
            if role in {'given', 'surname', 'patronymic', 'initial', 'suffix'}:
                # Apply nickname resolution if enabled
                if config.enable_en_nicknames and role == 'given':
                    normalized, nickname_traces = self._resolve_english_nickname(token, config)
                    traces.extend(nickname_traces)
                else:
                    normalized = token
                
                # Apply title case normalization for English names
                normalized = self._normalize_english_name_token(normalized, role, config)
                normalized_tokens.append(normalized)
                if normalized != token:
                    traces.append(f"English normalization: '{token}' -> '{normalized}'")
                else:
                    traces.append(f"English token unchanged: '{token}'")
            else:
                normalized_tokens.append(token)
                traces.append(f"No English normalization for role '{role}': '{token}'")
        
        return normalized_tokens, traces

    def _normalize_english_name_token(self, token: str, role: str, config: NormalizationConfig) -> str:
        """Normalize a single English name token."""
        if not token:
            return token
        
        # Normalize apostrophes to canonical form for person tokens
        if role in {'given', 'surname', 'patronymic', 'initial'} and "'" in token:
            token = self._normalize_apostrophe(token)
        
        # Handle apostrophes and hyphens
        if "'" in token or "-" in token:
            # Preserve apostrophes and hyphens, normalize case
            return self._title_case_with_punctuation(token)
        
        # Apply title case
        return token.title()
    
    def _normalize_apostrophe(self, token: str) -> str:
        """Normalize apostrophes to canonical form."""
        if not token:
            return token
        
        # Replace ASCII apostrophe with canonical apostrophe
        return token.replace("'", "'")

    def _title_case_with_punctuation(self, token: str) -> str:
        """Apply title case while preserving punctuation."""
        if not token:
            return token
        
        # Split by common punctuation but preserve it
        parts = []
        current = ""
        
        for char in token:
            if char in ["'", "-", "."]:
                if current:
                    parts.append(current.title())
                    current = ""
                parts.append(char)
            else:
                current += char
        
        if current:
            parts.append(current.title())
        
        return "".join(parts)

    def _resolve_english_nickname(self, token: str, config: NormalizationConfig) -> Tuple[str, List[str]]:
        """Resolve English nickname to full name."""
        if not token:
            return token, []
        
        traces = []
        
        try:
            from ..nameparser_adapter import get_nameparser_adapter
            
            # Get nameparser adapter
            nameparser = get_nameparser_adapter()
            
            # Check if token is a nickname
            expanded, was_expanded = nameparser.expand_nickname(token)
            
            if was_expanded:
                traces.append(f"nickname.resolved: '{token}' -> '{expanded}'")
                return expanded, traces
            else:
                traces.append(f"nickname.resolved: '{token}' (no expansion found)")
                return token, traces
                
        except Exception as e:
            self.logger.warning(f"English nickname resolution failed for '{token}': {e}")
            traces.append(f"nickname.resolved: '{token}' (resolution failed: {e})")
            return token, traces

    def _normalize_english_tokens(
        self,
        tokens: List[str],
        roles: List[str],
        config: NormalizationConfig
    ) -> Tuple[List[str], List[TokenTrace]]:
        """
        Normalize English tokens with title/suffix removal, nickname resolution, 
        apostrophe normalization, and hyphenated surname handling.
        
        Args:
            tokens: List of tokens to normalize
            roles: List of corresponding roles
            config: Normalization configuration
            
        Returns:
            Tuple of (normalized_tokens, traces)
        """
        if not tokens:
            return tokens, []
        
        # Load English lexicons if not already loaded
        if not hasattr(self, '_en_titles'):
            self._load_english_lexicons()
        
        # Check gate conditions
        gates = self._check_english_gates(config)
        
        normalized_tokens = []
        traces = []
        
        for i, (token, role) in enumerate(zip(tokens, roles)):
            original_token = token
            current_traces = []
            
            # Skip non-personal tokens
            if role not in {'given', 'surname', 'patronymic', 'initial', 'suffix', 'unknown'}:
                normalized_tokens.append(token)
                continue
            
            # Step 1: Remove titles and suffixes (gate: en_title_suffix)
            if gates['en_title_suffix']:
                # Remove titles (Mr, Mrs, Ms, Dr, Prof, etc.)
                if token in self._en_titles:
                    current_traces.append(TokenTrace(
                        token=token,
                        role=role,
                        rule="en.title_stripped",
                        output="",
                        fallback=False,
                        notes=f"Removed English title: {token}"
                    ))
                    traces.extend(current_traces)
                    continue  # Skip this token entirely
                
                # Remove suffixes (Jr, Sr, II, III, etc.)
                if token in self._en_suffixes:
                    current_traces.append(TokenTrace(
                        token=token,
                        role=role,
                        rule="en.suffix_stripped",
                        output="",
                        fallback=False,
                        notes=f"Removed English suffix: {token}"
                    ))
                    traces.extend(current_traces)
                    continue  # Skip this token entirely
            
            # Step 2: Resolve nicknames for given names (gate: en_nickname)
            if gates['en_nickname'] and role == 'given' and token.lower() in self._en_nicknames:
                full_name = self._en_nicknames[token.lower()]
                # Apply title case to the resolved name
                token = full_name.title()
                current_traces.append(TokenTrace(
                    token=original_token,
                    role=role,
                    rule="en.nickname_resolved",
                    output=token,
                    fallback=False,
                    notes=f"Resolved nickname: {original_token} -> {token}"
                ))
            
            # Step 3: Normalize apostrophes (gate: en_apostrophe)
            if gates['en_apostrophe'] and "'" in token:
                # Normalize apostrophe type (curly vs straight)
                normalized_apostrophe = token.replace("'", "'").replace("'", "'")
                if normalized_apostrophe != token:
                    token = normalized_apostrophe
                    current_traces.append(TokenTrace(
                        token=original_token,
                        role=role,
                        rule="token.apostrophe_preserved",
                        output=token,
                        fallback=False,
                        notes=f"Normalized apostrophe type: {original_token} -> {token}"
                    ))
            
            # Step 4: Handle hyphenated surnames (gate: en_double_surname)
            if gates['en_double_surname'] and '-' in token and role in {'surname', 'given'}:
                # Apply title case to each segment
                segments = token.split('-')
                titlecased_segments = [seg.title() for seg in segments]
                hyphenated_token = '-'.join(titlecased_segments)
                
                if hyphenated_token != token:
                    token = hyphenated_token
                    current_traces.append(TokenTrace(
                        token=original_token,
                        role=role,
                        rule="token.hyphenated_case",
                        output=token,
                        fallback=False,
                        notes=f"Applied title case to hyphenated segments: {original_token} -> {token}"
                    ))
            else:
                # Apply regular title case for non-hyphenated tokens
                if role in {'given', 'surname', 'patronymic'}:
                    titlecased_token = token.title()
                    if titlecased_token != token:
                        token = titlecased_token
                        current_traces.append(TokenTrace(
                            token=original_token,
                            role=role,
                            rule="en.title_case",
                            output=token,
                            fallback=False,
                            notes=f"Applied title case: {original_token} -> {token}"
                        ))
            
            normalized_tokens.append(token)
            traces.extend(current_traces)
        
        return normalized_tokens, traces

    def _load_english_lexicons(self) -> None:
        """Load English lexicon files."""
        try:
            # Load English titles
            titles_path = Path(__file__).resolve().parents[5] / "data" / "lexicons" / "en_titles.txt"
            with open(titles_path, 'r', encoding='utf-8') as f:
                self._en_titles = {line.strip() for line in f if line.strip()}
            
            # Load English suffixes
            suffixes_path = Path(__file__).resolve().parents[5] / "data" / "lexicons" / "en_suffixes.txt"
            with open(suffixes_path, 'r', encoding='utf-8') as f:
                self._en_suffixes = {line.strip() for line in f if line.strip()}
            
            # Load English nicknames
            nicknames_path = Path(__file__).resolve().parents[5] / "data" / "lexicons" / "en_nicknames.json"
            with open(nicknames_path, 'r', encoding='utf-8') as f:
                self._en_nicknames = json.load(f)
            
            self.logger.info(f"Loaded English lexicons: titles={len(self._en_titles)}, suffixes={len(self._en_suffixes)}, nicknames={len(self._en_nicknames)}")
            
        except Exception as e:
            self.logger.error(f"Failed to load English lexicons: {e}")
            # Set empty dictionaries as fallback
            self._en_titles = set()
            self._en_suffixes = set()
            self._en_nicknames = {}

    def _check_english_gates(self, config: NormalizationConfig) -> Dict[str, bool]:
        """
        Check English normalization gate conditions.
        
        Args:
            config: Normalization configuration
            
        Returns:
            Dictionary with gate status for each feature
        """
        gates = {
            'en_title_suffix': config.enable_nameparser_en or config.enable_en_rules,
            'en_nickname': config.enable_en_nicknames,
            'en_apostrophe': config.enable_nameparser_en or config.enable_en_rules,
            'en_double_surname': config.enable_nameparser_en or config.enable_en_rules
        }
        
        # Log gate status
        enabled_gates = [name for name, enabled in gates.items() if enabled]
        if enabled_gates:
            self.logger.debug(f"English normalization gates enabled: {enabled_gates}")
        else:
            self.logger.debug("All English normalization gates disabled")
        
        return gates

    async def _normalize_morphology(
        self,
        tokens: List[str],
        roles: List[str],
        config: NormalizationConfig,
        *,
        skip_indices: Optional[Set[int]] = None,
        effective_flags: Optional[Any] = None,
    ) -> Tuple[List[str], List[str]]:
        """Apply morphological normalization to tokens with caching support."""
        if not config.enable_morphology or not config.enable_advanced_features:
            return tokens, ["Morphological normalization disabled"]

        # For English, apply English-specific token normalization
        if config.language == "en":
            # Apply English token normalization if enabled
            if config.enable_en_rules or config.enable_nameparser_en:
                normalized_tokens, en_traces = self._normalize_english_tokens(tokens, roles, config)
                return normalized_tokens, en_traces
            else:
                return await self._normalize_english_morphology(tokens, roles, config)

        normalized_tokens = []
        traces = []
        cache_info = {}  # Track cache hits/misses for debug tracing

        skip_set: Set[int] = skip_indices or set()

        for index, (token, role) in enumerate(zip(tokens, roles)):
            try:
                # Only skip morphology for tokens that were successfully resolved as diminutives
                # skip_set contains indices of unresolved diminutive lookups, not resolved ones
                # So we should NOT skip morphology for these - they need morphological processing
                # The skip logic here is incorrect and breaks morphology for normal declensions
                
                if role in {'given', 'surname', 'patronymic', 'initial'}:
                    if config.enable_cache:
                        # Use cached morphology adapter with new to_nominative_cached method
                        # Create feature flags object
                        if effective_flags is not None:
                            feature_flags = FeatureFlags(
                                enforce_nominative=getattr(effective_flags, 'enforce_nominative', True),
                                preserve_feminine_surnames=getattr(effective_flags, 'preserve_feminine_surnames', True),
                                morphology_custom_rules_first=getattr(effective_flags, 'morphology_custom_rules_first', True)
                            )
                        else:
                            # Use default feature flags
                            feature_flags = FeatureFlags()
                        
                        # Use the new to_nominative_cached method
                        print(f"DEBUG: Processing token '{token}' with role '{role}' and flags morphology_custom_rules_first={feature_flags.morphology_custom_rules_first}")
                        normalized, trace_note = self.morphology_adapter.to_nominative_cached(
                            token,
                            config.language,
                            feature_flags,
                            role
                        )
                        print(f"DEBUG: Result: '{token}' -> '{normalized}' (trace: {trace_note})")
                        
                        # Record cache info for debug tracing
                        cache_info[token] = {
                            'morph': 'hit'  # Assume hit since we're using cached method
                        }
                        
                        # Record metrics
                        self.metrics_collector.collect_morphology_metrics(
                            config.language,
                            self.morphology_adapter.get_stats()
                        )
                        
                        # Add trace based on trace_note
                        if trace_note == "morph.to_nominative":
                            traces.append(f"Morphology normalization: '{token}' -> '{normalized}'")
                        elif trace_note == "morph.preserve_feminine":
                            traces.append(f"Preserved feminine surname: '{token}' -> '{normalized}'")
                        elif trace_note == "morph.nominal_noop":
                            traces.append(f"No morphological change needed: '{token}'")
                        else:
                            traces.append(f"Morphology processing: '{token}' -> '{normalized}' ({trace_note})")
                    else:
                        # Use direct morphology processor
                        morph_result = self.morphology_processor.normalize_slavic_token(
                            token, role, config.language, config.enable_advanced_features,
                            config.preserve_feminine_suffix_uk
                        )
                        # morph_result is a tuple (normalized_token, trace_info)
                        normalized, morph_traces = morph_result
                        traces.extend(morph_traces)
                        cache_info[token] = {'morph': 'disabled'}
                    
                    if normalized:
                        normalized_tokens.append(normalized)
                    else:
                        normalized_tokens.append(token)
                        traces.append(f"Morphological normalization returned None for '{token}'")
                else:
                    normalized_tokens.append(token)
                    traces.append(f"No morphological processing for role '{role}'")
            except Exception as e:
                self.logger.warning(f"Morphological normalization failed for '{token}': {e}")
                normalized_tokens.append(token)
                traces.append(f"Morphological normalization failed for '{token}': {e}")

        # Store cache info for debug tracing
        if config.debug_tracing:
            self._debug_cache_info = cache_info

        return normalized_tokens, traces

    async def _process_gender(
        self,
        tokens: List[str],
        roles: List[str],
        config: NormalizationConfig
    ) -> Tuple[List[str], List[str], Dict[str, Any]]:
        """Process gender inference and surname adjustment."""
        if not config.enable_gender_adjustment or not config.enable_advanced_features:
            return tokens, ["Gender processing disabled"], {}

        # Check for multiple persons (skip gender adjustment for multiple persons)
        given_count = sum(1 for role in roles if role == 'given')
        has_comma = ',' in tokens
        unknown_count = sum(1 for role in roles if role == 'unknown')

        # If we have multiple given names, comma, or many unknown tokens (like "Мария" classified as unknown)
        # then this is likely multiple persons - skip global gender adjustment
        if given_count > 1 or has_comma or unknown_count > 2:
            return tokens, ["Gender processing skipped: multiple persons detected"], {}

        traces = []
        gender_info = {}

        try:
            # Infer gender from tokens
            gender, confidence, evidence = self.gender_processor.infer_gender(
                tokens, roles, config.language
            )

            gender_info = {
                'person_gender': gender,
                'gender_confidence': confidence
            }

            traces.extend(evidence)

            if gender and confidence > 0.6:
                # Adjust surnames if needed
                adjusted_tokens = []
                for token, role in zip(tokens, roles):
                    if role == 'surname':
                        adjusted, was_changed, adjust_traces = self.gender_processor.adjust_surname_gender(
                            token, gender, config.language
                        )
                        adjusted_tokens.append(adjusted)
                        traces.extend(adjust_traces)

                        if was_changed:
                            traces.append(f"Surname gender adjusted: '{token}' -> '{adjusted}'")
                    else:
                        adjusted_tokens.append(token)

                return adjusted_tokens, traces, gender_info
            else:
                traces.append(f"Gender confidence too low ({confidence:.2f}) for adjustment")

        except Exception as e:
            self.logger.warning(f"Gender processing failed: {e}")
            traces.append(f"Gender processing failed: {e}")

        return tokens, traces, gender_info

    def _reconstruct_text(self, tokens: List[str], roles: List[str], language: str = "auto") -> str:
        """Reconstruct normalized text from tokens."""
        # Only include personal tokens (not unknown/organization tokens)
        personal_tokens = []
        for token, role in zip(tokens, roles):
            if role in {'given', 'surname', 'patronymic', 'initial'}:
                personal_tokens.append((token, role))

        # Sort tokens by role: given, surname, patronymic, initial (language-dependent)
        if language == "uk":
            # Ukrainian order: surname given patronymic
            role_order = {'surname': 0, 'given': 1, 'patronymic': 2, 'initial': 3}
        else:
            # Default order: given surname patronymic
            role_order = {'given': 0, 'surname': 1, 'patronymic': 2, 'initial': 3}
        personal_tokens.sort(key=lambda x: role_order.get(x[1], 999))
        
        # Extract just the tokens
        sorted_tokens = [token for token, role in personal_tokens]

        return " ".join(sorted_tokens) if sorted_tokens else ""

    def _build_token_trace(
        self,
        original_tokens: List[str],
        roles: List[str],
        final_tokens: List[str],
        processing_traces: List[str],
        cache_info: Optional[Dict[str, Dict[str, str]]] = None
    ) -> List[TokenTrace]:
        """Build detailed token trace for debugging."""
        trace = []
        
        # Ensure final_tokens is a list
        if isinstance(final_tokens, str):
            self.logger.error(f"ERROR: final_tokens is a string '{final_tokens}' instead of list! Converting to list of characters.")
            final_tokens = list(final_tokens)
        elif not isinstance(final_tokens, list):
            self.logger.error(f"ERROR: final_tokens is {type(final_tokens)} instead of list! Converting to list.")
            final_tokens = list(final_tokens) if final_tokens else []

        for i, (orig, role) in enumerate(zip(original_tokens, roles)):
            # CRITICAL FIX: Ensure final_tokens and original_tokens are synchronized
            if i < len(final_tokens):
                final = final_tokens[i]
            else:
                # If final_tokens is shorter, this means token was filtered out
                final = ""  # Empty output indicates filtered token
                self.logger.warning(f"Token '{orig}' at index {i} was filtered out (final_tokens length: {len(final_tokens)})")

            # Find relevant traces for this token
            token_traces = [t for t in processing_traces if orig in t or str(i) in t]

            # Create comprehensive rule description
            rule_parts = []
            if role in PERSON_ROLES:
                rule_parts.append(f"role_classification:{role}")
            if orig != final:
                rule_parts.append("morphological_normalization")
            if not rule_parts:
                rule_parts.append("passthrough")

            # Add cache information if available
            cache_data = None
            if cache_info and orig in cache_info:
                cache_data = cache_info[orig]

            # Detect if this is a hyphenated surname
            is_hyphenated = is_hyphenated_surname(orig)

            # Add flags including ner_disabled
            flags = {}
            if self.ner_disabled:
                flags['ner_disabled'] = True

            trace.append(TokenTrace(
                token=orig,
                role=role,
                rule=" + ".join(rule_parts),
                output=final,
                cache=cache_data,
                fallback=final == orig,
                notes="; ".join(token_traces[:2]),  # Limit notes length
                is_hyphenated_surname=is_hyphenated,
                flags=flags if flags else None
            ))

        return trace

    def _apply_tokenizer_improvements(
        self,
        tokens: List[str],
        base_traces: List[TokenTrace],
        effective_flags
    ) -> Tuple[List[str], List[TokenTrace]]:
        """
        Apply tokenizer improvements based on feature flags.

        Args:
            tokens: Original tokens from tokenization
            base_traces: Original traces from tokenization

        Returns:
            Tuple of (improved_tokens, improvement_traces)
        """
        improved_tokens = tokens[:]
        improvement_traces = []
        trace_steps = [] if getattr(effective_flags, 'debug_tracing', False) else None

        self.logger.debug(f"Tokenizer improvements: fix_initials={getattr(effective_flags, 'fix_initials_double_dot', True)}, preserve_hyphenated={getattr(effective_flags, 'preserve_hyphenated_case', True)}")

        # Apply double dot collapse if enabled
        if getattr(effective_flags, 'fix_initials_double_dot', True):
            self.logger.debug(f"Applying double dot collapse to tokens: {improved_tokens}")
            original_count = len(improved_tokens)
            original_tokens = improved_tokens[:]
            
            # Always pass trace_steps to get detailed traces
            trace_steps = []
            improved_tokens = collapse_double_dots(improved_tokens, trace=trace_steps)
            self.logger.debug(f"After collapse: {improved_tokens}")

            dots_collapsed = original_count - len(improved_tokens)
            # Also check if any tokens actually changed
            tokens_changed = [i for i, (orig, new) in enumerate(zip(original_tokens, improved_tokens)) if orig != new]

            if dots_collapsed > 0 or tokens_changed:
                improvement_traces.append(TokenTrace(
                    token="[tokenizer]",
                    role="tokenizer",
                    rule="collapse_double_dots",
                    output=f"collapsed {dots_collapsed} double dots",
                    fallback=False,
                    notes=f"Changed tokens: {tokens_changed}"
                ))
                self.logger.debug(f"Double dots collapsed: {dots_collapsed}, changed tokens: {tokens_changed}")
            
            # Add detailed trace steps
            if trace_steps:
                for trace_step in trace_steps:
                    improvement_traces.append(TokenTrace(
                        token=trace_step.get('token_before', ''),
                        role="tokenizer",
                        rule=trace_step.get('rule', 'unknown'),
                        output=trace_step.get('token_after', ''),
                        fallback=False,
                        notes=f"Stage: {trace_step.get('stage', 'tokenize')}"
                    ))

        # Apply hyphenated name normalization if enabled
        if getattr(effective_flags, 'preserve_hyphenated_case', True):
            for i, token in enumerate(improved_tokens):
                if '-' in token:
                    original = token
                    normalized = normalize_hyphenated_name(token, titlecase=True, trace=trace_steps)
                    if normalized != original:
                        improved_tokens[i] = normalized
                    improvement_traces.append(TokenTrace(
                        token=original,
                        role="tokenizer",
                        rule="normalize_hyphen",
                        output=improved_tokens[i],
                        fallback=False,
                        notes=f"Normalized hyphenated name: {original} -> {improved_tokens[i]}"
                    ))

        # Convert trace_steps to improvement_traces format if we have any
        if trace_steps:
            for trace_step in trace_steps:
                # Convert trace_step dict to improvement_traces format
                    improvement_traces.append(TokenTrace(
                        token=trace_step.get('token_before', ''),
                        role="tokenizer",
                        rule=trace_step.get('rule', 'unknown'),
                        output=trace_step.get('token_after', ''),
                        fallback=False,
                        notes=f"Stage: {trace_step.get('stage', 'tokenize')}"
                    ))

        return improved_tokens, improvement_traces

    def _apply_tokenizer_improvements_post(
        self,
        tokens: List[str],
        roles: List[str],
        effective_flags
    ) -> Tuple[List[str], List[TokenTrace]]:
        """
        Apply tokenizer improvements after morphological processing.

        This is specifically for fixing issues that occur during morphological
        processing, like initials getting extra dots added.

        Args:
            tokens: Tokens after morphological processing
            roles: Corresponding roles for tokens

        Returns:
            Tuple of (improved_tokens, improvement_traces)
        """
        improved_tokens = tokens[:]
        improvement_traces = []
        trace_steps = [] if getattr(effective_flags, 'debug_tracing', False) else None

        self.logger.debug(f"Post-processing tokenizer improvements: fix_initials={getattr(effective_flags, 'fix_initials_double_dot', True)}")

        # Apply double dot collapse to initials if enabled
        if getattr(effective_flags, 'fix_initials_double_dot', True):
            for i, (token, role) in enumerate(zip(improved_tokens, roles)):
                # Process any token with double dots, not just initials
                if ".." in token:
                    original = token
                    # Apply collapse_double_dots to single token
                    result = collapse_double_dots([token], trace=trace_steps)
                    improved = result[0] if isinstance(result, list) and len(result) > 0 else token
                    if improved != original:
                        improved_tokens[i] = improved
                        improvement_traces.append(TokenTrace(
                            token=original,
                            role="tokenizer",
                            rule="collapse_double_dots_post",
                            output=improved,
                            fallback=False,
                            notes=f"Role: {role}"
                        ))
                        self.logger.debug(f"Post-processing: collapsed '{original}' to '{improved}' for role '{role}'")

        # Apply hyphenated name normalization if enabled
        if getattr(effective_flags, 'preserve_hyphenated_case', True):
            for i, (token, role) in enumerate(zip(improved_tokens, roles)):
                if '-' in token and role in ("surname", "given"):
                    original = token
                    # Apply normalize_hyphenated_name
                    improved = normalize_hyphenated_name(token, titlecase=True, trace=trace_steps)
                    if improved != original:
                        improved_tokens[i] = improved
                        improvement_traces.append(TokenTrace(
                            token=original,
                            role="tokenizer",
                            rule="normalize_hyphen_post",
                            output=improved,
                            fallback=False,
                            notes=f"Role: {role}"
                        ))
                        self.logger.debug(f"Post-processing: normalized hyphenated '{original}' to '{improved}' for role '{role}'")

        # Convert trace_steps to improvement_traces format if we have any
        if trace_steps:
            for trace_step in trace_steps:
                # Convert trace_step dict to improvement_traces format
                    improvement_traces.append(TokenTrace(
                        token=trace_step.get('token_before', ''),
                        role="tokenizer",
                        rule=trace_step.get('rule', 'unknown'),
                        output=trace_step.get('token_after', ''),
                        fallback=False,
                        notes=f"Stage: {trace_step.get('stage', 'tokenize')}"
                    ))

        return improved_tokens, improvement_traces

    def _apply_yo_strategy(self, tokens: List[str], strategy: str) -> Tuple[List[str], List[TokenTrace]]:
        """
        Apply Russian 'ё' strategy to tokens.
        
        Args:
            tokens: List of tokens to process
            strategy: 'preserve' or 'fold'
            
        Returns:
            Tuple of (processed_tokens, trace_entries)
        """
        processed_tokens = []
        trace_entries = []
        
        for token in tokens:
            if strategy == "fold" and ('ё' in token or 'Ё' in token):
                # Apply ё → е conversion
                processed_token = token.replace('ё', 'е').replace('Ё', 'Е')
                processed_tokens.append(processed_token)
                
                # Add trace for yo.fold
                trace_entries.append(TokenTrace(
                    token=token,
                    role="unknown",  # Will be determined later by role tagger
                    rule="yo.fold",
                    normal_form=processed_token,
                    output=processed_token,
                    fallback=False,
                    notes=f"yo_strategy_{strategy}: ё → е",
                    is_hyphenated_surname=is_hyphenated_surname(token)
                ))
            else:
                # Preserve original token
                processed_tokens.append(token)
        
        return processed_tokens, trace_entries

    def clear_caches(self):
        """Clear all processor caches."""
        self.morphology_processor.clear_cache()
        self.diminutive_resolver.clear_cache()
        self._normalization_cache.clear()
        self.logger.info("All processor caches cleared")

    def get_statistics(self) -> Dict[str, Any]:
        """Get processing statistics."""
        return {
            'cache_size': len(self._normalization_cache),
            'processors': {
                'token_processor': type(self.token_processor).__name__,
                'role_classifier': type(self.role_classifier).__name__,
                'morphology_processor': type(self.morphology_processor).__name__,
                'gender_processor': type(self.gender_processor).__name__,
                'diminutive_resolver': type(self.diminutive_resolver).__name__,
            }
        }

    def _apply_diminutive_resolution(
        self,
        tokens: List[str],
        roles: List[str],
        language: str,
        *,
        allow_cross_lang: bool,
    ) -> Tuple[List[str], List[str], Set[int]]:
        resolved_tokens: List[str] = []
        traces: List[str] = []
        unresolved_indices: Set[int] = set()

        allowed_roles = {"given", "nickname", "unknown", "surname"}

        for idx, (token, role) in enumerate(zip(tokens, roles)):
            if role in allowed_roles:
                canonical = self.diminutive_resolver.resolve(
                    token,
                    language,
                    allow_cross_lang=allow_cross_lang,
                )
                if canonical:
                    resolved_tokens.append(canonical)
                    normalized_original = unicodedata.normalize("NFC", token).lower()
                    if role != "given":
                        roles[idx] = "given"
                    if canonical != normalized_original:
                        traces.append(
                            json.dumps(
                                {
                                    "type": "morph",
                                    "action": "diminutive_resolved",
                                    "from": token,
                                    "to": canonical,
                                    "lang": language,
                                },
                                ensure_ascii=False,
                            )
                        )
                    continue
                unresolved_indices.add(idx)

            resolved_tokens.append(token)

        return resolved_tokens, traces, unresolved_indices

    def _apply_diminutives(
        self,
        tokens: List[str],
        roles: List[str],
        language: str,
        effective_flags
    ) -> Tuple[List[str], List[str], Set[int]]:
        """
        Apply diminutives dictionary-only mapping for RU/UK/EN languages.
        
        Args:
            tokens: List of tokens to process
            roles: List of corresponding roles
            language: Language code ('ru', 'uk', or 'en')
            effective_flags: Feature flags object
            
        Returns:
            Tuple of (resolved_tokens, traces, unresolved_indices)
        """
        resolved_tokens: List[str] = []
        traces: List[str] = []
        unresolved_indices: Set[int] = set()
        
        # Load diminutives dictionaries if not already loaded
        if not hasattr(self, '_diminutives_ru'):
            self._load_diminutives_dictionaries()
        
        # Get the appropriate dictionary
        if language == "ru":
            diminutives_dict = self._diminutives_ru
        elif language == "uk":
            diminutives_dict = self._diminutives_uk
        elif language == "en":
            # Check if English nicknames are enabled
            if not getattr(effective_flags, 'enable_en_nicknames', True):
                # English nicknames disabled, return tokens as-is
                return tokens, [], set()
            diminutives_dict = self._diminutives_en
        else:
            # For unsupported languages, return tokens as-is
            return tokens, [], set()
        
        allowed_roles = {"given", "nickname", "unknown", "surname"}
        
        for idx, (token, role) in enumerate(zip(tokens, roles)):
            if role in allowed_roles:
                # Look up in dictionary using lowercase key
                token_lower = token.lower()
                canonical = diminutives_dict.get(token_lower)
                
                if canonical:
                    resolved_tokens.append(canonical)
                    # Update role to 'given' if it was a diminutive
                    if role != "given":
                        roles[idx] = "given"
                    
                    # Add trace
                    traces.append(
                        json.dumps(
                            {
                                "type": "morph",
                                "action": "diminutive_resolved",
                                "from": token,
                                "to": canonical,
                                "lang": language,
                                "rule": "morph.diminutive_resolved"
                            },
                            ensure_ascii=False,
                        )
                    )
                    continue
                else:
                    # No mapping found, mark as unresolved
                    unresolved_indices.add(idx)
            
            resolved_tokens.append(token)
        
        return resolved_tokens, traces, unresolved_indices

    def _load_diminutives_dictionaries(self) -> None:
        """Load diminutives dictionaries from data files."""
        try:
            # Load Russian diminutives
            ru_path = Path(__file__).resolve().parents[5] / "data" / "diminutives_ru.json"
            with open(ru_path, 'r', encoding='utf-8') as f:
                self._diminutives_ru = json.load(f)
            
            # Load Ukrainian diminutives
            uk_path = Path(__file__).resolve().parents[5] / "data" / "diminutives_uk.json"
            with open(uk_path, 'r', encoding='utf-8') as f:
                self._diminutives_uk = json.load(f)
            
            # Load English nicknames
            en_path = Path(__file__).resolve().parents[5] / "data" / "lexicons" / "en_nicknames.json"
            with open(en_path, 'r', encoding='utf-8') as f:
                self._diminutives_en = json.load(f)
                
            self.logger.info(f"Loaded diminutives dictionaries: RU={len(self._diminutives_ru)} entries, UK={len(self._diminutives_uk)} entries, EN={len(self._diminutives_en)} entries")
            
        except Exception as e:
            self.logger.error(f"Failed to load diminutives dictionaries: {e}")
            # Set empty dictionaries as fallback
            self._diminutives_ru = {}
            self._diminutives_uk = {}
            self._diminutives_en = {}

    def _create_role_tagger_traces(self, role_tags: List) -> List[str]:
        """Create traces for role tagger results."""
        traces = []

        # Count roles for summary
        role_counts = {}
        stopword_count = 0
        org_count = 0

        for tag in role_tags:
            role_counts[tag.role] = role_counts.get(tag.role, 0) + 1
            if tag.role == "stopword":
                stopword_count += 1
            elif tag.role == "organization":
                org_count += 1

        # Add summary traces as strings
        if stopword_count > 0:
            traces.append(f"Role tagger: filtered {stopword_count} stopwords")

        if org_count > 0:
            traces.append(f"Role tagger: detected {org_count} organization tokens")

        return traces

    def _create_fsm_role_tagger_traces(self, role_tags: List, tokens: List[str]) -> List[str]:
        """Create traces for FSM role tagger results."""
        traces = []
        
        # Count roles for summary
        role_counts = {}
        org_count = 0
        unknown_count = 0
        
        for tag in role_tags:
            role_counts[tag.role.value] = role_counts.get(tag.role.value, 0) + 1
            if tag.role.value == "org":
                org_count += 1
            elif tag.role.value == "unknown":
                unknown_count += 1
        
        # Add summary traces
        if org_count > 0:
            traces.append(f"FSM role tagger: detected {org_count} organization tokens")
        
        if unknown_count > 0:
            traces.append(f"FSM role tagger: {unknown_count} tokens marked as unknown")
        
        # Add detailed traces for each token
        for i, (token, tag) in enumerate(zip(tokens, role_tags)):
            trace_entry = f"FSM role tagger: token '{token}' -> {tag.role.value} (reason: {tag.reason})"
            if tag.evidence:
                trace_entry += f" [evidence: {', '.join(tag.evidence)}]"
            traces.append(trace_entry)
        
        return traces

    def _extract_organization_spans_from_fsm_tags(self, role_tags: List) -> List[List[str]]:
        """Extract organization spans from FSM role tags."""
        org_spans = []
        current_span = []
        
        for tag in role_tags:
            if tag.role.value == "org":
                current_span.append(tag.token if hasattr(tag, 'token') else "")
            else:
                if current_span:
                    org_spans.append(current_span)
                    current_span = []
        
        # Add final span if exists
        if current_span:
            org_spans.append(current_span)
        
        return org_spans

    def _is_cyrillic_token(self, token: str) -> bool:
        """Check if a token contains primarily Cyrillic characters."""
        if not token:
            return False

        cyrillic_chars = sum(1 for c in token if '\u0400' <= c <= '\u04FF' or c in 'ЁёІіЇїЄєҐґ')
        latin_chars = sum(1 for c in token if 'A' <= c <= 'Z' or 'a' <= c <= 'z')

        # Consider token Cyrillic if it has any Cyrillic chars and more Cyrillic than Latin
        return cyrillic_chars > 0 and cyrillic_chars >= latin_chars

    def _is_latin_token(self, token: str) -> bool:
        """Check if a token contains primarily Latin characters."""
        if not token:
            return False

        cyrillic_chars = sum(1 for c in token if '\u0400' <= c <= '\u04FF' or c in 'ЁёІіЇїЄєҐґ')
        latin_chars = sum(1 for c in token if 'A' <= c <= 'Z' or 'a' <= c <= 'z')

        # Consider token Latin if it has Latin chars and more Latin than Cyrillic
        return latin_chars > 0 and latin_chars > cyrillic_chars

    def _apply_role_filtering(self, tokens: List[str], roles: List[str], role_tags: List, effective_flags, language: str = "auto", trace: Optional[List[Any]] = None) -> Tuple[List[str], List[str], List[str]]:
        """Filter tokens based on FSM role tagger results."""
        if not role_tags or len(role_tags) != len(tokens):
            return tokens, roles, []

        filtered_tokens = []
        filtered_roles = []
        traces = []

        # FSM role tags use TokenRole enum values
        excluded_roles = {"unknown", "org"}  # Exclude unknown and organization roles
        removed_count = 0
        org_context_windows = []

        for i, (token, role, tag) in enumerate(zip(tokens, roles, role_tags)):
            # Check for script filtering: remove Latin tokens in Cyrillic languages
            if language in ("ru", "uk") and self._is_latin_token(token):
                # Filter out Latin tokens in Russian/Ukrainian context
                removed_count += 1
                traces.append(f"Script filtering: removed Latin token '{token}' in {language} context")

                if trace is not None:
                    trace.append({
                        'stage': 'filter',
                        'rule': 'mixed_script_filtered',
                        'token': token,
                        'reason': f'latin_token_in_{language}_context'
                    })
                continue

            # Check if token should be excluded based on FSM role
            if getattr(effective_flags, 'strict_stopwords', False) and tag.role.value in excluded_roles:
                removed_count += 1

                if tag.role.value == "unknown" and tag.reason in ["stopword", "payment_context_filtered"]:
                    # This is a stopword or payment context removal
                    traces.append(f"FSM filtering: removed '{token}' (role: {tag.role.value}, reason: {tag.reason})")

                    # Add detailed trace step if tracing is enabled
                    if trace is not None:
                        trace.append({
                            'stage': 'filter',
                            'rule': 'stopword_removed',
                            'token': token,
                            'reason': 'service_word'
                        })

                elif tag.role.value == "org":
                    # This is an organization context removal
                    traces.append(f"FSM filtering: removed '{token}' (role: {tag.role.value}, reason: {tag.reason})")

                    # Find legal forms in context window
                    window_start = max(0, i - 3)
                    window_end = min(len(tokens), i + 4)
                    context_window = tokens[window_start:window_end]

                    # Look for legal forms in the window
                    legal_forms_in_window = []
                    for j, ctx_token in enumerate(context_window):
                        ctx_tag = role_tags[window_start + j] if window_start + j < len(role_tags) else None
                        if ctx_tag and ctx_tag.reason == "legal_form":
                            legal_forms_in_window.append(ctx_token)

                    if legal_forms_in_window:
                        org_context_windows.append(f"±3: {legal_forms_in_window}")

                    # Add detailed trace step if tracing is enabled
                    if trace is not None:
                        trace.append({
                            'stage': 'filter',
                            'rule': 'org_legal_form_context',
                            'window': f'±3',
                            'hit': legal_forms_in_window
                        })
                else:
                    traces.append(f"FSM filtering: removed '{token}' (role: {tag.role.value}, reason: {tag.reason})")

                continue

            filtered_tokens.append(token)
            filtered_roles.append(role)

        if removed_count > 0:
            traces.append(f"FSM role filtering removed {removed_count} tokens")

        if org_context_windows:
            traces.append(f"Organization context detected: {', '.join(org_context_windows)}")

        return filtered_tokens, filtered_roles, traces

    def _is_ascii_fastpath_eligible(self, text: str, config: NormalizationConfig) -> bool:
        """
        Check if text is eligible for ASCII fastpath processing.
        
        Args:
            text: Input text to check
            config: Normalization configuration
            
        Returns:
            True if text is eligible for ASCII fastpath, False otherwise
        """
        from ....utils.ascii_utils import is_ascii_name
        
        # Check if ASCII fastpath is enabled
        if not config.enable_ascii_fastpath:
            return False
        
        # Check if text is ASCII and suitable for fastpath
        if not is_ascii_name(text):
            return False
        
        # Check if language is English (ASCII fastpath is primarily for English names)
        if config.language not in ["en", "english"]:
            return False
        
        # Check if advanced features are not required (fastpath is simpler)
        if config.enable_advanced_features and config.enable_morphology:
            # Only use fastpath if morphology is not critical
            return False
        
        return True

    async def _ascii_fastpath_normalize(self, text: str, config: NormalizationConfig) -> NormalizationResult:
        """
        ASCII fastpath normalization without heavy Unicode/morphology operations.
        
        Args:
            text: ASCII text to normalize
            config: Normalization configuration
            
        Returns:
            NormalizationResult with fastpath processing
        """
        from ....utils.ascii_utils import ascii_fastpath_normalize
        
        try:
            # Use ASCII fastpath normalization
            tokens, roles, normalized_text = ascii_fastpath_normalize(text, config.language)
            
            # Create token traces for ASCII fastpath
            traces = [
                f"ASCII fastpath: processed '{text}' -> '{normalized_text}'",
                f"ASCII fastpath: {len(tokens)} tokens, roles: {roles}",
                "ASCII fastpath: skipped Unicode normalization and morphology"
            ]
            
            # Create token traces
            token_traces = []
            for i, (token, role) in enumerate(zip(tokens, roles)):
                token_traces.append(TokenTrace(
                    token=token,
                    role=role,
                    rule="enable_ascii_fastpath",
                    morph_lang=None,
                    normal_form=token,
                    output=token,
                    fallback=False,
                    notes=f"ASCII fastpath processing",
                    is_hyphenated_surname=is_hyphenated_surname(token)
                ))
            
            # Create result
            result = NormalizationResult(
                normalized=normalized_text,
                tokens=tokens,
                trace=traces,
                errors=[],
                language=config.language,
                confidence=0.95,  # High confidence for ASCII names
                original_length=len(text),
                normalized_length=len(normalized_text),
                token_count=len(tokens),
                processing_time=0.0,  # Will be set by caller
                success=True,
                token_traces=token_traces
            )
            
            self.logger.info(f"ASCII fastpath: processed '{text}' -> '{normalized_text}' ({len(tokens)} tokens)")
            return result
            
        except Exception as e:
            self.logger.error(f"ASCII fastpath failed for '{text}': {e}")
            # Fall back to regular processing
            return await self._normalize_with_error_handling(text, config)
