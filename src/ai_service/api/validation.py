"""
Request validation and sanitization.
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field, validator
from .models import ProcessRequest, ProcessingOptions, FlagOverrides


class ValidationError(Exception):
    """Custom validation error."""
    def __init__(self, message: str, field: str = None, code: str = None):
        self.message = message
        self.field = field
        self.code = code
        super().__init__(message)


class RequestValidator:
    """Validates and sanitizes incoming requests."""

    # Security patterns
    SUSPICIOUS_PATTERNS = [
        r'<script[^>]*>.*?</script>',  # XSS
        r'javascript:',                # JavaScript URLs
        r'on\w+\s*=',                 # Event handlers
        r'data:text/html',            # Data URLs
        r'eval\s*\(',                 # eval() calls
        r'expression\s*\(',           # CSS expressions
    ]

    # Content length limits
    MAX_TEXT_LENGTH = 10000
    MAX_FLAGS_COUNT = 50
    MIN_TEXT_LENGTH = 1

    # Rate limiting patterns
    SPAM_PATTERNS = [
        r'(.)\1{20,}',                # Repeated characters
        r'(\w+\s+)\1{10,}',          # Repeated words
        r'[A-Z]{50,}',               # All caps spam
    ]

    def __init__(self):
        self.compiled_suspicious = [re.compile(pattern, re.IGNORECASE) for pattern in self.SUSPICIOUS_PATTERNS]
        self.compiled_spam = [re.compile(pattern, re.IGNORECASE) for pattern in self.SPAM_PATTERNS]

    def validate_request(self, request: ProcessRequest) -> Tuple[ProcessRequest, List[str]]:
        """
        Validate and sanitize request.

        Returns:
            Tuple of (sanitized_request, warnings)
        """
        warnings = []

        # Basic text validation
        sanitized_text, text_warnings = self._validate_text(request.text)
        warnings.extend(text_warnings)

        # Options validation
        if request.options:
            sanitized_options, options_warnings = self._validate_options(request.options)
            warnings.extend(options_warnings)
        else:
            sanitized_options = ProcessingOptions()

        # Create sanitized request
        sanitized_request = ProcessRequest(
            text=sanitized_text,
            options=sanitized_options
        )

        return sanitized_request, warnings

    def _validate_text(self, text: str) -> Tuple[str, List[str]]:
        """Validate and sanitize input text."""
        warnings = []

        # Length check
        if len(text) < self.MIN_TEXT_LENGTH:
            raise ValidationError(f"Text too short (minimum {self.MIN_TEXT_LENGTH} characters)", "text", "TEXT_TOO_SHORT")

        if len(text) > self.MAX_TEXT_LENGTH:
            text = text[:self.MAX_TEXT_LENGTH]
            warnings.append(f"Text truncated to {self.MAX_TEXT_LENGTH} characters")

        # Security check
        for pattern in self.compiled_suspicious:
            if pattern.search(text):
                raise ValidationError("Suspicious content detected", "text", "SECURITY_VIOLATION")

        # Spam check
        for pattern in self.compiled_spam:
            if pattern.search(text):
                warnings.append("Potential spam content detected")

        # Basic sanitization
        sanitized = self._sanitize_text(text)
        if sanitized != text:
            warnings.append("Text was sanitized for safety")

        return sanitized, warnings

    def _sanitize_text(self, text: str) -> str:
        """Sanitize text content."""
        # Remove null bytes
        text = text.replace('\x00', '')

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)

        # Remove control characters (except newlines, tabs, carriage returns)
        text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)

        # Trim whitespace
        text = text.strip()

        return text

    def _validate_options(self, options: ProcessingOptions) -> Tuple[ProcessingOptions, List[str]]:
        """Validate processing options."""
        warnings = []

        # Validate thresholds
        if options.search_threshold < 0.0 or options.search_threshold > 1.0:
            options.search_threshold = max(0.0, min(1.0, options.search_threshold))
            warnings.append("search_threshold clamped to [0.0, 1.0]")

        if options.search_escalation_threshold < 0.0 or options.search_escalation_threshold > 1.0:
            options.search_escalation_threshold = max(0.0, min(1.0, options.search_escalation_threshold))
            warnings.append("search_escalation_threshold clamped to [0.0, 1.0]")

        # Validate cache TTL
        if options.cache_ttl_seconds and (options.cache_ttl_seconds < 60 or options.cache_ttl_seconds > 86400):
            options.cache_ttl_seconds = max(60, min(86400, options.cache_ttl_seconds))
            warnings.append("cache_ttl_seconds clamped to [60, 86400]")

        # Validate flags
        if options.flags:
            sanitized_flags, flag_warnings = self._validate_flags(options.flags)
            options.flags = sanitized_flags
            warnings.extend(flag_warnings)

        return options, warnings

    def _validate_flags(self, flags: FlagOverrides) -> Tuple[FlagOverrides, List[str]]:
        """Validate feature flags."""
        warnings = []

        # Count non-None flags
        active_flags = sum(1 for value in flags.__dict__.values() if value is not None)
        if active_flags > self.MAX_FLAGS_COUNT:
            warnings.append(f"Too many flags specified ({active_flags}), some may be ignored")

        # Validate percentage
        if flags.factory_rollout_percentage is not None:
            if flags.factory_rollout_percentage < 0 or flags.factory_rollout_percentage > 100:
                flags.factory_rollout_percentage = max(0, min(100, flags.factory_rollout_percentage))
                warnings.append("factory_rollout_percentage clamped to [0, 100]")

        # Validate latency threshold
        if flags.max_latency_threshold_ms is not None:
            if flags.max_latency_threshold_ms <= 0 or flags.max_latency_threshold_ms > 10000:
                flags.max_latency_threshold_ms = max(1.0, min(10000.0, flags.max_latency_threshold_ms))
                warnings.append("max_latency_threshold_ms clamped to [1, 10000]")

        # Validate confidence threshold
        if flags.min_confidence_threshold is not None:
            if flags.min_confidence_threshold < 0.0 or flags.min_confidence_threshold > 1.0:
                flags.min_confidence_threshold = max(0.0, min(1.0, flags.min_confidence_threshold))
                warnings.append("min_confidence_threshold clamped to [0.0, 1.0]")

        # Validate language overrides
        if flags.language_overrides:
            valid_overrides = {}
            for lang, impl in flags.language_overrides.items():
                if len(lang) <= 5 and impl in ['legacy', 'factory', 'auto']:  # Basic validation
                    valid_overrides[lang] = impl
                else:
                    warnings.append(f"Invalid language override: {lang}={impl}")
            flags.language_overrides = valid_overrides

        return flags, warnings

    def validate_production_config(self, flags: Dict[str, Any]) -> List[str]:
        """Validate production configuration and provide recommendations."""
        issues = []

        # Critical flags that should be enabled in production
        critical_flags = {
            'enable_search': True,
            'enable_vector_fallback': True,
            'enable_ac_tier0': True,
            'preserve_feminine_suffix_uk': True,
            'enable_enhanced_diminutives': True,
            'enable_spacy_uk_ner': True,
        }

        for flag, expected_value in critical_flags.items():
            if flags.get(flag) != expected_value:
                issues.append(f"Production warning: {flag} should be {expected_value}")

        # Performance flags that should be optimized
        performance_flags = {
            'enable_ascii_fastpath': True,
            'morphology_custom_rules_first': True,
            'debug_tracing': False,
        }

        for flag, expected_value in performance_flags.items():
            if flags.get(flag) != expected_value:
                issues.append(f"Performance warning: {flag} should be {expected_value} for optimal performance")

        # Check for conflicting flags
        if flags.get('enable_spacy_en_ner') and flags.get('enable_ascii_fastpath'):
            issues.append("Conflict warning: enable_spacy_en_ner=True may slow down ASCII fastpath")

        if flags.get('debug_tracing') and not flags.get('enable_performance_fallback'):
            issues.append("Performance warning: debug_tracing=True without performance fallback may cause slowdowns")

        return issues


class SchemaValidator:
    """JSON Schema validation utilities."""

    @staticmethod
    def get_openapi_schema() -> Dict[str, Any]:
        """Get OpenAPI schema for API documentation."""
        return {
            "openapi": "3.0.3",
            "info": {
                "title": "AI Service API",
                "version": "1.0.0",
                "description": "Name normalization and sanctions screening API with advanced feature flags"
            },
            "paths": {
                "/api/v1/process": {
                    "post": {
                        "summary": "Process text with normalization and search",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/ProcessRequest"}
                                }
                            }
                        },
                        "responses": {
                            "200": {
                                "description": "Successful processing",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ProcessResponse"}
                                    }
                                }
                            },
                            "400": {
                                "description": "Validation error",
                                "content": {
                                    "application/json": {
                                        "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "components": {
                "schemas": {
                    "ProcessRequest": ProcessRequest.model_json_schema(),
                    "ProcessResponse": {"type": "object"},  # Would be full response schema
                    "ErrorResponse": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string"},
                            "field": {"type": "string"},
                            "code": {"type": "string"}
                        }
                    }
                }
            }
        }


# Global validator instance
validator = RequestValidator()


def validate_request(request: ProcessRequest) -> Tuple[ProcessRequest, List[str]]:
    """Global request validation function."""
    return validator.validate_request(request)