#!/usr/bin/env python3
"""
AI Service for normalization and variant generation
for sanctions data verification
"""

import os
import sys
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, validator
import uvicorn

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from ai_service.config import SERVICE_CONFIG, SECURITY_CONFIG, INTEGRATION_CONFIG, DEPLOYMENT_CONFIG
from ai_service.exceptions import (
    AuthenticationError, 
    ValidationAPIError, 
    ServiceUnavailableError,
    InternalServerError
)
from ai_service.services.orchestrator_service import OrchestratorService
from ai_service.utils import setup_logging, get_logger

# Setup centralized logging
setup_logging()
logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="Sanctions AI Service",
    description="AI service for normalization and variant generation of sanctions data",
    version="1.0.0",
    docs_url=INTEGRATION_CONFIG.docs_url if INTEGRATION_CONFIG.enable_docs else None,
    redoc_url=INTEGRATION_CONFIG.redoc_url if INTEGRATION_CONFIG.enable_docs else None
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

# Initialize orchestrator
orchestrator = None

# Security
security = HTTPBearer()

def verify_admin_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
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
    
    if not expected_token or expected_token == 'your-secure-api-key-here':
        logger.warning("Admin API key not configured properly")
        raise AuthenticationError("Admin API key not configured")
    
    if credentials.credentials != expected_token:
        logger.warning(f"Invalid admin API key attempt: {credentials.credentials[:10]}...")
        raise AuthenticationError("Invalid API key")
    
    return credentials.credentials


class TextNormalizationRequest(BaseModel):
    """Request model for text normalization"""
    text: str = Field(..., max_length=SERVICE_CONFIG.max_input_length)
    language: str = "auto"
    remove_stop_words: bool = False  # For names, don't remove stop words
    apply_stemming: bool = False     # For names, don't apply stemming
    apply_lemmatization: bool = True # For names, apply lemmatization
    clean_unicode: bool = True
    preserve_names: bool = True      # Preserve names and surnames


class VariantGenerationRequest(BaseModel):
    """Request model for variant generation"""
    text: str = Field(..., max_length=SERVICE_CONFIG.max_input_length)
    language: str = "en"
    max_variants: int = 10
    similarity_threshold: float = 0.8


class EmbeddingRequest(BaseModel):
    """Request model for embedding generation"""
    texts: List[str] = Field(..., max_length=SERVICE_CONFIG.max_input_length)
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"


class ProcessTextRequest(BaseModel):
    """Request model for text processing"""
    text: str = Field(..., max_length=SERVICE_CONFIG.max_input_length)
    generate_variants: bool = True
    generate_embeddings: bool = False
    cache_result: bool = True


class ProcessBatchRequest(BaseModel):
    """Request model for batch text processing"""
    texts: List[str]
    generate_variants: bool = True
    generate_embeddings: bool = False
    max_concurrent: int = 10

    @validator('texts')
    def validate_texts(cls, v):
        """Validate each text in the list"""
        for text in v:
            if len(text) > SERVICE_CONFIG.max_input_length:
                raise ValueError(
                    f"Text length {len(text)} exceeds maximum allowed length {SERVICE_CONFIG.max_input_length}"
                )
        return v


class SearchSimilarRequest(BaseModel):
    """Request model for similar text search"""
    query: str = Field(..., max_length=SERVICE_CONFIG.max_input_length)
    candidates: List[str]
    threshold: float = 0.7
    top_k: int = 10
    use_embeddings: bool = False

    @validator('candidates')
    def validate_candidates(cls, v):
        """Validate each candidate text in the list"""
        for text in v:
            if len(text) > SERVICE_CONFIG.max_input_length:
                raise ValueError(
                    f"Candidate text length {len(text)} exceeds maximum allowed length {SERVICE_CONFIG.max_input_length}"
                )
        return v


class ComplexityAnalysisRequest(BaseModel):
    """Request model for text complexity analysis"""
    text: str = Field(..., max_length=SERVICE_CONFIG.max_input_length)


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
        logger.error("Run: poetry run post-install or python -m spacy download <model_name>")
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
        orchestrator = OrchestratorService(cache_size=10000, default_ttl=3600)
        logger.info("Orchestrator successfully initialized")
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
                "success_rate": stats["successful"] / stats["total_processed"] if stats["total_processed"] > 0 else 0,
                "cache_hit_rate": stats["cache"]["hit_rate"] if "cache" in stats else 0,
                "services": stats.get("services", {})
            }
        }
    else:
        return {
            "status": "initializing",
            "service": "AI Service",
            "version": "1.0.0",
            "orchestrator": {"initialized": False}
        }


