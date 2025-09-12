"""
Orchestrator Service V2 - Refactored
Clean, SOLID-principle implementation using extracted components.
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..config import PERFORMANCE_CONFIG, SERVICE_CONFIG
from ..exceptions import ServiceInitializationError
from ..utils import get_logger
from .context_extractors import ContextExtractionCoordinator
from .processing_pipeline import ProcessingContext, ProcessingPipeline
from .service_coordinator import ServiceCoordinator, ServiceRegistry
from .statistics_manager import StatisticsManager


@dataclass
class ProcessingResult:
    """
    Clean processing result structure
    Simplified from the original monolithic version
    """
    
    original_text: str
    normalized_text: str
    language: str
    language_confidence: float
    variants: List[str]
    token_variants: Optional[Dict[str, List[str]]] = None
    embeddings: Optional[List] = None
    processing_time: float = 0.0
    success: bool = True
    errors: List[str] = None
    smart_filter: Optional[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    @property
    def error(self) -> str:
        """Get first error message for backward compatibility"""
        return self.errors[0] if self.errors else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "original_text": self.original_text,
            "normalized_text": self.normalized_text,
            "language": self.language,
            "language_confidence": self.language_confidence,
            "variants": self.variants,
            "token_variants": self.token_variants,
            "embeddings": self.embeddings,
            "processing_time": self.processing_time,
            "success": self.success,
            "errors": self.errors,
            "smart_filter": self.smart_filter,
        }


class OrchestratorV2:
    """
    Refactored Orchestrator Service
    
    Follows SOLID principles:
    - Single Responsibility: Only orchestrates the processing flow
    - Open/Closed: Extensible via pipeline stages
    - Liskov Substitution: Components can be substituted
    - Interface Segregation: Components have focused interfaces  
    - Dependency Inversion: Depends on abstractions, not concretions
    """
    
    def __init__(self, cache_size: Optional[int] = None, default_ttl: Optional[int] = None):
        """
        Initialize the refactored orchestrator
        
        Args:
            cache_size: Cache size override
            default_ttl: Default TTL override
        """
        
        self.logger = get_logger(__name__)
        
        # Initialize component managers
        self.service_coordinator = ServiceCoordinator(cache_size, default_ttl)
        self.statistics_manager = StatisticsManager()
        
        # Will be initialized in startup
        self.services: Optional[ServiceRegistry] = None
        self.processing_pipeline: Optional[ProcessingPipeline] = None
        self.context_extractor: Optional[ContextExtractionCoordinator] = None
        
        self.logger.info("OrchestratorV2 created - awaiting initialization")
    
    async def initialize(self) -> None:
        """Initialize all services and components"""
        
        try:
            # Initialize services
            self.services = self.service_coordinator.initialize_all_services()
            
            # Register services with statistics manager
            for service_name, status in self.services.service_states.items():
                self.statistics_manager.register_service(service_name, status)
            
            # Initialize processing pipeline
            self.processing_pipeline = ProcessingPipeline(self.services)
            
            # Initialize context extraction coordinator
            self.context_extractor = ContextExtractionCoordinator(
                self.services.pattern_service
            )
            
            self.logger.info("OrchestratorV2 fully initialized")
            
        except Exception as e:
            self.logger.error(f"OrchestratorV2 initialization failed: {e}")
            raise ServiceInitializationError(f"Orchestrator initialization failed: {str(e)}")
    
    async def process_text(
        self,
        text: str,
        generate_variants: bool = True,
        generate_embeddings: bool = False,
        cache_result: bool = True,
        force_reprocess: bool = False,
        timeout: Optional[float] = None,
    ) -> ProcessingResult:
        """
        Process text through the complete pipeline
        
        Args:
            text: Input text to process
            generate_variants: Whether to generate variants
            generate_embeddings: Whether to generate embeddings  
            cache_result: Whether to cache the result
            force_reprocess: Whether to force reprocessing
            timeout: Processing timeout in seconds
            
        Returns:
            ProcessingResult with all processing results
        """
        
        if not self.processing_pipeline:
            raise ServiceInitializationError("Orchestrator not initialized")
        
        start_time = datetime.now()
        
        try:
            # Handle timeout validation
            if timeout is not None and timeout <= 0:
                return ProcessingResult(
                    original_text=text,
                    normalized_text="",
                    language="unknown",
                    language_confidence=0.0,
                    variants=[],
                    processing_time=0.0,
                    success=False,
                    errors=[f"Invalid timeout value: {timeout}"],
                )
            
            # Check cache first (if not forcing reprocess and not generating embeddings)
            if not force_reprocess and not generate_embeddings and cache_result:
                cached_result = await self._check_cache(text, generate_variants, generate_embeddings)
                if cached_result:
                    self.statistics_manager.update_cache_stats(hit=True)
                    return cached_result
                
            self.statistics_manager.update_cache_stats(hit=False)
            
            # Process through pipeline
            processing_context = await self.processing_pipeline.process_text(
                text=text,
                generate_variants=generate_variants,
                generate_embeddings=generate_embeddings,
            )
            
            # Apply domain-specific context extraction if needed
            final_normalized = await self._apply_context_extraction(processing_context)
            
            # Create result
            result = ProcessingResult(
                original_text=text,
                normalized_text=final_normalized,
                language=processing_context.language,
                language_confidence=processing_context.language_confidence,
                variants=processing_context.variants or [final_normalized],
                token_variants=processing_context.token_variants,
                embeddings=processing_context.embeddings,
                processing_time=processing_context.processing_time,
                success=processing_context.success,
                errors=processing_context.errors,
                smart_filter=processing_context.smart_filter_result,
            )
            
            # Cache result if requested
            if cache_result and not generate_embeddings:
                await self._cache_result(text, generate_variants, generate_embeddings, result)
            
            # Update statistics
            self.statistics_manager.update_processing_stats(result.processing_time, result.success)
            self.statistics_manager.record_stage_timings(processing_context.stage_timings)
            
            return result
            
        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            self.logger.error(f"Text processing failed: {e}")
            
            # Update failure statistics
            self.statistics_manager.update_processing_stats(processing_time, success=False)
            
            return ProcessingResult(
                original_text=text,
                normalized_text="",
                language="unknown",
                language_confidence=0.0,
                variants=[],
                processing_time=processing_time,
                success=False,
                errors=[str(e)],
            )
    
    async def process_batch(
        self,
        texts: List[str],
        generate_variants: bool = True,
        generate_embeddings: bool = False,
        max_concurrent: int = 10,
    ) -> List[ProcessingResult]:
        """
        Process multiple texts concurrently
        
        Args:
            texts: List of texts to process
            generate_variants: Whether to generate variants
            generate_embeddings: Whether to generate embeddings
            max_concurrent: Maximum concurrent processing tasks
            
        Returns:
            List of processing results
        """
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_single(text: str) -> ProcessingResult:
            async with semaphore:
                return await self.process_text(
                    text=text,
                    generate_variants=generate_variants,
                    generate_embeddings=generate_embeddings,
                )
        
        # Execute all tasks concurrently
        tasks = [process_single(text) for text in texts]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                self.logger.error(f"Batch processing error for text {i}: {result}")
                processed_results.append(
                    ProcessingResult(
                        original_text=texts[i],
                        normalized_text="",
                        language="unknown",
                        language_confidence=0.0,
                        variants=[],
                        processing_time=0.0,
                        success=False,
                        errors=[str(result)],
                    )
                )
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def _apply_context_extraction(self, context: ProcessingContext) -> str:
        """
        Apply domain-specific context extraction to get final normalized text
        
        Args:
            context: Processing context from pipeline
            
        Returns:
            Final normalized text after context extraction
        """
        
        if not self.context_extractor:
            return context.normalized_text
        
        try:
            # Use smart filter signals to guide extraction if available
            prefer_company = None
            if context.smart_filter_result:
                signals = context.smart_filter_result.get("detected_signals", [])
                if "company" in signals and "name" not in signals:
                    prefer_company = True
                elif "name" in signals and "company" not in signals:
                    prefer_company = False
            
            # Extract best entity
            best_entity, entity_type = self.context_extractor.determine_best_entity(
                context.original_text,
                context.language,
                prefer_company=prefer_company
            )
            
            if best_entity:
                self.logger.info(f"Context extraction: {entity_type} -> '{best_entity}'")
                return best_entity
            
        except Exception as e:
            self.logger.warning(f"Context extraction failed: {e}")
        
        # Fallback to pipeline result
        return context.normalized_text
    
    async def _check_cache(
        self, text: str, generate_variants: bool, generate_embeddings: bool
    ) -> Optional[ProcessingResult]:
        """Check cache for existing result"""
        
        if not self.services or not self.services.cache_service:
            return None
        
        cache_key = self._generate_cache_key(text, generate_variants, generate_embeddings)
        return self.services.cache_service.get(cache_key)
    
    async def _cache_result(
        self,
        text: str,
        generate_variants: bool,
        generate_embeddings: bool,
        result: ProcessingResult
    ) -> None:
        """Cache processing result"""
        
        if not self.services or not self.services.cache_service:
            return
        
        cache_key = self._generate_cache_key(text, generate_variants, generate_embeddings)
        self.services.cache_service.set(cache_key, result, ttl=3600)
    
    def _generate_cache_key(
        self, text: str, generate_variants: bool, generate_embeddings: bool
    ) -> str:
        """Generate cache key for request"""
        
        import hashlib
        
        key_data = f"{text}_{generate_variants}_{generate_embeddings}"
        return f"orchestrator_v2_{hashlib.md5(key_data.encode()).hexdigest()}"
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get comprehensive processing statistics"""
        
        stats = self.statistics_manager.get_comprehensive_stats()
        
        # Add service health information
        if self.service_coordinator:
            stats["service_health"] = self.service_coordinator.get_service_health()
        
        return stats
    
    def get_health_check(self) -> Dict[str, Any]:
        """Get health check information"""
        
        health = self.statistics_manager.get_health_summary()
        
        if self.services:
            health["services_initialized"] = True
            health["pipeline_ready"] = self.processing_pipeline is not None
            health["context_extractor_ready"] = self.context_extractor is not None
        else:
            health["services_initialized"] = False
            health["pipeline_ready"] = False
            health["context_extractor_ready"] = False
        
        return health
    
    def clear_cache(self) -> None:
        """Clear processing cache"""
        
        if self.services and self.services.cache_service:
            self.services.cache_service.clear()
            self.logger.info("Cache cleared")
    
    def reset_stats(self) -> None:
        """Reset all statistics"""
        
        self.statistics_manager.reset_stats()
        self.logger.info("Statistics reset")
    
    async def shutdown(self) -> None:
        """Clean shutdown of orchestrator and all services"""
        
        self.logger.info("Shutting down OrchestratorV2...")
        
        # Shutdown services
        if self.service_coordinator:
            self.service_coordinator.shutdown_services()
        
        # Reset references
        self.services = None
        self.processing_pipeline = None
        self.context_extractor = None
        
        self.logger.info("OrchestratorV2 shutdown completed")
    
    # Legacy compatibility methods
    async def search_similar_names(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.7,
        top_k: int = 10,
        use_embeddings: bool = True,
    ) -> Dict[str, Any]:
        """Search for similar names (legacy compatibility)"""
        
        if not self.services or not self.services.embedding_service:
            return {"method": "error", "query": query, "results": [], "error": "Embedding service not available"}
        
        try:
            if use_embeddings:
                search_result = self.services.embedding_service.find_similar_texts(
                    query=query, candidates=candidates, threshold=threshold, top_k=top_k
                )
                
                if search_result.get("success"):
                    return {
                        "method": "embeddings",
                        "query": query,
                        "results": search_result["results"],
                        "total_candidates": search_result["total_candidates"],
                        "threshold": threshold,
                    }
            
            # Fallback method would go here
            return {"method": "fallback", "query": query, "results": [], "error": "Fallback not implemented"}
            
        except Exception as e:
            return {"method": "error", "query": query, "results": [], "error": str(e)}
    
    async def analyze_text_complexity(self, text: str) -> Dict[str, Any]:
        """Analyze text complexity (legacy compatibility)"""
        
        if not self.services:
            return {"text": text, "error": "Services not initialized", "complexity_score": 0.0}
        
        try:
            # Basic complexity analysis using available services
            complexity_info = {
                "text": text,
                "text_length": len(text),
                "word_count": len(text.split()),
                "complexity_score": min(len(text) / 1000, 1.0),  # Simple heuristic
            }
            
            # Add language analysis if available
            if self.services.language_service:
                lang_result = self.services.language_service.detect_language(text)
                complexity_info["language"] = lang_result
            
            # Add unicode analysis if available  
            if self.services.unicode_service:
                unicode_result = self.services.unicode_service.normalize_text(text, aggressive=False)
                complexity_info["unicode"] = {
                    "confidence": unicode_result.get("confidence", 1.0),
                    "changes": unicode_result.get("changes", []),
                }
            
            return complexity_info
            
        except Exception as e:
            return {"text": text, "error": str(e), "complexity_score": 0.0}