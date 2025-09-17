"""
Factory class for coordinating normalization processors.
Provides better error handling, logging, and orchestration of the refactored components.
"""

import json
import unicodedata
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from ....utils.logging_config import get_logger
from ....utils.perf_timer import PerfTimer
from ....utils.feature_flags import get_feature_flag_manager
from ....utils.profiling import profile_function, profile_time, get_profiling_stats, print_profiling_report
from ....contracts.base_contracts import NormalizationResult, TokenTrace
from ..error_handling import ErrorReportingMixin

from .token_processor import TokenProcessor
from .role_classifier import RoleClassifier
from .morphology_processor import MorphologyProcessor
from .gender_processor import GenderProcessor
from ..token_ops import collapse_double_dots, normalize_hyphenated_name
from ..morphology.diminutive_resolver import DiminutiveResolver
from ..role_tagger import RoleTagger
from ..role_tagger_service import RoleTaggerService
from ..lexicon_loader import get_lexicons

try:
    from ....data.dicts import russian_names, ukrainian_names
    DICTIONARIES_AVAILABLE = True
except ImportError:  # pragma: no cover - optional heavy dependency
    DICTIONARIES_AVAILABLE = False
    russian_names = None  # type: ignore
    ukrainian_names = None  # type: ignore

PERSON_ROLES = {"given", "surname", "patronymic", "initial"}
SEPARATOR_TOKENS = {"и", "та", "and", ","}


@dataclass
class NormalizationConfig:
    """Configuration for normalization processing."""
    remove_stop_words: bool = True
    preserve_names: bool = True
    enable_advanced_features: bool = True
    enable_morphology: bool = True
    enable_gender_adjustment: bool = True
    language: str = 'ru'
    use_factory: bool = True  # Flag to use factory vs legacy implementation
    # New Ukrainian-specific flags
    strict_stopwords: bool = False  # Use strict stopword filtering for initials
    preserve_feminine_suffix_uk: bool = False  # Preserve Ukrainian feminine suffixes (-ська/-цька)
    enable_spacy_uk_ner: bool = False  # Enable spaCy Ukrainian NER


