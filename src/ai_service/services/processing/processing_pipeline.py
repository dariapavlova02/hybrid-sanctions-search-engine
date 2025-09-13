"""
Text Processing Pipeline
Implements Chain of Responsibility pattern for text processing stages.
"""

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

from ..exceptions import ProcessingError
from ..utils import get_logger
from ..utils.input_validation import ValidationResult, input_validator
from .service_coordinator import ServiceRegistry


@dataclass
class ProcessingContext:
    """Context object passed through the processing pipeline"""
    
    # Input data
    original_text: str
    processing_options: Dict[str, Any]
    
    # Processing state
    current_text: str
    language: str = "unknown"
    language_confidence: float = 0.0
    
    # Results accumulated during processing
    normalized_text: str = ""
    variants: List[str] = None
    token_variants: Optional[Dict[str, List[str]]] = None
    embeddings: Optional[List] = None
    smart_filter_result: Optional[Dict[str, Any]] = None
    validation_result: Optional[ValidationResult] = None
    
    # Processing metadata
    start_time: datetime = None
    processing_time: float = 0.0
    errors: List[str] = None
    stage_timings: Dict[str, float] = None
    
    def __post_init__(self):
        """Initialize defaults"""
        if self.variants is None:
            self.variants = []
        if self.errors is None:
            self.errors = []
        if self.stage_timings is None:
            self.stage_timings = {}
        if self.start_time is None:
            self.start_time = datetime.now()
    
    @property
    def success(self) -> bool:
        """Check if processing was successful"""
        return len(self.errors) == 0
    
    def add_error(self, error: str) -> None:
        """Add error to context"""
        self.errors.append(error)
    
    def record_stage_timing(self, stage_name: str, duration: float) -> None:
        """Record timing for a processing stage"""
        self.stage_timings[stage_name] = duration


