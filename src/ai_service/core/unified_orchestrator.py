"""
Unified Orchestrator Service - Implementation of the layered architecture.

This is the single, authoritative orchestrator that implements the layer specification
from CLAUDE.md. It replaces all other orchestrator implementations.

Layers implemented:
1. Validation & Sanitization
2. Smart Filter (optional skip)
3. Language Detection
4. Unicode Normalization
5. Name Normalization (morph)
6. Signals (enrichment)
7. Variants (optional)
8. Embeddings (optional)
9. Decision & Response
"""

import asyncio
import time
from typing import Any, Dict, List, Optional

from ..config import SERVICE_CONFIG
from ..contracts.base_contracts import (
    ProcessingContext,
    ProcessingStage,
    SignalsResult,
    UnifiedProcessingResult,
    NormalizationResult,
    ValidationServiceInterface,
    SmartFilterInterface,
    LanguageDetectionInterface,
    UnicodeServiceInterface,
    NormalizationServiceInterface,
    SignalsServiceInterface,
    VariantsServiceInterface,
    EmbeddingsServiceInterface,
)
from ..exceptions import ServiceInitializationError, InternalServerError
from ..utils import get_logger

logger = get_logger(__name__)


class UnifiedOrchestrator:
    """
    Unified orchestrator implementing the 9-layer processing model.

    This is the SINGLE orchestrator - all other orchestrator implementations
    should be deprecated in favor of this one.
    """

    def __init__(
        self,
        # Required services
        validation_service: ValidationServiceInterface,
        language_service: LanguageDetectionInterface,
        unicode_service: UnicodeServiceInterface,
        normalization_service: NormalizationServiceInterface,
        signals_service: SignalsServiceInterface,

        # Optional services
        smart_filter_service: Optional[SmartFilterInterface] = None,
        variants_service: Optional[VariantsServiceInterface] = None,
        embeddings_service: Optional[EmbeddingsServiceInterface] = None,

        # Configuration
        enable_smart_filter: bool = True,
        enable_variants: bool = False,
        enable_embeddings: bool = False,
        allow_smart_filter_skip: bool = False,
    ):
        # Validate required services are not None
        if validation_service is None:
            raise ServiceInitializationError("validation_service cannot be None")
        if language_service is None:
            raise ServiceInitializationError("language_service cannot be None")
        if unicode_service is None:
            raise ServiceInitializationError("unicode_service cannot be None")
        if normalization_service is None:
            raise ServiceInitializationError("normalization_service cannot be None")
        if signals_service is None:
            raise ServiceInitializationError("signals_service cannot be None")

        self.validation_service = validation_service
        self.smart_filter_service = smart_filter_service
        self.language_service = language_service
        self.unicode_service = unicode_service
        self.normalization_service = normalization_service
        self.signals_service = signals_service
        self.variants_service = variants_service
        self.embeddings_service = embeddings_service

        # Configuration flags
        self.enable_smart_filter = enable_smart_filter and smart_filter_service is not None
        self.enable_variants = enable_variants and variants_service is not None
        self.enable_embeddings = enable_embeddings and embeddings_service is not None
        self.allow_smart_filter_skip = allow_smart_filter_skip

        logger.info(f"UnifiedOrchestrator initialized with stages: "
                   f"validation=True, smart_filter={self.enable_smart_filter}, "
                   f"language=True, unicode=True, normalization=True, signals=True, "
                   f"variants={self.enable_variants}, embeddings={self.enable_embeddings}")

    async def process(
        self,
        text: str,
        *,
        # Normalization flags (must have real effect per CLAUDE.md)
        remove_stop_words: bool = True,
        preserve_names: bool = True,
        enable_advanced_features: bool = True,
        # Processing hints
        language_hint: Optional[str] = None,
        generate_variants: Optional[bool] = None,
        generate_embeddings: Optional[bool] = None,
    ) -> UnifiedProcessingResult:
        """
        Process text through the unified 9-layer pipeline.

        Args:
            text: Input text to process
            remove_stop_words: Clean STOP_ALL tokens in normalization
            preserve_names: Keep `. - '` for initials/compound names
            enable_advanced_features: Use morphology + diminutives + gender
            language_hint: Optional language hint
            generate_variants: Override variants generation
            generate_embeddings: Override embeddings generation

        Returns:
            UnifiedProcessingResult with all layers' output
        """
        start_time = time.time()
        context = ProcessingContext(original_text=text)
        errors = []

        try:
            # ================================================================
            # Layer 1: Validation & Sanitization
            # ================================================================
            logger.debug("Stage 1: Validation & Sanitization")
            validation_result = await self.validation_service.validate_and_sanitize(text)
            context.sanitized_text = validation_result.get("sanitized_text", text)
            if not validation_result.get("should_process", True):
                return self._create_early_response(context, "Input validation failed", start_time)

            # ================================================================
            # Layer 2: Smart Filter (optional skip)
            # ================================================================
            if self.enable_smart_filter:
                logger.debug("Stage 2: Smart Filter")
                filter_result = await self.smart_filter_service.should_process(context.sanitized_text)
                context.should_process = filter_result.should_process
                context.metadata["smart_filter"] = {
                    "should_process": filter_result.should_process,
                    "confidence": filter_result.confidence,
                    "classification": filter_result.classification,
                    "detected_signals": filter_result.detected_signals,
                    "details": filter_result.details
                }

                if not context.should_process and self.allow_smart_filter_skip:
                    return self._create_filtered_response(context, filter_result, start_time)

            # ================================================================
            # Layer 3: Language Detection
            # ================================================================
            logger.debug("Stage 3: Language Detection")
            lang_result = await self.language_service.detect_language(context.sanitized_text)
            context.language = language_hint or lang_result.get("language", "en")
            context.language_confidence = lang_result.get("confidence", 0.0)

            # ================================================================
            # Layer 4: Unicode Normalization
            # ================================================================
            logger.debug("Stage 4: Unicode Normalization")
            unicode_normalized = await self.unicode_service.normalize_unicode(context.sanitized_text)

            # ================================================================
            # Layer 5: Name Normalization (morph) - THE CORE
            # ================================================================
            logger.debug("Stage 5: Name Normalization")
            norm_result = await self.normalization_service.normalize_async(
                unicode_normalized,
                language=context.language,
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names,
                enable_advanced_features=enable_advanced_features
            )

            if not norm_result.success:
                errors.extend(norm_result.errors)

            # ================================================================
            # Layer 6: Signals (enrichment)
            # ================================================================
            logger.debug("Stage 6: Signals Extraction")
            signals_result = await self.signals_service.extract_signals(
                original_text=context.original_text,
                normalization_result=norm_result
            )

            # ================================================================
            # Layer 7: Variants (optional)
            # ================================================================
            variants = None
            if (generate_variants is True) or (generate_variants is None and self.enable_variants):
                logger.debug("Stage 7: Variant Generation")
                try:
                    variants = await self.variants_service.generate_variants(
                        norm_result.normalized, context.language
                    )
                except Exception as e:
                    logger.warning(f"Variant generation failed: {e}")
                    errors.append(f"Variants: {str(e)}")

            # ================================================================
            # Layer 8: Embeddings (optional)
            # ================================================================
            embeddings = None
            if (generate_embeddings is True) or (generate_embeddings is None and self.enable_embeddings):
                logger.debug("Stage 8: Embedding Generation")
                try:
                    embeddings = await self.embeddings_service.generate_embeddings(norm_result.normalized)
                except Exception as e:
                    logger.warning(f"Embedding generation failed: {e}")
                    errors.append(f"Embeddings: {str(e)}")

            # ================================================================
            # Layer 9: Decision & Response
            # ================================================================
            processing_time = time.time() - start_time

            # Warn if processing is slow
            if processing_time > 0.1:  # 100ms threshold per CLAUDE.md
                logger.warning(f"Slow processing: {processing_time:.3f}s for text: {text[:50]}...")

            return UnifiedProcessingResult(
                original_text=context.original_text,
                language=context.language,
                language_confidence=context.language_confidence,
                normalized_text=norm_result.normalized,
                tokens=norm_result.tokens,
                trace=norm_result.trace,
                signals=signals_result,
                variants=variants,
                embeddings=embeddings,
                processing_time=processing_time,
                success=len(errors) == 0,
                errors=errors
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Processing failed: {e}", exc_info=True)

            return UnifiedProcessingResult(
                original_text=context.original_text,
                language=context.language or "unknown",
                language_confidence=context.language_confidence or 0.0,
                normalized_text="",
                tokens=[],
                trace=[],
                signals=SignalsResult(),
                processing_time=processing_time,
                success=False,
                errors=[str(e)]
            )

    def _create_early_response(
        self,
        context: ProcessingContext,
        reason: str,
        start_time: float
    ) -> UnifiedProcessingResult:
        """Create response for early termination"""
        return UnifiedProcessingResult(
            original_text=context.original_text,
            language="unknown",
            language_confidence=0.0,
            normalized_text="",
            tokens=[],
            trace=[],
            signals=SignalsResult(),
            processing_time=time.time() - start_time,
            success=False,
            errors=[reason]
        )

    def _create_filtered_response(
        self,
        context: ProcessingContext,
        filter_result,  # SmartFilterResult object
        start_time: float
    ) -> UnifiedProcessingResult:
        """Create response when smart filter suggests skipping"""
        return UnifiedProcessingResult(
            original_text=context.original_text,
            language=context.language or "unknown",
            language_confidence=context.language_confidence or 0.0,
            normalized_text=context.sanitized_text or context.original_text,
            tokens=[],
            trace=[],
            signals=SignalsResult(confidence=filter_result.confidence),
            processing_time=time.time() - start_time,
            success=True,
            errors=[]
        )

    # Convenience methods for backward compatibility

    async def normalize_async(
        self,
        text: str,
        **kwargs
    ) -> NormalizationResult:
        """
        Backward compatibility: direct normalization.
        For new code, use process() instead.
        """
        logger.warning("normalize_async is deprecated. Use process() instead.")

        # Extract normalization-specific flags
        norm_flags = {k: v for k, v in kwargs.items()
                     if k in ['language', 'remove_stop_words', 'preserve_names', 'enable_advanced_features']}

        # Run minimal pipeline: validation -> unicode -> normalization
        validation_result = await self.validation_service.validate_and_sanitize(text)
        sanitized = validation_result.get("sanitized_text", text)

        unicode_normalized = await self.unicode_service.normalize_unicode(sanitized)

        return await self.normalization_service.normalize_async(unicode_normalized, **norm_flags)

    async def extract_signals(
        self,
        original_text: str,
        normalization_result: NormalizationResult
    ) -> SignalsResult:
        """Backward compatibility: direct signals extraction"""
        logger.warning("extract_signals is deprecated. Use process() instead.")
        return await self.signals_service.extract_signals(original_text, normalization_result)