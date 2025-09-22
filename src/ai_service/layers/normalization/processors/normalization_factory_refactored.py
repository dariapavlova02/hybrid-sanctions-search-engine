"""
Refactored Normalization Factory with improved modularity and maintainability.

This is a refactored version of the original normalization_factory.py
breaking down the large monolithic class into smaller, more manageable modules.
"""

import asyncio
from typing import Dict, List, Set, Optional, Any
from pathlib import Path

from .config import NormalizationConfig
from .english_processor import EnglishNameProcessor
from .person_extraction import PersonExtractor
from .result_builder import ResultBuilder, ProcessingMetrics
from ..tokenizer_service import TokenizerService
from ..morphology_adapter import MorphologyAdapter
from ....contracts.base_contracts import NormalizationResult, TokenTrace
from ....utils.logging_config import get_logger
from ....utils.perf_timer import PerfTimer
from ....utils.profiling import profile_function


class NormalizationFactoryRefactored:
    """
    Refactored factory for coordinating normalization processors.

    Breaks down the original monolithic factory into focused, reusable components:
    - Configuration management
    - English name processing
    - Person extraction and grouping
    - Result building and validation

    This design improves maintainability, testability, and separation of concerns.
    """

    def __init__(
        self,
        name_dictionaries: Optional[Dict[str, Set[str]]] = None,
        diminutive_maps: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        """Initialize the refactored factory with component services."""
        self.logger = get_logger(__name__)

        # Initialize component services
        self.english_processor = EnglishNameProcessor()
        self.person_extractor = PersonExtractor()
        self.result_builder = ResultBuilder()

        # Initialize core services
        self.tokenizer_service = TokenizerService()
        self.morphology_adapter = MorphologyAdapter()

        # Initialize dictionaries
        self.name_dictionaries = name_dictionaries or {}
        self.diminutive_maps = diminutive_maps or {}

        # Load dictionaries if available
        self._load_language_dictionaries()

        self.logger.info("NormalizationFactoryRefactored initialized with modular components")

    @profile_function("normalization_factory_refactored.normalize_text")
    async def normalize_text(
        self,
        text: str,
        config: NormalizationConfig,
        feature_flags: Optional[Any] = None
    ) -> NormalizationResult:
        """Normalize text using the refactored modular approach."""
        if not text or not text.strip():
            return self.result_builder.build_minimal_result(
                text or "",
                "Empty input text",
                config.language
            )

        # Create processing metrics
        metrics = self.result_builder.create_processing_metrics(text)

        try:
            # Step 1: Language detection and text preparation
            detected_language = self._detect_language(text, config)

            # Step 2: Tokenization and initial processing
            tokens, traces, metadata = await self._tokenize_and_process(
                text, detected_language, config
            )

            if not tokens:
                return self.result_builder.build_minimal_result(
                    text,
                    "No valid tokens found",
                    detected_language
                )

            # Step 3: Role classification and filtering
            roles, updated_traces = await self._classify_roles(
                tokens, traces, detected_language, config
            )

            # Step 4: Morphological normalization
            normalized_tokens, morph_traces = await self._apply_morphology(
                tokens, roles, detected_language, config
            )

            # Step 5: Person extraction and grouping
            persons = self.person_extractor.extract_persons_from_sequence(
                normalized_tokens, roles, detected_language, config
            )

            # Step 6: Result building
            all_traces = self.result_builder.merge_traces(updated_traces, morph_traces)
            organizations_core = self.result_builder.extract_organizations_core(text, all_traces)

            result = self.result_builder.build_normalization_result(
                original_text=text,
                normalized_tokens=normalized_tokens,
                token_traces=all_traces,
                persons=persons,
                language=detected_language,
                config=config,
                metrics=metrics,
                organizations_core=organizations_core
            )

            # Step 7: Validation
            validation_errors = self.result_builder.validate_result(result, config)
            if validation_errors:
                for error in validation_errors:
                    self.result_builder.add_error_to_metrics(metrics, error)

            return result

        except Exception as e:
            self.logger.error(f"Error in normalize_text: {e}", exc_info=True)
            self.result_builder.add_error_to_metrics(metrics, str(e))
            return self.result_builder.build_minimal_result(
                text,
                f"Processing error: {str(e)}",
                config.language
            )

    async def normalize_text_batch(
        self,
        texts: List[str],
        config: NormalizationConfig,
        feature_flags: Optional[Any] = None
    ) -> List[NormalizationResult]:
        """Normalize multiple texts in batch for better performance."""
        if not texts:
            return []

        # Process texts concurrently
        tasks = [
            self.normalize_text(text, config, feature_flags)
            for text in texts
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Convert exceptions to error results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_result = self.result_builder.build_minimal_result(
                    texts[i],
                    f"Batch processing error: {str(result)}",
                    config.language
                )
                processed_results.append(error_result)
            else:
                processed_results.append(result)

        return processed_results

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages."""
        return ["ru", "uk", "en"]

    def validate_config(self, config: NormalizationConfig) -> List[str]:
        """Validate configuration and return any validation errors."""
        errors = []

        try:
            config.validate()
        except ValueError as e:
            errors.append(str(e))

        # Additional validation
        if config.language not in self.get_supported_languages() + ["auto"]:
            errors.append(f"Unsupported language: {config.language}")

        return errors

    def get_component_status(self) -> Dict[str, Any]:
        """Get status of all components for diagnostics."""
        return {
            "english_processor": {
                "available": bool(self.english_processor),
                "lexicons_loaded": getattr(self.english_processor, 'lexicons_loaded', False)
            },
            "person_extractor": {
                "available": bool(self.person_extractor),
                "separators_loaded": len(self.person_extractor.person_separators) > 0
            },
            "morphology_adapter": {
                "available": bool(self.morphology_adapter),
            },
            "dictionaries": {
                "languages": list(self.name_dictionaries.keys()),
                "diminutive_maps": list(self.diminutive_maps.keys())
            }
        }

    async def _tokenize_and_process(
        self,
        text: str,
        language: str,
        config: NormalizationConfig
    ) -> tuple[List[str], List[TokenTrace], Dict[str, Any]]:
        """Tokenize and perform initial processing."""
        # Use tokenizer service for consistent tokenization
        tokenization_result = await self.tokenizer_service.tokenize_async(
            text,
            language=language,
            preserve_names=config.preserve_names
        )

        tokens = tokenization_result.get("tokens", [])
        traces = []
        metadata = {}

        # Create initial traces
        for token in tokens:
            trace = self.result_builder.create_token_trace(
                original_token=token,
                normalized_token=token,
                role="unknown",
                rule="tokenization"
            )
            traces.append(trace)

        return tokens, traces, metadata

    async def _classify_roles(
        self,
        tokens: List[str],
        traces: List[TokenTrace],
        language: str,
        config: NormalizationConfig
    ) -> tuple[List[str], List[TokenTrace]]:
        """Classify token roles using appropriate classifier."""
        roles = []
        updated_traces = []

        for i, (token, trace) in enumerate(zip(tokens, traces)):
            # Basic role classification logic
            role = self._classify_single_token(token, i, tokens, language, config)
            roles.append(role)

            # Update trace with role information
            updated_trace = self.result_builder.create_token_trace(
                original_token=trace.token,
                normalized_token=trace.output,
                role=role,
                rule=f"role_classification_{language}",
                notes=f"Classified as {role}"
            )
            updated_traces.append(updated_trace)

        return roles, updated_traces

    async def _apply_morphology(
        self,
        tokens: List[str],
        roles: List[str],
        language: str,
        config: NormalizationConfig
    ) -> tuple[List[str], List[TokenTrace]]:
        """Apply morphological normalization."""
        if not config.enable_advanced_features or not config.enable_morphology:
            # Return tokens as-is with basic traces
            traces = []
            for token, role in zip(tokens, roles):
                trace = self.result_builder.create_token_trace(
                    original_token=token,
                    normalized_token=token,
                    role=role,
                    rule="no_morphology",
                    notes="Morphology disabled"
                )
                traces.append(trace)
            return tokens, traces

        normalized_tokens = []
        traces = []

        for token, role in zip(tokens, roles):
            # Apply morphology based on language and role
            if language == "en":
                # Use English processor
                normalized_token = self.english_processor.normalize_english_name_token(
                    token, role, config
                )
                rule = "english_normalization"
            elif language in ["ru", "uk"] and role in ["given", "surname", "patronymic"]:
                # Use morphology adapter for Cyrillic languages
                try:
                    morph_result = await self.morphology_adapter.normalize_token_async(
                        token, language, role
                    )
                    normalized_token = morph_result.get("normalized", token)
                    rule = f"morphology_{language}"
                except Exception as e:
                    self.logger.warning(f"Morphology failed for {token}: {e}")
                    normalized_token = token.title()
                    rule = "morphology_fallback"
            else:
                # Basic title case normalization
                normalized_token = token.title()
                rule = "title_case"

            normalized_tokens.append(normalized_token)

            trace = self.result_builder.create_token_trace(
                original_token=token,
                normalized_token=normalized_token,
                role=role,
                rule=rule,
                morphology_lang=language if rule.startswith("morphology") else None
            )
            traces.append(trace)

        return normalized_tokens, traces

    def _classify_single_token(
        self,
        token: str,
        position: int,
        all_tokens: List[str],
        language: str,
        config: NormalizationConfig
    ) -> str:
        """Classify a single token's role."""
        if not token:
            return "unknown"

        token_lower = token.lower()

        # Check for initials
        if len(token) <= 2 and token.endswith('.'):
            return "initial"

        # Check for obvious organization indicators
        org_indicators = {"ооо", "тов", "llc", "ltd", "inc", "corp"}
        if token_lower in org_indicators:
            return "legal_form"

        # Simple positional logic for person names
        if position == 0 and len(all_tokens) > 1:
            return "given"
        elif position == len(all_tokens) - 1 and len(all_tokens) > 1:
            return "surname"
        elif position == 1 and len(all_tokens) >= 3:
            # Middle position might be patronymic
            if language in ["ru", "uk"] and self._looks_like_patronymic(token):
                return "patronymic"
            return "given"

        return "unknown"

    def _looks_like_patronymic(self, token: str) -> bool:
        """Check if token looks like a patronymic."""
        if not token:
            return False

        token_lower = token.lower()
        patronymic_endings = ["ович", "евич", "ич", "овна", "евна", "івна", "ївна"]

        return any(token_lower.endswith(ending) for ending in patronymic_endings)

    def _detect_language(self, text: str, config: NormalizationConfig) -> str:
        """Detect language of the text."""
        if config.language != "auto":
            return config.language

        # Simple language detection based on character sets
        cyrillic_chars = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        latin_chars = sum(1 for c in text if c.isascii() and c.isalpha())
        total_chars = cyrillic_chars + latin_chars

        if total_chars == 0:
            return "en"  # Default fallback

        cyrillic_ratio = cyrillic_chars / total_chars

        if cyrillic_ratio > 0.5:
            # Distinguish between Russian and Ukrainian
            ukrainian_chars = sum(1 for c in text if c in 'іїєґІЇЄҐ')
            if ukrainian_chars > 0:
                return "uk"
            return "ru"
        else:
            return "en"

    def _load_language_dictionaries(self):
        """Load language-specific dictionaries if available."""
        try:
            # This would load actual dictionaries in a full implementation
            # For now, we'll use empty dictionaries
            self.name_dictionaries = {
                "ru": set(),
                "uk": set(),
                "en": set()
            }

            self.diminutive_maps = {
                "ru": {},
                "uk": {},
                "en": {}
            }

            self.logger.info("Language dictionaries initialized (empty for demo)")
        except Exception as e:
            self.logger.warning(f"Failed to load dictionaries: {e}")
            self.name_dictionaries = {}
            self.diminutive_maps = {}