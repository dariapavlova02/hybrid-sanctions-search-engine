#!/usr/bin/env python3
"""
AI Service for normalization and variant generation
for sanctions data verification
"""

import os
import sys
import secrets
from pathlib import Path
from typing import Any, Dict, List, Optional
import time
from collections import defaultdict

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, ValidationError, validator, ValidationError

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_service.config import (
    DEPLOYMENT_CONFIG,
    INTEGRATION_CONFIG,
    SECURITY_CONFIG,
    SERVICE_CONFIG,
)
from ai_service.core.orchestrator_factory import OrchestratorFactory
from ai_service.exceptions import (
    AuthenticationError,
    InternalServerError,
    ServiceUnavailableError,
    ValidationAPIError,
)
from ai_service.utils import get_logger, setup_logging
from ai_service.utils.response_formatter import format_processing_result
from ai_service.contracts.base_contracts import NormalizationResponse, ProcessResponse, UnifiedProcessingResult
from ai_service.utils.feature_flags import FeatureFlags, get_feature_flag_manager

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI application

class NormalizationOptions(BaseModel):
    """Normalization options including feature flags"""
    
    flags: Optional[FeatureFlags] = None


class TextNormalizationRequest(BaseModel):
    """Request model for text normalization"""

    text: str = Field(..., max_length=SERVICE_CONFIG.max_input_length, min_length=1)
    language: str = "auto"
    remove_stop_words: bool = False  # For names, don't remove stop words
    apply_stemming: bool = False  # For names, don't apply stemming
    apply_lemmatization: bool = True  # For names, apply lemmatization
    clean_unicode: bool = True
    preserve_names: bool = True  # Preserve names and surnames
    options: Optional[NormalizationOptions] = None

    @validator('text')
    def validate_text_content(cls, v):
        """Additional text validation for security"""
        if not v.strip():
            raise ValueError("Text cannot be empty")

        # Check for excessive special characters (potential attack)
        special_char_count = sum(1 for c in v if not c.isalnum() and not c.isspace())
        if special_char_count > len(v) * 0.5:  # More than 50% special chars
            raise ValueError("Text contains too many special characters")

        return v


class ProcessTextRequest(BaseModel):
    """Request model for text processing"""

    text: str = Field(..., max_length=SERVICE_CONFIG.max_input_length)
    generate_variants: bool = True
    generate_embeddings: bool = False
    cache_result: bool = True
    options: Optional[NormalizationOptions] = None

    @validator("text")
    def validate_text_length(cls, v):
        """Validate text length"""
        if len(v) > SERVICE_CONFIG.max_input_length:
            raise ValueError(f"Text too long: {len(v)} > {SERVICE_CONFIG.max_input_length}")
        return v


class ProcessBatchRequest(BaseModel):
    """Request model for batch text processing"""

    texts: List[str]
    generate_variants: bool = True
    generate_embeddings: bool = False
    max_concurrent: int = 10

    @validator("texts")
    def validate_texts(cls, v):
        """Validate each text in the list"""
        for text in v:
            if len(text) > SERVICE_CONFIG.max_input_length:
                raise ValueError(f"Text too long: {len(text)} > {SERVICE_CONFIG.max_input_length}")
        return v


class SearchSimilarRequest(BaseModel):
    """Request model for searching similar names"""

    query: str
    candidates: List[str]
    threshold: float = 0.7
    top_k: int = 10
    use_embeddings: bool = True


class ComplexityAnalysisRequest(BaseModel):
    """Request model for text processing"""

    text: str = Field(..., max_length=SERVICE_CONFIG.max_input_length)


app = FastAPI(
    title="Sanctions AI Service",
    description="AI service for normalization and variant generation of sanctions data",
    version="1.0.0",
    docs_url=INTEGRATION_CONFIG.docs_url if INTEGRATION_CONFIG.enable_docs else None,
    redoc_url=INTEGRATION_CONFIG.redoc_url if INTEGRATION_CONFIG.enable_docs else None,
)

