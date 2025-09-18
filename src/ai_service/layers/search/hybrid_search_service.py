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
from ...contracts.trace_models import SearchTrace, SearchTraceHit, SearchTraceStep
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
        self._ac_request_times: List[float] = []
        self._vector_request_times: List[float] = []

        # Fallback services
        self._fallback_watchlist_service: Optional[WatchlistIndexService] = None
        self._fallback_vector_service: Optional[EnhancedVectorIndex] = None

        # Service state
        self._initialized = False
        self._last_health_check = None

        # Embedding service for vector queries (lazy init)
        self._embedding_service = None
        self._embedding_service_checked = False
        
        # Embedding cache
        self._embedding_cache: Dict[str, Tuple[List[float], datetime]] = {}
        self._cache_lock = asyncio.Lock()

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

            # Start hot-reloading if supported
            if hasattr(self.config, 'start_hot_reload'):
                try:
                    # Watch for changes in environment variables
                    from pathlib import Path
                    watch_paths = [Path(".env"), Path("config/settings.py")]
                    asyncio.create_task(self.config.start_hot_reload(watch_paths))
                    self.logger.info("Hot-reloading enabled for search configuration")
                except Exception as e:
                    self.logger.warning(f"Failed to enable hot-reloading: {e}")

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
        processed_text = self._preprocess_query_for_embedding(query_text)
        
        # Check cache first
        cached_vector = await self._get_cached_embedding(processed_text)
        if cached_vector is not None:
            self.logger.debug(f"Using cached embedding for: {processed_text[:50]}...")
            return cached_vector
        
        service = await self._get_embedding_service()
        if service is not None:
            loop = asyncio.get_running_loop()

            def _compute():
                return service.get_embeddings_optimized(
                    [processed_text], 
                    batch_size=self.config.embedding_batch_size, 
                    use_cache=True
                )

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
                    normalized_vector = [v / norm for v in vector]
                    
                    # Cache the result
                    await self._cache_embedding(processed_text, normalized_vector)
                    self.logger.debug(f"Generated and cached embedding for: {processed_text[:50]}...")
                    
                    return normalized_vector
            except Exception as exc:  # pragma: no cover - depends on embedding runtime
                self.logger.warning(f"Embedding generation failed: {exc}")

        # Fallback to pseudo embedding
        pseudo_vector = self._pseudo_embedding(processed_text)
        await self._cache_embedding(processed_text, pseudo_vector)
        return pseudo_vector

    async def _get_cached_embedding(self, text: str) -> Optional[List[float]]:
        """Get cached embedding if available and not expired."""
        if not self.config.enable_embedding_cache:
            return None
            
        async with self._cache_lock:
            if text in self._embedding_cache:
                vector, timestamp = self._embedding_cache[text]
                age_seconds = (datetime.now() - timestamp).total_seconds()
                if age_seconds < self.config.embedding_cache_ttl_seconds:
                    return vector
                else:
                    # Remove expired entry
                    del self._embedding_cache[text]
        return None

    async def _cache_embedding(self, text: str, vector: List[float]) -> None:
        """Cache embedding with TTL."""
        if not self.config.enable_embedding_cache:
            return
            
        async with self._cache_lock:
            # Remove oldest entries if cache is full
            if len(self._embedding_cache) >= self.config.embedding_cache_size:
                # Remove oldest entry
                oldest_key = min(self._embedding_cache.keys(), 
                               key=lambda k: self._embedding_cache[k][1])
                del self._embedding_cache[oldest_key]
            
            self._embedding_cache[text] = (vector, datetime.now())

    def _preprocess_query_for_embedding(self, text: str) -> str:
        """Preprocess query text for better embedding generation."""
        if not self.config.enable_embedding_preprocessing:
            return text
            
        # Basic preprocessing: normalize whitespace, remove extra punctuation
        import re
        processed = re.sub(r'\s+', ' ', text.strip())
        processed = re.sub(r'[^\w\s\-\.]', '', processed)
        return processed

    def _ensure_fallback_services(self) -> None:
        """Initialize fallback services with proper error handling."""
        if not self.config.enable_fallback:
            return
            
        try:
            if self._fallback_watchlist_service is None:
                self._fallback_watchlist_service = WatchlistIndexService()
                self.logger.debug("Initialized WatchlistIndexService fallback")
                
            if self._fallback_vector_service is None:
                self._fallback_vector_service = EnhancedVectorIndex()
                self.logger.debug("Initialized EnhancedVectorIndex fallback")
                
        except Exception as exc:
            self.logger.error(f"Failed to initialize fallback services: {exc}")
            # Don't raise - fallback should be graceful

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
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
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
        
        # Create dummy trace if none provided
        if search_trace is None:
            search_trace = SearchTrace(enabled=False)
        
        start_time = time.time()
        self._metrics.total_requests += 1
        
        try:
            # Determine search strategy based on options
            if opts.search_mode == SearchMode.AC:
                candidates = await self._ac_search_only(normalized, text, opts, search_trace)
            elif opts.search_mode == SearchMode.VECTOR:
                candidates = await self._vector_search_only(normalized, text, opts, search_trace)
            else:  # HYBRID mode
                candidates = await self._hybrid_search(normalized, text, opts, search_trace)
            
            # Process and rank results
            candidates = self._process_results(candidates, opts)
            
            # Limit payload size to prevent excessive memory usage
            search_trace.limit_payload_size(max_size_kb=200)
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            avg_score = sum(c.score for c in candidates) / len(candidates) if candidates else 0.0
            self._update_metrics(True, processing_time, len(candidates), avg_score)
            
            self.logger.info(
                f"Search completed: {len(candidates)} candidates found in {processing_time:.2f}ms"
            )
            
            return candidates
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._update_metrics(False, processing_time, 0)
            
            self.logger.error(f"Search failed: {e}")

            # Fallback to local indexes when Elasticsearch is unavailable
            return await self._fallback_search(normalized, text, opts, search_trace)
    
    async def _ac_search_only(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
    ) -> List[Candidate]:
        """Execute AC search only."""
        self._metrics.ac_requests += 1

        # Create dummy trace if none provided
        if search_trace is None:
            search_trace = SearchTrace(enabled=False)

        try:
            query_text = normalized.normalized or text
            start_time = time.perf_counter()
            
            candidates = await self._ac_adapter.search(
                query=query_text,
                opts=opts,
                index_name=self.config.elasticsearch.ac_index
            )

            search_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

            # Update AC-specific metrics
            self._update_ac_metrics(search_time, len(candidates))

            # Convert candidates to SearchTraceHit
            ac_hits = []
            for rank, candidate in enumerate(candidates, 1):
                signals = {
                    'dob_match': self._check_dob_match(candidate.metadata, query_text),
                    'doc_id_match': self._check_doc_id_match(candidate.doc_id, query_text),
                    'entity_type': candidate.entity_type,
                    'match_fields': candidate.match_fields,
                    'confidence': candidate.confidence
                }
                
                hit = SearchTraceHit(
                    doc_id=candidate.doc_id,
                    score=candidate.score,
                    rank=rank,
                    source="AC",
                    signals=signals
                )
                ac_hits.append(hit)
            
            # Add AC search step to trace
            search_trace.add_step(SearchTraceStep(
                stage="AC",
                query=query_text,
                topk=opts.top_k,
                took_ms=search_time,
                hits=ac_hits,
                meta={
                    "index_name": self.config.elasticsearch.ac_index,
                    "search_mode": "exact",
                    "fallback_enabled": self.config.enable_fallback,
                    "adapter_connected": getattr(self._ac_adapter, "_connected", True)
                }
            ))
            
            if (
                not candidates
                and self.config.enable_fallback
                and not getattr(self._ac_adapter, "_connected", True)
            ):
                self.logger.warning("AC adapter unavailable – using fallback search")
                return await self._fallback_search(normalized, text, opts, search_trace)

            return candidates

        except Exception as e:
            self.logger.error(f"AC search failed: {e}")
            search_trace.note(f"AC search failed: {str(e)}")
            return []

    async def _vector_search_only(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
    ) -> List[Candidate]:
        """Execute vector search only."""
        self._metrics.vector_requests += 1

        # Create dummy trace if none provided
        if search_trace is None:
            search_trace = SearchTrace(enabled=False)

        try:
            query_text = normalized.normalized or text
            start_time = time.perf_counter()
            
            query_vector = await self._build_query_vector(normalized, text)
            candidates = await self._vector_adapter.search(
                query=query_vector,
                opts=opts,
                index_name=self.config.elasticsearch.vector_index
            )
            
            search_time = (time.perf_counter() - start_time) * 1000  # Convert to ms

            # Update Vector-specific metrics
            self._update_vector_metrics(search_time, len(candidates))

            # Convert candidates to SearchTraceHit
            vector_hits = []
            for rank, candidate in enumerate(candidates, 1):
                signals = {
                    'dob_match': self._check_dob_match(candidate.metadata, query_text),
                    'doc_id_match': self._check_doc_id_match(candidate.doc_id, query_text),
                    'entity_type': candidate.entity_type,
                    'match_fields': candidate.match_fields,
                    'confidence': candidate.confidence,
                    'vector_similarity': candidate.score
                }
                
                hit = SearchTraceHit(
                    doc_id=candidate.doc_id,
                    score=candidate.score,
                    rank=rank,
                    source="SEMANTIC",
                    signals=signals
                )
                vector_hits.append(hit)
            
            # Add vector search step to trace
            search_trace.add_step(SearchTraceStep(
                stage="SEMANTIC",
                query=query_text,
                topk=opts.top_k,
                took_ms=search_time,
                hits=vector_hits,
                meta={
                    "index_name": self.config.elasticsearch.vector_index,
                    "search_mode": "vector_similarity",
                    "fallback_enabled": self.config.enable_fallback,
                    "adapter_connected": getattr(self._vector_adapter, "_connected", True),
                    "embedding_model": getattr(self._embedding_service, 'model_name', 'unknown')
                }
            ))
            
            if (
                not candidates
                and self.config.enable_fallback
                and not getattr(self._vector_adapter, "_connected", True)
            ):
                self.logger.warning("Vector adapter unavailable – using fallback search")
                return await self._fallback_search(normalized, text, opts, search_trace)

            return candidates

        except Exception as e:
            self.logger.error(f"Vector search failed: {e}")
            search_trace.note(f"Vector search failed: {str(e)}")
            return []
    
    async def _hybrid_search(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
    ) -> List[Candidate]:
        """Execute hybrid search with escalation and vector fallback."""
        self._metrics.hybrid_requests += 1
        
        # Create dummy trace if none provided
        if search_trace is None:
            search_trace = SearchTrace(enabled=False)
        
        query_text = normalized.normalized or text
        hybrid_start_time = time.perf_counter()
        
        # Step 1: Try AC search first
        ac_candidates = await self._ac_search_only(normalized, text, opts, search_trace)
        
        # Check if AC results are sufficient
        if self._should_escalate(ac_candidates, opts):
            self.logger.info("AC results insufficient, escalating to vector search")
            self._metrics.escalation_triggered += 1
            
            # Step 2: Execute vector search
            vector_candidates = await self._vector_search_only(normalized, text, opts, search_trace)
            
            # Step 3: Check if vector fallback is needed
            if self._should_use_vector_fallback(ac_candidates, vector_candidates, opts):
                self.logger.info("Using vector fallback for better results")
                fallback_candidates = await self._vector_fallback_search(normalized, text, opts, search_trace)
                
                # Combine all results
                all_candidates = self._combine_results(ac_candidates, vector_candidates, opts)
                all_candidates.extend(fallback_candidates)
                
                # Remove duplicates and rerank
                all_candidates = self._deduplicate_and_rerank(all_candidates, opts)
                
                # Add hybrid step to trace
                hybrid_time = (time.perf_counter() - hybrid_start_time) * 1000
                self._add_hybrid_trace_step(search_trace, query_text, opts, all_candidates, hybrid_time, {
                    "escalation_triggered": True,
                    "vector_fallback_used": True,
                    "ac_candidates": len(ac_candidates),
                    "vector_candidates": len(vector_candidates),
                    "fallback_candidates": len(fallback_candidates),
                    "final_candidates": len(all_candidates)
                })
                
                return all_candidates
            else:
                # Step 4: Combine and deduplicate results
                all_candidates = self._combine_results(ac_candidates, vector_candidates, opts)
                
                # Add hybrid step to trace
                hybrid_time = (time.perf_counter() - hybrid_start_time) * 1000
                self._add_hybrid_trace_step(search_trace, query_text, opts, all_candidates, hybrid_time, {
                    "escalation_triggered": True,
                    "vector_fallback_used": False,
                    "ac_candidates": len(ac_candidates),
                    "vector_candidates": len(vector_candidates),
                    "final_candidates": len(all_candidates)
                })
                
                return all_candidates
        else:
            # Add hybrid step to trace (AC only)
            hybrid_time = (time.perf_counter() - hybrid_start_time) * 1000
            self._add_hybrid_trace_step(search_trace, query_text, opts, ac_candidates, hybrid_time, {
                "escalation_triggered": False,
                "vector_fallback_used": False,
                "ac_candidates": len(ac_candidates),
                "vector_candidates": 0,
                "final_candidates": len(ac_candidates)
            })
            
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
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
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
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
    ) -> List[Candidate]:
        """Fallback to local indexes when Elasticsearch is unavailable."""
        self.logger.warning("Using fallback search due to Elasticsearch unavailability")
        if not self.config.enable_fallback:
            return []

        self._ensure_fallback_services()

        fallback_results: List[Candidate] = []
        query_text = normalized.normalized or text
        max_results = min(opts.top_k, self.config.fallback_max_results)

        # AC fallback search
        if self._fallback_watchlist_service and self._fallback_watchlist_service.ready():
            try:
                ac_hits = self._fallback_watchlist_service.search(
                    query_text, 
                    top_k=max_results, 
                    trace=search_trace
                )
                for doc_id, score in ac_hits:
                    if len(fallback_results) >= max_results:
                        break
                        
                    doc = self._fallback_watchlist_service.get_doc(doc_id, trace=search_trace)
                    if not doc:
                        continue
                        
                    # Apply fallback threshold
                    if float(score) < self.config.fallback_threshold:
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
                            trace={
                                "reason": "fallback_ac",
                                "service": "WatchlistIndexService",
                                "threshold": self.config.fallback_threshold
                            }
                        )
                    )
            except Exception as exc:
                self.logger.error(f"AC fallback search failed: {exc}")

        # Vector fallback search if AC didn't provide enough results
        if (len(fallback_results) < max_results and 
            self._fallback_vector_service and 
            self.config.enable_vector_fallback):
            try:
                remaining_results = min(
                    max_results - len(fallback_results),
                    self.config.vector_fallback_max_results
                )
                vector_hits = self._fallback_vector_service.search(
                    query_text, 
                    top_k=remaining_results
                )
                for doc_id, score in vector_hits:
                    if len(fallback_results) >= max_results:
                        break
                        
                    # Apply vector-specific fallback threshold
                    if float(score) < self.config.vector_fallback_threshold:
                        continue
                        
                    doc = None
                    if self._fallback_watchlist_service:
                        doc = self._fallback_watchlist_service.get_doc(doc_id, trace=search_trace)
                        
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
                            trace={
                                "reason": "fallback_vector",
                                "service": "EnhancedVectorIndex",
                                "threshold": self.config.vector_fallback_threshold,
                                "max_results": self.config.vector_fallback_max_results
                            }
                        )
                    )
            except Exception as exc:
                self.logger.error(f"Vector fallback search failed: {exc}")

        self.logger.info(f"Fallback search returned {len(fallback_results)} results")
        return fallback_results
    
    async def _check_fallback_health(self) -> Dict[str, Any]:
        """Check health status of fallback services."""
        health = {
            "watchlist_service": {"available": False, "ready": False, "error": None},
            "vector_service": {"available": False, "ready": False, "error": None},
            "vector_fallback_enabled": self.config.enable_vector_fallback,
            "vector_fallback_config": {
                "threshold": self.config.vector_fallback_threshold,
                "max_results": self.config.vector_fallback_max_results,
                "timeout_ms": self.config.vector_fallback_timeout_ms
            }
        }
        
        if not self.config.enable_fallback_health_check:
            return health
            
        # Check WatchlistIndexService
        if self._fallback_watchlist_service:
            try:
                health["watchlist_service"]["available"] = True
                health["watchlist_service"]["ready"] = self._fallback_watchlist_service.ready()
            except Exception as exc:
                health["watchlist_service"]["error"] = str(exc)
        
        # Check EnhancedVectorIndex
        if self._fallback_vector_service:
            try:
                health["vector_service"]["available"] = True
                # EnhancedVectorIndex doesn't have a ready() method, so we assume it's ready if available
                health["vector_service"]["ready"] = True
            except Exception as exc:
                health["vector_service"]["error"] = str(exc)
        
        return health
    
    async def clear_embedding_cache(self) -> None:
        """Clear the embedding cache."""
        async with self._cache_lock:
            self._embedding_cache.clear()
        self.logger.info("Embedding cache cleared")
    
    async def get_embedding_cache_stats(self) -> Dict[str, Any]:
        """Get embedding cache statistics."""
        async with self._cache_lock:
            cache_size = len(self._embedding_cache)
            max_size = self.config.embedding_cache_size
            ttl_seconds = self.config.embedding_cache_ttl_seconds
            
            # Calculate cache age statistics
            now = datetime.now()
            ages = []
            for _, (_, timestamp) in self._embedding_cache.items():
                age = (now - timestamp).total_seconds()
                ages.append(age)
            
            avg_age = sum(ages) / len(ages) if ages else 0
            max_age = max(ages) if ages else 0
            
            return {
                "cache_size": cache_size,
                "max_size": max_size,
                "utilization": cache_size / max_size if max_size > 0 else 0,
                "ttl_seconds": ttl_seconds,
                "avg_age_seconds": avg_age,
                "max_age_seconds": max_age,
                "cache_enabled": self.config.enable_embedding_cache
            }
    
    def _update_metrics(self, success: bool, processing_time_ms: float, result_count: int, avg_score: float = 0.0) -> None:
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

        # Update result quality metrics
        self._metrics.avg_results_per_request = (
            (self._metrics.avg_results_per_request * (self._metrics.total_requests - 1) + result_count)
            / self._metrics.total_requests
        )

        # Update average score
        if result_count > 0:
            self._metrics.avg_score = (
                (self._metrics.avg_score * (self._metrics.total_requests - 1) + avg_score)
                / self._metrics.total_requests
            )
        
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

    def _update_ac_metrics(self, processing_time_ms: float, result_count: int) -> None:
        """Update AC-specific search metrics."""
        # Update AC latency tracking
        self._ac_request_times.append(processing_time_ms)
        if len(self._ac_request_times) > self.config.metrics_window_size:
            self._ac_request_times.pop(0)

        # Calculate average AC latency
        if self._ac_request_times:
            self._metrics.avg_ac_latency_ms = sum(self._ac_request_times) / len(self._ac_request_times)

        # Update AC hit rate
        if result_count > 0:
            self._metrics.ac_hit_rate = (
                (self._metrics.ac_hit_rate * (self._metrics.ac_requests - 1) + 1.0)
                / self._metrics.ac_requests
            )
        else:
            self._metrics.ac_hit_rate = (
                (self._metrics.ac_hit_rate * (self._metrics.ac_requests - 1) + 0.0)
                / self._metrics.ac_requests
            )

    def _update_vector_metrics(self, processing_time_ms: float, result_count: int) -> None:
        """Update Vector-specific search metrics."""
        # Update Vector latency tracking
        self._vector_request_times.append(processing_time_ms)
        if len(self._vector_request_times) > self.config.metrics_window_size:
            self._vector_request_times.pop(0)

        # Calculate average Vector latency
        if self._vector_request_times:
            self._metrics.avg_vector_latency_ms = sum(self._vector_request_times) / len(self._vector_request_times)

        # Update Vector hit rate
        if result_count > 0:
            self._metrics.vector_hit_rate = (
                (self._metrics.vector_hit_rate * (self._metrics.vector_requests - 1) + 1.0)
                / self._metrics.vector_requests
            )
        else:
            self._metrics.vector_hit_rate = (
                (self._metrics.vector_hit_rate * (self._metrics.vector_requests - 1) + 0.0)
                / self._metrics.vector_requests
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
            if self.config.enable_fallback:
                fallback_health = await self._check_fallback_health()
                health_status["fallback_services"] = fallback_health
            
            # Add embedding cache information
            health_status["embedding_cache"] = await self.get_embedding_cache_stats()

        except Exception as e:
            health_status["status"] = "unhealthy"
            health_status["error"] = str(e)
            self.logger.error(f"Health check failed: {e}")
        
        self._last_health_check = health_status
        return health_status
    
    def get_metrics(self) -> SearchMetrics:
        """Get current search metrics."""
        return self._metrics

    def get_comprehensive_metrics(self) -> Dict[str, Any]:
        """Get comprehensive metrics including adapter-specific stats."""
        base_metrics = self._metrics.to_dict()

        # Add adapter-specific latency stats
        comprehensive = {
            **base_metrics,
            "adapter_stats": {},
            "request_counts": {
                "total": self._metrics.total_requests,
                "ac_only": self._metrics.ac_requests,
                "vector_only": self._metrics.vector_requests,
                "hybrid": self._metrics.hybrid_requests,
                "escalations": self._metrics.escalation_triggered
            }
        }

        # Get AC adapter stats
        if self._ac_adapter and hasattr(self._ac_adapter, 'get_latency_stats'):
            try:
                comprehensive["adapter_stats"]["ac"] = self._ac_adapter.get_latency_stats()
            except Exception as e:
                self.logger.warning(f"Failed to get AC adapter stats: {e}")

        # Get Vector adapter stats
        if self._vector_adapter and hasattr(self._vector_adapter, 'get_latency_stats'):
            try:
                comprehensive["adapter_stats"]["vector"] = self._vector_adapter.get_latency_stats()
            except Exception as e:
                self.logger.warning(f"Failed to get Vector adapter stats: {e}")

        return comprehensive
    
    def reset_metrics(self) -> None:
        """Reset search metrics."""
        self._metrics = SearchMetrics()
        self._request_times.clear()
        self._ac_request_times.clear()
        self._vector_request_times.clear()
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
    
    def _add_hybrid_trace_step(
        self, 
        search_trace: SearchTrace, 
        query: str, 
        opts: SearchOpts, 
        candidates: List[Candidate], 
        took_ms: float, 
        meta: Dict[str, Any]
    ) -> None:
        """Add hybrid search step to trace."""
        # Convert candidates to SearchTraceHit
        hybrid_hits = []
        for rank, candidate in enumerate(candidates, 1):
            signals = {
                'dob_match': self._check_dob_match(candidate.metadata, query),
                'doc_id_match': self._check_doc_id_match(candidate.doc_id, query),
                'entity_type': candidate.entity_type,
                'match_fields': candidate.match_fields,
                'confidence': candidate.confidence,
                'search_mode': candidate.search_mode.value
            }
            
            hit = SearchTraceHit(
                doc_id=candidate.doc_id,
                score=candidate.score,
                rank=rank,
                source="HYBRID",
                signals=signals
            )
            hybrid_hits.append(hit)
        
        # Add hybrid step to trace
        search_trace.add_step(SearchTraceStep(
            stage="HYBRID",
            query=query,
            topk=opts.top_k,
            took_ms=took_ms,
            hits=hybrid_hits,
            meta=meta
        ))
    
    def _check_dob_match(self, metadata: Dict[str, Any], query: str) -> bool:
        """Check if date of birth matches query."""
        if not metadata or not query:
            return False
        
        dob = metadata.get('dob')
        if not dob:
            return False
        
        query_lower = query.lower()
        dob_lower = str(dob).lower()
        
        # Check for year match
        if len(str(dob)) >= 4 and len(query) >= 4:
            dob_year = str(dob)[-4:] if str(dob)[-4:].isdigit() else ""
            query_year = "".join([c for c in query if c.isdigit()])
            if dob_year and query_year and dob_year in query_year:
                return True
        
        return dob_lower in query_lower or query_lower in dob_lower
    
    def _check_doc_id_match(self, doc_id: str, query: str) -> bool:
        """Check if document ID matches query."""
        if not doc_id or not query:
            return False
        
        query_lower = query.lower()
        doc_id_lower = doc_id.lower()
        
        return doc_id_lower in query_lower or query_lower in doc_id_lower
    
    async def update_configuration(self, new_config: HybridSearchConfig) -> None:
        """Update search service configuration with validation."""
        self.logger.info("Updating search service configuration...")
        
        try:
            # Validate new configuration before applying
            self._validate_configuration(new_config)
            
            # Update configuration
            old_config = self.config
            self.config = new_config
            
            # Reinitialize adapters with new configuration
            if self._client_factory:
                self._client_factory = ElasticsearchClientFactory(self.config)
                self._ac_adapter = ElasticsearchACAdapter(
                    self.config,
                    client_factory=self._client_factory,
                )
                self._vector_adapter = ElasticsearchVectorAdapter(
                    self.config,
                    client_factory=self._client_factory,
                )
            
            # Update fallback services if needed
            self._ensure_fallback_services()
            
            # Clear embedding cache if cache settings changed
            if (old_config.enable_embedding_cache != new_config.enable_embedding_cache or
                old_config.embedding_cache_size != new_config.embedding_cache_size or
                old_config.embedding_cache_ttl_seconds != new_config.embedding_cache_ttl_seconds):
                await self.clear_embedding_cache()
                self.logger.info("Embedding cache cleared due to configuration changes")
            
            self.logger.info("Search service configuration updated successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to update search service configuration: {e}")
            # Revert to old configuration
            self.config = old_config
            raise
    
    def _validate_configuration(self, config: HybridSearchConfig) -> None:
        """Validate configuration before applying."""
        try:
            # Use Pydantic validation
            config.validate(config)
            
            # Additional runtime validation
            if config.es_hosts:
                # Test host format
                for host in config.es_hosts:
                    if ':' not in host:
                        raise ValueError(f"Invalid host format: {host}")
                    
                    host_part, port_part = host.split(':', 1)
                    if not host_part or not port_part:
                        raise ValueError(f"Invalid host:port format: {host}")
                    
                    try:
                        port = int(port_part)
                        if not (1 <= port <= 65535):
                            raise ValueError(f"Invalid port: {port}")
                    except ValueError:
                        raise ValueError(f"Invalid port number: {port_part}")
            
            # Validate thresholds
            if config.enable_escalation and config.escalation_threshold <= 0.5:
                raise ValueError("Escalation threshold should be greater than 0.5")
            
            if config.enable_fallback and config.fallback_threshold <= 0.1:
                raise ValueError("Fallback threshold should be greater than 0.1")
            
            if config.vector_similarity_threshold <= 0.3:
                raise ValueError("Vector similarity threshold should be greater than 0.3")
            
            # Validate cache settings
            if config.enable_embedding_cache and config.embedding_cache_size < 100:
                raise ValueError("Embedding cache size should be at least 100")
            
            self.logger.info("Configuration validation passed")
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            raise ValueError(f"Invalid configuration: {e}")
