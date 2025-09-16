"""
Elasticsearch adapters for AC and Vector search modes.

Provides adapters for:
- AC (exact/almost-exact) search using Elasticsearch text search
- Vector (kNN) search using Elasticsearch dense vector search
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from ...utils.logging_config import get_logger

from .contracts import Candidate, SearchOpts, ElasticsearchAdapter, SearchMode
from .config import HybridSearchConfig


class ElasticsearchACAdapter(ElasticsearchAdapter):
    """
    Elasticsearch adapter for AC (exact/almost-exact) search.
    
    Implements text-based search on normalized names, aliases, and legal names.
    Uses Elasticsearch text analysis, fuzzy matching, and phrase queries.
    """
    
    def __init__(self, config: HybridSearchConfig):
        """
        Initialize AC search adapter.
        
        Args:
            config: Search configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Elasticsearch client (TODO: initialize actual client)
        self._client = None
        self._latency_stats = {
            "total_requests": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "request_times": []
        }
        
        # Connection status
        self._connected = False
        self._last_connection_check = None
    
    async def _ensure_connection(self) -> None:
        """Ensure Elasticsearch connection is established."""
        if self._connected and self._last_connection_check:
            # Check if connection is still valid (within last 5 minutes)
            if (datetime.now() - self._last_connection_check).seconds < 300:
                return
        
        try:
            # TODO: Initialize actual Elasticsearch client
            # from elasticsearch import AsyncElasticsearch
            # 
            # self._client = AsyncElasticsearch(
            #     hosts=self.config.elasticsearch.hosts,
            #     username=self.config.elasticsearch.username,
            #     password=self.config.elasticsearch.password,
            #     api_key=self.config.elasticsearch.api_key,
            #     ca_certs=self.config.elasticsearch.ca_certs,
            #     verify_certs=self.config.elasticsearch.verify_certs,
            #     max_retries=self.config.elasticsearch.max_retries,
            #     retry_on_timeout=self.config.elasticsearch.retry_on_timeout,
            #     timeout=self.config.elasticsearch.timeout
            # )
            
            # For now, simulate connection
            self._client = "mock_client"
            self._connected = True
            self._last_connection_check = datetime.now()
            
            self.logger.info("Elasticsearch AC adapter connected")
            
        except Exception as e:
            self._connected = False
            self.logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    async def search(
        self, 
        query: str, 
        opts: SearchOpts,
        index_name: str = "watchlist_ac"
    ) -> List[Candidate]:
        """
        Execute AC search query.
        
        Args:
            query: Search query text
            opts: Search options
            index_name: Elasticsearch index name
            
        Returns:
            List of search candidates
        """
        start_time = time.time()
        
        try:
            await self._ensure_connection()
            
            # TODO: Implement actual Elasticsearch AC search
            # For now, return mock results
            candidates = await self._mock_ac_search(query, opts, index_name)
            
            # Update latency stats
            latency_ms = (time.time() - start_time) * 1000
            self._update_latency_stats(latency_ms)
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"AC search failed: {e}")
            return []
    
    async def _mock_ac_search(
        self, 
        query: str, 
        opts: SearchOpts, 
        index_name: str
    ) -> List[Candidate]:
        """Mock AC search implementation (TODO: replace with real Elasticsearch query)."""
        
        # TODO: Replace with actual Elasticsearch query
        # Example query structure:
        # {
        #     "query": {
        #         "bool": {
        #             "should": [
        #                 {
        #                     "multi_match": {
        #                         "query": query,
        #                         "fields": ["normalized_text^2.0", "aliases^1.5", "legal_names^1.8"],
        #                         "type": "best_fields",
        #                         "fuzziness": opts.ac_fuzziness,
        #                         "boost": opts.ac_boost
        #                     }
        #                 },
        #                 {
        #                     "match_phrase": {
        #                         "normalized_text": {
        #                             "query": query,
        #                             "boost": 2.0
        #                         }
        #                     }
        #                 }
        #             ],
        #             "minimum_should_match": 1
        #         }
        #     },
        #     "size": opts.top_k,
        #     "min_score": opts.ac_min_score,
        #     "timeout": f"{opts.timeout_ms}ms"
        # }
        
        # Mock results for testing
        mock_candidates = [
            Candidate(
                doc_id=f"ac_result_{i}",
                score=0.9 - (i * 0.1),
                text=f"Mock AC result {i} for query: {query}",
                entity_type="person",
                metadata={"source": "ac_search", "index": index_name},
                search_mode=SearchMode.AC,
                match_fields=["normalized_text"],
                confidence=0.8
            )
            for i in range(min(3, opts.top_k))
        ]
        
        return mock_candidates
    
    def _update_latency_stats(self, latency_ms: float) -> None:
        """Update latency statistics."""
        self._latency_stats["total_requests"] += 1
        self._latency_stats["request_times"].append(latency_ms)
        
        # Keep only recent requests
        if len(self._latency_stats["request_times"]) > 1000:
            self._latency_stats["request_times"].pop(0)
        
        # Calculate average latency
        if self._latency_stats["request_times"]:
            self._latency_stats["avg_latency_ms"] = (
                sum(self._latency_stats["request_times"]) / 
                len(self._latency_stats["request_times"])
            )
            
            # Calculate P95 latency
            sorted_times = sorted(self._latency_stats["request_times"])
            p95_index = int(len(sorted_times) * 0.95)
            self._latency_stats["p95_latency_ms"] = (
                sorted_times[p95_index] if p95_index < len(sorted_times) 
                else sorted_times[-1]
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch AC adapter health."""
        try:
            await self._ensure_connection()
            
            # TODO: Implement actual health check
            # response = await self._client.cluster.health()
            
            return {
                "adapter": "elasticsearch_ac",
                "status": "healthy",
                "connected": self._connected,
                "latency_stats": self.get_latency_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "adapter": "elasticsearch_ac",
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Get adapter-specific latency statistics."""
        return {
            "total_requests": self._latency_stats["total_requests"],
            "avg_latency_ms": self._latency_stats["avg_latency_ms"],
            "p95_latency_ms": self._latency_stats["p95_latency_ms"]
        }


class ElasticsearchVectorAdapter(ElasticsearchAdapter):
    """
    Elasticsearch adapter for Vector (kNN) search.
    
    Implements dense vector similarity search using Elasticsearch kNN capabilities.
    Uses HNSW algorithm for efficient approximate nearest neighbor search.
    """
    
    def __init__(self, config: HybridSearchConfig):
        """
        Initialize Vector search adapter.
        
        Args:
            config: Search configuration
        """
        self.config = config
        self.logger = get_logger(__name__)
        
        # Elasticsearch client (TODO: initialize actual client)
        self._client = None
        self._latency_stats = {
            "total_requests": 0,
            "avg_latency_ms": 0.0,
            "p95_latency_ms": 0.0,
            "request_times": []
        }
        
        # Connection status
        self._connected = False
        self._last_connection_check = None
    
    async def _ensure_connection(self) -> None:
        """Ensure Elasticsearch connection is established."""
        if self._connected and self._last_connection_check:
            # Check if connection is still valid (within last 5 minutes)
            if (datetime.now() - self._last_connection_check).seconds < 300:
                return
        
        try:
            # TODO: Initialize actual Elasticsearch client
            # from elasticsearch import AsyncElasticsearch
            # 
            # self._client = AsyncElasticsearch(
            #     hosts=self.config.elasticsearch.hosts,
            #     username=self.config.elasticsearch.username,
            #     password=self.config.elasticsearch.password,
            #     api_key=self.config.elasticsearch.api_key,
            #     ca_certs=self.config.elasticsearch.ca_certs,
            #     verify_certs=self.config.elasticsearch.verify_certs,
            #     max_retries=self.config.elasticsearch.max_retries,
            #     retry_on_timeout=self.config.elasticsearch.retry_on_timeout,
            #     timeout=self.config.elasticsearch.timeout
            # )
            
            # For now, simulate connection
            self._client = "mock_client"
            self._connected = True
            self._last_connection_check = datetime.now()
            
            self.logger.info("Elasticsearch Vector adapter connected")
            
        except Exception as e:
            self._connected = False
            self.logger.error(f"Failed to connect to Elasticsearch: {e}")
            raise
    
    async def search(
        self, 
        query: str, 
        opts: SearchOpts,
        index_name: str = "watchlist_vector"
    ) -> List[Candidate]:
        """
        Execute Vector search query.
        
        Args:
            query: Search query text
            opts: Search options
            index_name: Elasticsearch index name
            
        Returns:
            List of search candidates
        """
        start_time = time.time()
        
        try:
            await self._ensure_connection()
            
            # TODO: Implement actual Elasticsearch Vector search
            # For now, return mock results
            candidates = await self._mock_vector_search(query, opts, index_name)
            
            # Update latency stats
            latency_ms = (time.time() - start_time) * 1000
            self._update_latency_stats(latency_ms)
            
            return candidates
            
        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            return []
    
    async def _mock_vector_search(
        self, 
        query: str, 
        opts: SearchOpts, 
        index_name: str
    ) -> List[Candidate]:
        """Mock Vector search implementation (TODO: replace with real Elasticsearch query)."""
        
        # TODO: Replace with actual Elasticsearch kNN query
        # Example query structure:
        # {
        #     "knn": {
        #         "field": "dense_vector",
        #         "query_vector": query_vector,  # Generated from query text
        #         "k": opts.top_k,
        #         "num_candidates": opts.max_escalation_results,
        #         "boost": opts.vector_boost
        #     },
        #     "size": opts.top_k,
        #     "min_score": opts.vector_min_score,
        #     "timeout": f"{opts.timeout_ms}ms"
        # }
        
        # Mock results for testing
        mock_candidates = [
            Candidate(
                doc_id=f"vector_result_{i}",
                score=0.85 - (i * 0.05),
                text=f"Mock Vector result {i} for query: {query}",
                entity_type="person",
                metadata={"source": "vector_search", "index": index_name},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector"],
                confidence=0.75
            )
            for i in range(min(5, opts.top_k))
        ]
        
        return mock_candidates
    
    def _update_latency_stats(self, latency_ms: float) -> None:
        """Update latency statistics."""
        self._latency_stats["total_requests"] += 1
        self._latency_stats["request_times"].append(latency_ms)
        
        # Keep only recent requests
        if len(self._latency_stats["request_times"]) > 1000:
            self._latency_stats["request_times"].pop(0)
        
        # Calculate average latency
        if self._latency_stats["request_times"]:
            self._latency_stats["avg_latency_ms"] = (
                sum(self._latency_stats["request_times"]) / 
                len(self._latency_stats["request_times"])
            )
            
            # Calculate P95 latency
            sorted_times = sorted(self._latency_stats["request_times"])
            p95_index = int(len(sorted_times) * 0.95)
            self._latency_stats["p95_latency_ms"] = (
                sorted_times[p95_index] if p95_index < len(sorted_times) 
                else sorted_times[-1]
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch Vector adapter health."""
        try:
            await self._ensure_connection()
            
            # TODO: Implement actual health check
            # response = await self._client.cluster.health()
            
            return {
                "adapter": "elasticsearch_vector",
                "status": "healthy",
                "connected": self._connected,
                "latency_stats": self.get_latency_stats(),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                "adapter": "elasticsearch_vector",
                "status": "unhealthy",
                "connected": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def get_latency_stats(self) -> Dict[str, float]:
        """Get adapter-specific latency statistics."""
        return {
            "total_requests": self._latency_stats["total_requests"],
            "avg_latency_ms": self._latency_stats["avg_latency_ms"],
            "p95_latency_ms": self._latency_stats["p95_latency_ms"]
        }
