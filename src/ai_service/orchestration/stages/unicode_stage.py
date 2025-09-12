"""
Unicode normalization stage implementing Single Responsibility Principle.
Only responsible for Unicode text normalization.
"""

import logging
import unicodedata
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


class UnicodeNormalizationStage(ProcessingStageInterface):
    """
    Unicode normalization stage.
    Single Responsibility: Only normalizes Unicode characters.
    """

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.enabled = self.config.get("enabled", True)
        self.normalization_form = self.config.get("normalization_form", "NFC")
        self.remove_control_chars = self.config.get("remove_control_chars", True)
        self.remove_zero_width = self.config.get("remove_zero_width", True)
        self.logger = logging.getLogger(f"{__name__}.UnicodeNormalizationStage")

    async def process(self, context: ProcessingContext) -> ProcessingContext:
        """Normalize Unicode text"""
        text = context.current_text
        original_length = len(text)

        # Unicode normalization
        try:
            normalized_text = unicodedata.normalize(self.normalization_form, text)
        except ValueError as e:
            self.logger.warning(f"Unicode normalization failed: {e}")
            normalized_text = text

        # Remove control characters
        if self.remove_control_chars:
            normalized_text = "".join(
                char
                for char in normalized_text
                if not unicodedata.category(char).startswith("C")
                or char in ["\n", "\r", "\t"]  # Keep common whitespace
            )

        # Remove zero-width characters
        if self.remove_zero_width:
            zero_width_chars = [
                "\u200b",  # Zero width space
                "\u200c",  # Zero width non-joiner
                "\u200d",  # Zero width joiner
                "\ufeff",  # Byte order mark
            ]
            for char in zero_width_chars:
                normalized_text = normalized_text.replace(char, "")

        # Update context
        context.current_text = normalized_text

        # Store normalization results
        context.stage_results[ProcessingStage.UNICODE_NORMALIZATION] = {
            "normalization_form": self.normalization_form,
            "original_length": original_length,
            "normalized_length": len(normalized_text),
            "length_changed": original_length != len(normalized_text),
            "control_chars_removed": self.remove_control_chars,
            "zero_width_removed": self.remove_zero_width,
        }

        self.logger.debug(
            f"Unicode normalization completed: {original_length} -> {len(normalized_text)} chars"
        )

        return context

    def get_stage_name(self) -> ProcessingStage:
        """Get stage identifier"""
        return ProcessingStage.UNICODE_NORMALIZATION

    def is_enabled(self) -> bool:
        """Check if stage is enabled"""
        return self.enabled

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update stage configuration"""
        self.config.update(config)
        self.enabled = self.config.get("enabled", True)
        self.normalization_form = self.config.get("normalization_form", "NFC")
        self.remove_control_chars = self.config.get("remove_control_chars", True)
        self.remove_zero_width = self.config.get("remove_zero_width", True)

        self.logger.info(f"Updated Unicode normalization config: {self.config}")