class NormalizationFactory(ErrorReportingMixin):
    """Factory for coordinating all normalization processors."""

    def __init__(
        self,
        name_dictionaries: Optional[Dict[str, Set[str]]] = None,
        diminutive_maps: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        super().__init__()
        self.logger = get_logger(__name__)

        # Feature flags for tokenizer improvements
        self.feature_flags = get_feature_flag_manager()

        # Initialize processors
        self.token_processor = TokenProcessor()
        self.role_classifier = RoleClassifier(name_dictionaries, diminutive_maps)
        self.morphology_processor = MorphologyProcessor(diminutive_maps)
        self.gender_processor = GenderProcessor()
        self.diminutive_resolver = DiminutiveResolver(Path(__file__).resolve().parents[5])

        # Initialize role taggers with lexicons
        self.lexicons = get_lexicons()
        self.role_tagger = RoleTagger(self.lexicons)  # Legacy role tagger
        self.role_tagger_service = RoleTaggerService(self.lexicons)  # New FSM-based role tagger
        
        # Initialize NER for Ukrainian
        self.ner_gateway = None
        try:
            from ..ner_gateways import get_spacy_uk_ner
            self.ner_gateway = get_spacy_uk_ner()
        except ImportError:
            self.logger.warning("NER gateway not available")

        # Cache for performance
        self._normalization_cache = {}

        self.logger.info("NormalizationFactory initialized with all processors")

    @profile_function("normalization_factory.normalize_text")
    async def normalize_text(
        self,
        text: str,
        config: NormalizationConfig
    ) -> NormalizationResult:
        """Normalize text and return a complete NormalizationResult."""
        with PerfTimer() as timer:
            try:
                result = await self._normalize_with_error_handling(text, config)
                result.processing_time = timer.elapsed
                result.success = len(result.errors or []) == 0
                return result
            except Exception as e:
                self.logger.error(f"Normalization failed for text '{text}': {e}")
                return self._build_error_result(text, str(e), timer.elapsed)

    async def _normalize_with_error_handling(
        self,
        text: str,
        config: NormalizationConfig
    ) -> NormalizationResult:
        """Core normalization logic with comprehensive error handling."""

        errors: List[str] = []

        # Step 1: Tokenization
        try:
            tokens, tokenization_traces, token_meta = self.token_processor.strip_noise_and_tokenize(
                text,
                language=config.language,
                remove_stop_words=config.remove_stop_words,
                preserve_names=config.preserve_names
            )
            self.logger.debug(f"Tokenized '{text}' into {len(tokens)} tokens")
        except Exception as e:
            self.logger.error(f"Tokenization failed: {e}")
            return self._build_error_result(text, f"Tokenization failed: {e}")

        # Step 1.5: Apply tokenizer improvements (pre-processing)
        tokens, improvement_traces_pre = self._apply_tokenizer_improvements(tokens, tokenization_traces)
        self.logger.debug(f"Applied pre-processing tokenizer improvements: {len(improvement_traces_pre)} improvements")

        if not tokens:
            return self._build_empty_result(text, config.language)

        quoted_segments = token_meta.get("quoted_segments", [])

        # Step 1.6: Role tagging with FSM-based service
        try:
            # Get NER hints if enabled for Ukrainian
            ner_hints = None
            if config.enable_spacy_uk_ner and config.language == "uk" and self.ner_gateway:
                try:
                    ner_hints = self.ner_gateway.extract_entities(text)
                    self.logger.debug(f"NER extracted {len(ner_hints.person_spans)} person spans and {len(ner_hints.org_spans)} org spans")
                except Exception as e:
                    self.logger.warning(f"NER extraction failed: {e}")
            
            # Use new FSM-based role tagger service
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
            classified_tokens, roles, role_traces, org_entities = await self._classify_token_roles(
                tokens, config, quoted_segments
            )
            original_tagged_tokens = list(zip(classified_tokens, roles))
            self.logger.debug(f"Classified roles: {list(zip(classified_tokens, roles))}")
        except Exception as e:
            self.logger.error(f"Role classification failed: {e}")
            errors.append(f"Role classification failed: {e}")
            classified_tokens = tokens
            roles = ['unknown'] * len(tokens)
            role_traces = [f"Role classification failed: {e}"]
            org_entities = []
            original_tagged_tokens = list(zip(classified_tokens, roles))

        # Step 2.5: Filter tokens based on FSM role tagger results
        if role_tags and self.feature_flags._flags.strict_stopwords:
            filtered_tokens, filtered_roles, filter_traces = self._apply_role_filtering(
                classified_tokens, roles, role_tags
            )
            self.logger.debug(f"FSM role filtering removed {len(classified_tokens) - len(filtered_tokens)} tokens")
        else:
            filtered_tokens = classified_tokens
            filtered_roles = roles
            filter_traces = []

        diminutive_traces: List[str] = []
        unresolved_diminutive_indices: Set[int] = set()
        # Use filtered tokens and roles if filtering was applied
        if role_tags and self.feature_flags._flags.strict_stopwords:
            tokens_for_morphology = filtered_tokens
            roles_for_morphology = filtered_roles
        else:
            tokens_for_morphology = classified_tokens
            roles_for_morphology = roles
        if (
            config.language in {"ru", "uk"}
            and self.feature_flags.use_diminutives_dictionary_only()
        ):
            (
                tokens_for_morphology,
                diminutive_traces,
                unresolved_diminutive_indices,
            ) = self._apply_diminutive_resolution(
                classified_tokens,
                roles,
                config.language,
                allow_cross_lang=self.feature_flags.allow_diminutives_cross_lang(),
            )

        # Step 3: Morphological normalization
        try:
            normalized_tokens, morph_traces = await self._normalize_morphology(
                tokens_for_morphology, roles, config, skip_indices=unresolved_diminutive_indices
            )
        except Exception as e:
            self.logger.error(f"Morphological normalization failed: {e}")
            errors.append(f"Morphological normalization failed: {e}")
            normalized_tokens = tokens_for_morphology
            morph_traces = [f"Morphological normalization failed: {e}"]

        # Step 4: Gender processing
        try:
            final_tokens, gender_traces, gender_info = await self._process_gender(
                normalized_tokens, roles, config
            )
        except Exception as e:
            self.logger.error(f"Gender processing failed: {e}")
            errors.append(f"Gender processing failed: {e}")
            final_tokens = normalized_tokens
            gender_traces = [f"Gender processing failed: {e}"]
            gender_info = {}

        # Step 4.5: Apply tokenizer improvements (post-processing)
        final_tokens, improvement_traces_post = self._apply_tokenizer_improvements_post(final_tokens, roles)
        self.logger.debug(f"Applied post-processing tokenizer improvements: {len(improvement_traces_post)} improvements")

        # Step 5: Build trace
        processing_traces: List[str] = (
            tokenization_traces
            + [str(trace) for trace in improvement_traces_pre]
            + [str(trace) for trace in role_tagger_traces]
            + filter_traces
            + diminutive_traces
            + role_traces
            + morph_traces
            + gender_traces
            + [str(trace) for trace in improvement_traces_post]
        )
        
        # Add FSM role traces to the trace
        if role_tags:
            fsm_trace_entries = self.role_tagger_service.get_trace_entries(tokens, role_tags)
            for fsm_entry in fsm_trace_entries:
                processing_traces.append(f"FSM role trace: {fsm_entry}")
        trace = self._build_token_trace(
            classified_tokens,
            roles,
            final_tokens,
            processing_traces,
        )

        # Step 6: Separate personal/org tokens
        personal_tokens = [
            tok for tok, role in zip(final_tokens, roles) if role in PERSON_ROLES
        ]
        organizations = org_entities or [
            tok for tok, role in zip(classified_tokens, roles) if role == 'org'
        ]

        filtered_person_tokens = self._filter_person_tokens(trace, config.preserve_names)
        final_normalized_text = " ".join(filtered_person_tokens)

        persons = self._extract_persons(
            original_tagged_tokens,
            final_tokens,
            roles,
            config.language,
        )
        persons_core = [person["tokens"] for person in persons] if persons else ([] if not filtered_person_tokens else [filtered_person_tokens])

        output_tokens = filtered_person_tokens + organizations

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
        )

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

    def _build_empty_result(self, text: str, language: str) -> NormalizationResult:
        """Build empty result for texts with no tokens."""
        return NormalizationResult(
            normalized="",
            tokens=[],
            trace=[],
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

    def _filter_person_tokens(self, trace: List[TokenTrace], preserve_names: bool) -> List[str]:
        """Filter tokens to include only person-related tokens from trace."""
        filtered_tokens = []
        for token_trace in trace:
            if token_trace.role in PERSON_ROLES:
                filtered_tokens.append(token_trace.output)
        return filtered_tokens

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
        tagged_tokens, traces, organizations = self.role_classifier.tag_tokens(
            tokens, config.language, quoted_segments
        )
        classified_tokens = [token for token, _ in tagged_tokens]
        roles = [role for _, role in tagged_tokens]
        if not classified_tokens:
            return tokens, ['unknown'] * len(tokens), traces, []
        return classified_tokens, roles, traces, organizations

    async def _normalize_morphology(
        self,
        tokens: List[str],
        roles: List[str],
        config: NormalizationConfig,
        *,
        skip_indices: Optional[Set[int]] = None,
    ) -> Tuple[List[str], List[str]]:
        """Apply morphological normalization to tokens using legacy logic."""
        if not config.enable_morphology or not config.enable_advanced_features:
            return tokens, ["Morphological normalization disabled"]

        # Import legacy service to use its _normalize_slavic_token method
        from ..normalization_service_legacy import NormalizationService
        legacy_service = NormalizationService()

        normalized_tokens = []
        traces = []

        skip_set: Set[int] = skip_indices or set()

        for index, (token, role) in enumerate(zip(tokens, roles)):
            try:
                if index in skip_set and role in {'given', 'nickname'}:
                    normalized_tokens.append(token)
                    traces.append(f"Skipped diminutive heuristics for '{token}' in dictionary-only mode")
                    continue
                if role in {'given', 'surname', 'patronymic', 'initial'}:
                    # Use legacy full token normalization with Ukrainian feminine suffix preservation
                    normalized = legacy_service._normalize_slavic_token(
                        token, role, config.language, None, config.enable_advanced_features,
                        preserve_feminine_suffix_uk=config.preserve_feminine_suffix_uk
                    )
                    if normalized:
                        normalized_tokens.append(normalized)
                        traces.append(f"Legacy normalization: '{token}' -> '{normalized}'")
                    else:
                        normalized_tokens.append(token)
                        traces.append(f"Legacy normalization returned None for '{token}'")
                else:
                    normalized_tokens.append(token)
                    traces.append(f"No morphological processing for role '{role}'")
            except Exception as e:
                self.logger.warning(f"Morphological normalization failed for '{token}': {e}")
                normalized_tokens.append(token)
                traces.append(f"Morphological normalization failed for '{token}': {e}")

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

    def _reconstruct_text(self, tokens: List[str], roles: List[str]) -> str:
        """Reconstruct normalized text from tokens."""
        # Only include personal tokens (not unknown/organization tokens)
        personal_tokens = []
        for token, role in zip(tokens, roles):
            if role in {'given', 'surname', 'patronymic', 'initial'}:
                personal_tokens.append(token)

        return " ".join(personal_tokens) if personal_tokens else ""

    def _build_token_trace(
        self,
        original_tokens: List[str],
        roles: List[str],
        final_tokens: List[str],
        processing_traces: List[str]
    ) -> List[TokenTrace]:
        """Build detailed token trace for debugging."""
        trace = []

        for i, (orig, role) in enumerate(zip(original_tokens, roles)):
            final = final_tokens[i] if i < len(final_tokens) else orig

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

            trace.append(TokenTrace(
                token=orig,
                role=role,
                rule=" + ".join(rule_parts),
                output=final,
                fallback=final == orig,
                notes="; ".join(token_traces[:2])  # Limit notes length
            ))

        return trace

    def _apply_tokenizer_improvements(
        self,
        tokens: List[str],
        base_traces: List[TokenTrace]
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

        self.logger.debug(f"Tokenizer improvements: fix_initials={self.feature_flags._flags.fix_initials_double_dot}, preserve_hyphenated={self.feature_flags._flags.preserve_hyphenated_case}")

        # Apply double dot collapse if enabled
        if self.feature_flags._flags.fix_initials_double_dot:
            self.logger.debug(f"Applying double dot collapse to tokens: {improved_tokens}")
            original_count = len(improved_tokens)
            original_tokens = improved_tokens[:]
            improved_tokens = collapse_double_dots(improved_tokens)
            self.logger.debug(f"After collapse: {improved_tokens}")

            dots_collapsed = original_count - len(improved_tokens)
            # Also check if any tokens actually changed
            tokens_changed = [i for i, (orig, new) in enumerate(zip(original_tokens, improved_tokens)) if orig != new]

            if dots_collapsed > 0 or tokens_changed:
                improvement_traces.append({
                    "type": "tokenizer",
                    "action": "collapse_double_dots",
                    "count": dots_collapsed,
                    "changed_tokens": tokens_changed
                })
                self.logger.debug(f"Double dots collapsed: {dots_collapsed}, changed tokens: {tokens_changed}")

        # Apply hyphenated name normalization if enabled
        if self.feature_flags._flags.preserve_hyphenated_case:
            for i, token in enumerate(improved_tokens):
                if '-' in token and token != normalize_hyphenated_name(token, titlecase=True):
                    original = token
                    improved_tokens[i] = normalize_hyphenated_name(token, titlecase=True)
                    improvement_traces.append({
                        "type": "tokenizer",
                        "action": "normalize_hyphen",
                        "original": original,
                        "normalized": improved_tokens[i]
                    })

        return improved_tokens, improvement_traces

    def _apply_tokenizer_improvements_post(
        self,
        tokens: List[str],
        roles: List[str]
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

        self.logger.debug(f"Post-processing tokenizer improvements: fix_initials={self.feature_flags._flags.fix_initials_double_dot}")

        # Apply double dot collapse to initials if enabled
        if self.feature_flags._flags.fix_initials_double_dot:
            for i, (token, role) in enumerate(zip(improved_tokens, roles)):
                if role == "initial" and ".." in token:
                    original = token
                    # Apply collapse_double_dots to single token
                    improved = collapse_double_dots([token])[0]
                    if improved != original:
                        improved_tokens[i] = improved
                        improvement_traces.append({
                            "type": "tokenizer",
                            "action": "collapse_double_dots_post",
                            "original": original,
                            "normalized": improved,
                            "role": role
                        })
                        self.logger.debug(f"Post-processing: collapsed '{original}' to '{improved}' for role '{role}'")

        # Apply hyphenated name normalization if enabled
        if self.feature_flags._flags.preserve_hyphenated_case:
            for i, (token, role) in enumerate(zip(improved_tokens, roles)):
                if '-' in token and role in ("surname", "given"):
                    original = token
                    # Apply normalize_hyphenated_name
                    improved = normalize_hyphenated_name(token, titlecase=True)
                    if improved != original:
                        improved_tokens[i] = improved
                        improvement_traces.append({
                            "type": "tokenizer",
                            "action": "normalize_hyphen_post",
                            "original": original,
                            "normalized": improved,
                            "role": role
                        })
                        self.logger.debug(f"Post-processing: normalized hyphenated '{original}' to '{improved}' for role '{role}'")

        return improved_tokens, improvement_traces

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
                    normalized_original = unicodedata.normalize("NFKC", token).lower()
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

    def _apply_role_filtering(self, tokens: List[str], roles: List[str], role_tags: List) -> Tuple[List[str], List[str], List[str]]:
        """Filter tokens based on FSM role tagger results."""
        if not role_tags or len(role_tags) != len(tokens):
            return tokens, roles, []

        filtered_tokens = []
        filtered_roles = []
        traces = []

        # FSM role tags use TokenRole enum values
        excluded_roles = {"unknown", "org"}  # Exclude unknown and organization roles
        removed_count = 0

        for token, role, tag in zip(tokens, roles, role_tags):
            # Check if token should be excluded based on FSM role
            if self.feature_flags._flags.strict_stopwords and tag.role.value in excluded_roles:
                removed_count += 1
                traces.append(f"FSM filtering: removed '{token}' (role: {tag.role.value}, reason: {tag.reason})")
                continue

            filtered_tokens.append(token)
            filtered_roles.append(role)

        if removed_count > 0:
            traces.append(f"FSM role filtering removed {removed_count} tokens")

        return filtered_tokens, filtered_roles, traces
