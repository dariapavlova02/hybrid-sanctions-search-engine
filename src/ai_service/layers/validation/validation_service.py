"""
Validation Service - Layer 1 of the unified architecture.

Provides basic input validation and sanitization.
Wraps existing validation utilities with the new interface.
"""

from typing import Any, Dict

from ...contracts.base_contracts import ValidationServiceInterface
from ...utils.input_validation import InputValidator
from ...utils.logging_config import get_logger

logger = get_logger(__name__)


class ValidationService(ValidationServiceInterface):
    """
    Layer 1: Input validation and sanitization.

    Responsibilities:
    - Basic input validation and length checks
    - Safe text cleanup (trim, collapse spaces)
    - Early blocking of obviously invalid inputs
    - NOT responsible for: language detection, normalization, or business logic
    """

    def __init__(self):
        self._validator = None

    async def initialize(self):
        """Initialize the validation service"""
        try:
            self._validator = InputValidator()
            logger.info("ValidationService initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize ValidationService: {e}")
            raise

    async def validate_and_sanitize(self, text: str) -> Dict[str, Any]:
        """
        Basic validation and safe cleanup.

        Args:
            text: Input text to validate

        Returns:
            Dict with validation results:
            - sanitized_text: Cleaned text
            - should_process: Whether to continue processing
            - warnings: List of validation warnings
            - risk_level: Basic risk assessment
        """
        if self._validator is None:
            raise RuntimeError("ValidationService not initialized")

        try:
            # Use existing validation logic
            result = self._validator.validate_and_sanitize(text)

            return {
                "sanitized_text": result.sanitized_text,
                "should_process": result.is_valid,
                "warnings": result.warnings,
                "blocked_patterns": result.blocked_patterns,
                "risk_level": result.risk_level,
                "is_valid": result.is_valid,
            }

        except Exception as e:
            logger.error(f"Validation failed for text: {text[:50]}... Error: {e}")
            # Safe fallback: basic sanitization
            sanitized = text.strip()[:1000] if text else ""

            return {
                "sanitized_text": sanitized,
                "should_process": len(sanitized) > 0,
                "warnings": [f"Validation error: {str(e)}"],
                "blocked_patterns": [],
                "risk_level": "unknown",
                "is_valid": len(sanitized) > 0,
            }
