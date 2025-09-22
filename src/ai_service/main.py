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
from fastapi.responses import JSONResponse, Response
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
# from ai_service.layers.search.contracts import SearchRequest, SearchOpts
from ai_service.utils.feature_flags import FeatureFlags, get_feature_flag_manager
from ai_service.monitoring.prometheus_exporter import get_exporter

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)

# Import lazy_imports module to trigger initialization
from ai_service.utils.lazy_imports import NAMEPARSER, RAPIDFUZZ, NLP_EN, NLP_UK, NLP_RU

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


# class SearchRequest(BaseModel):
#     """Request model for name search"""
#     
#     query: str = Field(..., max_length=SERVICE_CONFIG.max_input_length, min_length=1)
#     opts: SearchOpts = Field(default_factory=SearchOpts)
#     
#     @validator('query')
#     def validate_query(cls, v):
#         """Validate search query"""
#         if not v.strip():
#             raise ValueError("Query cannot be empty")
#         return v.strip()


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

# Import admin endpoints
from ai_service.api.admin_endpoints import router as admin_router

# Configure CORS
if INTEGRATION_CONFIG.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=INTEGRATION_CONFIG.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

# Include admin endpoints
app.include_router(admin_router)

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

# Add rate limiting middleware - optimized for 100+ RPS
app.middleware("http")(RateLimitingMiddleware(max_requests=6000, window_seconds=60))

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
    try:
        import spacy
    except ImportError:
        logger.warning("spaCy not available, skipping model checks")
        return False

    required_models = ["en_core_web_sm", "ru_core_news_sm", "uk_core_news_sm"]
    missing_models = []

    for model_name in required_models:
        try:
            nlp = spacy.load(model_name)
            logger.info(f"Model {model_name} loaded successfully")
        except OSError:
            missing_models.append(model_name)
            logger.warning(f"Model {model_name} not found")

    if missing_models:
        logger.warning(f"Missing models: {', '.join(missing_models)}")
        logger.warning(
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

    # Check models on startup (non-blocking)
    if not check_spacy_models():
        logger.warning("SpaCy models not available. NER features will be disabled.")

    try:
        # Initialize unified orchestrator with production configuration
        orchestrator = await OrchestratorFactory.create_production_orchestrator()
        logger.info("Unified orchestrator successfully initialized")
    except Exception as e:
        logger.error(f"Error initializing orchestrator: {e}")
        raise


@app.get("/health")
async def health_check():
    """Basic service health check"""
    if orchestrator:
        return {
            "status": "healthy",
            "service": "AI Service",
            "version": "1.0.0",
            "timestamp": time.time(),
        }
    else:
        return {
            "status": "initializing",
            "service": "AI Service",
            "version": "1.0.0",
            "timestamp": time.time(),
        }


@app.get("/health/detailed")
async def detailed_health_check():
    """Detailed service health check with component status"""
    if orchestrator:
        stats = orchestrator.get_processing_stats()

        # Get search service health if available
        search_health = {}
        if hasattr(orchestrator, 'search_service') and orchestrator.search_service:
            try:
                search_health = await orchestrator.search_service.health_check()
            except Exception as e:
                search_health = {"status": "error", "error": str(e)}

        # Check HTTP client pool health
        try:
            from ai_service.utils.http_client_pool import get_http_pool
            pool = get_http_pool()
            pool_stats = pool.get_stats()
            pool_health = {
                "status": "healthy",
                "active_clients": pool_stats.get("async_client_created", False),
                "connections": pool_stats
            }
        except Exception as e:
            pool_health = {"status": "error", "error": str(e)}

        return {
            "status": "healthy",
            "service": "AI Service",
            "version": "1.0.0",
            "timestamp": time.time(),
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
            "components": {
                "search_service": search_health,
                "http_client_pool": pool_health,
            }
        }
    else:
        return {
            "status": "initializing",
            "service": "AI Service",
            "version": "1.0.0",
            "timestamp": time.time(),
            "orchestrator": {"initialized": False},
        }


@app.get("/health/live")
async def liveness_check():
    """Kubernetes liveness probe - basic service availability"""
    return {"status": "alive", "timestamp": time.time()}


@app.get("/health/ready")
async def readiness_check():
    """Kubernetes readiness probe - service ready to accept traffic"""
    if orchestrator:
        # Check if core services are available
        try:
            stats = orchestrator.get_processing_stats()

            # Check if we can process a simple request (lightweight check)
            is_ready = (
                stats.get("total_processed", 0) >= 0 and  # Orchestrator is working
                hasattr(orchestrator, 'normalization_service')  # Core service available
            )

            if is_ready:
                return {
                    "status": "ready",
                    "timestamp": time.time(),
                    "message": "Service ready to accept requests"
                }
            else:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "timestamp": time.time(),
                        "message": "Service not ready"
                    }
                )
        except Exception as e:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready",
                    "timestamp": time.time(),
                    "error": str(e)
                }
            )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "timestamp": time.time(),
                "message": "Orchestrator not initialized"
            }
        )


