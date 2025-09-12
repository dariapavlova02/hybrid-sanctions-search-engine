"""
Normalization service stage adapter implementing Single Responsibility Principle.
Integrates NormalizationService into the processing pipeline.
"""

import logging
from typing import Any, Dict

try:
    from ..interfaces import (
        ProcessingContext,
        ProcessingStage,
        ProcessingStageInterface,
    )
except ImportError:
    import sys
    from pathlib import Path

    orchestration_path = Path(__file__).parent.parent
    sys.path.insert(0, str(orchestration_path))

    from interfaces import ProcessingContext, ProcessingStage, ProcessingStageInterface

# Import NormalizationService
try:
    from ...services.normalization_service import NormalizationService
except ImportError:
    import sys
    from pathlib import Path

    services_path = Path(__file__).parent.parent.parent / "services"
    sys.path.insert(0, str(services_path))

    from normalization_service import NormalizationService


class NormalizationServiceStage(ProcessingStageInterface):
    """
    Normalization service stage adapter.
    Single Responsibility: Integrates NormalizationService into pipeline.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.preserve_names = self.config.get("preserve_names", True)
        self.remove_stop_words = self.config.get("remove_stop_words", False)
        self.apply_stemming = self.config.get("apply_stemming", False)
        self.apply_lemmatization = self.config.get("apply_lemmatization", True)
        self.clean_unicode = self.config.get("clean_unicode", True)
        self.enable_advanced_features = self.config.get("enable_advanced_features", True)
        self.logger = logging.getLogger(f"{__name__}.NormalizationServiceStage")
        
        # Initialize NormalizationService
        try:
            self.normalization_service = NormalizationService()
        except Exception as e:
            self.logger.error(f"Failed to initialize NormalizationService: {e}")
            self.normalization_service = None

    async def process(self, context: ProcessingContext) -> ProcessingContext:
        """Process text using NormalizationService"""
        if not self.normalization_service:
            self.logger.error("NormalizationService not available")
            context.stage_results[ProcessingStage.TEXT_NORMALIZATION] = {
                "error": "NormalizationService not available",
                "success": False,
            }
            return context

        text = context.current_text
        original_text = text

        try:
            # Detect language if not already detected
            language = context.language or "auto"
            
            # Normalize text using NormalizationService
            result = await self.normalization_service.normalize_async(
                text=text,
                language=language,
                remove_stop_words=self.remove_stop_words,
                apply_stemming=self.apply_stemming,
                apply_lemmatization=self.apply_lemmatization,
                clean_unicode=self.clean_unicode,
                preserve_names=self.preserve_names,
                enable_advanced_features=self.enable_advanced_features,
            )

            # Update context with normalized text
            context.current_text = result.normalized
            
            # Update language if detected
            if language == "auto" and result.language:
                context.language = result.language
                context.language_confidence = result.confidence

            # Store normalization results
            context.stage_results[ProcessingStage.TEXT_NORMALIZATION] = {
                "original_text": original_text,
                "normalized_text": result.normalized,
                "tokens": result.tokens,
                "language": result.language,
                "confidence": result.confidence,
                "original_length": result.original_length,
                "normalized_length": result.normalized_length,
                "token_count": result.token_count,
                "processing_time": result.processing_time,
                "success": result.success,
                "errors": result.errors or [],
                "preserve_names": self.preserve_names,
                "remove_stop_words": self.remove_stop_words,
                "apply_stemming": self.apply_stemming,
                "apply_lemmatization": self.apply_lemmatization,
                "clean_unicode": self.clean_unicode,
                "enable_advanced_features": self.enable_advanced_features,
                "text_changed": original_text != result.normalized,
            }

            if result.success:
                self.logger.debug(
                    f"Text normalized successfully: {result.original_length} -> {result.normalized_length} chars, {result.token_count} tokens"
                )
            else:
                self.logger.warning(f"Text normalization failed: {result.errors}")

        except Exception as e:
            self.logger.error(f"NormalizationService processing failed: {e}")
            context.stage_results[ProcessingStage.TEXT_NORMALIZATION] = {
                "original_text": original_text,
                "normalized_text": text,
                "success": False,
                "error": str(e),
                "text_changed": False,
            }

        return context

    def get_stage_name(self) -> ProcessingStage:
        """Get stage identifier"""
        return ProcessingStage.TEXT_NORMALIZATION

    def is_enabled(self) -> bool:
        """Check if stage is enabled"""
        return self.enabled and self.normalization_service is not None