@app.post("/process")
async def process_text(request: ProcessTextRequest):
    """
    Complete text processing through orchestrator
    
    Args:
        request: Text processing request
        
    Returns:
        Processing result with normalized text and variants
        
    Raises:
        ServiceUnavailableError: If orchestrator is not initialized
        InternalServerError: If processing fails
    """
    if not orchestrator:
        raise ServiceUnavailableError("Orchestrator not initialized")
    
    try:
        result = await orchestrator.process_text(
            text=request.text,
            generate_variants=request.generate_variants,
            generate_embeddings=request.generate_embeddings,
            cache_result=request.cache_result
        )
        
        return {
            "success": result.success,
            "original_text": result.original_text,
            "normalized_text": result.normalized_text,
            "language": result.language,
            "language_confidence": result.language_confidence,
            "variants": result.variants,
            "processing_time": result.processing_time,
            "has_embeddings": result.embeddings is not None,
            "errors": result.errors
        }
    except Exception as e:
        logger.error(f"Error processing text: {e}")
        raise InternalServerError(f"Text processing failed: {str(e)}")


@app.post("/normalize")
async def normalize_text(request: TextNormalizationRequest):
    """
    Text normalization for search (legacy endpoint)
    
    Args:
        request: Text normalization request
        
    Returns:
        Normalized text result
        
    Raises:
        ServiceUnavailableError: If orchestrator is not initialized
        InternalServerError: If normalization fails
    """
    if not orchestrator:
        raise ServiceUnavailableError("Orchestrator not initialized")
    
    try:
        # Use orchestrator for normalization
        result = await orchestrator.process_text(
            text=request.text,
            generate_variants=False,
            generate_embeddings=False,
            cache_result=True
        )
        
        return {
            "original_text": result.original_text,
            "normalized_text": result.normalized_text,
            "language": result.language,
            "processing_time": result.processing_time,
            "success": result.success
        }
    except Exception as e:
        logger.error(f"Error normalizing text: {e}")
        raise InternalServerError(f"Text normalization failed: {str(e)}")


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
            max_concurrent=request.max_concurrent
        )
        
        processed_results = []
        for result in results:
            processed_results.append({
                "success": result.success,
                "original_text": result.original_text,
                "normalized_text": result.normalized_text,
                "language": result.language,
                "language_confidence": result.language_confidence,
                "variants_count": len(result.variants),
                "processing_time": result.processing_time,
                "errors": result.errors
            })
        
        return {
            "results": processed_results,
            "total_texts": len(request.texts),
            "successful": sum(1 for r in results if r.success),
            "total_processing_time": sum(r.processing_time for r in results)
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
            use_embeddings=request.use_embeddings
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
                "success_rate": stats["successful"] / stats["total_processed"] if stats["total_processed"] > 0 else 0,
                "average_processing_time": stats["average_time"]
            },
            "cache": stats.get("cache", {}),
            "services": stats.get("services", {})
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
            "uk": {"supported": True, "name": "Ukrainian"}
        },
        "auto_detection": True,
        "fallback_language": "en"
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
            "languages": "/languages"
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
            "Real-time statistics"
        ]
    }


# Exception handlers
@app.exception_handler(AuthenticationError)
async def authentication_exception_handler(request, exc):
    """Handle authentication errors"""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message
    )


@app.exception_handler(ValidationAPIError)
async def validation_exception_handler(request, exc):
    """Handle validation errors"""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message
    )


@app.exception_handler(ServiceUnavailableError)
async def service_unavailable_exception_handler(request, exc):
    """Handle service unavailable errors"""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message
    )


@app.exception_handler(InternalServerError)
async def internal_server_exception_handler(request, exc):
    """Handle internal server errors"""
    return HTTPException(
        status_code=exc.status_code,
        detail=exc.message
    )


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=DEPLOYMENT_CONFIG.host,
        port=DEPLOYMENT_CONFIG.port,
        reload=DEPLOYMENT_CONFIG.auto_reload,
        log_level=DEPLOYMENT_CONFIG.log_level
    )