"""
Language detection stage implementing Single Responsibility Principle.
Only responsible for detecting text language.
"""

import logging
from typing import Any, Dict, Optional

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


class LanguageDetectionStage(ProcessingStageInterface):
    """
    Language detection stage.
    Single Responsibility: Only detects language of text.
    Dependency Inversion: Depends on language service interface.
    """

    def __init__(self, language_service=None, config: Dict[str, Any] = None):
        self.language_service = language_service
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.8)
        self.default_language = self.config.get("default_language", "en")
        self.logger = logging.getLogger(f"{__name__}.LanguageDetectionStage")

        # Initialize language service if not provided
        if not self.language_service and self.enabled:
            try:
                from ...services.language_detection_service import (
                    LanguageDetectionService,
                )

                self.language_service = LanguageDetectionService()
                self.logger.info("Initialized language detection service")
            except Exception as e:
                self.logger.warning(f"Failed to initialize language service: {e}")
                self.enabled = False

    async def process(self, context: ProcessingContext) -> ProcessingContext:
        """Detect language of text"""
        if not self.language_service:
            self.logger.warning("Language service not available, using default")
            context.language = self.default_language
            context.language_confidence = 0.0
            return context

        try:
            # Use enhanced language detection if available
            if hasattr(self.language_service, "detect_language"):
                detection_result = self.language_service.detect_language(
                    context.current_text
                )
                language = detection_result.get("language", self.default_language)
                confidence = detection_result.get("confidence", 0.0)
                detailed_scores = detection_result.get("detailed_scores", {})
            else:
                # Fallback to basic detection
                language = self._basic_language_detection(context.current_text)
                confidence = 0.5  # Default confidence for basic detection
                detailed_scores = {}

            # Apply confidence threshold
            if confidence < self.confidence_threshold:
                self.logger.debug(
                    f"Low confidence ({confidence:.2f}), using default language"
                )
                language = self.default_language
                confidence = 0.0

            # Update context
            context.language = language
            context.language_confidence = confidence

            # Store detailed results
            context.stage_results[ProcessingStage.LANGUAGE_DETECTION] = {
                "detected_language": language,
                "confidence": confidence,
                "detailed_scores": detailed_scores,
                "threshold_applied": confidence < self.confidence_threshold,
                "default_used": confidence < self.confidence_threshold,
            }

            self.logger.debug(
                f"Detected language: {language} (confidence: {confidence:.2f})"
            )

        except Exception as e:
            self.logger.error(f"Language detection failed: {e}")
            # Fallback to default
            context.language = self.default_language
            context.language_confidence = 0.0

            context.stage_results[ProcessingStage.LANGUAGE_DETECTION] = {
                "detected_language": self.default_language,
                "confidence": 0.0,
                "error": str(e),
                "fallback_used": True,
            }

        return context

    def get_stage_name(self) -> ProcessingStage:
        """Get stage identifier"""
        return ProcessingStage.LANGUAGE_DETECTION

    def is_enabled(self) -> bool:
        """Check if stage is enabled"""
        return self.enabled

    def _basic_language_detection(self, text: str) -> str:
        """Basic language detection fallback"""
        # Simple heuristic based on character sets
        cyrillic_chars = sum(1 for char in text if "\u0400" <= char <= "\u04ff")
        latin_chars = sum(1 for char in text if char.isalpha() and char.isascii())

        total_alpha = cyrillic_chars + latin_chars
        if total_alpha == 0:
            return self.default_language

        cyrillic_ratio = cyrillic_chars / total_alpha

        if cyrillic_ratio > 0.3:
            # Check for Ukrainian-specific characters
            ukrainian_chars = sum(1 for char in text if char in "іїєґІЇЄҐ")
            if ukrainian_chars > 0:
                return "uk"
            else:
                return "ru"
        else:
            return "en"

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update stage configuration"""
        self.config.update(config)
        self.enabled = self.config.get("enabled", True)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.8)
        self.default_language = self.config.get("default_language", "en")

        self.logger.info(f"Updated language detection config: {self.config}")

    def get_supported_languages(self) -> list:
        """Get list of supported languages"""
        if self.language_service and hasattr(
            self.language_service, "get_supported_languages"
        ):
            return self.language_service.get_supported_languages()
        else:
            return ["en", "ru", "uk"]  # Default supported languages