class ProcessingStage(ABC):
    """Abstract base class for processing stages"""
    
    def __init__(self, stage_name: str):
        self.stage_name = stage_name
        self.logger = get_logger(f"{__name__}.{stage_name}")
    
    async def execute(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """
        Execute processing stage with timing and error handling
        
        Args:
            context: Processing context
            services: Service registry
            
        Returns:
            Updated processing context
        """
        stage_start = datetime.now()
        
        try:
            self.logger.debug(f"Starting {self.stage_name} stage")
            context = await self.process(context, services)
            
        except Exception as e:
            error_msg = f"{self.stage_name} stage failed: {str(e)}"
            self.logger.error(error_msg)
            context.add_error(error_msg)
            
        finally:
            # Record timing
            stage_duration = (datetime.now() - stage_start).total_seconds()
            context.record_stage_timing(self.stage_name, stage_duration)
            self.logger.debug(f"Completed {self.stage_name} stage in {stage_duration:.3f}s")
        
        return context
    
    @abstractmethod
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """
        Process the context - to be implemented by concrete stages
        
        Args:
            context: Processing context
            services: Service registry
            
        Returns:
            Updated processing context
        """
        pass


class ValidationStage(ProcessingStage):
    """Input validation and sanitization stage"""
    
    def __init__(self):
        super().__init__("validation")
    
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """Validate and sanitize input text"""
        
        validation_result = input_validator.validate_and_sanitize(
            context.original_text,
            strict_mode=False,
            remove_homoglyphs=True,
        )
        
        context.validation_result = validation_result
        
        if validation_result.warnings:
            self.logger.warning(f"Input validation warnings: {validation_result.warnings}")
        
        if not validation_result.is_valid:
            context.add_error(f"Input validation failed: {validation_result.blocked_patterns}")
            return context
        
        # Use sanitized text for further processing
        context.current_text = validation_result.sanitized_text
        
        return context


class SmartFilterStage(ProcessingStage):
    """Smart filtering stage for early text classification"""
    
    def __init__(self):
        super().__init__("smart_filter")
    
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """Apply smart filtering to determine if full processing is needed"""
        
        if not services.smart_filter:
            self.logger.debug("Smart filter not available, skipping")
            return context
        
        try:
            filter_result = services.smart_filter.should_process_text(context.current_text)
            
            context.smart_filter_result = {
                "should_process": filter_result.should_process,
                "confidence": filter_result.confidence,
                "detected_signals": filter_result.detected_signals,
                "processing_recommendation": filter_result.processing_recommendation,
                "estimated_complexity": filter_result.estimated_complexity,
                "signal_details": filter_result.signal_details
            }
            
            # If smart filter says skip processing, set a flag but continue
            if not filter_result.should_process:
                self.logger.info(f"SmartFilter recommends skipping: {filter_result.processing_recommendation}")
            else:
                self.logger.info(f"SmartFilter signals: {filter_result.detected_signals}, confidence: {filter_result.confidence:.3f}")
            
        except Exception as e:
            self.logger.warning(f"Smart filter failed: {e}")
            context.smart_filter_result = {"error": str(e)}
        
        return context


class LanguageDetectionStage(ProcessingStage):
    """Language detection stage"""
    
    def __init__(self):
        super().__init__("language_detection")
    
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """Detect language of the text"""
        
        language_result = services.language_service.detect_language(context.current_text)
        
        context.language = language_result["language"]
        context.language_confidence = language_result["confidence"]
        
        self.logger.info(f"Language detected: {context.language} (confidence: {context.language_confidence:.2f})")
        
        return context


class UnicodeNormalizationStage(ProcessingStage):
    """Unicode normalization stage"""
    
    def __init__(self):
        super().__init__("unicode_normalization")
    
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """Normalize Unicode characters"""
        
        unicode_result = services.unicode_service.normalize_text(
            context.current_text, aggressive=False
        )
        
        context.current_text = unicode_result["normalized"]
        
        if unicode_result.get("changes"):
            self.logger.debug(f"Unicode normalization applied changes: {unicode_result['changes']}")
        
        return context


class TextNormalizationStage(ProcessingStage):
    """Advanced text normalization stage"""
    
    def __init__(self):
        super().__init__("text_normalization")
    
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """Perform advanced text normalization"""
        
        # Use advanced normalization if available, fallback to basic normalization
        if hasattr(services, 'advanced_normalization_service') and services.advanced_normalization_service:
            try:
                norm_result = await services.advanced_normalization_service.normalize_advanced(
                    context.current_text,
                    language=context.language,
                    enable_morphology=True,
                    enable_transliterations=True,
                    enable_phonetic_variants=True,
                    preserve_names=True,
                    clean_unicode=False,  # Already normalized by unicode stage
                )
                
                if norm_result:
                    context.normalized_text = norm_result.get("normalized", context.current_text)
                    context.token_variants = norm_result.get("token_variants", {})
                else:
                    raise Exception("Advanced normalization returned None")
                    
            except Exception as e:
                self.logger.warning(f"Advanced normalization failed, using basic: {e}")
                # Fallback to basic normalization
                await self._basic_normalization(context, services)
        else:
            await self._basic_normalization(context, services)
        
        return context
    
    async def _basic_normalization(self, context: ProcessingContext, services: ServiceRegistry) -> None:
        """Fallback basic normalization"""
        
        norm_result = await services.normalization_service.normalize_async(
            context.current_text,
            language=context.language,
            preserve_names=True,
            apply_lemmatization=True,
            apply_stemming=False,
            remove_stop_words=False,
        )
        
        if norm_result:
            context.normalized_text = getattr(norm_result, "normalized", context.current_text)
        else:
            context.normalized_text = context.current_text
            context.add_error("Basic normalization also failed")


class VariantGenerationStage(ProcessingStage):
    """Variant generation stage"""
    
    def __init__(self):
        super().__init__("variant_generation")
    
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """Generate text variants"""
        
        # Check if variant generation is requested
        if not context.processing_options.get("generate_variants", False):
            self.logger.debug("Variant generation not requested, skipping")
            return context
        
        if len(context.normalized_text.strip()) <= 2:
            self.logger.debug("Text too short for variant generation")
            return context
        
        try:
            # This would need the variant service to be added to ServiceRegistry
            if hasattr(services, 'variant_service') and services.variant_service:
                variant_result = services.variant_service.generate_variants(
                    text=context.normalized_text,
                    language=context.language,
                    max_variants=50,
                )
                
                if variant_result and "variants" in variant_result:
                    context.variants = variant_result["variants"]
                    
                    # Remove duplicates and empty strings
                    context.variants = list(
                        set(v for v in context.variants if v and len(v.strip()) > 0)
                    )
            
            # Ensure at least the normalized text is in variants
            if not context.variants:
                context.variants = [context.normalized_text]
                
        except Exception as e:
            self.logger.warning(f"Variant generation failed: {e}")
            context.variants = [context.normalized_text]
        
        return context


class EmbeddingGenerationStage(ProcessingStage):
    """Embedding generation stage"""
    
    def __init__(self):
        super().__init__("embedding_generation")
    
    async def process(self, context: ProcessingContext, services: ServiceRegistry) -> ProcessingContext:
        """Generate embeddings"""
        
        # Check if embedding generation is requested
        if not context.processing_options.get("generate_embeddings", False):
            self.logger.debug("Embedding generation not requested, skipping")
            return context
        
        try:
            embedding_result = services.embedding_service.get_embeddings(
                [context.normalized_text], normalize=True
            )
            
            if embedding_result.get("success"):
                context.embeddings = embedding_result["embeddings"]
            else:
                self.logger.warning("Embedding generation failed")
                
        except Exception as e:
            self.logger.warning(f"Embedding generation failed: {e}")
        
        return context


class ProcessingPipeline:
    """
    Main processing pipeline that orchestrates all processing stages
    """
    
    def __init__(self, services: ServiceRegistry):
        """
        Initialize processing pipeline
        
        Args:
            services: Initialized service registry
        """
        self.services = services
        self.logger = get_logger(__name__)
        
        # Define the processing stages in order
        self.stages = [
            ValidationStage(),
            SmartFilterStage(),
            LanguageDetectionStage(),
            UnicodeNormalizationStage(),
            TextNormalizationStage(),
            VariantGenerationStage(),
            EmbeddingGenerationStage(),
        ]
        
    async def process_text(
        self,
        text: str,
        generate_variants: bool = True,
        generate_embeddings: bool = False,
        **kwargs
    ) -> ProcessingContext:
        """
        Process text through the complete pipeline
        
        Args:
            text: Input text to process
            generate_variants: Whether to generate variants
            generate_embeddings: Whether to generate embeddings
            **kwargs: Additional processing options
            
        Returns:
            ProcessingContext with results
        """
        
        # Create processing context
        context = ProcessingContext(
            original_text=text,
            current_text=text,
            processing_options={
                "generate_variants": generate_variants,
                "generate_embeddings": generate_embeddings,
                **kwargs
            }
        )
        
        # Execute all stages
        for stage in self.stages:
            context = await stage.execute(context, self.services)
            
            # If there are critical errors, stop processing
            if context.errors and self._should_stop_on_error(stage, context):
                break
        
        # Calculate total processing time
        context.processing_time = (datetime.now() - context.start_time).total_seconds()
        
        self.logger.info(f"Processing completed in {context.processing_time:.3f}s")
        
        return context
    
    def _should_stop_on_error(self, stage: ProcessingStage, context: ProcessingContext) -> bool:
        """
        Determine if processing should stop based on the error and stage
        
        Args:
            stage: The stage that encountered an error
            context: Processing context with errors
            
        Returns:
            True if processing should stop
        """
        # For now, only stop on validation errors
        if isinstance(stage, ValidationStage):
            return True
        
        # For other stages, continue processing
        return False