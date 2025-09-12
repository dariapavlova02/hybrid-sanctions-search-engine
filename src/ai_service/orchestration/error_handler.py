"""
Advanced error handling system with recovery strategies.
Single Responsibility: Handles errors and implements recovery strategies.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# Import interfaces
try:
    from ..interfaces import ErrorHandlerInterface, ProcessingContext, ProcessingStage
except ImportError:
    # Fallback for when loaded via importlib
    import sys
    from pathlib import Path

    orchestration_path = Path(__file__).parent
    sys.path.insert(0, str(orchestration_path))

    from interfaces import ErrorHandlerInterface, ProcessingContext, ProcessingStage


class ErrorSeverity(str, Enum):
    """Error severity levels"""

    LOW = "low"  # Minor issues, continue processing
    MEDIUM = "medium"  # Significant issues, attempt recovery
    HIGH = "high"  # Critical issues, stop current processing
    CRITICAL = "critical"  # System-level issues, halt entire pipeline


class RecoveryStrategy(str, Enum):
    """Error recovery strategies"""

    CONTINUE = "continue"  # Continue with next stage
    RETRY = "retry"  # Retry current stage
    FALLBACK = "fallback"  # Use fallback processing
    SKIP_STAGE = "skip_stage"  # Skip current stage, continue pipeline
    ABORT = "abort"  # Abort entire processing


@dataclass
class ErrorRule:
    """Rule for handling specific error types"""

    error_types: List[type]
    severity: ErrorSeverity
    strategy: RecoveryStrategy
    max_retries: int = 3
    retry_delay_ms: int = 100
    fallback_handler: Optional[Callable] = None
    continue_on_failure: bool = True


@dataclass
class ErrorStats:
    """Error statistics tracking"""

    total_errors: int = 0
    errors_by_stage: Dict[str, int] = field(default_factory=dict)
    errors_by_type: Dict[str, int] = field(default_factory=dict)
    errors_by_severity: Dict[str, int] = field(default_factory=dict)
    recovery_attempts: Dict[str, int] = field(default_factory=dict)
    successful_recoveries: Dict[str, int] = field(default_factory=dict)

    def record_error(
        self, stage: ProcessingStage, error_type: str, severity: ErrorSeverity
    ):
        """Record an error occurrence"""
        self.total_errors += 1

        stage_name = stage.value
        self.errors_by_stage[stage_name] = self.errors_by_stage.get(stage_name, 0) + 1
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        self.errors_by_severity[severity.value] = (
            self.errors_by_severity.get(severity.value, 0) + 1
        )

    def record_recovery_attempt(self, strategy: RecoveryStrategy):
        """Record a recovery attempt"""
        strategy_name = strategy.value
        self.recovery_attempts[strategy_name] = (
            self.recovery_attempts.get(strategy_name, 0) + 1
        )

    def record_successful_recovery(self, strategy: RecoveryStrategy):
        """Record a successful recovery"""
        strategy_name = strategy.value
        self.successful_recoveries[strategy_name] = (
            self.successful_recoveries.get(strategy_name, 0) + 1
        )


class AdvancedErrorHandler(ErrorHandlerInterface):
    """
    Advanced error handler with configurable recovery strategies.
    Single Responsibility: Handles errors and implements recovery.
    Open/Closed: New error rules can be added without modification.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.logger = logging.getLogger(f"{__name__}.AdvancedErrorHandler")
        self.stats = ErrorStats()

        # Initialize error rules
        self.error_rules: Dict[type, ErrorRule] = {}
        self._setup_default_error_rules()

        # Load custom rules from config
        if "custom_error_rules" in self.config:
            self._load_custom_error_rules(self.config["custom_error_rules"])

    def _setup_default_error_rules(self):
        """Setup default error handling rules"""
        try:
            from ...exceptions import (
                AIServiceException,
                LanguageDetectionError,
                NormalizationError,
                ValidationError,
            )
            
            # Define ProcessingError locally
            class ProcessingError(AIServiceException):
                pass
                
            class VariantGenerationError(AIServiceException):
                pass
                
            class EmbeddingError(AIServiceException):
                pass
        except ImportError:
            # Define all exceptions locally for testing
            class AIServiceException(Exception):
                pass
                
            class ProcessingError(AIServiceException):
                pass
                
            class ValidationError(AIServiceException):
                pass

            class LanguageDetectionError(AIServiceException):
                pass

            class NormalizationError(AIServiceException):
                pass

            class VariantGenerationError(AIServiceException):
                pass

            class EmbeddingError(AIServiceException):
                pass

        # Validation errors - usually critical, don't continue
        self.error_rules[ValidationError] = ErrorRule(
            error_types=[ValidationError],
            severity=ErrorSeverity.HIGH,
            strategy=RecoveryStrategy.ABORT,
            continue_on_failure=False,
        )

        # Language detection errors - use fallback
        self.error_rules[LanguageDetectionError] = ErrorRule(
            error_types=[LanguageDetectionError],
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.FALLBACK,
            continue_on_failure=True,
            fallback_handler=self._language_detection_fallback,
        )

        # Text normalization errors - retry with fallback
        self.error_rules[NormalizationError] = ErrorRule(
            error_types=[NormalizationError],
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.RETRY,
            max_retries=2,
            continue_on_failure=True,
        )

        # Variant generation errors - skip stage, continue
        self.error_rules[VariantGenerationError] = ErrorRule(
            error_types=[VariantGenerationError],
            severity=ErrorSeverity.LOW,
            strategy=RecoveryStrategy.SKIP_STAGE,
            continue_on_failure=True,
        )

        # Embedding errors - skip stage, continue
        self.error_rules[EmbeddingError] = ErrorRule(
            error_types=[EmbeddingError],
            severity=ErrorSeverity.LOW,
            strategy=RecoveryStrategy.SKIP_STAGE,
            continue_on_failure=True,
        )

        # Generic processing errors - retry once
        self.error_rules[ProcessingError] = ErrorRule(
            error_types=[ProcessingError],
            severity=ErrorSeverity.MEDIUM,
            strategy=RecoveryStrategy.RETRY,
            max_retries=1,
            continue_on_failure=True,
        )

        # System errors - abort
        self.error_rules[Exception] = ErrorRule(
            error_types=[Exception],  # Catch-all
            severity=ErrorSeverity.CRITICAL,
            strategy=RecoveryStrategy.ABORT,
            continue_on_failure=False,
        )

    def _load_custom_error_rules(self, custom_rules: List[Dict[str, Any]]):
        """Load custom error rules from configuration"""
        for rule_config in custom_rules:
            try:
                # This would parse custom rule configuration
                # Simplified for this example
                pass
            except Exception as e:
                self.logger.warning(f"Failed to load custom error rule: {e}")

    async def handle_stage_error(
        self, stage: ProcessingStage, error: Exception, context: ProcessingContext
    ) -> ProcessingContext:
        """Handle error in processing stage with recovery strategies"""
        error_type = type(error)
        error_name = error_type.__name__

        # Find applicable error rule
        rule = self._find_error_rule(error_type)

        # Record error statistics
        self.stats.record_error(stage, error_name, rule.severity)

        self.logger.error(
            f"Stage {stage.value} error: {error_name} - {str(error)}\n"
            f"Severity: {rule.severity.value}, Strategy: {rule.strategy.value}"
        )

        # Execute recovery strategy
        recovered_context = await self._execute_recovery_strategy(
            stage, error, context, rule
        )

        return recovered_context

    def _find_error_rule(self, error_type: type) -> ErrorRule:
        """Find the most specific error rule for the given error type"""
        # Try exact match first
        if error_type in self.error_rules:
            return self.error_rules[error_type]

        # Try parent classes
        for registered_type, rule in self.error_rules.items():
            if issubclass(error_type, registered_type):
                return rule

        # Fallback to generic Exception rule
        return self.error_rules[Exception]

    async def _execute_recovery_strategy(
        self,
        stage: ProcessingStage,
        error: Exception,
        context: ProcessingContext,
        rule: ErrorRule,
    ) -> ProcessingContext:
        """Execute the recovery strategy defined in the rule"""
        self.stats.record_recovery_attempt(rule.strategy)

        try:
            if rule.strategy == RecoveryStrategy.CONTINUE:
                # Just continue with current context
                return context

            elif rule.strategy == RecoveryStrategy.RETRY:
                # Retry logic would be handled at pipeline level
                # For now, just mark that retry was attempted
                context.metadata[f"{stage.value}_retry_attempted"] = True
                return context

            elif rule.strategy == RecoveryStrategy.FALLBACK:
                # Use fallback handler if available
                if rule.fallback_handler:
                    context = await rule.fallback_handler(stage, error, context)
                    self.stats.record_successful_recovery(rule.strategy)
                return context

            elif rule.strategy == RecoveryStrategy.SKIP_STAGE:
                # Mark stage as skipped
                context.stage_results[stage] = {
                    "skipped": True,
                    "reason": f"Error: {str(error)}",
                    "error_type": type(error).__name__,
                }
                self.stats.record_successful_recovery(rule.strategy)
                return context

            elif rule.strategy == RecoveryStrategy.ABORT:
                # Re-raise error to abort processing
                raise error

            else:
                self.logger.warning(f"Unknown recovery strategy: {rule.strategy}")
                return context

        except Exception as recovery_error:
            self.logger.error(f"Recovery strategy failed: {recovery_error}")
            # If recovery fails, just continue with original context
            return context

    def should_continue_on_error(
        self, stage: ProcessingStage, error: Exception
    ) -> bool:
        """Determine if processing should continue after error"""
        error_type = type(error)
        rule = self._find_error_rule(error_type)
        return rule.continue_on_failure

    def get_error_stats(self) -> Dict[str, Any]:
        """Get comprehensive error statistics"""
        return {
            "total_errors": self.stats.total_errors,
            "errors_by_stage": dict(self.stats.errors_by_stage),
            "errors_by_type": dict(self.stats.errors_by_type),
            "errors_by_severity": dict(self.stats.errors_by_severity),
            "recovery_attempts": dict(self.stats.recovery_attempts),
            "successful_recoveries": dict(self.stats.successful_recoveries),
            "recovery_success_rate": self._calculate_recovery_success_rate(),
        }

    def _calculate_recovery_success_rate(self) -> Dict[str, float]:
        """Calculate success rate for each recovery strategy"""
        success_rates = {}

        for strategy, attempts in self.stats.recovery_attempts.items():
            if attempts > 0:
                successes = self.stats.successful_recoveries.get(strategy, 0)
                success_rates[strategy] = (successes / attempts) * 100
            else:
                success_rates[strategy] = 0.0

        return success_rates

    # Fallback handlers
    async def _language_detection_fallback(
        self, stage: ProcessingStage, error: Exception, context: ProcessingContext
    ) -> ProcessingContext:
        """Fallback handler for language detection errors"""
        # Simple heuristic-based language detection
        text = context.current_text
        cyrillic_ratio = (
            sum(1 for c in text if "\u0400" <= c <= "\u04ff") / len(text) if text else 0
        )

        if cyrillic_ratio > 0.3:
            context.language = "ru"  # Default to Russian for Cyrillic
        else:
            context.language = "en"  # Default to English

        context.language_confidence = 0.5  # Low confidence for fallback

        context.stage_results[ProcessingStage.LANGUAGE_DETECTION] = {
            "fallback_used": True,
            "detected_language": context.language,
            "confidence": context.language_confidence,
            "original_error": str(error),
        }

        return context

    def reset_stats(self):
        """Reset error statistics"""
        self.stats = ErrorStats()
        self.logger.info("Error statistics reset")

    def add_error_rule(self, error_type: type, rule: ErrorRule):
        """Add custom error rule (Open/Closed Principle)"""
        self.error_rules[error_type] = rule
        self.logger.info(f"Added custom error rule for {error_type.__name__}")

    def get_error_rules_info(self) -> Dict[str, Any]:
        """Get information about configured error rules"""
        rules_info = {}

        for error_type, rule in self.error_rules.items():
            rules_info[error_type.__name__] = {
                "severity": rule.severity.value,
                "strategy": rule.strategy.value,
                "max_retries": rule.max_retries,
                "continue_on_failure": rule.continue_on_failure,
            }

        return rules_info