@app.get("/metrics")
async def get_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus text format
    """
    try:
        # Get the Prometheus exporter
        exporter = get_exporter()

        # Update service status metrics based on orchestrator availability
        if orchestrator:
            stats = orchestrator.get_processing_stats()

            # Update success rate if available
            total_requests = stats.get('total_processed', 0)
            successful_requests = stats.get('successful', 0)
            if total_requests > 0:
                success_rate = successful_requests / total_requests
                exporter.update_success_rate(success_rate)

            # Update cache hit rate if available
            if 'cache' in stats:
                cache_hit_rate = stats['cache'].get('hit_rate', 0.0)
                exporter.update_cache_hit_rate(cache_hit_rate)

            # Update active connections estimate (based on service availability)
            if 'services' in stats:
                active_services = sum(1 for s in stats['services'].values() if s.get('available', False))
                exporter.update_active_connections(active_services)

        # Return metrics in Prometheus format with correct Content-Type
        metrics_content = exporter.get_metrics().decode('utf-8')
        return Response(
            content=metrics_content,
            media_type=exporter.get_metrics_content_type()
        )

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


# @app.post("/search")
# async def search_names(request: SearchRequest):
#     """Search for names using hybrid search"""
#     if not orchestrator:
#         raise HTTPException(status_code=503, detail="Orchestrator not initialized")
# 
#     try:
#         # Check if search service is available
#         if not hasattr(orchestrator, 'search_service') or not orchestrator.search_service:
#             raise HTTPException(status_code=503, detail="Search service not available")
# 
#         # Perform search using HybridSearchService
#         results = await orchestrator.search_service.search(
#             query=request.query,
#             opts=request.opts
#         )
# 
#         return {
#             "query": request.query,
#             "results": results,
#             "total_results": len(results),
#             "search_time_ms": getattr(results, 'search_time_ms', 0) if hasattr(results, 'search_time_ms') else 0
#         }
#     except Exception as e:
#         logger.error(f"Error searching names: {e}")
#         raise HTTPException(status_code=500, detail="Internal Server Error")


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


@app.post("/reload-config")
async def reload_configuration(token: str = Depends(verify_admin_token)):
    """Reload configuration - Admin only"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        # Reload search service configuration if available
        if hasattr(orchestrator, 'search_service') and orchestrator.search_service:
            if hasattr(orchestrator.search_service, 'config') and hasattr(orchestrator.search_service.config, '_reload_configuration'):
                orchestrator.search_service.config._reload_configuration()
                logger.info("Search service configuration reloaded")
        
        return {"message": "Configuration reloaded successfully"}
    except Exception as e:
        logger.error(f"Error reloading configuration: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.get("/config-status")
async def get_configuration_status(token: str = Depends(verify_admin_token)):
    """Get configuration status - Admin only"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        status = {
            "search_service": {
                "enabled": hasattr(orchestrator, 'search_service') and orchestrator.search_service is not None,
                "hot_reload": False,
                "reload_stats": {}
            }
        }
        
        # Get search service configuration status
        if hasattr(orchestrator, 'search_service') and orchestrator.search_service:
            if hasattr(orchestrator.search_service, 'config'):
                config = orchestrator.search_service.config
                if hasattr(config, 'get_reload_stats'):
                    status["search_service"]["hot_reload"] = True
                    status["search_service"]["reload_stats"] = config.get_reload_stats()
        
        return status
    except Exception as e:
        logger.error(f"Error getting configuration status: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@app.post("/validate-config")
async def validate_configuration(token: str = Depends(verify_admin_token)):
    """Validate current configuration - Admin only"""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")

    try:
        validation_results = {
            "search_service": {
                "enabled": hasattr(orchestrator, 'search_service') and orchestrator.search_service is not None,
                "validation_passed": False,
                "errors": [],
                "warnings": []
            }
        }
        
        # Validate search service configuration
        if hasattr(orchestrator, 'search_service') and orchestrator.search_service:
            try:
                config = orchestrator.search_service.config
                
                # Validate configuration using Pydantic validation
                config.validate(config)
                validation_results["search_service"]["validation_passed"] = True
                
                # Additional runtime validation
                if hasattr(config, 'es_hosts') and config.es_hosts:
                    # Test Elasticsearch connectivity
                    try:
                        if hasattr(orchestrator.search_service, '_client_factory') and orchestrator.search_service._client_factory:
                            health = await orchestrator.search_service._client_factory.health_check()
                            if health.get('status') != 'green':
                                validation_results["search_service"]["warnings"].append(
                                    f"Elasticsearch cluster status: {health.get('status', 'unknown')}"
                                )
                    except Exception as e:
                        validation_results["search_service"]["warnings"].append(
                            f"Elasticsearch connectivity check failed: {str(e)}"
                        )
                
                # Validate fallback services
                if hasattr(config, 'enable_fallback') and config.enable_fallback:
                    if not hasattr(orchestrator.search_service, '_fallback_watchlist_service') or not orchestrator.search_service._fallback_watchlist_service:
                        validation_results["search_service"]["warnings"].append(
                            "Fallback enabled but watchlist service not available"
                        )
                
            except Exception as e:
                validation_results["search_service"]["validation_passed"] = False
                validation_results["search_service"]["errors"].append(str(e))
        
        return validation_results
    except Exception as e:
        logger.error(f"Error validating configuration: {e}")
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
            "health_detailed": "/health/detailed",
            "health_live": "/health/live",
            "health_ready": "/health/ready",
            "metrics": "/metrics",
            "process": "/process",
            "process_batch": "/process-batch",
            # "search": "/search",  # Temporarily disabled
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
            # "Hybrid search",  # Temporarily disabled
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
