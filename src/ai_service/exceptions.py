"""
Custom exceptions for AI Service
Centralized exception handling with proper error codes and messages
"""

from typing import Optional, Dict, Any


class AIServiceException(Exception):
    """Base exception for AI Service"""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize exception
        
        Args:
            message: Error message
            error_code: Error code for API responses
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}


class ConfigurationError(AIServiceException):
    """Configuration related errors"""
    pass


class ServiceInitializationError(AIServiceException):
    """Service initialization errors"""
    pass


class LanguageDetectionError(AIServiceException):
    """Language detection errors"""
    pass


class NormalizationError(AIServiceException):
    """Text normalization errors"""
    pass


class VariantGenerationError(AIServiceException):
    """Variant generation errors"""
    pass


class EmbeddingError(AIServiceException):
    """Embedding generation errors"""
    pass


class CacheError(AIServiceException):
    """Cache related errors"""
    pass


class ValidationError(AIServiceException):
    """Input validation errors"""
    pass


class ProcessingError(AIServiceException):
    """Text processing errors"""
    pass


class SmartFilterError(AIServiceException):
    """Smart filter errors"""
    pass


class TemplateError(AIServiceException):
    """Template building errors"""
    pass


class PatternError(AIServiceException):
    """Pattern matching errors"""
    pass


class UnicodeError(AIServiceException):
    """Unicode processing errors"""
    pass


class MorphologyError(AIServiceException):
    """Morphological analysis errors"""
    pass


class SignalDetectionError(AIServiceException):
    """Signal detection errors"""
    pass


class APIError(AIServiceException):
    """API related errors"""
    
    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize API error
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Error code for API responses
            details: Additional error details
        """
        super().__init__(message, error_code, details)
        self.status_code = status_code


class AuthenticationError(APIError):
    """Authentication errors"""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, 401, "AUTHENTICATION_ERROR")


class AuthorizationError(APIError):
    """Authorization errors"""
    
    def __init__(self, message: str = "Access denied"):
        super().__init__(message, 403, "AUTHORIZATION_ERROR")


class ValidationAPIError(APIError):
    """Input validation API errors"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, "VALIDATION_ERROR", details)


class RateLimitError(APIError):
    """Rate limiting errors"""
    
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(message, 429, "RATE_LIMIT_ERROR")


class ServiceUnavailableError(APIError):
    """Service unavailable errors"""
    
    def __init__(self, message: str = "Service temporarily unavailable"):
        super().__init__(message, 503, "SERVICE_UNAVAILABLE")


class InternalServerError(APIError):
    """Internal server errors"""
    
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, 500, "INTERNAL_SERVER_ERROR")


def handle_exception(exception: Exception) -> AIServiceException:
    """
    Convert generic exceptions to AIServiceException
    
    Args:
        exception: Original exception
        
    Returns:
        AIServiceException instance
    """
    if isinstance(exception, AIServiceException):
        return exception
    
    # Convert common exceptions
    if isinstance(exception, ValueError):
        return ValidationError(str(exception))
    elif isinstance(exception, KeyError):
        return ConfigurationError(f"Missing configuration: {str(exception)}")
    elif isinstance(exception, FileNotFoundError):
        return ConfigurationError(f"File not found: {str(exception)}")
    elif isinstance(exception, ImportError):
        return ServiceInitializationError(f"Import error: {str(exception)}")
    else:
        return AIServiceException(
            f"Unexpected error: {str(exception)}",
            error_code="UNEXPECTED_ERROR",
            details={"original_type": type(exception).__name__}
        )


def create_error_response(exception: AIServiceException) -> Dict[str, Any]:
    """
    Create standardized error response
    
    Args:
        exception: AIServiceException instance
        
    Returns:
        Dictionary with error response
    """
    response = {
        "error": True,
        "error_code": exception.error_code,
        "message": exception.message,
        "details": exception.details
    }
    
    if isinstance(exception, APIError):
        response["status_code"] = exception.status_code
    
    return response
