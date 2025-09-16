"""
Hybrid Search Service - combines AC (exact) and Vector (kNN) search modes.

This service implements the main search functionality with escalation:
1. AC search for exact/almost-exact matches on normalized names, aliases, legal names
2. Vector search for kNN similarity on dense vectors
3. Escalation: if AC doesn't return results or has weak scores, trigger vector search
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from ...core.base_service import BaseService
from ...utils.logging_config import get_logger
from ...contracts.base_contracts import NormalizationResult

from .contracts import (
    Candidate, 
    SearchOpts, 
    SearchService, 
    SearchMode, 
    SearchMetrics
)
from .config import HybridSearchConfig
from .elasticsearch_adapters import ElasticsearchACAdapter, ElasticsearchVectorAdapter


class HybridSearchService(BaseService, SearchService):
    """
    Hybrid search service combining AC and Vector search modes.
    
    Implements escalation strategy:
    - First attempt: AC search for exact/almost-exact matches
    - Escalation: If AC results are weak or empty, trigger vector search
    - Fallback: If Elasticsearch is unavailable, use local indexes
    """
    
    def __init__(self, config: Optional[HybridSearchConfig] = None):
        """
        Initialize hybrid search service.
        
        Args:
            config: Search configuration, uses default if None
        """
        super().__init__("hybrid_search")
        self.config = config or HybridSearchConfig()
        
        # Search adapters
        self._ac_adapter: Optional[ElasticsearchACAdapter] = None
        self._vector_adapter: Optional[ElasticsearchVectorAdapter] = None
        
        # Metrics tracking
        self._metrics = SearchMetrics()
        self._request_times: List[float] = []
        
        # Fallback services (TODO: integrate with existing layers)
        self._fallback_watchlist_service = None  # TODO: WatchlistIndexService integration
        self._fallback_vector_service = None     # TODO: EnhancedVectorIndex integration
        
        # Service state
        self._initialized = False
        self._last_health_check = None
    
    def _do_initialize(self) -> None:
        """Initialize search adapters and fallback services."""
        try:
            # Initialize Elasticsearch adapters
            self._ac_adapter = ElasticsearchACAdapter(self.config)
            self._vector_adapter = ElasticsearchVectorAdapter(self.config)
            
            # TODO: Initialize fallback services
            # self._fallback_watchlist_service = WatchlistIndexService()
            # self._fallback_vector_service = EnhancedVectorIndex()
            
            self._initialized = True
            self.logger.info("Hybrid search service initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize hybrid search service: {e}")
            raise
    
    async def find_candidates(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts
    ) -> List[Candidate]:
        """
        Find search candidates using hybrid search strategy.
        
        Args:
            normalized: Normalized text result from normalization layer
            text: Original input text
            opts: Search options and parameters
            
        Returns:
            List of search candidates sorted by score (descending)
        """
        if not self._initialized:
            self.initialize()
        
        start_time = time.time()
        self._metrics.total_requests += 1
        
        try:
            # Determine search strategy based on options
            if opts.search_mode == SearchMode.AC:
                candidates = await self._ac_search_only(normalized, text, opts)
            elif opts.search_mode == SearchMode.VECTOR:
                candidates = await self._vector_search_only(normalized, text, opts)
            else:  # HYBRID mode
                candidates = await self._hybrid_search(normalized, text, opts)
            
            # Process and rank results
            candidates = self._process_results(candidates, opts)
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            self._update_metrics(True, processing_time, len(candidates))
            
            self.logger.info(
                f"Search completed: {len(candidates)} candidates found in {processing_time:.2f}ms"
            )
            
            return candidates
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._update_metrics(False, processing_time, 0)
            
            self.logger.error(f"Search failed: {e}")
            
            # TODO: Implement fallback to local indexes
            return await self._fallback_search(normalized, text, opts)
    
    async def _ac_search_only(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute AC search only."""
        self._metrics.ac_requests += 1
        
        try:
            # TODO: Implement AC search using ElasticsearchACAdapter
            # For now, return empty list as placeholder
            candidates = await self._ac_adapter.search(
                query=text,
                opts=opts,
                index_name=self.config.elasticsearch.ac_index
            )
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"AC search failed: {e}")
            return []
    
    async def _vector_search_only(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute vector search only."""
        self._metrics.vector_requests += 1
        
        try:
            # TODO: Implement vector search using ElasticsearchVectorAdapter
            # For now, return empty list as placeholder
            candidates = await self._vector_adapter.search(
                query=text,
                opts=opts,
                index_name=self.config.elasticsearch.vector_index
            )
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    async def _hybrid_search(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute hybrid search with escalation."""
        self._metrics.hybrid_requests += 1
        
        # Step 1: Try AC search first
        ac_candidates = await self._ac_search_only(normalized, text, opts)
        
        # Check if AC results are sufficient
        if self._should_escalate(ac_candidates, opts):
            self.logger.info("AC results insufficient, escalating to vector search")
            self._metrics.escalation_triggered += 1
            
            # Step 2: Execute vector search
            vector_candidates = await self._vector_search_only(normalized, text, opts)
            
            # Step 3: Combine and deduplicate results
            all_candidates = self._combine_results(ac_candidates, vector_candidates, opts)
            
            return all_candidates
        else:
            return ac_candidates
    
    def _should_escalate(self, ac_candidates: List[Candidate], opts: SearchOpts) -> bool:
        """Determine if escalation to vector search is needed."""
        if not opts.enable_escalation:
            return False
        
        if not ac_candidates:
            return True
        
        # Check if best AC score is below escalation threshold
        best_score = max(candidate.score for candidate in ac_candidates)
        return best_score < opts.escalation_threshold
    
    def _combine_results(
        self, 
        ac_candidates: List[Candidate], 
        vector_candidates: List[Candidate], 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Combine and deduplicate results from AC and vector search."""
        # TODO: Implement result combination logic
        # - Deduplicate by doc_id
        # - Apply score boosting based on search mode
        # - Sort by combined score
        
        all_candidates = ac_candidates + vector_candidates
        
        if self.config.enable_deduplication:
            # Simple deduplication by doc_id (keep highest score)
            seen = {}
            for candidate in all_candidates:
                if candidate.doc_id not in seen or candidate.score > seen[candidate.doc_id].score:
                    seen[candidate.doc_id] = candidate
            all_candidates = list(seen.values())
        
        # Sort by score descending
        all_candidates.sort(key=lambda x: x.score, reverse=True)
        
        return all_candidates[:opts.top_k]
    
    def _process_results(self, candidates: List[Candidate], opts: SearchOpts) -> List[Candidate]:
        """Process and filter search results."""
        # Apply threshold filtering
        filtered_candidates = [
            c for c in candidates 
            if c.score >= opts.threshold
        ]
        
        # Apply entity type filtering
        if opts.entity_types:
            filtered_candidates = [
                c for c in filtered_candidates
                if c.entity_type in opts.entity_types
            ]
        
        # Apply metadata filtering
        if opts.metadata_filters:
            filtered_candidates = [
                c for c in filtered_candidates
                if self._matches_metadata_filters(c, opts.metadata_filters)
            ]
        
        return filtered_candidates
    
    def _matches_metadata_filters(self, candidate: Candidate, filters: Dict[str, Any]) -> bool:
        """Check if candidate matches metadata filters."""
        # TODO: Implement metadata filtering logic
        for key, value in filters.items():
            if key not in candidate.metadata:
                return False
            if candidate.metadata[key] != value:
                return False
        return True
    
    async def _fallback_search(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Fallback to local indexes when Elasticsearch is unavailable."""
        self.logger.warning("Using fallback search due to Elasticsearch unavailability")
        
        # TODO: Implement fallback using existing local indexes
        # - WatchlistIndexService for AC-like search
        # - EnhancedVectorIndex for vector search
        
        return []
    
    def _update_metrics(self, success: bool, processing_time_ms: float, result_count: int) -> None:
        """Update search metrics."""
        if success:
            self._metrics.successful_requests += 1
        else:
            self._metrics.failed_requests += 1
        
        # Update latency tracking
        self._request_times.append(processing_time_ms)
        if len(self._request_times) > self.config.metrics_window_size:
            self._request_times.pop(0)
        
        # Calculate average latency
        if self._request_times:
            self._metrics.avg_hybrid_latency_ms = sum(self._request_times) / len(self._request_times)
            
            # Calculate P95 latency
            sorted_times = sorted(self._request_times)
            p95_index = int(len(sorted_times) * 0.95)
            self._metrics.p95_latency_ms = sorted_times[p95_index] if p95_index < len(sorted_times) else sorted_times[-1]
        
        # Update hit rate (simplified calculation)
        if result_count > 0:
            self._metrics.hybrid_hit_rate = (
                (self._metrics.hybrid_hit_rate * (self._metrics.total_requests - 1) + 1.0) 
                / self._metrics.total_requests
            )
        else:
            self._metrics.hybrid_hit_rate = (
                (self._metrics.hybrid_hit_rate * (self._metrics.total_requests - 1) + 0.0) 
                / self._metrics.total_requests
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check search service health status."""
        health_status = {
            "service": "hybrid_search",
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "initialized": self._initialized,
            "metrics": self._metrics.to_dict()
        }
        
        try:
            # Check Elasticsearch adapters
            if self._ac_adapter:
                ac_health = await self._ac_adapter.health_check()
                health_status["ac_adapter"] = ac_health
            
            if self._vector_adapter:
                vector_health = await self._vector_adapter.health_check()
                health_status["vector_adapter"] = vector_health
            
            # Check fallback services
            health_status["fallback_available"] = (
                self._fallback_watchlist_service is not None and 
                self._fallback_vector_service is not None
            )
            
        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        self._last_health_check = health_status
        return health_status
    
    def get_metrics(self) -> SearchMetrics:
        """Get current search metrics."""
        return self._metrics
    
    def reset_metrics(self) -> None:
        """Reset search metrics."""
        self._metrics = SearchMetrics()
        self._request_times.clear()
        self.logger.info("Search metrics reset")
    
    def get_status(self) -> Dict[str, Any]:
        """Get detailed service status."""
        return {
            "service_name": self.service_name,
            "initialized": self._initialized,
            "config": self.config.to_dict(),
            "metrics": self._metrics.to_dict(),
            "last_health_check": self._last_health_check,
            "fallback_services": {
                "watchlist": self._fallback_watchlist_service is not None,
                "vector": self._fallback_vector_service is not None,
            }
        }
