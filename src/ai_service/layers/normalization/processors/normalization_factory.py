"""
Factory class for coordinating normalization processors.
Provides better error handling, logging, and orchestration of the refactored components.
"""

from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass
from ....utils.logging_config import get_logger
from ....utils.perf_timer import PerfTimer
from ....contracts.base_contracts import TokenTrace
from ..error_handling import ErrorReportingMixin

from .token_processor import TokenProcessor
from .role_classifier import RoleClassifier
from .morphology_processor import MorphologyProcessor
from .gender_processor import GenderProcessor


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


class NormalizationFactory(ErrorReportingMixin):
    """Factory for coordinating all normalization processors."""

    def __init__(self, name_dictionaries: Dict[str, Set[str]] = None):
        super().__init__()
        self.logger = get_logger(__name__)

        # Initialize processors
        self.token_processor = TokenProcessor()
        self.role_classifier = RoleClassifier(name_dictionaries)
        self.morphology_processor = MorphologyProcessor()
        self.gender_processor = GenderProcessor()

        # Cache for performance
        self._normalization_cache = {}

        self.logger.info("NormalizationFactory initialized with all processors")

    async def normalize_text(
        self,
        text: str,
        config: NormalizationConfig
    ) -> Tuple[str, List[str], List[TokenTrace], Dict[str, Any]]:
        """
        Normalize text using coordinated processors.

        Args:
            text: Input text to normalize
            config: Normalization configuration

        Returns:
            Tuple of (normalized_text, tokens, trace, metadata)
        """
        with PerfTimer() as timer:
            try:
                return await self._normalize_with_error_handling(text, config)
            except Exception as e:
                self.logger.error(f"Normalization failed for text '{text}': {e}")
                return text, [], [], {
                    'error': str(e),
                    'processing_time': timer.elapsed,
                    'success': False
                }

    async def _normalize_with_error_handling(
        self,
        text: str,
        config: NormalizationConfig
    ) -> Tuple[str, List[str], List[TokenTrace], Dict[str, Any]]:
        """Core normalization logic with comprehensive error handling."""

        # Step 1: Tokenization
        try:
            tokens, tokenization_traces = self.token_processor.strip_noise_and_tokenize(
                text,
                preserve_names=config.preserve_names
            )
            self.logger.debug(f"Tokenized '{text}' into {len(tokens)} tokens")
        except Exception as e:
            self.logger.error(f"Tokenization failed: {e}")
            return text, [], [], {'error': f'Tokenization failed: {e}'}

        if not tokens:
            return "", [], [], {'warning': 'No tokens after tokenization'}

        # Step 2: Role classification
        try:
            roles, role_traces = await self._classify_token_roles(tokens, config)
            self.logger.debug(f"Classified roles: {list(zip(tokens, roles))}")
        except Exception as e:
            self.logger.error(f"Role classification failed: {e}")
            roles = ['unknown'] * len(tokens)
            role_traces = [f"Role classification failed: {e}"]

        # Step 3: Morphological normalization
        try:
            normalized_tokens, morph_traces = await self._normalize_morphology(
                tokens, roles, config
            )
        except Exception as e:
            self.logger.error(f"Morphological normalization failed: {e}")
            normalized_tokens = tokens
            morph_traces = [f"Morphological normalization failed: {e}"]

        # Step 4: Gender processing
        try:
            final_tokens, gender_traces, gender_info = await self._process_gender(
                normalized_tokens, roles, config
            )
        except Exception as e:
            self.logger.error(f"Gender processing failed: {e}")
            final_tokens = normalized_tokens
            gender_traces = [f"Gender processing failed: {e}"]
            gender_info = {}

        # Step 5: Reconstruct text
        try:
            final_text = self._reconstruct_text(final_tokens, roles)
        except Exception as e:
            self.logger.error(f"Text reconstruction failed: {e}")
            final_text = " ".join(final_tokens)

        # Step 6: Build trace
        trace = self._build_token_trace(
            tokens, roles, final_tokens,
            tokenization_traces + role_traces + morph_traces + gender_traces
        )

        metadata = {
            'original_length': len(text),
            'final_length': len(final_text),
            'token_count': len(final_tokens),
            'success': True,
            **gender_info
        }

        return final_text, final_tokens, trace, metadata

    async def _classify_token_roles(
        self,
        tokens: List[str],
        config: NormalizationConfig
    ) -> Tuple[List[str], List[str]]:
        """Classify the role of each token."""
        roles = []
        traces = []

        for i, token in enumerate(tokens):
            try:
                role, confidence, evidence = self.role_classifier.classify_personal_role(
                    token, i, len(tokens), config.language, tokens
                )
                roles.append(role)
                traces.append(f"Token '{token}' classified as '{role}' (conf: {confidence:.2f})")
                traces.extend(evidence)
            except Exception as e:
                self.logger.warning(f"Role classification failed for token '{token}': {e}")
                roles.append('unknown')
                traces.append(f"Role classification failed for '{token}': {e}")

        return roles, traces

    async def _normalize_morphology(
        self,
        tokens: List[str],
        roles: List[str],
        config: NormalizationConfig
    ) -> Tuple[List[str], List[str]]:
        """Apply morphological normalization to tokens."""
        if not config.enable_morphology or not config.enable_advanced_features:
            return tokens, ["Morphological normalization disabled"]

        normalized_tokens = []
        traces = []

        for token, role in zip(tokens, roles):
            try:
                if role in {'given', 'surname', 'patronymic'}:
                    normalized, morph_traces = await self.morphology_processor.normalize_slavic_token(
                        token, role, config.language, config.enable_morphology
                    )
                    normalized_tokens.append(normalized)
                    traces.extend(morph_traces)
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
            token_traces = [t for t in processing_traces if orig in t]

            trace.append(TokenTrace(
                token=orig,
                role=role,
                rule="processor_pipeline",
                output=final,
                fallback=final == orig,
                notes="; ".join(token_traces[:3])  # Limit notes length
            ))

        return trace

    def clear_caches(self):
        """Clear all processor caches."""
        self.morphology_processor.clear_cache()
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
            }
        }