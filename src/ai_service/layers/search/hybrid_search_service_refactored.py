"""
Refactored Hybrid Search Service with improved modularity and maintainability.

This is a refactored version of the original hybrid_search_service.py
breaking down the large monolithic class into smaller, more manageable components.
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ...core.base_service import BaseService
from ...utils.logging_config import get_logger
from ...contracts.base_contracts import NormalizationResult

from .contracts import Candidate, SearchOpts, SearchService, SearchMode, SearchMetrics
from ...contracts.trace_models import SearchTrace, SearchTraceHit, SearchTraceStep
from .config import HybridSearchConfig
from .elasticsearch_adapters import ElasticsearchACAdapter, ElasticsearchVectorAdapter
from .elasticsearch_client import ElasticsearchClientFactory
from ..embeddings.indexing.watchlist_index_service import WatchlistIndexService
from ..embeddings.indexing.enhanced_vector_index_service import EnhancedVectorIndex

# Import refactored components
from .components import (
    SearchCacheManager,
    PerformanceMonitor,
    SearchExecutor,
    ResultProcessor
)

try:  # Optional heavy dependency
    from ..embeddings.optimized_embedding_service import OptimizedEmbeddingService
except Exception:  # pragma: no cover - optional dependency may be unavailable
    OptimizedEmbeddingService = None  # type: ignore


class HybridSearchServiceRefactored(BaseService, SearchService):
    """
    Refactored hybrid search service with modular components.

    Breaks down the original monolithic service into focused, reusable components:
    - Cache management for embeddings, results, and queries
    - Performance monitoring and metrics collection
    - Search execution for AC, vector, and hybrid modes
    - Result processing including deduplication and reranking

    This design improves maintainability, testability, and separation of concerns.
    """

    def __init__(self, config: Optional[HybridSearchConfig] = None):
        """Initialize refactored hybrid search service."""
        super().__init__("hybrid_search_refactored")
        self.config = config or HybridSearchConfig.from_env()

        # Initialize component services
        self.cache_manager = SearchCacheManager(ttl_minutes=self.config.cache_ttl_minutes)
        self.performance_monitor = PerformanceMonitor(history_limit=10000)
        self.result_processor = ResultProcessor()

        # Search adapters - will be initialized during service initialization
        self._ac_adapter: Optional[ElasticsearchACAdapter] = None
        self._vector_adapter: Optional[ElasticsearchVectorAdapter] = None
        self._client_factory: Optional[ElasticsearchClientFactory] = None

        # Search executor - initialized with adapters
        self.search_executor: Optional[SearchExecutor] = None

        # Fallback services
        self._fallback_watchlist_service: Optional[WatchlistIndexService] = None
        self._fallback_vector_service: Optional[EnhancedVectorIndex] = None

        # Service state
        self._initialized = False
        self._last_health_check = None

        # Embedding service for vector queries (lazy init)
        self._embedding_service = None
        self._embedding_service_checked = False

        # Fusion weights/boosts
        self._fusion_weights, self._fusion_boosts = self._load_fusion_weights()

        self.logger.info("HybridSearchServiceRefactored initialized with modular components")

    def _do_initialize(self) -> None:
        """Initialize the service and its components."""
        try:
            # Initialize Elasticsearch adapters
            self._client_factory = ElasticsearchClientFactory(self.config.elasticsearch)
            self._ac_adapter = ElasticsearchACAdapter(self._client_factory)
            self._vector_adapter = ElasticsearchVectorAdapter(self._client_factory)

            # Initialize search executor with adapters
            self.search_executor = SearchExecutor(
                ac_adapter=self._ac_adapter,
                vector_adapter=self._vector_adapter
            )

            # Ensure fallback services are available
            self._ensure_fallback_services()

            self._initialized = True
            self.logger.info("HybridSearchServiceRefactored initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize HybridSearchServiceRefactored: {e}")
            self._initialized = False
            raise

    async def find_candidates(
        self,
        normalized: NormalizationResult,
        query: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Find candidates using the configured search strategy."""
        start_time = time.time()

        try:
            # Validate inputs
            if not query or not query.strip():
                return []

            # Check cache first
            cache_key = self.cache_manager.generate_search_cache_key(query, opts)
            cached_results = await self.cache_manager.get_cached_search_result(cache_key)
            if cached_results is not None:
                processing_time_ms = (time.time() - start_time) * 1000
                await self.performance_monitor.record_query_performance(
                    query=query,
                    search_mode="cached",
                    processing_time_ms=processing_time_ms,
                    result_count=len(cached_results),
                    cache_hit=True
                )
                return cached_results

            # Determine search strategy
            candidates = await self._execute_search_strategy(normalized, query, opts)

            # Process results
            processed_candidates = self.result_processor.process_results(
                candidates, query, opts
            )

            # Cache results
            await self.cache_manager.cache_search_result(cache_key, processed_candidates)

            # Record performance
            processing_time_ms = (time.time() - start_time) * 1000
            await self.performance_monitor.record_query_performance(
                query=query,
                search_mode=opts.mode.value if opts.mode else "auto",
                processing_time_ms=processing_time_ms,
                result_count=len(processed_candidates)
            )

            return processed_candidates

        except Exception as e:
            self.logger.error(f"Search failed for query '{query}': {e}", exc_info=True)

            # Record error
            processing_time_ms = (time.time() - start_time) * 1000
            await self.performance_monitor.record_query_performance(
                query=query,
                search_mode="error",
                processing_time_ms=processing_time_ms,
                result_count=0,
                error=str(e)
            )

            return []

    async def _execute_search_strategy(
        self,
        normalized: NormalizationResult,
        query: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute the appropriate search strategy."""
        if not self.search_executor:
            raise RuntimeError("Search executor not initialized")

        # Handle explicit search mode requests
        if opts.mode == SearchMode.AC_ONLY:
            return await self.search_executor.execute_ac_search(query, normalized, opts)
        elif opts.mode == SearchMode.VECTOR_ONLY:
            query_vector = await self._build_query_vector(normalized, query)
            return await self.search_executor.execute_vector_search(query_vector, normalized, opts)
        elif opts.mode == SearchMode.HYBRID:
            query_vector = await self._build_query_vector(normalized, query)
            return await self.search_executor.execute_hybrid_search(
                query, query_vector, normalized, opts
            )

        # Auto mode: intelligent escalation strategy
        return await self._auto_search_with_escalation(normalized, query, opts)

    async def _auto_search_with_escalation(
        self,
        normalized: NormalizationResult,
        query: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute auto search with escalation strategy."""
        # First attempt: AC search for exact/almost-exact matches
        ac_candidates = await self.search_executor.execute_ac_search(query, normalized, opts)

        # Check if escalation to vector search is needed
        if not self.search_executor.should_escalate_to_vector(ac_candidates, opts):
            return ac_candidates

        # Escalation: Add vector search results
        query_vector = await self._build_query_vector(normalized, query)
        vector_candidates = await self.search_executor.execute_vector_search(
            query_vector, normalized, opts
        )

        # Combine results using fusion strategy
        if self.search_executor.should_use_vector_fallback(ac_candidates, vector_candidates, opts):
            return vector_candidates
        else:
            # Combine both result sets
            return self.result_processor.combine_result_sets(
                ac_candidates, vector_candidates,
                weights=[0.7, 0.3]  # Prefer AC results
            )

    async def _build_query_vector(self, normalized: NormalizationResult, text: str) -> List[float]:
        """Build query vector for vector search."""
        # Check cache first
        processed_text = self._preprocess_query_for_embedding(text)
        cached_vector = await self.cache_manager.get_cached_embedding(processed_text)
        if cached_vector:
            return cached_vector

        # Get embedding service
        embedding_service = await self._get_embedding_service()
        if not embedding_service:
            # Fallback to pseudo embedding
            vector = self._pseudo_embedding(text)
        else:
            try:
                vector = await embedding_service.encode_async(processed_text)
            except Exception as e:
                self.logger.warning(f"Embedding service failed: {e}")
                vector = self._pseudo_embedding(text)

        # Cache the vector
        await self.cache_manager.cache_embedding(processed_text, vector)
        return vector

    async def _get_embedding_service(self):
        """Get embedding service with lazy initialization."""
        if self._embedding_service_checked:
            return self._embedding_service

        self._embedding_service_checked = True

        if OptimizedEmbeddingService is None:
            self.logger.warning("OptimizedEmbeddingService not available")
            return None

        try:
            def _init_service():
                return OptimizedEmbeddingService()

            # Initialize in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            self._embedding_service = await loop.run_in_executor(None, _init_service)
            self.logger.info("Embedding service initialized successfully")

        except Exception as e:
            self.logger.warning(f"Failed to initialize embedding service: {e}")
            self._embedding_service = None

        return self._embedding_service

    def _pseudo_embedding(self, text: str) -> List[float]:
        """Generate pseudo embedding for fallback."""
        # Simple hash-based embedding for testing/fallback
        import hashlib

        hash_obj = hashlib.md5(text.encode())
        hash_bytes = hash_obj.digest()

        # Convert to float vector (dimension 384 to match sentence transformers)
        vector = []
        for i in range(0, min(len(hash_bytes), 48)):  # 48 * 8 = 384
            byte_val = hash_bytes[i % len(hash_bytes)]
            for j in range(8):
                bit = (byte_val >> j) & 1
                vector.append(float(bit) * 2.0 - 1.0)  # Convert to [-1, 1]

        # Pad to 384 dimensions
        while len(vector) < 384:
            vector.append(0.0)

        return vector[:384]

    def _preprocess_query_for_embedding(self, text: str) -> str:
        """Preprocess query text for embedding."""
        if not text:
            return ""

        # Basic preprocessing
        processed = text.lower().strip()

        # Remove extra whitespace
        import re
        processed = re.sub(r'\s+', ' ', processed)

        return processed

    def _ensure_fallback_services(self) -> None:
        """Ensure fallback services are available."""
        try:
            if not self._fallback_watchlist_service:
                self._fallback_watchlist_service = WatchlistIndexService()

            if not self._fallback_vector_service:
                self._fallback_vector_service = EnhancedVectorIndex()

            self.logger.info("Fallback services initialized")

        except Exception as e:
            self.logger.warning(f"Failed to initialize fallback services: {e}")

    def _load_fusion_weights(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Load fusion weights and boosts from configuration."""
        # Default weights for combining different search modes
        weights = {
            "ac_weight": 0.7,
            "vector_weight": 0.3,
            "hybrid_weight": 0.5
        }

        # Default boosts for different result types
        boosts = {
            "exact_match_boost": 1.5,
            "partial_match_boost": 1.2,
            "fuzzy_match_boost": 1.0
        }

        # Load from config if available
        if hasattr(self.config, 'fusion_weights'):
            weights.update(self.config.fusion_weights)

        if hasattr(self.config, 'fusion_boosts'):
            boosts.update(self.config.fusion_boosts)

        return weights, boosts

    # Metrics and monitoring methods
    async def get_search_metrics(self) -> SearchMetrics:
        """Get search performance metrics."""
        return self.performance_monitor.get_core_metrics()

    async def get_performance_stats(self, time_window_minutes: Optional[int] = None):
        """Get detailed performance statistics."""
        return await self.performance_monitor.get_performance_stats(time_window_minutes)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        embedding_stats = await self.cache_manager.get_embedding_cache_stats()
        search_stats = await self.cache_manager.get_search_cache_stats()
        query_stats = await self.cache_manager.get_query_cache_stats()

        return {
            "embedding_cache": embedding_stats,
            "search_cache": search_stats,
            "query_cache": query_stats
        }

    # Cache management methods
    async def clear_all_caches(self) -> None:
        """Clear all caches."""
        await self.cache_manager.clear_embedding_cache()
        await self.cache_manager.clear_search_cache()
        await self.cache_manager.clear_query_cache()

    async def cleanup_expired_entries(self) -> int:
        """Clean up expired cache entries."""
        return await self.cache_manager.cleanup_expired_cache_entries()

    # Configuration methods
    def update_processing_config(self, **kwargs) -> None:
        """Update result processing configuration."""
        self.result_processor.update_config(**kwargs)

    def update_escalation_config(self, **kwargs) -> None:
        """Update search escalation configuration."""
        if self.search_executor:
            self.search_executor.update_escalation_config(**kwargs)

    def get_component_status(self) -> Dict[str, Any]:
        """Get status of all components for diagnostics."""
        return {
            "service_initialized": self._initialized,
            "cache_manager": bool(self.cache_manager),
            "performance_monitor": bool(self.performance_monitor),
            "search_executor": bool(self.search_executor),
            "result_processor": bool(self.result_processor),
            "ac_adapter": bool(self._ac_adapter),
            "vector_adapter": bool(self._vector_adapter),
            "embedding_service": bool(self._embedding_service),
            "fallback_services": {
                "watchlist": bool(self._fallback_watchlist_service),
                "vector": bool(self._fallback_vector_service)
            }
        }