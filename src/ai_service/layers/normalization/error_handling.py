"""
Enhanced error handling for normalization service.
Provides structured error recovery and comprehensive logging.
"""

import logging
import traceback
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum

from ...utils.logging_config import get_logger


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class NormalizationError:
    """Structured error information."""
    stage: str
    message: str
    severity: ErrorSeverity
    token: Optional[str] = None
    original_exception: Optional[Exception] = None
    recovery_action: Optional[str] = None
    context: Dict[str, Any] = None

    def __post_init__(self):
        if self.context is None:
            self.context = {}


class ErrorHandler:
    """Centralized error handling for normalization processes."""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.errors: List[NormalizationError] = []
        self.recovery_strategies: Dict[str, Callable] = {}
        self._register_recovery_strategies()

    def _register_recovery_strategies(self):
        """Register error recovery strategies."""
        self.recovery_strategies = {
            'tokenization_failed': self._recover_tokenization,
            'role_classification_failed': self._recover_role_classification,
            'morphology_failed': self._recover_morphology,
            'gender_processing_failed': self._recover_gender_processing,
            'text_reconstruction_failed': self._recover_text_reconstruction,
        }

    def handle_error(
        self,
        stage: str,
        exception: Exception,
        context: Dict[str, Any] = None,
        token: str = None
    ) -> Dict[str, Any]:
        """
        Handle an error with structured recovery.

        Args:
            stage: Processing stage where error occurred
            exception: The exception that occurred
            context: Additional context information
            token: Specific token that caused the error

        Returns:
            Recovery result with fallback values
        """
        context = context or {}

        # Determine error severity
        severity = self._determine_severity(exception, stage)

        # Create error record
        error = NormalizationError(
            stage=stage,
            message=str(exception),
            severity=severity,
            token=token,
            original_exception=exception,
            context=context
        )

        # Log the error
        self._log_error(error)

        # Store for later analysis
        self.errors.append(error)

        # Attempt recovery
        recovery_result = self._attempt_recovery(error)

        return recovery_result

    def _determine_severity(self, exception: Exception, stage: str) -> ErrorSeverity:
        """Determine error severity based on exception type and stage."""
        critical_stages = {'text_reconstruction', 'core_normalization'}
        critical_exceptions = {ImportError, MemoryError, SystemError}

        if type(exception) in critical_exceptions:
            return ErrorSeverity.CRITICAL

        if stage in critical_stages:
            return ErrorSeverity.HIGH

        if isinstance(exception, (ValueError, KeyError)):
            return ErrorSeverity.MEDIUM

        return ErrorSeverity.LOW

    def _log_error(self, error: NormalizationError):
        """Log error with appropriate level."""
        log_message = f"{error.stage}: {error.message}"
        if error.token:
            log_message += f" (token: '{error.token}')"

        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message, exc_info=error.original_exception)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message, exc_info=error.original_exception)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:
            self.logger.debug(log_message)

    def _attempt_recovery(self, error: NormalizationError) -> Dict[str, Any]:
        """Attempt to recover from error using registered strategies."""
        recovery_key = f"{error.stage}_failed"

        if recovery_key in self.recovery_strategies:
            try:
                result = self.recovery_strategies[recovery_key](error)
                error.recovery_action = f"Applied {recovery_key} strategy"
                self.logger.info(f"Recovery successful for {error.stage}")
                return result
            except Exception as recovery_exception:
                self.logger.error(f"Recovery failed for {error.stage}: {recovery_exception}")

        # Default recovery - return safe fallback values
        return self._default_recovery(error)

    def _recover_tokenization(self, error: NormalizationError) -> Dict[str, Any]:
        """Recover from tokenization failures."""
        text = error.context.get('text', '')

        # Simple fallback: split by whitespace
        tokens = text.split() if text else []

        return {
            'tokens': tokens,
            'traces': [f"Tokenization fallback applied due to: {error.message}"],
            'success': len(tokens) > 0
        }

    def _recover_role_classification(self, error: NormalizationError) -> Dict[str, Any]:
        """Recover from role classification failures."""
        tokens = error.context.get('tokens', [])

        # Simple heuristic: first token is given, last is surname
        roles = []
        for i, token in enumerate(tokens):
            if i == 0:
                roles.append('given')
            elif i == len(tokens) - 1 and len(tokens) > 1:
                roles.append('surname')
            else:
                roles.append('unknown')

        return {
            'roles': roles,
            'traces': [f"Role classification fallback applied due to: {error.message}"],
            'success': True
        }

    def _recover_morphology(self, error: NormalizationError) -> Dict[str, Any]:
        """Recover from morphological analysis failures."""
        token = error.token or error.context.get('token', '')
        role = error.context.get('role', 'unknown')

        # Simple case normalization
        if role in {'given', 'surname', 'patronymic'}:
            normalized = token.capitalize() if token else ''
        else:
            normalized = token

        return {
            'normalized_token': normalized,
            'traces': [f"Morphology fallback applied due to: {error.message}"],
            'success': True
        }

    def _recover_gender_processing(self, error: NormalizationError) -> Dict[str, Any]:
        """Recover from gender processing failures."""
        return {
            'gender': None,
            'confidence': 0.0,
            'adjusted_tokens': error.context.get('tokens', []),
            'traces': [f"Gender processing fallback applied due to: {error.message}"],
            'success': True
        }

    def _recover_text_reconstruction(self, error: NormalizationError) -> Dict[str, Any]:
        """Recover from text reconstruction failures."""
        tokens = error.context.get('tokens', [])

        # Simple joining
        reconstructed = ' '.join(tokens) if tokens else ''

        return {
            'reconstructed_text': reconstructed,
            'traces': [f"Text reconstruction fallback applied due to: {error.message}"],
            'success': len(reconstructed) > 0
        }

    def _default_recovery(self, error: NormalizationError) -> Dict[str, Any]:
        """Default recovery strategy for unhandled errors."""
        return {
            'fallback_applied': True,
            'error_stage': error.stage,
            'error_message': error.message,
            'success': False
        }

    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of all errors encountered."""
        if not self.errors:
            return {'total_errors': 0, 'severity_distribution': {}}

        severity_counts = {}
        for error in self.errors:
            severity = error.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1

        stage_counts = {}
        for error in self.errors:
            stage = error.stage
            stage_counts[stage] = stage_counts.get(stage, 0) + 1

        return {
            'total_errors': len(self.errors),
            'severity_distribution': severity_counts,
            'stage_distribution': stage_counts,
            'recent_errors': [
                {
                    'stage': e.stage,
                    'message': e.message,
                    'severity': e.severity.value,
                    'token': e.token
                }
                for e in self.errors[-5:]  # Last 5 errors
            ]
        }

    def clear_errors(self):
        """Clear error history."""
        self.errors.clear()
        self.logger.info("Error history cleared")

    def has_critical_errors(self) -> bool:
        """Check if any critical errors occurred."""
        return any(error.severity == ErrorSeverity.CRITICAL for error in self.errors)

    def get_errors_by_severity(self, severity: ErrorSeverity) -> List[NormalizationError]:
        """Get errors by severity level."""
        return [error for error in self.errors if error.severity == severity]

    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """Register a custom recovery strategy."""
        self.recovery_strategies[error_type] = strategy
        self.logger.info(f"Registered recovery strategy for {error_type}")


class ErrorReportingMixin:
    """Mixin to add error reporting capabilities to classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.error_handler = ErrorHandler()

    def safe_execute(
        self,
        operation: Callable,
        stage: str,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> Any:
        """
        Safely execute an operation with error handling.

        Args:
            operation: Function to execute
            stage: Processing stage name
            context: Additional context for error recovery
            **kwargs: Arguments to pass to operation

        Returns:
            Operation result or recovery result
        """
        try:
            return operation(**kwargs)
        except Exception as e:
            return self.error_handler.handle_error(stage, e, context)

    async def safe_execute_async(
        self,
        operation: Callable,
        stage: str,
        context: Dict[str, Any] = None,
        **kwargs
    ) -> Any:
        """Async version of safe_execute."""
        try:
            return await operation(**kwargs)
        except Exception as e:
            return self.error_handler.handle_error(stage, e, context)

    def get_error_report(self) -> Dict[str, Any]:
        """Get comprehensive error report."""
        return self.error_handler.get_error_summary()