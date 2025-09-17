"""Hybrid Search Service - combines AC (exact) and Vector (kNN) search modes."""

import asyncio
import json
import math
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
from .elasticsearch_client import ElasticsearchClientFactory
from ..embeddings.indexing.watchlist_index_service import WatchlistIndexService
from ..embeddings.indexing.enhanced_vector_index_service import EnhancedVectorIndex

try:  # Optional heavy dependency
    from ..embeddings.optimized_embedding_service import OptimizedEmbeddingService
except Exception:  # pragma: no cover - optional dependency may be unavailable
    OptimizedEmbeddingService = None  # type: ignore


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
        self.config = config or HybridSearchConfig.from_env()

        # Search adapters
        self._ac_adapter: Optional[ElasticsearchACAdapter] = None
        self._vector_adapter: Optional[ElasticsearchVectorAdapter] = None
        self._client_factory: Optional[ElasticsearchClientFactory] = None

        # Metrics tracking
        self._metrics = SearchMetrics()
        self._request_times: List[float] = []

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
    
    def _do_initialize(self) -> None:
        """Initialize search adapters and fallback services."""
        try:
            self._client_factory = ElasticsearchClientFactory(self.config)
            self._ac_adapter = ElasticsearchACAdapter(
                self.config,
                client_factory=self._client_factory,
            )
            self._vector_adapter = ElasticsearchVectorAdapter(
                self.config,
                client_factory=self._client_factory,
            )

            self._initialized = True
            self.logger.info("Hybrid search service initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize hybrid search service: {e}")
            raise

    async def _get_embedding_service(self):
        """Lazily initialize and return embedding service if available."""
        if self._embedding_service_checked:
            return self._embedding_service

        self._embedding_service_checked = True

        if OptimizedEmbeddingService is None:
            self.logger.warning("OptimizedEmbeddingService not available; using pseudo embeddings")
            self._embedding_service = None
            return None

        loop = asyncio.get_running_loop()

        def _init_service():
            return OptimizedEmbeddingService(
                enable_batch_optimization=True,
                enable_gpu=False,
                precompute_common_patterns=False,
            )

        try:
            self._embedding_service = await loop.run_in_executor(None, _init_service)
        except Exception as exc:  # pragma: no cover - depends on environment
            self.logger.warning(f"Failed to initialize embedding service: {exc}")
            self._embedding_service = None

        return self._embedding_service

    def _pseudo_embedding(self, text: str) -> List[float]:
        dimension = self.config.vector_search.vector_dimension
        if dimension <= 0:
            return []

        vector = [0.0] * dimension
        encoded = text.encode("utf-8")
        if not encoded:
            return vector

        for idx, byte in enumerate(encoded):
            position = (byte + idx) % dimension
            vector[position] += 1.0

        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    async def _build_query_vector(self, normalized: NormalizationResult, text: str) -> List[float]:
        query_text = normalized.normalized or text
        service = await self._get_embedding_service()
        if service is not None:
            loop = asyncio.get_running_loop()

            def _compute():
                return service.get_embeddings_optimized([query_text], batch_size=1, use_cache=True)

            try:
                result = await loop.run_in_executor(None, _compute)
                embeddings = result.get("embeddings") if isinstance(result, dict) else None
                if embeddings and embeddings[0]:
                    vector = list(embeddings[0])
                    dimension = self.config.vector_search.vector_dimension
                    if len(vector) > dimension:
                        vector = vector[:dimension]
                    elif len(vector) < dimension:
                        vector.extend([0.0] * (dimension - len(vector)))
                    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
                    return [v / norm for v in vector]
            except Exception as exc:  # pragma: no cover - depends on embedding runtime
                self.logger.warning(f"Embedding generation failed: {exc}")

        return self._pseudo_embedding(query_text)

    def _ensure_fallback_services(self) -> None:
        if not self.config.enable_fallback:
            return
        if self._fallback_watchlist_service is None:
            self._fallback_watchlist_service = WatchlistIndexService()
        if self._fallback_vector_service is None:
            self._fallback_vector_service = EnhancedVectorIndex()

    def _load_fusion_weights(self) -> Tuple[Dict[str, float], Dict[str, float]]:
        """Load fusion weights and boosts from configuration."""
        default_weights = {"ac": 0.6, "vector": 0.4}
        default_boosts = {
            "shared_hit_bonus": 0.1,
            "metadata_match_bonus": 0.05,
        }

        path_candidates = [
            Path("config/weights.json"),
            Path("weights.json"),
        ]

        for candidate in path_candidates:
            if candidate.exists():
                try:
                    with candidate.open("r", encoding="utf-8") as f:
                        data = json.load(f)
                    fusion = data.get("search_fusion", {})
                    weights = fusion.get("weights", {})
                    boosts = fusion.get("boosts", {})

                    if weights:
                        normalized = {**default_weights}
                        normalized.update(weights)
                        total = sum(normalized.values())
                        if total > 0:
                            normalized = {k: v / total for k, v in normalized.items()}
                        else:
                            normalized = default_weights
                        default_weights = normalized

                    if boosts:
                        merged_boosts = {**default_boosts}
                        merged_boosts.update(boosts)
                        default_boosts = merged_boosts
                except Exception as exc:
                    self.logger.warning(f"Failed to load fusion weights from {candidate}: {exc}")
                finally:
                    break

        return default_weights, default_boosts
    
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
            query_text = normalized.normalized or text
            candidates = await self._ac_adapter.search(
                query=query_text,
                opts=opts,
                index_name=self.config.elasticsearch.ac_index
            )
            if (
                not candidates
                and self.config.enable_fallback
                and not getattr(self._ac_adapter, "_connected", True)
            ):
                self.logger.warning("AC adapter unavailable – using fallback search")
                return await self._fallback_search(normalized, text, opts)

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
            query_vector = await self._build_query_vector(normalized, text)
            candidates = await self._vector_adapter.search(
                query=query_vector,
                opts=opts,
                index_name=self.config.elasticsearch.vector_index
            )
            if (
                not candidates
                and self.config.enable_fallback
                and not getattr(self._vector_adapter, "_connected", True)
            ):
                self.logger.warning("Vector adapter unavailable – using fallback search")
                return await self._fallback_search(normalized, text, opts)

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
        """Execute hybrid search with escalation and vector fallback."""
        self._metrics.hybrid_requests += 1
        
        # Step 1: Try AC search first
        ac_candidates = await self._ac_search_only(normalized, text, opts)
        
        # Check if AC results are sufficient
        if self._should_escalate(ac_candidates, opts):
            self.logger.info("AC results insufficient, escalating to vector search")
            self._metrics.escalation_triggered += 1
            
            # Step 2: Execute vector search
            vector_candidates = await self._vector_search_only(normalized, text, opts)
            
            # Step 3: Check if vector fallback is needed
            if self._should_use_vector_fallback(ac_candidates, vector_candidates, opts):
                self.logger.info("Using vector fallback for better results")
                fallback_candidates = await self._vector_fallback_search(normalized, text, opts)
                
                # Combine all results
                all_candidates = self._combine_results(ac_candidates, vector_candidates, opts)
                all_candidates.extend(fallback_candidates)
                
                # Remove duplicates and rerank
                all_candidates = self._deduplicate_and_rerank(all_candidates, opts)
                
                return all_candidates
            else:
                # Step 4: Combine and deduplicate results
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

    def _should_use_vector_fallback(
        self, 
        ac_candidates: List[Candidate], 
        vector_candidates: List[Candidate], 
        opts: SearchOpts
    ) -> bool:
        """Determine if vector fallback should be used."""
        if not getattr(self.config, 'enable_vector_fallback', True):
            return False
        
        # If no AC results at all, use fallback
        if not ac_candidates:
            return True
        
        # If AC results are very weak, use fallback
        best_ac_score = max(candidate.score for candidate in ac_candidates)
        if best_ac_score < 0.3:  # Very low confidence
            return True
        
        # If vector results are significantly better, use fallback
        if vector_candidates:
            best_vector_score = max(candidate.score for candidate in vector_candidates)
            if best_vector_score > best_ac_score * 1.5:  # 50% better
                return True
        
        return False

    async def _vector_fallback_search(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Execute vector fallback search with kNN + BM25."""
        try:
            # Build query vector
            query_vector = await self._build_query_vector(normalized, text)
            
            # Use vector adapter's fallback search
            fallback_candidates = await self._vector_adapter.search_vector_fallback(
                query_vector=query_vector,
                query_text=text,
                opts=opts
            )
            
            # Apply RapidFuzz reranking if enabled
            if getattr(self.config, 'enable_rapidfuzz_rerank', True):
                fallback_candidates = self._apply_rapidfuzz_reranking(fallback_candidates, text)
            
            # Apply DoB/ID anchor checking if enabled
            if getattr(self.config, 'enable_dob_id_anchors', True):
                fallback_candidates = self._apply_anchor_boost(fallback_candidates, text)
            
            return fallback_candidates
            
        except Exception as e:
            self.logger.error(f"Vector fallback search failed: {e}")
            return []

    def _apply_rapidfuzz_reranking(
        self, 
        candidates: List[Candidate], 
        query_text: str
    ) -> List[Candidate]:
        """Apply RapidFuzz reranking to vector fallback results."""
        try:
            from rapidfuzz import fuzz
            
            for candidate in candidates:
                if hasattr(candidate, 'trace') and candidate.trace:
                    # Calculate string similarity
                    text = candidate.text.lower()
                    query = query_text.lower()
                    
                    # Use different fuzz algorithms for better matching
                    ratio = fuzz.ratio(query, text)
                    partial_ratio = fuzz.partial_ratio(query, text)
                    token_sort_ratio = fuzz.token_sort_ratio(query, text)
                    
                    # Use the best score
                    fuzz_score = max(ratio, partial_ratio, token_sort_ratio)
                    
                    # Update trace
                    candidate.trace["fuzz"] = fuzz_score
                    
                    # Boost score based on string similarity
                    if fuzz_score > 80:
                        candidate.score *= 1.2  # 20% boost for high similarity
                    elif fuzz_score > 60:
                        candidate.score *= 1.1  # 10% boost for medium similarity
            
            # Sort by updated scores
            candidates.sort(key=lambda c: c.score, reverse=True)
            
        except ImportError:
            self.logger.warning("RapidFuzz not available, skipping reranking")
        except Exception as e:
            self.logger.error(f"RapidFuzz reranking failed: {e}")
        
        return candidates

    def _apply_anchor_boost(
        self, 
        candidates: List[Candidate], 
        query_text: str
    ) -> List[Candidate]:
        """Apply DoB/ID anchor boost to vector fallback results."""
        import re
        
        # Extract DoB patterns from query
        dob_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b\d{2}\.\d{2}\.\d{4}\b',  # DD.MM.YYYY
            r'\b\d{2}/\d{2}/\d{4}\b',  # DD/MM/YYYY
        ]
        
        # Extract ID patterns from query
        id_patterns = [
            r'\bpassport\s*\d+\b',
            r'\bID\s*\d+\b',
            r'\b№\s*\d+\b',
            r'\b[A-Z]{2}\d{6}\b',  # Passport format
        ]
        
        query_dobs = []
        query_ids = []
        
        for pattern in dob_patterns:
            query_dobs.extend(re.findall(pattern, query_text))
        
        for pattern in id_patterns:
            query_ids.extend(re.findall(pattern, query_text))
        
        for candidate in candidates:
            if hasattr(candidate, 'trace') and candidate.trace:
                anchor_matches = []
                
                # Check DoB anchors
                if query_dobs and candidate.metadata.get('dob'):
                    candidate_dob = candidate.metadata['dob']
                    for query_dob in query_dobs:
                        if query_dob in candidate_dob or candidate_dob in query_dob:
                            anchor_matches.append("dob_anchor")
                            candidate.score *= 1.3  # 30% boost for DoB match
                            break
                
                # Check ID anchors
                if query_ids and candidate.metadata.get('doc_id'):
                    candidate_id = candidate.metadata['doc_id']
                    for query_id in query_ids:
                        if query_id in candidate_id or candidate_id in query_id:
                            anchor_matches.append("id_anchor")
                            candidate.score *= 1.2  # 20% boost for ID match
                            break
                
                # Update trace
                candidate.trace["anchors"] = anchor_matches
        
        return candidates

    def _deduplicate_and_rerank(
        self, 
        candidates: List[Candidate], 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Deduplicate and rerank combined results."""
        if not candidates:
            return []
        
        # Deduplicate by doc_id
        seen_docs = set()
        deduplicated = []
        
        for candidate in candidates:
            if candidate.doc_id not in seen_docs:
                seen_docs.add(candidate.doc_id)
                deduplicated.append(candidate)
        
        # Sort by score
        deduplicated.sort(key=lambda c: c.score, reverse=True)
        
        return deduplicated[:opts.top_k]
    
    def _combine_results(
        self, 
        ac_candidates: List[Candidate], 
        vector_candidates: List[Candidate], 
        opts: SearchOpts
    ) -> List[Candidate]:
        """Combine and deduplicate results from AC and vector search."""
        ac_weight = self._fusion_weights.get("ac", 0.6)
        vector_weight = self._fusion_weights.get("vector", 0.4)

        combined: Dict[str, Candidate] = {}

        for candidate in ac_candidates:
            weighted_score = candidate.score * ac_weight
            combined[candidate.doc_id] = Candidate(
                doc_id=candidate.doc_id,
                score=weighted_score,
                text=candidate.text,
                entity_type=candidate.entity_type,
                metadata=dict(candidate.metadata),
                search_mode=SearchMode.AC,
                match_fields=list(candidate.match_fields),
                confidence=candidate.confidence,
            )

        for candidate in vector_candidates:
            weighted_score = candidate.score * vector_weight
            if candidate.doc_id in combined:
                existing = combined[candidate.doc_id]
                merged_metadata = {**candidate.metadata, **existing.metadata}
                merged_fields = sorted(set(existing.match_fields + candidate.match_fields))
                combined_score = (
                    existing.score
                    + weighted_score
                    + self._fusion_boosts.get("shared_hit_bonus", 0.0)
                )
                combined[candidate.doc_id] = Candidate(
                    doc_id=candidate.doc_id,
                    score=combined_score,
                    text=existing.text or candidate.text,
                    entity_type=existing.entity_type or candidate.entity_type,
                    metadata=merged_metadata,
                    search_mode=SearchMode.HYBRID,
                    match_fields=merged_fields,
                    confidence=max(existing.confidence, candidate.confidence),
                )
            else:
                combined[candidate.doc_id] = Candidate(
                    doc_id=candidate.doc_id,
                    score=weighted_score,
                    text=candidate.text,
                    entity_type=candidate.entity_type,
                    metadata=dict(candidate.metadata),
                    search_mode=SearchMode.VECTOR,
                    match_fields=list(candidate.match_fields),
                    confidence=candidate.confidence,
                )

        metadata_filters = opts.metadata_filters or {}
        metadata_bonus = self._fusion_boosts.get("metadata_match_bonus", 0.0)
        if metadata_filters and metadata_bonus:
            for candidate in combined.values():
                if self._matches_metadata_filters(candidate, metadata_filters):
                    candidate.score += metadata_bonus

        results = list(combined.values())
        results.sort(key=lambda c: c.score, reverse=True)

        if self.config.enable_deduplication:
            deduped: Dict[str, Candidate] = {}
            for candidate in results:
                if candidate.doc_id not in deduped:
                    deduped[candidate.doc_id] = candidate
            results = list(deduped.values())

        return results[:opts.top_k]
    
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
        
        # Process AC pattern hits - mark as should_process=True and apply boosts
        for candidate in filtered_candidates:
            if hasattr(candidate, 'should_process') and candidate.should_process:
                # AC pattern hit - apply additional processing
                if hasattr(candidate, 'trace') and candidate.trace:
                    tier = candidate.trace.get('tier', 0)
                    if tier == 0:
                        # T0: Exact document ID - highest priority
                        candidate.score *= 1.5
                    elif tier == 1:
                        # T1: Full name with context - high priority
                        candidate.score *= 1.2
            
            # Process vector fallback hits
            if hasattr(candidate, 'trace') and candidate.trace:
                reason = candidate.trace.get('reason', '')
                if reason == 'vector_fallback':
                    # Apply vector fallback specific processing
                    cosine_sim = candidate.trace.get('cosine', 0.0)
                    fuzz_score = candidate.trace.get('fuzz', 0)
                    anchors = candidate.trace.get('anchors', [])
                    
                    # Boost based on cosine similarity
                    if cosine_sim > 0.7:
                        candidate.score *= 1.3  # High similarity boost
                    elif cosine_sim > 0.5:
                        candidate.score *= 1.1  # Medium similarity boost
                    
                    # Additional boost for anchor matches
                    if 'dob_anchor' in anchors:
                        candidate.score *= 1.2
                    if 'id_anchor' in anchors:
                        candidate.score *= 1.1
        
        return filtered_candidates
    
    def _matches_metadata_filters(self, candidate: Candidate, filters: Dict[str, Any]) -> bool:
        """Check if candidate matches metadata filters."""
        for key, value in filters.items():
            candidate_value = None
            if key in {"country", "country_code"}:
                candidate_value = (
                    candidate.metadata.get("country")
                    or candidate.metadata.get("country_code")
                )
            elif key in {"dob", "date_of_birth"}:
                candidate_value = (
                    candidate.metadata.get("dob")
                    or candidate.metadata.get("date_of_birth")
                )
            elif key in {"id", "doc_id"}:
                candidate_value = candidate.doc_id
            elif key == "entity_id":
                candidate_value = candidate.metadata.get("entity_id") or candidate.doc_id
            else:
                candidate_value = candidate.metadata.get(key)

            if isinstance(value, list):
                if candidate_value not in value:
                    return False
            else:
                if candidate_value != value:
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
        if not self.config.enable_fallback:
            return []

        self._ensure_fallback_services()

        fallback_results: List[Candidate] = []
        query_text = normalized.normalized or text

        if self._fallback_watchlist_service and self._fallback_watchlist_service.ready():
            ac_hits = self._fallback_watchlist_service.search(query_text, top_k=opts.top_k)
            for doc_id, score in ac_hits:
                doc = self._fallback_watchlist_service.get_doc(doc_id)
                if not doc:
                    continue
                fallback_results.append(
                    Candidate(
                        doc_id=doc_id,
                        score=float(score),
                        text=doc.text,
                        entity_type=doc.entity_type,
                        metadata=doc.metadata,
                        search_mode=SearchMode.FALLBACK_AC,
                        match_fields=["fallback_ac"],
                        confidence=min(1.0, float(score)),
                    )
                )

        if not fallback_results and self._fallback_vector_service:
            vector_hits = self._fallback_vector_service.search(query_text, top_k=opts.top_k)
            for doc_id, score in vector_hits:
                doc = None
                if self._fallback_watchlist_service:
                    doc = self._fallback_watchlist_service.get_doc(doc_id)
                fallback_results.append(
                    Candidate(
                        doc_id=doc_id,
                        score=float(score),
                        text=doc.text if doc else query_text,
                        entity_type=doc.entity_type if doc else "unknown",
                        metadata=doc.metadata if doc else {},
                        search_mode=SearchMode.FALLBACK_VECTOR,
                        match_fields=["fallback_vector"],
                        confidence=min(1.0, float(score)),
                    )
                )

        return fallback_results
    
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
            health_status["fallback_enabled"] = self.config.enable_fallback

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