# Configure CORS
if INTEGRATION_CONFIG.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=INTEGRATION_CONFIG.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# Rate limiting for DoS protection
class RateLimitingMiddleware:
    """Simple in-memory rate limiting middleware for DoS protection"""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.requests = defaultdict(list)

    async def __call__(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        current_time = time.time()

        # Clean old requests
        self.requests[client_ip] = [
            req_time for req_time in self.requests[client_ip]
            if current_time - req_time < self.window_seconds
        ]

        # Check rate limit
        if len(self.requests[client_ip]) >= self.max_requests:
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            return JSONResponse(
                status_code=429,
                content={"detail": "Too Many Requests - Rate limit exceeded"}
            )

        # Add current request
        self.requests[client_ip].append(current_time)

        response = await call_next(request)
        return response

# Add rate limiting middleware
app.middleware("http")(RateLimitingMiddleware(max_requests=1000, window_seconds=60))

# Initialize orchestrator
orchestrator = None

# Security
security = HTTPBearer()


def _extract_signals_dict(result: UnifiedProcessingResult) -> Dict[str, Any]:
    """Extract signals information as dictionary"""
    if not result.signals:
        return None
    
    return {
        "persons": [
            {
                "core": person.core,
                "full_name": person.full_name,
                "dob": person.dob,
                "ids": person.ids,
                "confidence": person.confidence,
                "evidence": person.evidence,
            }
            for person in result.signals.persons
        ],
        "organizations": [
            {
                "core": org.core,
                "legal_form": org.legal_form,
                "full_name": org.full_name,
                "ids": org.ids,
                "confidence": org.confidence,
                "evidence": org.evidence,
            }
            for org in result.signals.organizations
        ],
        "confidence": result.signals.confidence,
    }


def _extract_decision_dict(result: UnifiedProcessingResult) -> Dict[str, Any]:
    """Extract decision information as dictionary"""
    if not result.decision:
        return None
    
    return {
        "risk_level": result.decision.risk.value,
        "risk_score": result.decision.score,
        "decision_reasons": result.decision.reasons,
        "decision_details": result.decision.details,
    }


def _merge_feature_flags(request_flags: Optional[FeatureFlags]) -> FeatureFlags:
    """Merge request feature flags with global configuration."""
    global_flags = get_feature_flag_manager()._flags
    
    if request_flags is None:
        return global_flags
    
    # Create a new FeatureFlags instance with request flags taking precedence
    return FeatureFlags(
        use_factory_normalizer=request_flags.use_factory_normalizer,
        fix_initials_double_dot=request_flags.fix_initials_double_dot,
        preserve_hyphenated_case=request_flags.preserve_hyphenated_case,
        strict_stopwords=request_flags.strict_stopwords,
        enable_ac_tier0=request_flags.enable_ac_tier0,
        enable_vector_fallback=request_flags.enable_vector_fallback,
        # New validation flags
        enable_spacy_ner=request_flags.enable_spacy_ner,
        enable_nameparser_en=request_flags.enable_nameparser_en,
        enable_fsm_tuned_roles=request_flags.enable_fsm_tuned_roles,
        enable_enhanced_diminutives=request_flags.enable_enhanced_diminutives,
        enable_enhanced_gender_rules=request_flags.enable_enhanced_gender_rules,
        enable_ascii_fastpath=request_flags.enable_ascii_fastpath,
        # Keep other global flags
        normalization_implementation=global_flags.normalization_implementation,
        factory_rollout_percentage=global_flags.factory_rollout_percentage,
        enable_performance_fallback=global_flags.enable_performance_fallback,
        max_latency_threshold_ms=global_flags.max_latency_threshold_ms,
        enable_accuracy_monitoring=global_flags.enable_accuracy_monitoring,
        min_confidence_threshold=global_flags.min_confidence_threshold,
        enable_dual_processing=global_flags.enable_dual_processing,
        log_implementation_choice=global_flags.log_implementation_choice,
        use_diminutives_dictionary_only=global_flags.use_diminutives_dictionary_only,
        diminutives_allow_cross_lang=global_flags.diminutives_allow_cross_lang,
        language_overrides=global_flags.language_overrides,
    )


def verify_admin_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> str:
    """
    Verify admin API token

    Args:
        credentials: HTTP authorization credentials

    Returns:
        Verified token string

    Raises:
        AuthenticationError: If token is invalid or not configured
    """
    expected_token = SECURITY_CONFIG.admin_api_key

    # Enhanced token validation
    if not expected_token or expected_token == "your-secure-api-key-here":
        logger.warning("Admin API key not configured properly")
        raise AuthenticationError("Admin API key not configured")

    # Check minimum token length and complexity
    if len(expected_token) < 32:
        logger.warning("Admin API key is too short (minimum 32 characters)")
        raise AuthenticationError("Admin API key not configured properly")

    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(credentials.credentials, expected_token):
        logger.warning(
            f"Invalid admin API key attempt from: {credentials.credentials[:8]}***"
        )
        raise AuthenticationError("Invalid API key")

    return credentials.credentials


def check_spacy_models():
    """Check availability of required SpaCy models"""
    required_models = ["en_core_web_sm", "ru_core_news_sm", "uk_core_news_sm"]
    missing_models = []

    for model_name in required_models:
        try:
            import spacy

            nlp = spacy.load(model_name)
            logger.info(f"Model {model_name} loaded successfully")
        except OSError:
            missing_models.append(model_name)
            logger.warning(f"Model {model_name} not found")

    if missing_models:
        logger.error(f"Missing models: {', '.join(missing_models)}")
        logger.error(
            "Run: poetry run post-install or python -m spacy download <model_name>"
        )
        return False

    logger.info("All SpaCy models are available")
    return True


@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup"""
    global orchestrator

    logger.info("Initializing AI services...")

    # Check models on startup
    if not check_spacy_models():
        logger.error("Failed to load required models. Service may not work correctly.")

    try:
        # Initialize unified orchestrator with production configuration
        orchestrator = await OrchestratorFactory.create_production_orchestrator()
        logger.info("Unified orchestrator successfully initialized")
    except Exception as e:
        logger.error(f"Error initializing orchestrator: {e}")
        raise


@app.get("/health")
async def health_check():
    """Service health check"""
    if orchestrator:
        stats = orchestrator.get_processing_stats()
        return {
            "status": "healthy",
            "service": "AI Service",
            "version": "1.0.0",
            "implementation": "full",
            "orchestrator": {
                "initialized": True,
                "processed_total": stats["total_processed"],
                "success_rate": (
                    stats["successful"] / stats["total_processed"]
                    if stats["total_processed"] > 0
                    else 0
                ),
                "cache_hit_rate": stats.get("cache", {}).get("hit_rate", 0) if isinstance(stats.get("cache"), dict) else 0,
                "services": stats.get("services", {}),
            },
        }
    else:
        return {
            "status": "initializing",
            "service": "AI Service",
            "version": "1.0.0",
            "orchestrator": {"initialized": False},
        }


@app.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus text format
    """
    try:
        if not orchestrator:
            return "# HELP ai_service_up Service is up and running\n# TYPE ai_service_up gauge\nai_service_up 0\n"

        # Get orchestrator metrics
        stats = orchestrator.get_processing_stats()

        # Get MetricsService metrics if available
        metrics_lines = []

        # Basic service metrics
        metrics_lines.append("# HELP ai_service_up Service is up and running")
        metrics_lines.append("# TYPE ai_service_up gauge")
        metrics_lines.append("ai_service_up 1")

        # Processing metrics
        metrics_lines.append("# HELP ai_service_requests_total Total processed requests")
        metrics_lines.append("# TYPE ai_service_requests_total counter")
        metrics_lines.append(f"ai_service_requests_total {stats.get('total_processed', 0)}")

        metrics_lines.append("# HELP ai_service_requests_successful_total Total successful requests")
        metrics_lines.append("# TYPE ai_service_requests_successful_total counter")
        metrics_lines.append(f"ai_service_requests_successful_total {stats.get('successful', 0)}")

        metrics_lines.append("# HELP ai_service_requests_failed_total Total failed requests")
        metrics_lines.append("# TYPE ai_service_requests_failed_total counter")
        metrics_lines.append(f"ai_service_requests_failed_total {stats.get('failed', 0)}")

        # Performance metrics
        if 'performance' in stats:
            perf = stats['performance']
            metrics_lines.append("# HELP ai_service_processing_time_avg_seconds Average processing time")
            metrics_lines.append("# TYPE ai_service_processing_time_avg_seconds gauge")
            metrics_lines.append(f"ai_service_processing_time_avg_seconds {perf.get('avg_processing_time', 0)}")

            metrics_lines.append("# HELP ai_service_processing_time_p95_seconds 95th percentile processing time")
            metrics_lines.append("# TYPE ai_service_processing_time_p95_seconds gauge")
            metrics_lines.append(f"ai_service_processing_time_p95_seconds {perf.get('p95_processing_time', 0)}")

        # Cache metrics
        if 'cache' in stats:
            cache = stats['cache']
            metrics_lines.append("# HELP ai_service_cache_hit_rate Cache hit rate")
            metrics_lines.append("# TYPE ai_service_cache_hit_rate gauge")
            metrics_lines.append(f"ai_service_cache_hit_rate {cache.get('hit_rate', 0)}")

        # Service availability metrics
        if 'services' in stats:
            services = stats['services']
            for service_name, service_status in services.items():
                metrics_lines.append(f"# HELP ai_service_component_available Component {service_name} availability")
                metrics_lines.append(f"# TYPE ai_service_component_available gauge")
                available = 1 if service_status.get('available', True) else 0
                metrics_lines.append(f"ai_service_component_available{{component=\"{service_name}\"}} {available}")

        return "\n".join(metrics_lines) + "\n"

    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return f"# Error generating metrics: {e}\nai_service_up 0\n"


@app.post("/process", response_model=ProcessResponse)
async def process_text(request: ProcessTextRequest):
    """
    Complete text processing through orchestrator

    Args:
        request: Text processing request

    Returns:
        Processing result with normalized text, tokens, trace, and optional sections

    Raises:
        HTTPException: 503 if orchestrator not initialized, 500 for internal errors
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        # Merge feature flags from request with global configuration
        merged_flags = _merge_feature_flags(request.options.flags if request.options else None)
        
        # Log feature flags for tracing
        logger.info(f"Processing with feature flags: {merged_flags.to_dict()}")
        
        result = await orchestrator.process(
            text=request.text,
            generate_variants=request.generate_variants,
            generate_embeddings=request.generate_embeddings,
            # Normalization flags from updated spec
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            # Pass feature flags to orchestrator
            feature_flags=merged_flags,
        )

        # Note: Feature flags are logged separately, not added to trace
        # as trace should only contain TokenTrace objects

        # Convert to ProcessResponse model
        return ProcessResponse(
            normalized_text=result.normalized_text,
            tokens=result.tokens or [],
            trace=result.trace or [],
            language=result.language,
            success=result.success,
            errors=result.errors or [],
            processing_time=result.processing_time,
            signals=_extract_signals_dict(result) if result.signals else None,
            decision=_extract_decision_dict(result) if result.decision else None,
            embedding=result.embeddings if request.generate_embeddings else None,
        )
    except ServiceUnavailableError as e:
        logger.error(f"Service unavailable: {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise HTTPException(status_code=500, detail=f"Text processing failed: {str(e)}")


@app.post("/normalize", response_model=NormalizationResponse)
async def normalize_text(request: TextNormalizationRequest):
    """
    Text normalization for search (legacy endpoint)

    Args:
        request: Text normalization request

    Returns:
        Normalized text result with tokens and trace

    Raises:
        HTTPException: 503 if orchestrator not initialized, 500 for internal errors
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        # Debug logging
        logger.info(f"Processing text: '{request.text}'")
        logger.info(f"Orchestrator initialized: {orchestrator is not None}")
        
        # Merge feature flags from request with global configuration
        merged_flags = _merge_feature_flags(request.options.flags if request.options else None)
        
        # Log feature flags for tracing
        logger.info(f"Normalizing with feature flags: {merged_flags.to_dict()}")
        
        # Use unified orchestrator for normalization only
        result = await orchestrator.process(
            text=request.text,
            generate_variants=False,
            generate_embeddings=False,
            # Use request parameters for normalization flags
            remove_stop_words=request.remove_stop_words,
            preserve_names=request.preserve_names,
            enable_advanced_features=request.apply_lemmatization,
            # Pass feature flags to orchestrator
            feature_flags=merged_flags,
        )
        
        # Note: Feature flags are logged separately, not added to trace
        # as trace should only contain TokenTrace objects
        
        # Debug logging
        logger.info(f"Result: success={result.success}, tokens={result.tokens}, language={result.language}")
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result attributes: {dir(result)}")
        logger.info(f"Result normalized_text: {result.normalized_text}")
        logger.info(f"Result tokens: {result.tokens}")
        logger.info(f"Result language: {result.language}")

        return NormalizationResponse(
            normalized_text=result.normalized_text,
            tokens=result.tokens,
            trace=result.trace,
            language=result.language,
            success=result.success,
            errors=result.errors,
            processing_time=result.processing_time,
        )
    except Exception as e:
        logger.error(f"Error normalizing text: {e}")
        raise HTTPException(status_code=500, detail=f"Text normalization failed: {str(e)}")


@app.post("/process-batch")
async def process_batch(request: ProcessBatchRequest):
    """Batch text processing through orchestrator"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        results = await orchestrator.process_batch(
            texts=request.texts,
            generate_variants=request.generate_variants,
            generate_embeddings=request.generate_embeddings,
            max_concurrent=request.max_concurrent,
        )

        processed_results = []
        for result in results:
            processed_results.append(
                {
                    "success": result.success,
                    "original_text": result.original_text,
                    "normalized_text": result.normalized_text,
                    "language": result.language,
                    "language_confidence": result.language_confidence,
                    "variants_count": len(result.variants) if result.variants else 0,
                    "processing_time": result.processing_time,
                    "errors": result.errors or [],
                }
            )

        return {
            "results": processed_results,
            "total_texts": len(request.texts),
            "successful": sum(1 for r in results if r.success),
            "total_processing_time": sum(r.processing_time for r in results),
        }
    except Exception as e:
        logger.error(f"Error processing batch: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/search-similar")
async def search_similar_names(request: SearchSimilarRequest):
    """Search for similar names"""
    if not orchestrator:

        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = await orchestrator.search_similar_names(
            query=request.query,
            candidates=request.candidates,
            threshold=request.threshold,
            top_k=request.top_k,
            use_embeddings=request.use_embeddings,
        )

        return result
    except Exception as e:
        logger.error(f"Error searching similar names: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/analyze-complexity")
async def analyze_complexity(request: ComplexityAnalysisRequest):
    """Text complexity analysis"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        result = await orchestrator.analyze_text_complexity(request.text)
        return result
    except Exception as e:
        logger.error(f"Error analyzing complexity: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/stats")
async def get_statistics():
    """Get service operation statistics"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        stats = orchestrator.get_processing_stats()
        return {
            "processing": {
                "total_processed": stats["total_processed"],
                "successful": stats["successful"],
                "failed": stats["failed"],
                "success_rate": (
                    stats["successful"] / stats["total_processed"]
                    if stats["total_processed"] > 0
                    else 0
                ),
                "average_processing_time": stats["average_time"],
            },
            "cache": stats.get("cache", {}),
            "services": stats.get("services", {}),
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/clear-cache")
async def clear_cache(token: str = Depends(verify_admin_token)):
    """Clear cache - Admin only"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        orchestrator.clear_cache()
        return {"message": "Cache cleared successfully"}
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/reset-stats")
async def reset_statistics(token: str = Depends(verify_admin_token)):
    """Reset statistics - Admin only"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        orchestrator.reset_stats()
        return {"message": "Statistics reset successfully"}
    except Exception as e:
        logger.error(f"Error resetting statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    return {
        "supported_languages": {
            "en": {"supported": True, "name": "English"},
            "ru": {"supported": True, "name": "Russian"},
            "uk": {"supported": True, "name": "Ukrainian"},
        },
        "auto_detection": True,
        "fallback_language": "en",
    }


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Sanctions AI Service",
        "version": "1.0.0",
        "description": "AI service for normalization and variant generation of sanctions data",
        "implementation": "full_with_orchestrator",
        "orchestrator": orchestrator is not None,
        "endpoints": {
            "health": "/health",
            "process": "/process",
            "process_batch": "/process-batch",
            "search_similar": "/search-similar",
            "analyze_complexity": "/analyze-complexity",
            "stats": "/stats",
            "clear_cache": "/clear-cache",
            "reset_stats": "/reset-stats",
            "normalize": "/normalize",
            "languages": "/languages",
        },
        "features": [
            "Text normalization",
            "Variant generation",
            "Signal detection",
            "Similarity search",
            "Complexity analysis",
            "Batch processing",
            "Caching",
            "Multi-language support",
            "Real-time statistics",
        ],
    }


# Admin endpoints
@app.get("/admin/status")
async def admin_status(credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer())):
    """Admin status endpoint with authentication"""
    if not credentials or not secrets.compare_digest(credentials.credentials, SECURITY_CONFIG.admin_api_key):
        raise HTTPException(status_code=401, detail="Invalid admin token")
    
    # Get orchestrator statistics
    stats = {
        "total_processed": 0,
        "successful": 0,
        "failed": 0,
        "cache": {"hits": 0, "misses": 0}
    }
    
    detailed_stats = stats.copy()
    
    if orchestrator:
        # Get basic stats from orchestrator if available
        stats.update({
            "orchestrator_initialized": True,
            "processing_time": 0.0  # Simple value to avoid recursion
        })
        
        # Try to get detailed stats if method exists
        if hasattr(orchestrator, 'get_detailed_stats'):
            try:
                detailed_stats = orchestrator.get_detailed_stats()
            except Exception:
                pass  # Use default stats if method fails
    else:
        stats["orchestrator_initialized"] = False
    
    return {
        "status": "operational",
        "version": "1.0.0",
        "timestamp": "2023-01-01T00:00:00Z",
        "statistics": stats,
        "detailed_stats": detailed_stats
    }


# Exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request, exc):
    """Handle authentication errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


@app.exception_handler(ValidationAPIError)
async def validation_exception_handler(request, exc):
    """Handle validation errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_exception_handler(request, exc):
    """Handle service unavailable errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


@app.exception_handler(InternalServerError)
async def internal_server_exception_handler(request, exc):
    """Handle internal server errors"""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )


@app.exception_handler(ValidationError)
async def validation_exception_handler(request, exc):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )


@app.exception_handler(ValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: ValidationError):
    """Handle Pydantic validation errors"""
    return JSONResponse(
        status_code=422,
        content={"detail": "Validation error", "errors": exc.errors()}
    )



if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=DEPLOYMENT_CONFIG.host,
        port=DEPLOYMENT_CONFIG.port,
        reload=DEPLOYMENT_CONFIG.auto_reload,
        log_level=DEPLOYMENT_CONFIG.log_level,
    )
