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
from ..utils.feature_flags import FeatureFlags
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
from ..contracts.trace_models import SearchTrace, SearchTraceBuilder
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
        default_feature_flags: Optional[FeatureFlags] = None,
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
        self.default_feature_flags = default_feature_flags or FeatureFlags()
        
        # Legacy compatibility attributes for old tests
        self.cache_service = getattr(self, "cache_service", None)
        self.embedding_service = getattr(self, "embedding_service", None) or embeddings_service
        self.signal_service = getattr(self, "signal_service", None) or signals_service
        self.pattern_service = getattr(self, "pattern_service", None)
        self.template_builder = getattr(self, "template_builder", None)
        
        # Legacy processing stats for old tests
        self.processing_stats = getattr(self, "processing_stats", None) or {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache": 0,  # Legacy compatibility
            "errors": 0,
            "processing_times": []
        }

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

    def _safe_len(self, x):
        """Safe length calculation that handles mocks and other objects"""
        try:
            return len(x)
        except Exception:
            return 0

    def _coerce_lang(self, res) -> Dict[str, Any]:
        """Coerce language detection result to dict with language/confidence keys"""
        if res is None:
            return {"language": "en", "confidence": 0.0}  # Fallback to English
        
        if isinstance(res, dict):
            return res
        
        if hasattr(res, 'language') and hasattr(res, 'confidence'):
            return {"language": res.language, "confidence": res.confidence}
        
        # If it's a string, assume it's the language code
        if isinstance(res, str):
            return {"language": res, "confidence": 0.5}
        
        # If it's a tuple, assume (language, confidence)
        if isinstance(res, tuple) and len(res) >= 2:
            return {"language": res[0], "confidence": res[1]}
        
        # Default fallback
        return {"language": "en", "confidence": 0.0}

    async def _handle_validation_layer(
        self, text: str, context: ProcessingContext, start_time: float
    ) -> Optional[UnifiedProcessingResult]:
        """
        Handle Layer 1: Validation & Sanitization

        Returns:
            UnifiedProcessingResult if early termination needed, None otherwise
        """
        logger.debug("Stage 1: Validation & Sanitization")
        layer_start = time.time()

        validation_result = await self._maybe_await(self.validation_service.validate_and_sanitize(text))
        context.sanitized_text = validation_result.get("sanitized_text", text)

        # Debug trace for lengths
        logger.debug(f"Validation: input_len={self._safe_len(text)}, sanitized_len={self._safe_len(context.sanitized_text)}")

        if self.metrics_service:
            self.metrics_service.record_timer('processing.layer.validation', time.time() - layer_start)

        if not validation_result.get("should_process", True):
            if self.metrics_service:
                self.metrics_service.record_counter('processing.validation.failed', 1)
            return self._create_early_response(context, "Input validation failed", start_time)

        return None  # Continue processing

    async def _handle_smart_filter_layer(
        self, context: ProcessingContext, start_time: float
    ) -> Optional[UnifiedProcessingResult]:
        """
        Handle Layer 2: Smart Filter (optional skip)

        Returns:
            UnifiedProcessingResult if early termination needed, None otherwise
        """
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
                    self.metrics_service.record_counter('processing.smart_filter.skipped', 1)
                return self._create_filtered_response(
                    context, filter_result, start_time
                )

        return None  # Continue processing

    async def _handle_language_detection_layer(
        self, context: ProcessingContext, language_hint: Optional[str]
    ) -> None:
        """
        Handle Layer 3: Language Detection

        Updates the context with detected language and confidence.
        """
        logger.debug("Stage 3: Language Detection")
        layer_start = time.time()

        from ..config import LANGUAGE_CONFIG
        lang_raw = await self._maybe_await(self.language_service.detect_language_config_driven(
            context.sanitized_text,  # Use original text to preserve Ukrainian/Russian markers
            LANGUAGE_CONFIG
        ))

        # Coerce language result to dict format
        lang = self._coerce_lang(lang_raw)
        context.language = language_hint or lang["language"]
        context.language_confidence = lang["confidence"]

        # Debug trace for language detection
        try:
            confidence_val = float(context.language_confidence)
            logger.debug(f"Language: detected='{context.language}', confidence={confidence_val:.3f}")
        except (ValueError, TypeError):
            logger.debug(f"Language: detected='{context.language}', confidence={context.language_confidence}")

        if self.metrics_service:
            self.metrics_service.record_timer('processing.layer.language_detection', time.time() - layer_start)
            self.metrics_service.record_histogram('language_detection.confidence', context.language_confidence)
            self.metrics_service.record_counter(f'language_detection.detected.{context.language}', 1)

    async def _handle_unicode_normalization_layer(
        self, context: ProcessingContext
    ) -> str:
        """
        Handle Layer 4: Unicode Normalization

        Returns:
            Unicode normalized text
        """
        logger.debug("Stage 4: Unicode Normalization")
        layer_start = time.time()

        # Unicode normalization after language detection
        text_in = context.sanitized_text
        unicode_result = await self._maybe_await(self.unicode_service.normalize_unicode(text_in))

        # Handle both legacy string return and new dict return
        if isinstance(unicode_result, str):
            text_u = unicode_result
        else:
            text_u = unicode_result.get("normalized", text_in)

        # Debug trace for lengths
        logger.debug(f"Unicode: input_len={self._safe_len(text_in)}, normalized_len={self._safe_len(text_u)}")

        if self.metrics_service:
            self.metrics_service.record_timer('processing.layer.unicode_normalization', time.time() - layer_start)

        return text_u

    async def _handle_name_normalization_layer(
        self,
        text_u: str,
        context: ProcessingContext,
        remove_stop_words: bool,
        preserve_names: bool,
        enable_advanced_features: bool,
        feature_flags: FeatureFlags,
        errors: list
    ) -> Any:
        """
        Handle Layer 5: Name Normalization (morph) - THE CORE

        Args:
            text_u: Unicode normalized text
            context: Processing context
            remove_stop_words: Clean STOP_ALL tokens in normalization
            preserve_names: Keep `. - '` for initials/compound names
            enable_advanced_features: Use morphology + diminutives + gender
            errors: List to append errors to

        Returns:
            Normalization result from the service
        """
        logger.debug("Stage 5: Name Normalization")
        layer_start = time.time()

        # Align legacy flags with feature flag directives
        remove_stop_words = feature_flags.strict_stopwords
        if feature_flags.preserve_hyphenated_case:
            preserve_names = True

        # Use unicode-normalized text for normalization
        norm_result = await self._maybe_await(self.normalization_service.normalize_async(
            text_u,  # Use unicode-normalized text
            language=context.language,
            remove_stop_words=remove_stop_words,
            preserve_names=preserve_names,
            enable_advanced_features=enable_advanced_features,
            feature_flags=feature_flags,
        ))
        
        # Add flag reasons to trace if debug_trace is enabled
        if hasattr(norm_result, 'debug_trace') and norm_result.debug_trace:
            from ..utils.flag_propagation import create_flag_context
            flag_context = create_flag_context(feature_flags, "normalization", True)
            
            # Note: Flag reasons are logged separately, not added to trace
            # as trace should only contain TokenTrace objects

        # Note: Feature flags are logged separately, not added to trace
        # as trace should only contain TokenTrace objects

        if self.metrics_service:
            self.metrics_service.record_timer('processing.layer.normalization', time.time() - layer_start)
            if hasattr(norm_result, 'confidence') and norm_result.confidence is not None:
                self.metrics_service.record_histogram('normalization.confidence', norm_result.confidence)
            self.metrics_service.record_histogram('normalization.token_count', self._safe_len(norm_result.tokens))

        if not norm_result.success:
            if self.metrics_service:
                self.metrics_service.record_counter('processing.normalization.failed', 1)
            errors.extend(norm_result.errors)

        return norm_result

    async def _handle_signals_layer(
        self, text_u: str, norm_result: Any, context: ProcessingContext
    ) -> Any:
        """
        Handle Layer 6: Signals (enrichment)

        Args:
            text_u: Unicode normalized text
            norm_result: Result from name normalization
            context: Processing context

        Returns:
            Signals extraction result
        """
        logger.debug("Stage 6: Signals Extraction")
        layer_start = time.time()

        signals_result = await self._maybe_await(self.signals_service.extract_signals(
            text=text_u, normalization_result=norm_result, language=context.language  # Use unicode-normalized text
        ))

        # Debug logging
        logger.info(f"Signals result: {signals_result}")
        logger.info(f"Signals organizations: {signals_result.organizations}")
        logger.info(f"Signals persons: {signals_result.persons}")

        if self.metrics_service:
            self.metrics_service.record_timer('processing.layer.signals', time.time() - layer_start)
            self.metrics_service.record_histogram('signals.confidence', signals_result.confidence)
            self.metrics_service.record_histogram('signals.persons_count', self._safe_len(signals_result.persons))
            self.metrics_service.record_histogram('signals.organizations_count', self._safe_len(signals_result.organizations))

        return signals_result

    async def _handle_variants_layer(
        self, norm_result: Any, context: ProcessingContext, generate_variants: Optional[bool], errors: list
    ) -> Optional[list]:
        """
        Handle Layer 7: Variants (optional)

        Args:
            norm_result: Result from name normalization
            context: Processing context
            generate_variants: Override for variants generation
            errors: List to append errors to

        Returns:
            Generated variants or None if disabled/failed
        """
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
                        self.metrics_service.record_histogram('variants.count', self._safe_len(variants))
            except Exception as e:
                logger.warning(f"Variant generation failed: {e}")
                if self.metrics_service:
                    self.metrics_service.record_counter('processing.variants.failed', 1)
                errors.append(f"Variants: {str(e)}")

        return variants

    async def _handle_embeddings_layer(
        self, norm_result: Any, generate_embeddings: Optional[bool], errors: list
    ) -> Optional[list]:
        """
        Handle Layer 8: Embeddings (optional)

        Args:
            norm_result: Result from name normalization
            generate_embeddings: Override for embeddings generation
            errors: List to append errors to

        Returns:
            Generated embeddings or None if disabled/failed
        """
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
                        self.metrics_service.record_histogram('embeddings.dimension', self._safe_len(embeddings))
            except Exception as e:
                logger.warning(f"Embedding generation failed: {e}")
                if self.metrics_service:
                    self.metrics_service.record_counter('processing.embeddings.failed', 1)
                errors.append(f"Embeddings: {str(e)}")

        return embeddings

    async def _handle_decision_layer(
        self,
        context: ProcessingContext,
        norm_result: Any,
        signals_result: Any,
        variants: Optional[list],
        embeddings: Optional[list],
        errors: list,
        search_trace: Optional[SearchTrace] = None
    ) -> Optional[Any]:
        """
        Handle Layer 9: Decision & Response

        Args:
            context: Processing context
            norm_result: Result from name normalization
            signals_result: Result from signals extraction
            variants: Generated variants (optional)
            embeddings: Generated embeddings (optional)
            errors: List of errors

        Returns:
            Decision result or None if disabled/failed
        """
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
            success=self._safe_len(errors) == 0,
            errors=errors,
        )

        # Run decision engine if enabled
        if self.enable_decision_engine:
            logger.debug("Stage 9: Decision Engine")
            layer_start = time.time()
            try:
                # Create DecisionInput from processing results
                decision_input = self._create_decision_input(
                    context, temp_processing_result, signals_result
                )

                # Make decision using our new DecisionEngine
                decision_result = self.decision_engine.decide(decision_input, search_trace)

                logger.debug(
                    f"Decision made: {decision_result.risk.value} "
                    f"(score: {decision_result.score:.2f})"
                )
                if self.metrics_service:
                    self.metrics_service.record_timer('processing.layer.decision', time.time() - layer_start)
                    self.metrics_service.record_histogram('decision.score', decision_result.score)
                    self.metrics_service.record_counter(f'decision.result.{decision_result.risk.value.lower()}', 1)
            except Exception as e:
                logger.warning(f"Decision engine failed: {e}")
                if self.metrics_service:
                    self.metrics_service.record_counter('processing.decision.failed', 1)
                errors.append(f"Decision engine: {str(e)}")

        return decision_result

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
        feature_flags: Optional[FeatureFlags] = None,
        # Search tracing
        search_trace_enabled: bool = False,
        # Legacy compatibility kwargs (ignored but accepted)
        cache_result: Optional[bool] = None,
        embeddings: Optional[bool] = None,
        variants: Optional[bool] = None,
        **legacy_kwargs,
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
        
        # Initialize search trace if enabled
        search_trace = None
        if search_trace_enabled:
            search_trace = SearchTrace(enabled=True)

        # Defensive handling of feature flags
        effective_flags = self._validate_and_normalize_flags(feature_flags)
        context.processing_flags["feature_flags"] = effective_flags.to_dict()
        context.metadata["feature_flags"] = effective_flags.to_dict()

        # Handle legacy kwargs mapping
        if embeddings is not None:
            generate_embeddings = embeddings
        if variants is not None:
            generate_variants = variants

        # Handle caching if enabled and cache_service is available
        cache_key = None
        if cache_result and self.cache_service:
            cache_key = self._generate_cache_key(text, remove_stop_words, preserve_names)
            try:
                cached_result = self.cache_service.get(cache_key)
                if cached_result:
                    # Update stats for cache hit
                    self.update_stats(0.001, cache_hit=True, error=False)
                    return cached_result
            except Exception as e:
                logger.debug(f"Cache get failed: {e}")

        # Cache miss or caching disabled
        if self.cache_service:
            self.processing_stats["cache_misses"] += 1

        # Initialize metrics collection
        if self.metrics_service:
            self.metrics_service.record_counter('processing.requests.total', 1)
            self.metrics_service.record_gauge('processing.requests.active', 1)

        try:
            # ================================================================
            # Layer 1: Validation & Sanitization
            # ================================================================
            validation_result = await self._handle_validation_layer(text, context, start_time)
            if validation_result is not None:  # Early return if validation failed
                return validation_result

            # ================================================================
            # Layer 2: Smart Filter (optional skip)
            # ================================================================
            smart_filter_result = await self._handle_smart_filter_layer(context, start_time)
            if smart_filter_result is not None:  # Early return if filtered
                return smart_filter_result
            
            # Add trace note for smart filter
            if search_trace:
                search_trace.note("Smart filter passed - continuing with processing")

            # ================================================================
            # Layer 3: Language Detection (on original text to preserve language markers)
            # ================================================================
            await self._handle_language_detection_layer(context, language_hint)

            # ================================================================
            # Layer 4: Unicode Normalization (after language detection)
            # ================================================================
            text_u = await self._handle_unicode_normalization_layer(context)

            # ================================================================
            # Layer 5: Name Normalization (morph) - THE CORE
            # ================================================================
            norm_result = await self._handle_name_normalization_layer(
                text_u, context, remove_stop_words, preserve_names, enable_advanced_features, effective_flags, errors
            )
            
            # Add trace note for AC patterns after normalization
            if search_trace and hasattr(norm_result, 'tokens') and norm_result.tokens:
                # Simple check for potential AC patterns
                has_tier0_patterns = any(
                    len(token) > 3 and token.isupper() 
                    for token in norm_result.tokens
                )
                if not has_tier0_patterns:
                    search_trace.note("AC skipped - no tier0/1 patterns detected")
                else:
                    search_trace.note("AC patterns detected - proceeding with search")

            # ================================================================
            # Layer 6: Signals (enrichment)
            # ================================================================
            signals_result = await self._handle_signals_layer(text_u, norm_result, context)

            # ================================================================
            # Layer 7: Variants (optional)
            # ================================================================
            variants = await self._handle_variants_layer(norm_result, context, generate_variants, errors)

            # ================================================================
            # Layer 8: Embeddings (optional)
            # ================================================================
            embeddings = await self._handle_embeddings_layer(norm_result, generate_embeddings, errors)
            
            # Add trace note for vector fallback
            if search_trace and embeddings:
                search_trace.note("Vector fallback engaged - embeddings generated for search")

            # ================================================================
            # Layer 9: Decision & Response
            # ================================================================
            decision_result = await self._handle_decision_layer(
                context, norm_result, signals_result, variants, embeddings, errors, search_trace
            )

            processing_time = time.time() - start_time

            # Update final metrics
            if self.metrics_service:
                self.metrics_service.record_timer('processing.total_time', processing_time)
                self.metrics_service.record_gauge('processing.requests.active', -1)  # Decrement active requests
                if len(errors) == 0:
                    self.metrics_service.record_counter('processing.requests.successful', 1)
                else:
                    self.metrics_service.record_counter('processing.requests.failed', 1)
                    self.metrics_service.record_histogram('processing.error_count', self._safe_len(errors))

            # Warn if processing is slow
            if processing_time > 0.1:  # 100ms threshold per CLAUDE.md
                logger.warning(
                    f"Slow processing: {processing_time:.3f}s for text: {text[:50]}..."
                )
                if self.metrics_service:
                    self.metrics_service.record_counter('processing.slow_requests', 1)

            # Update legacy stats
            self.update_stats(processing_time, cache_hit=False, error=self._safe_len(errors) > 0)

            # Create the result
            result = UnifiedProcessingResult(
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
                success=self._safe_len(errors) == 0,
                errors=errors,
            )

            # Cache the result if caching is enabled and successful
            if cache_result and self.cache_service and cache_key and result.success:
                try:
                    self.cache_service.set(cache_key, result)
                except Exception as e:
                    logger.debug(f"Cache set failed: {e}")

            return result

        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"Processing failed: {e}", exc_info=True)

            # Update error metrics
            if self.metrics_service:
                self.metrics_service.record_counter('processing.requests.failed', 1)
                self.metrics_service.record_counter('processing.exceptions', 1)
                self.metrics_service.record_gauge('processing.requests.active', -1)  # Decrement active requests
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
            "persons_count": self._safe_len(signals_result.persons),
            "organizations_count": self._safe_len(signals_result.organizations),
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
        validation_result = await self._maybe_await(self.validation_service.validate_and_sanitize(text))
        sanitized = validation_result.get("sanitized_text", text)

        # Fixed order: Unicode normalization first
        unicode_result = await self._maybe_await(self.unicode_service.normalize_unicode(sanitized))
        
        # Handle both legacy string return and new dict return
        if isinstance(unicode_result, str):
            unicode_normalized = unicode_result
        else:
            unicode_normalized = unicode_result.get("normalized", sanitized)

        return await self._maybe_await(self.normalization_service.normalize_async(
            unicode_normalized, **norm_flags
        ))

    async def extract_signals(
        self, original_text: str, normalization_result: NormalizationResult
    ) -> SignalsResult:
        """Backward compatibility: direct signals extraction"""
        logger.warning("extract_signals is deprecated. Use process() instead.")
        return await self._maybe_await(self.signals_service.extract_async(
            text=original_text, normalization_result=normalization_result
        ))

    # Legacy compatibility methods for old tests
    def clear_cache(self):
        """Legacy method for cache clearing"""
        if hasattr(self.cache_service, 'clear'):
            self.cache_service.clear()
        logger.warning("clear_cache is deprecated. Use cache_service directly.")

    def _generate_cache_key(self, text: str, remove_stop_words: bool, preserve_names: bool) -> str:
        """Legacy method for cache key generation"""
        import hashlib
        key_data = f"{text}:{remove_stop_words}:{preserve_names}"
        hash_part = hashlib.md5(key_data.encode()).hexdigest()
        return f"orchestrator_{hash_part}"

    def _calculate_complexity_score(self, unicode_complexity, language_complexity, name_complexity) -> float:
        """Legacy method for complexity calculation"""
        # Extract confidence values from dictionaries if needed
        unicode_val = unicode_complexity.get('confidence', 0.0) if isinstance(unicode_complexity, dict) else unicode_complexity
        language_val = language_complexity.get('confidence', 0.0) if isinstance(language_complexity, dict) else language_complexity
        name_val = name_complexity.get('confidence', 0.0) if isinstance(name_complexity, dict) else name_complexity
        
        # Combine different complexity factors
        return min(1.0, (unicode_val + language_val + name_val) / 3.0)

    def _generate_complexity_recommendations(self, score: float) -> List[str]:
        """Legacy method for complexity recommendations"""
        if score < 0.3:
            return ["Text is simple", "Consider adding more context"]
        elif score < 0.7:
            return ["Text complexity is moderate", "Good balance", "Consider reviewing structure"]
        else:
            return ["Text is complex", "Consider simplifying", "Break into smaller parts", "Use simpler language"]

    def get_processing_stats(self) -> Dict[str, Any]:
        """Legacy method for getting processing statistics"""
        return self.processing_stats.copy()

    def reset_stats(self):
        """Legacy method for resetting statistics"""
        self.processing_stats = {
            "total_processed": 0,
            "successful": 0,
            "failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "cache": 0,  # Legacy compatibility
            "errors": 0,
            "processing_times": []
        }

    def update_stats(self, processing_time: float, cache_hit: bool = False, error: bool = False):
        """Legacy method for updating statistics"""
        self.processing_stats["total_processed"] += 1
        if cache_hit:
            self.processing_stats["cache_hits"] += 1
        else:
            self.processing_stats["cache_misses"] += 1
        if error:
            self.processing_stats["errors"] += 1
        self.processing_stats["processing_times"].append(processing_time)

    def _update_stats(self, processing_time: float, cache_hit: bool = False, error: bool = False):
        """Legacy method alias for updating statistics"""
        self.update_stats(processing_time, cache_hit, error)

    async def process_batch(self, texts: List[str], **kwargs) -> List[UnifiedProcessingResult]:
        """Legacy method for batch processing"""
        logger.warning("process_batch is deprecated. Use individual process() calls with asyncio.gather.")
        results = []
        for text in texts:
            try:
                result = await self.process(text, **kwargs)
                results.append(result)
            except Exception as e:
                # Create error result
                error_result = UnifiedProcessingResult(
                    original_text=text,
                    language="en",
                    language_confidence=0.0,
                    normalized_text=text,
                    success=False,
                    errors=[str(e)]
                )
                results.append(error_result)
        return results

    def _validate_and_normalize_flags(self, feature_flags: Optional[FeatureFlags]) -> FeatureFlags:
        """
        Validate and normalize feature flags with defensive handling.
        
        Args:
            feature_flags: Feature flags to validate, can be None
            
        Returns:
            Valid FeatureFlags instance, defaults to self.default_feature_flags if invalid
        """
        if feature_flags is None:
            return self.default_feature_flags
        
        # Validate that it's a FeatureFlags instance
        if not isinstance(feature_flags, FeatureFlags):
            logger.warning(f"Invalid feature_flags type: {type(feature_flags)}, using defaults")
            return self.default_feature_flags
        
        # Validate individual flag values
        try:
            # Check for any invalid boolean values
            flag_dict = feature_flags.to_dict()
            for flag_name, flag_value in flag_dict.items():
                if not isinstance(flag_value, bool):
                    logger.warning(f"Invalid flag value for {flag_name}: {flag_value} (type: {type(flag_value)}), using default")
                    # Reset to default value
                    if hasattr(self.default_feature_flags, flag_name):
                        setattr(feature_flags, flag_name, getattr(self.default_feature_flags, flag_name))
            
            return feature_flags
            
        except Exception as e:
            logger.warning(f"Error validating feature flags: {e}, using defaults")
            return self.default_feature_flags

    async def search_similar_names(self, query: str, limit: int = 10, candidates: Optional[List[str]] = None, use_embeddings: bool = True, **kwargs) -> Dict[str, Any]:
        """Legacy method for searching similar names"""
        logger.warning("search_similar_names is deprecated. Use embeddings_service directly.")

        results = []
        method = "embeddings" if use_embeddings else "fallback"

        if use_embeddings and self.embeddings_service and hasattr(self.embeddings_service, 'find_similar_texts'):
            raw_results = await self._maybe_await(self.embeddings_service.find_similar_texts(query, limit))
            # Convert to expected format if needed
            if isinstance(raw_results, list):
                results = raw_results

        return {
            "method": method,
            "query": query,
            "results": results[:limit] if results else []
        }

    async def analyze_text_complexity(self, text: str) -> Dict[str, Any]:
        """Legacy method for analyzing text complexity"""
        # Calculate individual complexity factors
        words = text.split()
        word_count = len(words)
        avg_word_length = sum(len(word) for word in words) / word_count if word_count > 0 else 0
        unicode_complexity = min(1.0, len(text) / 100.0)
        language_complexity = min(1.0, word_count / 20.0)
        name_complexity = min(1.0, avg_word_length / 10.0)
        
        score = self._calculate_complexity_score(unicode_complexity, language_complexity, name_complexity)
        recommendations = self._generate_complexity_recommendations(score)
        return {
            "complexity_score": score,
            "recommendations": recommendations,
            "word_count": word_count,
            "character_count": len(text)
        }
