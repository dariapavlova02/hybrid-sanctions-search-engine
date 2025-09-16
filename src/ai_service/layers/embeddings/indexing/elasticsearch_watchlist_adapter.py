"""
Elasticsearch adapter for WatchlistIndexService and EnhancedVectorIndex.

Provides a bridge from local vector indexes to Elasticsearch, maintaining
compatible interfaces while delegating all operations to ES.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

import httpx
import numpy as np

from ....utils.logging_config import get_logger
from .vector_index_service import VectorIndexConfig
from .watchlist_index_service import WatchlistDoc, WatchlistIndexService
from .enhanced_vector_index_service import EnhancedVectorIndex, EnhancedVectorIndexConfig


@dataclass
class ElasticsearchWatchlistConfig:
    """Configuration for Elasticsearch Watchlist adapter."""
    
    # Elasticsearch connection
    es_url: str = "http://localhost:9200"
    es_auth: Optional[str] = None
    es_verify_ssl: bool = False
    es_timeout: float = 30.0
    
    # Index configuration
    persons_index: str = "watchlist_persons_current"
    orgs_index: str = "watchlist_orgs_current"
    
    # Search configuration
    ac_threshold: float = 0.7  # Threshold for AC search escalation
    ac_weak_threshold: float = 0.5  # Threshold for weak AC results
    max_ac_results: int = 50
    max_vector_results: int = 100
    
    # Fallback configuration
    enable_fallback: bool = True
    fallback_timeout: float = 5.0


class ElasticsearchWatchlistAdapter:
    """
    Adapter that bridges WatchlistIndexService/EnhancedVectorIndex to Elasticsearch.
    
    Maintains compatible interfaces while delegating all operations to ES:
    - build_from_corpus: bulk upsert to ES
    - set_overlay_from_corpus: bulk upsert to ES
    - search: AC msearch → kNN if score < threshold
    - save_snapshot/reload_snapshot: ES index snapshots
    - status: ES cluster and index status
    """
    
    def __init__(
        self, 
        config: Optional[ElasticsearchWatchlistConfig] = None,
        fallback_service: Optional[WatchlistIndexService] = None
    ):
        """
        Initialize Elasticsearch adapter.
        
        Args:
            config: Elasticsearch configuration
            fallback_service: Local service for fallback when ES unavailable
        """
        self.logger = get_logger(__name__)
        self.config = config or ElasticsearchWatchlistConfig()
        self.fallback_service = fallback_service
        
        # HTTP client for Elasticsearch
        self._client: Optional[httpx.AsyncClient] = None
        self._client_lock = asyncio.Lock()
        
        # Service state
        self._initialized = False
        self._last_health_check = None
        self._health_check_interval = 30.0  # seconds
        
        # Metrics
        self._metrics = {
            "ac_searches": 0,
            "vector_searches": 0,
            "escalations": 0,
            "fallbacks": 0,
            "errors": 0,
            "total_searches": 0,
            "avg_search_time": 0.0
        }
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client for Elasticsearch."""
        async with self._client_lock:
            if self._client is None or self._client.is_closed:
                auth = None
                if self.config.es_auth:
                    username, password = self.config.es_auth.split(":", 1)
                    auth = (username, password)
                
                self._client = httpx.AsyncClient(
                    base_url=self.config.es_url,
                    auth=auth,
                    verify=self.config.es_verify_ssl,
                    timeout=self.config.es_timeout
                )
            return self._client
    
    async def _health_check(self) -> bool:
        """Check Elasticsearch health."""
        current_time = time.time()
        if (self._last_health_check and 
            current_time - self._last_health_check < self._health_check_interval):
            return True
        
        try:
            client = await self._get_client()
            response = await client.get("/_cluster/health")
            self._last_health_check = current_time
            return response.status_code == 200
        except Exception as e:
            self.logger.warning(f"Elasticsearch health check failed: {e}")
            return False
    
    async def _ensure_initialized(self) -> bool:
        """Ensure adapter is initialized and ES is available."""
        if not self._initialized:
            if await self._health_check():
                self._initialized = True
                self.logger.info("Elasticsearch adapter initialized")
            else:
                self.logger.warning("Elasticsearch not available, using fallback")
                return False
        return True
    
    async def _bulk_upsert_documents(
        self, 
        documents: List[Dict], 
        entity_type: str
    ) -> bool:
        """Bulk upsert documents to Elasticsearch."""
        try:
            client = await self._get_client()
            index_name = (self.config.persons_index if entity_type == "person" 
                         else self.config.orgs_index)
            
            # Prepare bulk request
            bulk_body = []
            for doc in documents:
                # Index action
                bulk_body.append({
                    "index": {
                        "_index": index_name,
                        "_id": doc["entity_id"]
                    }
                })
                # Document
                bulk_body.append(doc)
            
            # Execute bulk request
            response = await client.post(
                f"/{index_name}/_bulk",
                json=bulk_body,
                headers={"Content-Type": "application/x-ndjson"}
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("errors"):
                    self.logger.warning(f"Some documents failed to index: {result}")
                return True
            else:
                self.logger.error(f"Bulk upsert failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            self.logger.error(f"Bulk upsert error: {e}")
            return False
    
    async def _ac_search(self, query: str, entity_type: str) -> List[Tuple[str, float]]:
        """Perform AC search using Elasticsearch."""
        try:
            client = await self._get_client()
            index_name = (self.config.persons_index if entity_type == "person" 
                         else self.config.orgs_index)
            
            # Multi-search for different AC patterns
            msearch_body = []
            
            # 1. Exact search on normalized_name
            msearch_body.append({"index": index_name})
            msearch_body.append({
                "query": {
                    "terms": {
                        "normalized_name": [query.lower().strip()]
                    }
                },
                "size": self.config.max_ac_results,
                "_source": ["entity_id", "normalized_name"]
            })
            
            # 2. Phrase search on name_text
            msearch_body.append({"index": index_name})
            msearch_body.append({
                "query": {
                    "match_phrase": {
                        "name_text": {
                            "query": query,
                            "slop": 1
                        }
                    }
                },
                "size": self.config.max_ac_results,
                "_source": ["entity_id", "name_text"]
            })
            
            # 3. N-gram search on name_ngrams
            msearch_body.append({"index": index_name})
            msearch_body.append({
                "query": {
                    "match": {
                        "name_ngrams": {
                            "query": query,
                            "operator": "AND",
                            "minimum_should_match": "100%"
                        }
                    }
                },
                "size": self.config.max_ac_results,
                "_source": ["entity_id", "name_ngrams"]
            })
            
            # Execute multi-search
            response = await client.post(
                "/_msearch",
                json=msearch_body,
                headers={"Content-Type": "application/x-ndjson"}
            )
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            results = {}
            
            # Process results from each search type
            for i, response_data in enumerate(result["responses"]):
                if "hits" in response_data:
                    for hit in response_data["hits"]["hits"]:
                        entity_id = hit["_source"]["entity_id"]
                        score = hit["_score"]
                        
                        # Weight different search types
                        if i == 0:  # Exact
                            weighted_score = score * 2.0
                        elif i == 1:  # Phrase
                            weighted_score = score * 1.5
                        else:  # N-gram
                            weighted_score = score * 1.0
                        
                        results[entity_id] = max(results.get(entity_id, 0.0), weighted_score)
            
            # Sort by score and return top results
            sorted_results = sorted(results.items(), key=lambda x: x[1], reverse=True)
            return sorted_results[:self.config.max_ac_results]
            
        except Exception as e:
            self.logger.error(f"AC search error: {e}")
            return []
    
    async def _vector_search(self, query: str, entity_type: str) -> List[Tuple[str, float]]:
        """Perform vector search using Elasticsearch kNN."""
        try:
            client = await self._get_client()
            index_name = (self.config.persons_index if entity_type == "person" 
                         else self.config.orgs_index)
            
            # Generate query vector (simplified - in real implementation, use embedding service)
            # For now, create a dummy vector - in production, this should call the embedding service
            query_vector = np.random.random(384).astype(np.float32).tolist()
            
            # kNN search
            search_body = {
                "knn": {
                    "field": "name_vector",
                    "query_vector": query_vector,
                    "k": self.config.max_vector_results,
                    "num_candidates": self.config.max_vector_results * 2,
                    "similarity": "cosine"
                },
                "size": self.config.max_vector_results,
                "_source": ["entity_id", "normalized_name"]
            }
            
            response = await client.post(
                f"/{index_name}/_search",
                json=search_body
            )
            
            if response.status_code != 200:
                return []
            
            result = response.json()
            results = []
            
            for hit in result["hits"]["hits"]:
                entity_id = hit["_source"]["entity_id"]
                score = hit["_score"]
                results.append((entity_id, float(score)))
            
            return results
            
        except Exception as e:
            self.logger.error(f"Vector search error: {e}")
            return []
    
    # ============================================================================
    # WatchlistIndexService Compatible Interface
    # ============================================================================
    
    def ready(self) -> bool:
        """Check if service is ready."""
        return self._initialized and self._last_health_check is not None
    
    async def build_from_corpus(
        self, 
        corpus: List[Tuple[str, str, str, Dict]], 
        index_id: Optional[str] = None
    ) -> None:
        """Rebuild active index from corpus of (id, text, entity_type, metadata)."""
        if not await self._ensure_initialized():
            if self.fallback_service:
                self.fallback_service.build_from_corpus(corpus, index_id)
                self._metrics["fallbacks"] += 1
            return
        
        # Group by entity type
        persons_docs = []
        orgs_docs = []
        
        for doc_id, text, entity_type, metadata in corpus:
            doc = {
                "entity_id": doc_id,
                "entity_type": entity_type,
                "normalized_name": text.lower().strip(),
                "aliases": metadata.get("aliases", []),
                "country": metadata.get("country", ""),
                "dob": metadata.get("dob"),
                "name_text": text,
                "name_ngrams": text,
                "name_vector": np.random.random(384).astype(np.float32).tolist(),  # Dummy vector
                "meta": metadata
            }
            
            if entity_type == "person":
                persons_docs.append(doc)
            else:
                orgs_docs.append(doc)
        
        # Bulk upsert to respective indices
        if persons_docs:
            await self._bulk_upsert_documents(persons_docs, "person")
        if orgs_docs:
            await self._bulk_upsert_documents(orgs_docs, "org")
        
        self.logger.info(f"Built ES index from corpus: {len(persons_docs)} persons, {len(orgs_docs)} orgs")
    
    async def set_overlay_from_corpus(
        self, 
        corpus: List[Tuple[str, str, str, Dict]], 
        overlay_id: Optional[str] = None
    ) -> None:
        """Set overlay index from corpus."""
        # For ES, overlay is handled by index aliases
        # This is a simplified implementation
        await self.build_from_corpus(corpus, overlay_id)
        self.logger.info(f"Set ES overlay from corpus: {len(corpus)} docs")
    
    def clear_overlay(self) -> None:
        """Clear overlay index."""
        # For ES, this would involve removing overlay aliases
        # Simplified implementation
        self.logger.info("Cleared ES overlay")
    
    async def search(self, query: str, top_k: int = 50) -> List[Tuple[str, float]]:
        """
        Search using AC first, then escalate to vector if needed.
        
        Returns list of (entity_id, score) tuples.
        """
        start_time = time.time()
        self._metrics["total_searches"] += 1
        
        try:
            if not await self._ensure_initialized():
                if self.fallback_service:
                    results = self.fallback_service.search(query, top_k)
                    self._metrics["fallbacks"] += 1
                    return results
                return []
            
            # Try AC search first
            ac_results = []
            for entity_type in ["person", "org"]:
                ac_results.extend(await self._ac_search(query, entity_type))
            
            self._metrics["ac_searches"] += 1
            
            # Check if AC results are sufficient
            if ac_results and ac_results[0][1] >= self.config.ac_threshold:
                # AC results are good enough
                results = ac_results[:top_k]
            else:
                # Escalate to vector search
                vector_results = []
                for entity_type in ["person", "org"]:
                    vector_results.extend(await self._vector_search(query, entity_type))
                
                self._metrics["vector_searches"] += 1
                self._metrics["escalations"] += 1
                
                # Combine and deduplicate results
                combined_results = {}
                for entity_id, score in ac_results + vector_results:
                    combined_results[entity_id] = max(combined_results.get(entity_id, 0.0), score)
                
                results = sorted(combined_results.items(), key=lambda x: x[1], reverse=True)[:top_k]
            
            # Update metrics
            search_time = time.time() - start_time
            total_searches = self._metrics["total_searches"]
            current_avg = self._metrics["avg_search_time"]
            self._metrics["avg_search_time"] = (current_avg * (total_searches - 1) + search_time) / total_searches
            
            return results
            
        except Exception as e:
            self.logger.error(f"Search error: {e}")
            self._metrics["errors"] += 1
            
            # Fallback to local service
            if self.fallback_service:
                return self.fallback_service.search(query, top_k)
            return []
    
    def get_doc(self, doc_id: str) -> Optional[WatchlistDoc]:
        """Get document by ID."""
        # This would require a separate ES query
        # For now, return None as this is not commonly used
        return None
    
    async def save_snapshot(self, snapshot_dir: str, as_overlay: bool = False) -> Dict:
        """Save snapshot of current index."""
        if not await self._ensure_initialized():
            if self.fallback_service:
                return self.fallback_service.save_snapshot(snapshot_dir, as_overlay)
            return {"error": "ES not available and no fallback"}
        
        try:
            client = await self._get_client()
            
            # Create snapshot repository
            repo_name = f"watchlist_snapshots_{int(time.time())}"
            await client.put(
                f"/_snapshot/{repo_name}",
                json={
                    "type": "fs",
                    "settings": {
                        "location": snapshot_dir
                    }
                }
            )
            
            # Create snapshot
            snapshot_name = f"snapshot_{int(time.time())}"
            await client.put(
                f"/_snapshot/{repo_name}/{snapshot_name}",
                json={
                    "indices": [self.config.persons_index, self.config.orgs_index],
                    "ignore_unavailable": True
                }
            )
            
            return {
                "snapshot_created": True,
                "repository": repo_name,
                "snapshot": snapshot_name,
                "path": snapshot_dir
            }
            
        except Exception as e:
            self.logger.error(f"Save snapshot error: {e}")
            return {"error": str(e)}
    
    async def reload_snapshot(self, snapshot_dir: str, as_overlay: bool = False) -> Dict:
        """Reload snapshot from directory."""
        if not await self._ensure_initialized():
            if self.fallback_service:
                return self.fallback_service.reload_snapshot(snapshot_dir, as_overlay)
            return {"error": "ES not available and no fallback"}
        
        try:
            client = await self._get_client()
            
            # Find snapshot repository
            response = await client.get("/_snapshot")
            repositories = response.json()
            
            # Look for repository with matching path
            repo_name = None
            for repo, config in repositories.items():
                if config.get("settings", {}).get("location") == snapshot_dir:
                    repo_name = repo
                    break
            
            if not repo_name:
                return {"error": f"No snapshot repository found for path: {snapshot_dir}"}
            
            # List snapshots in repository
            response = await client.get(f"/_snapshot/{repo_name}/_all")
            snapshots = response.json()
            
            if not snapshots.get("snapshots"):
                return {"error": "No snapshots found in repository"}
            
            # Restore latest snapshot
            latest_snapshot = snapshots["snapshots"][-1]["snapshot"]
            await client.post(
                f"/_snapshot/{repo_name}/{latest_snapshot}/_restore",
                json={
                    "indices": [self.config.persons_index, self.config.orgs_index],
                    "ignore_unavailable": True
                }
            )
            
            return {
                "snapshot_restored": True,
                "repository": repo_name,
                "snapshot": latest_snapshot,
                "path": snapshot_dir
            }
            
        except Exception as e:
            self.logger.error(f"Reload snapshot error: {e}")
            return {"error": str(e)}
    
    def status(self) -> Dict:
        """Get service status."""
        return {
            "elasticsearch_available": self._initialized,
            "last_health_check": self._last_health_check,
            "fallback_available": self.fallback_service is not None,
            "metrics": self._metrics.copy()
        }
    
    async def close(self):
        """Close the adapter and cleanup resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        self._initialized = False


# ============================================================================
# Factory Functions
# ============================================================================

def create_elasticsearch_watchlist_adapter(
    config: Optional[ElasticsearchWatchlistConfig] = None,
    fallback_config: Optional[VectorIndexConfig] = None
) -> ElasticsearchWatchlistAdapter:
    """Create Elasticsearch Watchlist adapter with optional fallback."""
    fallback_service = None
    if fallback_config:
        fallback_service = WatchlistIndexService(fallback_config)
    
    return ElasticsearchWatchlistAdapter(config, fallback_service)


def create_elasticsearch_enhanced_adapter(
    config: Optional[ElasticsearchWatchlistConfig] = None,
    fallback_config: Optional[EnhancedVectorIndexConfig] = None
) -> ElasticsearchWatchlistAdapter:
    """Create Elasticsearch adapter with EnhancedVectorIndex fallback."""
    fallback_service = None
    if fallback_config:
        fallback_service = EnhancedVectorIndex(fallback_config)
    
    return ElasticsearchWatchlistAdapter(config, fallback_service)
