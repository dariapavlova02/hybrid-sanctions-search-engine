"""
Input validation stage implementing Single Responsibility Principle.
Only responsible for validating input data.
"""

import logging
from typing import Any, Dict

# Import interfaces
try:
    from ...exceptions import ValidationError
    from ..interfaces import (
        ProcessingContext,
        ProcessingStage,
        ProcessingStageInterface,
    )
except ImportError:
    # Fallback for when loaded via importlib
    import sys
    from pathlib import Path

    orchestration_path = Path(__file__).parent.parent
    sys.path.insert(0, str(orchestration_path))

    from interfaces import ProcessingContext, ProcessingStage, ProcessingStageInterface
    from shared.types.service_types import ValidationError


class ValidationStage(ProcessingStageInterface):
    """
    Input validation stage.
    Single Responsibility: Only validates input data.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.min_length = self.config.get("min_length", 1)
        self.max_length = self.config.get("max_length", 10000)
        self.allowed_chars = self.config.get("allowed_chars", None)
        self.logger = logging.getLogger(f"{__name__}.ValidationStage")

    async def process(self, context: ProcessingContext) -> ProcessingContext:
        """Validate input text"""
        text = context.current_text

        # Length validation
        if len(text) < self.min_length:
            raise ValidationError(f"Text too short: {len(text)} < {self.min_length}")

        if len(text) > self.max_length:
            raise ValidationError(f"Text too long: {len(text)} > {self.max_length}")

        # Character validation
        if self.allowed_chars:
            invalid_chars = set(text) - set(self.allowed_chars)
            if invalid_chars:
                raise ValidationError(f"Invalid characters found: {invalid_chars}")

        # Check for null bytes and other problematic characters
        if "\x00" in text:
            raise ValidationError("Null bytes not allowed in text")

        # Basic encoding check
        try:
            text.encode("utf-8")
        except UnicodeEncodeError as e:
            raise ValidationError(f"Text encoding error: {e}")

        # Store validation results
        context.stage_results[ProcessingStage.VALIDATION] = {
            "text_length": len(text),
            "validation_passed": True,
            "checks_performed": ["length", "encoding", "null_bytes"],
        }

        self.logger.debug(f"Validation passed for text of length {len(text)}")
        return context

    def get_stage_name(self) -> ProcessingStage:
        """Get stage identifier"""
        return ProcessingStage.VALIDATION

    def is_enabled(self) -> bool:
        """Check if stage is enabled"""
        return self.enabled

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update stage configuration"""
        self.config.update(config)
        self.enabled = self.config.get("enabled", True)
        self.min_length = self.config.get("min_length", 1)
        self.max_length = self.config.get("max_length", 10000)
        self.allowed_chars = self.config.get("allowed_chars", None)

        self.logger.info(f"Updated validation config: {self.config}")
