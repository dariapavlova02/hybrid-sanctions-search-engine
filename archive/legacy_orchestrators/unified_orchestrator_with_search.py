"""
Unified Orchestrator Service with Search Integration

Extended version of UnifiedOrchestrator that includes HybridSearchService integration
between Signals and Decision layers without breaking existing contracts.
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
from ..contracts.search_contracts import SearchOpts, SearchMode
from ..core.decision_engine import DecisionEngine
from ..config.settings import DecisionConfig
from ..exceptions import InternalServerError, ServiceInitializationError
from ..utils import get_logger
from ..monitoring.metrics_service import MetricsService, MetricType, AlertSeverity
from .search_integration import SearchIntegration, create_search_integration

logger = get_logger(__name__)


class UnifiedOrchestratorWithSearch:
    """
    Unified orchestrator with search integration implementing the 9+ layer processing model.

    This extends the original UnifiedOrchestrator with HybridSearchService integration
    between Signals (Layer 6) and Decision (Layer 9) layers.
    
    Layers implemented:
    1. Validation & Sanitization
    2. Smart Filter (optional skip)
    3. Language Detection
    4. Unicode Normalization
    5. Name Normalization (morph)
    6. Signals (enrichment)
    6.5. Hybrid Search (NEW)
    7. Variants (optional)
    8. Embeddings (optional)
    9. Decision & Response
    """

    def __init__(
        self,
        # Core services
        validation_service: ValidationServiceInterface,
        smart_filter_service: Optional[SmartFilterInterface] = None,
        language_service: LanguageDetectionInterface = None,
        unicode_service: UnicodeServiceInterface = None,
        normalization_service: NormalizationServiceInterface = None,
        signals_service: SignalsServiceInterface = None,
        variants_service: Optional[VariantsServiceInterface] = None,
        embeddings_service: Optional[EmbeddingsServiceInterface] = None,
        decision_engine: Optional[DecisionEngine] = None,
        # Search service (NEW)
        hybrid_search_service: Optional[Any] = None,
        # Feature flags
        enable_smart_filter: bool = True,
        enable_variants: bool = False,
        enable_embeddings: bool = False,
        enable_decision_engine: bool = False,
        enable_hybrid_search: bool = False,  # NEW
        # Processing behavior
        allow_smart_filter_skip: bool = False,
        # Metrics
        metrics_service: Optional[MetricsService] = None,
    ):
        """
        Initialize orchestrator with search integration.
        
        Args:
            hybrid_search_service: HybridSearchService instance for search functionality
            enable_hybrid_search: Enable hybrid search layer
            ... (other parameters same as original UnifiedOrchestrator)
        """
        # Store services
        self.validation_service = validation_service
        self.smart_filter_service = smart_filter_service
        self.language_service = language_service
        self.unicode_service = unicode_service
        self.normalization_service = normalization_service
        self.signals_service = signals_service
        self.variants_service = variants_service
        self.embeddings_service = embeddings_service
        self.decision_engine = decision_engine
        self.hybrid_search_service = hybrid_search_service  # NEW
        
        # Feature flags
        self.enable_smart_filter = enable_smart_filter
        self.enable_variants = enable_variants
        self.enable_embeddings = enable_embeddings
        self.enable_decision_engine = enable_decision_engine
        self.enable_hybrid_search = enable_hybrid_search  # NEW
        
        # Processing behavior
        self.allow_smart_filter_skip = allow_smart_filter_skip
        
        # Metrics
        self.metrics_service = metrics_service
        
        # Search integration (NEW)
        self.search_integration = create_search_integration(hybrid_search_service)
        
        # Log initialization
        logger.info(f"UnifiedOrchestratorWithSearch initialized with search: {enable_hybrid_search}")

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
        # Search options (NEW)
        search_opts: Optional[SearchOpts] = None,
        # Legacy compatibility kwargs (ignored but accepted)
        cache_result: Optional[bool] = None,
        embeddings: Optional[bool] = None,
        variants: Optional[bool] = None,
        **legacy_kwargs,
    ) -> UnifiedProcessingResult:
        """
        Process text through the 9+ layer pipeline with search integration.
        
        Args:
            text: Input text to process
            search_opts: Search options for hybrid search
            ... (other parameters same as original process method)
            
        Returns:
            UnifiedProcessingResult with search information
        """
        start_time = time.time()
        errors = []
        temp_processing_result = None
        signals_result = None
        
        # Create processing context
        context = ProcessingContext(
            original_text=text,
            sanitized_text="",
            should_process=True,
            language="auto",
            processing_stage=ProcessingStage.VALIDATION,
            metadata={}
        )
        
        try:
            # ================================================================
            # Layer 1: Validation & Sanitization
            # ================================================================
            logger.debug("Stage 1: Validation & Sanitization")
            layer_start = time.time()
            
            validation_result = await self._maybe_await(
                self.validation_service.validate_and_sanitize(text)
            )
            context.sanitized_text = validation_result.sanitized_text
            context.metadata["validation"] = {
                "is_valid": validation_result.is_valid,
                "sanitized_length": len(validation_result.sanitized_text),
                "original_length": len(text)
            }
            
            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.validation', time.time() - layer_start)
            
            if not validation_result.is_valid:
                return self._create_validation_error_response(context, validation_result, start_time)
            
            # ================================================================
            # Layer 2: Smart Filter (optional skip)
            # ================================================================
            if self.enable_smart_filter:
                logger.debug("Stage 2: Smart Filter")
                layer_start = time.time()
                
                filter_result = await self._maybe_await(
                    self.smart_filter_service.should_process(context.sanitized_text)
                )
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
                    return self._create_filtered_response(context, filter_result, start_time)
            
            # ================================================================
            # Layer 3: Language Detection
            # ================================================================
            logger.debug("Stage 3: Language Detection")
            layer_start = time.time()
            
            from ..config import LANGUAGE_CONFIG
            lang_raw = await self._maybe_await(
                self.language_service.detect_language_config_driven(
                    context.sanitized_text, LANGUAGE_CONFIG
                )
            )
            context.language = lang_raw.language
            context.metadata["language_detection"] = {
                "language": lang_raw.language,
                "confidence": lang_raw.confidence,
                "method": lang_raw.method
            }
            
            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.language_detection', time.time() - layer_start)
                self.metrics_service.record_histogram('language_detection.confidence', lang_raw.confidence)
            
            # ================================================================
            # Layer 4: Unicode Normalization
            # ================================================================
            logger.debug("Stage 4: Unicode Normalization")
            layer_start = time.time()
            
            unicode_result = await self._maybe_await(
                self.unicode_service.normalize_unicode(context.sanitized_text)
            )
            context.sanitized_text = unicode_result.normalized_text
            context.metadata["unicode_normalization"] = {
                "normalized_length": len(unicode_result.normalized_text),
                "changes_made": unicode_result.changes_made,
                "normalization_method": unicode_result.normalization_method
            }
            
            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.unicode_normalization', time.time() - layer_start)
            
            # ================================================================
            # Layer 5: Name Normalization (morph)
            # ================================================================
            logger.debug("Stage 5: Name Normalization")
            layer_start = time.time()
            
            normalization_result = await self._maybe_await(
                self.normalization_service.normalize_async(
                    context.sanitized_text,
                    language=context.language,
                    remove_stop_words=remove_stop_words,
                    preserve_names=preserve_names,
                    enable_advanced_features=enable_advanced_features
                )
            )
            
            context.metadata["normalization"] = {
                "normalized_text": normalization_result.normalized,
                "token_count": normalization_result.token_count,
                "language": normalization_result.language,
                "confidence": normalization_result.confidence,
                "processing_time": normalization_result.processing_time
            }
            
            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.normalization', time.time() - layer_start)
                self.metrics_service.record_histogram('normalization.token_count', normalization_result.token_count)
            
            # ================================================================
            # Layer 6: Signals (enrichment)
            # ================================================================
            logger.debug("Stage 6: Signals")
            layer_start = time.time()
            
            signals_result = await self._maybe_await(
                self.signals_service.extract(
                    context.sanitized_text,
                    normalization_result=normalization_result.__dict__,
                    language=context.language
                )
            )
            
            context.metadata["signals"] = {
                "persons_count": len(signals_result.get("persons", [])),
                "organizations_count": len(signals_result.get("organizations", [])),
                "extraction_time": signals_result.get("processing_time", 0.0)
            }
            
            if self.metrics_service:
                self.metrics_service.record_timer('processing.layer.signals', time.time() - layer_start)
                self.metrics_service.record_histogram('signals.persons_count', len(signals_result.get("persons", [])))
                self.metrics_service.record_histogram('signals.organizations_count', len(signals_result.get("organizations", [])))
            
            # ================================================================
            # Layer 6.5: Hybrid Search (NEW)
            # ================================================================
            search_info = None
            if self.enable_hybrid_search and self.search_integration.should_enable_search(signals_result):
                logger.debug("Stage 6.5: Hybrid Search")
                layer_start = time.time()
                
                try:
                    search_info = await self.search_integration.extract_and_search(
                        text=context.sanitized_text,
                        normalization_result=normalization_result,
                        signals_result=signals_result,
                        search_opts=search_opts
                    )
                    
                    if search_info:
                        context.metadata["search"] = {
                            "total_matches": search_info.total_matches,
                            "high_confidence_matches": search_info.high_confidence_matches,
                            "search_time": search_info.search_time,
                            "has_exact_matches": search_info.has_exact_matches,
                            "has_phrase_matches": search_info.has_phrase_matches,
                            "has_ngram_matches": search_info.has_ngram_matches,
                            "has_vector_matches": search_info.has_vector_matches
                        }
                        
                        logger.debug(f"Hybrid search found {search_info.total_matches} matches")
                    
                    if self.metrics_service:
                        self.metrics_service.record_timer('processing.layer.hybrid_search', time.time() - layer_start)
                        if search_info:
                            self.metrics_service.record_histogram('hybrid_search.total_matches', search_info.total_matches)
                            self.metrics_service.record_histogram('hybrid_search.high_confidence_matches', search_info.high_confidence_matches)
                
                except Exception as e:
                    logger.warning(f"Hybrid search failed: {e}")
                    if self.metrics_service:
                        self.metrics_service.increment_counter('processing.hybrid_search.failed')
                    errors.append(f"Hybrid search: {str(e)}")
            
            # ================================================================
            # Layer 7: Variants (optional)
            # ================================================================
            if self.enable_variants and self.variants_service:
                logger.debug("Stage 7: Variants")
                layer_start = time.time()
                
                try:
                    variants_result = await self._maybe_await(
                        self.variants_service.generate_variants(
                            context.sanitized_text,
                            language=context.language
                        )
                    )
                    
                    context.metadata["variants"] = {
                        "variants_count": len(variants_result.get("variants", [])),
                        "generation_time": variants_result.get("processing_time", 0.0)
                    }
                    
                    if self.metrics_service:
                        self.metrics_service.record_timer('processing.layer.variants', time.time() - layer_start)
                        self.metrics_service.record_histogram('variants.count', len(variants_result.get("variants", [])))
                
                except Exception as e:
                    logger.warning(f"Variants generation failed: {e}")
                    if self.metrics_service:
                        self.metrics_service.increment_counter('processing.variants.failed')
                    errors.append(f"Variants: {str(e)}")
            
            # ================================================================
            # Layer 8: Embeddings (optional)
            # ================================================================
            if self.enable_embeddings and self.embeddings_service:
                logger.debug("Stage 8: Embeddings")
                layer_start = time.time()
                
                try:
                    embeddings_result = await self._maybe_await(
                        self.embeddings_service.generate_embeddings(
                            context.sanitized_text,
                            language=context.language
                        )
                    )
                    
                    context.metadata["embeddings"] = {
                        "embedding_dimension": len(embeddings_result.get("embedding", [])),
                        "generation_time": embeddings_result.get("processing_time", 0.0)
                    }
                    
                    if self.metrics_service:
                        self.metrics_service.record_timer('processing.layer.embeddings', time.time() - layer_start)
                        self.metrics_service.record_histogram('embeddings.dimension', len(embeddings_result.get("embedding", [])))
                
                except Exception as e:
                    logger.warning(f"Embeddings generation failed: {e}")
                    if self.metrics_service:
                        self.metrics_service.increment_counter('processing.embeddings.failed')
                    errors.append(f"Embeddings: {str(e)}")
            
            # ================================================================
            # Layer 9: Decision & Response
            # ================================================================
            if self.enable_decision_engine:
                logger.debug("Stage 9: Decision Engine")
                layer_start = time.time()
                
                try:
                    # Create DecisionInput from processing results
                    decision_input = self._create_decision_input(
                        context, temp_processing_result, signals_result
                    )
                    
                    # Add search information if available (NEW)
                    if search_info:
                        decision_input = self.search_integration.create_decision_input_with_search(
                            decision_input, search_info
                        )
                    
                    # Make decision using DecisionEngine
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
                self.metrics_service.record_timer('processing.total', processing_time)
                self.metrics_service.record_histogram('processing.total_time', processing_time)
            
            # Create final result
            return UnifiedProcessingResult(
                success=True,
                processing_time=processing_time,
                language=context.language,
                normalized_text=normalization_result.normalized,
                signals=signals_result,
                metadata=context.metadata,
                errors=errors
            )
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            if self.metrics_service:
                self.metrics_service.increment_counter('processing.failed')
            return UnifiedProcessingResult(
                success=False,
                processing_time=time.time() - start_time,
                language=context.language,
                normalized_text="",
                signals={},
                metadata=context.metadata,
                errors=errors + [f"Processing failed: {str(e)}"]
            )
    
    def _create_decision_input(
        self, 
        context: ProcessingContext, 
        temp_processing_result: Any, 
        signals_result: SignalsResult
    ) -> DecisionInput:
        """Create DecisionInput from processing results"""
        # Extract signals information
        persons = signals_result.get("persons", [])
        organizations = signals_result.get("organizations", [])
        
        # Calculate person confidence
        person_confidence = 0.0
        if persons:
            person_confidences = [p.get("confidence", 0.0) for p in persons if isinstance(p, dict)]
            person_confidence = max(person_confidences) if person_confidences else 0.0
        
        # Calculate organization confidence
        org_confidence = 0.0
        if organizations:
            org_confidences = [o.get("confidence", 0.0) for o in organizations if isinstance(o, dict)]
            org_confidence = max(org_confidences) if org_confidences else 0.0
        
        # Check for date and ID matches
        date_match = any(
            p.get("date_match", False) for p in persons 
            if isinstance(p, dict) and "date_match" in p
        )
        id_match = any(
            p.get("id_match", False) for p in persons 
            if isinstance(p, dict) and "id_match" in p
        )
        
        return DecisionInput(
            text=context.sanitized_text,
            language=context.language,
            smartfilter=SmartFilterInfo(
                should_process=context.should_process,
                confidence=context.metadata.get("smart_filter", {}).get("confidence", 1.0)
            ),
            signals=SignalsInfo(
                person_confidence=person_confidence,
                org_confidence=org_confidence,
                date_match=date_match,
                id_match=id_match,
                evidence=signals_result
            ),
            similarity=SimilarityInfo()  # Will be filled by embeddings if available
        )
    
    def _create_validation_error_response(
        self, 
        context: ProcessingContext, 
        validation_result: Any, 
        start_time: float
    ) -> UnifiedProcessingResult:
        """Create response for validation errors"""
        return UnifiedProcessingResult(
            success=False,
            processing_time=time.time() - start_time,
            language=context.language,
            normalized_text="",
            signals={},
            metadata=context.metadata,
            errors=[f"Validation failed: {validation_result.error_message}"]
        )
    
    def _create_filtered_response(
        self, 
        context: ProcessingContext, 
        filter_result: Any, 
        start_time: float
    ) -> UnifiedProcessingResult:
        """Create response for filtered text"""
        return UnifiedProcessingResult(
            success=True,
            processing_time=time.time() - start_time,
            language=context.language,
            normalized_text=context.sanitized_text,
            signals={},
            metadata=context.metadata,
            errors=[]
        )
    
    async def _maybe_await(self, coro_or_result):
        """Await if coroutine, otherwise return as-is"""
        if asyncio.iscoroutine(coro_or_result):
            return await coro_or_result
        return coro_or_result
