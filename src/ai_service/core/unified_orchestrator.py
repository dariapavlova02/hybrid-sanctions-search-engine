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
    EmbeddingsServiceInterface,
    LanguageDetectionInterface,
    NormalizationResult,
    NormalizationServiceInterface,
    ProcessingContext,
    ProcessingStage,
    SignalsResult,
    SignalsServiceInterface,
    SmartFilterInterface,
    UnicodeServiceInterface,
    UnifiedProcessingResult,
    ValidationServiceInterface,
    VariantsServiceInterface,
)
from ..contracts.decision_contracts import (
    DecisionInput,
    DecisionOutput,
    RiskLevel,
    SmartFilterInfo,
    SignalsInfo,
    SimilarityInfo,
)
from ..core.decision_engine import DecisionEngine
from ..config.settings import DecisionConfig
from ..exceptions import InternalServerError, ServiceInitializationError
from ..utils import get_logger
from ..monitoring.metrics_service import MetricsService, MetricType, AlertSeverity

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
        decision_engine: Optional[DecisionEngine] = None,
        metrics_service: Optional[MetricsService] = None,
        # Configuration - defaults from SERVICE_CONFIG
        enable_smart_filter: Optional[bool] = None,
        enable_variants: Optional[bool] = None,
        enable_embeddings: Optional[bool] = None,
        enable_decision_engine: Optional[bool] = None,
        allow_smart_filter_skip: Optional[bool] = None,
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
        self.decision_engine = decision_engine
        self.metrics_service = metrics_service

        # Configuration flags - use SERVICE_CONFIG defaults if not provided
        self.enable_smart_filter = (
            (enable_smart_filter if enable_smart_filter is not None else SERVICE_CONFIG.enable_smart_filter)
            and smart_filter_service is not None
        )
        self.enable_variants = (
            (enable_variants if enable_variants is not None else SERVICE_CONFIG.enable_variants)
            and variants_service is not None
        )
        self.enable_embeddings = (
            (enable_embeddings if enable_embeddings is not None else SERVICE_CONFIG.enable_embeddings)
            and embeddings_service is not None
        )
        self.enable_decision_engine = (
            (enable_decision_engine if enable_decision_engine is not None else SERVICE_CONFIG.enable_decision_engine)
            and decision_engine is not None
        )
        self.allow_smart_filter_skip = (
            allow_smart_filter_skip if allow_smart_filter_skip is not None else SERVICE_CONFIG.allow_smart_filter_skip
        )

        logger.info(
            f"UnifiedOrchestrator initialized with stages: "
            f"validation=True, smart_filter={self.enable_smart_filter}, "
            f"language=True, unicode=True, normalization=True, signals=True, "
            f"variants={self.enable_variants}, embeddings={self.enable_embeddings}"
        )

    async def _maybe_await(self, x):
        """Helper to await if needed"""
        import inspect
        return await x if inspect.isawaitable(x) else x

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

        # Initialize metrics collection
        if self.metrics_service:
            self.metrics_service.increment_counter('processing.requests.total')
            self.metrics_service.set_gauge('processing.requests.active', 1)

        try:
            # ================================================================
            # Layer 1: Validation & Sanitization
            # ================================================================
            logger.debug("Stage 1: Validation & Sanitization")
            layer_start = time.time()

            validation_result = await self.validation_service.validate_and_sanitize(
                text
            )
            context.sanitized_text = validation_result.get("sanitized_text", text)

            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.validation', time.time() - layer_start)

            if not validation_result.get("should_process", True):
                if self.metrics_service:
                    self.metrics_service.increment_counter('processing.validation.failed')
                return self._create_early_response(
                    context, "Input validation failed", start_time
                )

            # ================================================================
            # Layer 2: Smart Filter (optional skip)
            # ================================================================
            if self.enable_smart_filter:
                logger.debug("Stage 2: Smart Filter")
                layer_start = time.time()

                filter_result = await self._maybe_await(self.smart_filter_service.should_process(
                    context.sanitized_text
                ))
                context.should_process = filter_result.should_process
                context.metadata["smart_filter"] = {
                    "should_process": filter_result.should_process,
                    "confidence": filter_result.confidence,
                    "classification": filter_result.classification,
                    "detected_signals": filter_result.detected_signals,
                    "details": filter_result.details,
                }

                if self.metrics_service:
                    self.metrics_service.record_timer('processing.layer.smart_filter', time.time() - layer_start)
                    self.metrics_service.record_histogram('smart_filter.confidence', filter_result.confidence)

                if not context.should_process and self.allow_smart_filter_skip:
                    if self.metrics_service:
                        self.metrics_service.increment_counter('processing.smart_filter.skipped')
                    return self._create_filtered_response(
                        context, filter_result, start_time
                    )

            # ================================================================
            # Layer 3: Unicode Normalization (MUST come before language detection)
            # ================================================================
            logger.debug("Stage 3: Unicode Normalization")
            layer_start = time.time()

            # Language detection EXPECTS unicode-normalized input
            unicode_result = await self.unicode_service.normalize_unicode(
                context.sanitized_text
            )
            unicode_normalized = unicode_result.get("normalized", context.sanitized_text)

            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.unicode_normalization', time.time() - layer_start)

            # ================================================================
            # Layer 4: Language Detection (on unicode-normalized text)
            # ================================================================
            logger.debug("Stage 4: Language Detection")
            layer_start = time.time()

            from ..config import LANGUAGE_CONFIG
            lang_result = self.language_service.detect_language_config_driven(
                unicode_normalized,  # Use unicode-normalized text for language detection
                LANGUAGE_CONFIG
            )
            context.language = language_hint or lang_result.language
            context.language_confidence = lang_result.confidence

            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.language_detection', time.time() - layer_start)
                self.metrics_service.record_histogram('language_detection.confidence', context.language_confidence)
                self.metrics_service.increment_counter(f'language_detection.detected.{context.language}')

            # ================================================================
            # Layer 5: Name Normalization (morph) - THE CORE
            # ================================================================
            logger.debug("Stage 5: Name Normalization")
            layer_start = time.time()

            norm_result = await self.normalization_service.normalize_async(
                unicode_normalized,
                language=context.language,
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names,
                enable_advanced_features=enable_advanced_features,
            )

            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.normalization', time.time() - layer_start)
                if hasattr(norm_result, 'confidence') and norm_result.confidence is not None:
                    self.metrics_service.record_histogram('normalization.confidence', norm_result.confidence)
                self.metrics_service.record_histogram('normalization.token_count', len(norm_result.tokens))

            if not norm_result.success:
                if self.metrics_service:
                    self.metrics_service.increment_counter('processing.normalization.failed')
                errors.extend(norm_result.errors)

            # ================================================================
            # Layer 6: Signals (enrichment)
            # ================================================================
            logger.debug("Stage 6: Signals Extraction")
            layer_start = time.time()

            signals_result = await self._maybe_await(self.signals_service.extract_signals(
                text=context.original_text, normalization_result=norm_result, language=context.language
            ))

            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.signals', time.time() - layer_start)
                self.metrics_service.record_histogram('signals.confidence', signals_result.confidence)
                self.metrics_service.record_histogram('signals.persons_count', len(signals_result.persons))
                self.metrics_service.record_histogram('signals.organizations_count', len(signals_result.organizations))

            # ================================================================
            # Layer 7: Variants (optional)
            # ================================================================
            variants = None
            if (generate_variants is True) or (
                generate_variants is None and self.enable_variants
            ):
                logger.debug("Stage 7: Variant Generation")
                layer_start = time.time()
                try:
                    if self.variants_service is not None:
                        variants = await self._maybe_await(self.variants_service.generate_variants(
                            norm_result.normalized, context.language
                        ))
                    else:
                        logger.debug("Variants service not available - skipping variant generation")
                    if self.metrics_service:
                        self.metrics_service.record_timer('processing.layer.variants', time.time() - layer_start)
                        if variants:
                            self.metrics_service.record_histogram('variants.count', len(variants))
                except Exception as e:
                    logger.warning(f"Variant generation failed: {e}")
                    if self.metrics_service:
                        self.metrics_service.increment_counter('processing.variants.failed')
                    errors.append(f"Variants: {str(e)}")

            # ================================================================
            # Layer 8: Embeddings (optional)
            # ================================================================
            embeddings = None
            if (generate_embeddings is True) or (
                generate_embeddings is None and self.enable_embeddings
            ):
                logger.debug("Stage 8: Embedding Generation")
                layer_start = time.time()
                try:
                    if self.embeddings_service is not None:
                        embeddings = await self._maybe_await(self.embeddings_service.generate_embeddings(
                            norm_result.normalized
                        ))
                    else:
                        logger.debug("Embeddings service not available - skipping embedding generation")
                    if self.metrics_service:
                        self.metrics_service.record_timer('processing.layer.embeddings', time.time() - layer_start)
                        if embeddings is not None:
                            self.metrics_service.record_histogram('embeddings.dimension', len(embeddings) if hasattr(embeddings, '__len__') else 0)
                except Exception as e:
                    logger.warning(f"Embedding generation failed: {e}")
                    if self.metrics_service:
                        self.metrics_service.increment_counter('processing.embeddings.failed')
                    errors.append(f"Embeddings: {str(e)}")

            # ================================================================
            # Layer 9: Decision & Response
            # ================================================================
            decision_result = None

            # Create processing result for decision engine
            temp_processing_result = UnifiedProcessingResult(
                original_text=context.original_text,
                language=context.language,
                language_confidence=context.language_confidence,
                normalized_text=norm_result.normalized,
                tokens=norm_result.tokens,
                trace=norm_result.trace,
                signals=signals_result,
                variants=variants,
                embeddings=embeddings,
                processing_time=0.0,  # Will be set below
                success=len(errors) == 0,
                errors=errors,
            )

            # Run decision engine if enabled
            decision_result = None
            if self.enable_decision_engine:
                logger.debug("Stage 9: Decision Engine")
                layer_start = time.time()
                try:
                    # Create DecisionInput from processing results
                    decision_input = self._create_decision_input(
                        context, temp_processing_result, signals_result
                    )
                    
                    # Make decision using our new DecisionEngine
                    decision_result = self.decision_engine.decide(decision_input)
                    
                    logger.debug(
                        f"Decision made: {decision_result.risk.value} "
                        f"(score: {decision_result.score:.2f})"
                    )
                    if self.metrics_service:
                        self.metrics_service.record_timer('processing.layer.decision', time.time() - layer_start)
                        self.metrics_service.record_histogram('decision.score', decision_result.score)
                        self.metrics_service.increment_counter(f'decision.result.{decision_result.risk.value.lower()}')
                except Exception as e:
                    logger.warning(f"Decision engine failed: {e}")
                    if self.metrics_service:
                        self.metrics_service.increment_counter('processing.decision.failed')
                    errors.append(f"Decision engine: {str(e)}")

            processing_time = time.time() - start_time

            # Update final metrics
            if self.metrics_service:
                self.metrics_service.record_timer('processing.total_time', processing_time)
                self.metrics_service.set_gauge('processing.requests.active', -1)  # Decrement active requests
                if len(errors) == 0:
                    self.metrics_service.increment_counter('processing.requests.successful')
                else:
                    self.metrics_service.increment_counter('processing.requests.failed')
                    self.metrics_service.record_histogram('processing.error_count', len(errors))

            # Warn if processing is slow
            if processing_time > 0.1:  # 100ms threshold per CLAUDE.md
                logger.warning(
                    f"Slow processing: {processing_time:.3f}s for text: {text[:50]}..."
                )
                if self.metrics_service:
                    self.metrics_service.increment_counter('processing.slow_requests')

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
                decision=decision_result,
                processing_time=processing_time,
                success=len(errors) == 0,
                errors=errors,
            )

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Processing failed: {e}", exc_info=True)

            # Update error metrics
            if self.metrics_service:
                self.metrics_service.increment_counter('processing.requests.failed')
                self.metrics_service.increment_counter('processing.exceptions')
                self.metrics_service.set_gauge('processing.requests.active', -1)  # Decrement active requests
                self.metrics_service.record_timer('processing.total_time', processing_time)

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
                errors=[str(e)],
            )

    def _create_early_response(
        self, context: ProcessingContext, reason: str, start_time: float
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
            errors=[reason],
        )

    def _create_filtered_response(
        self,
        context: ProcessingContext,
        filter_result,  # SmartFilterResult object
        start_time: float,
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
            errors=[],
        )

    def _create_decision_input(
        self, 
        context: ProcessingContext, 
        processing_result: UnifiedProcessingResult,
        signals_result: SignalsResult
    ) -> DecisionInput:
        """Create DecisionInput from processing results"""
        
        # Extract smart filter information
        smart_filter_info = context.metadata.get("smart_filter", {})
        smart_filter = SmartFilterInfo(
            should_process=smart_filter_info.get("should_process", True),
            confidence=smart_filter_info.get("confidence", 1.0),
            estimated_complexity=smart_filter_info.get("classification")
        )
        
        # Extract signals information
        person_confidence = 0.0
        org_confidence = 0.0
        date_match = False
        id_match = False
        evidence = {}
        
        if signals_result.persons:
            # Use the highest person confidence
            person_confidence = max(p.confidence for p in signals_result.persons)
            # Check for ID matches in person data
            for person in signals_result.persons:
                if hasattr(person, 'ids') and person.ids:
                    id_match = True
                    break
        
        if signals_result.organizations:
            # Use the highest organization confidence
            org_confidence = max(o.confidence for o in signals_result.organizations)
            # Check for ID matches in organization data
            for org in signals_result.organizations:
                if hasattr(org, 'ids') and org.ids:
                    id_match = True
                    break
        
        # Check for date matches in extras
        if hasattr(signals_result, 'extras') and isinstance(signals_result.extras, dict) and signals_result.extras.get('dates'):
            date_match = True
        
        # Create evidence dict
        evidence = {
            "persons_count": len(signals_result.persons),
            "organizations_count": len(signals_result.organizations),
            "signals_confidence": signals_result.confidence
        }
        
        signals = SignalsInfo(
            person_confidence=person_confidence,
            org_confidence=org_confidence,
            date_match=date_match,
            id_match=id_match,
            evidence=evidence
        )
        
        # Extract similarity information (if embeddings are available)
        similarity = SimilarityInfo()
        if processing_result.embeddings:
            # For now, we don't have similarity search implemented
            # This would be populated when similarity search is added
            similarity = SimilarityInfo(cos_top=None, cos_p95=None)
        
        return DecisionInput(
            text=context.original_text,
            language=context.language,
            smartfilter=smart_filter,
            signals=signals,
            similarity=similarity
        )

    # Convenience methods for backward compatibility

    async def normalize_async(self, text: str, **kwargs) -> NormalizationResult:
        """
        Backward compatibility: direct normalization.
        For new code, use process() instead.
        """
        logger.warning("normalize_async is deprecated. Use process() instead.")

        # Extract normalization-specific flags
        norm_flags = {
            k: v
            for k, v in kwargs.items()
            if k
            in [
                "language",
                "remove_stop_words",
                "preserve_names",
                "enable_advanced_features",
            ]
        }

        # Run minimal pipeline: validation -> unicode -> normalization
        validation_result = await self.validation_service.validate_and_sanitize(text)
        sanitized = validation_result.get("sanitized_text", text)

        unicode_result = await self.unicode_service.normalize_unicode(sanitized)
        unicode_normalized = unicode_result.get("normalized", sanitized)

        return await self.normalization_service.normalize_async(
            unicode_normalized, **norm_flags
        )

    async def extract_signals(
        self, original_text: str, normalization_result: NormalizationResult
    ) -> SignalsResult:
        """Backward compatibility: direct signals extraction"""
        logger.warning("extract_signals is deprecated. Use process() instead.")
        return await self.signals_service.extract_async(
            text=original_text, normalization_result=normalization_result
        )
