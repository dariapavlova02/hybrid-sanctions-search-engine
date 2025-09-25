"""Hybrid Search Service - combines AC (exact) and Vector (kNN) search modes."""

import asyncio
import json
import math
import time
from datetime import datetime, timedelta
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
from .fuzzy_search_service import FuzzySearchService, FuzzyConfig
from .sanctions_data_loader import SanctionsDataLoader
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

        # Fuzzy search service for typo handling
        fuzzy_config = FuzzyConfig(
            min_score_threshold=0.5,   # Lower threshold for better fuzzy coverage
            high_confidence_threshold=0.80,
            partial_match_threshold=0.70,
            enable_name_fuzzy=True,
            name_boost_factor=1.2
        )
        self._fuzzy_service = FuzzySearchService(fuzzy_config)
        self._fuzzy_candidates_cache: Dict[str, List[str]] = {}  # Cache for candidates

        # Sanctions data loader for fuzzy candidates
        self._sanctions_loader = SanctionsDataLoader()
        self._sanctions_loaded = False

        # Force reload sanctions in production if needed
        import os
        if os.getenv("FORCE_RELOAD_SANCTIONS", "false").lower() == "true":
            self.logger.warning("🔄 FORCE_RELOAD_SANCTIONS=true, will force reload sanctions data")

        # Embedding cache
        self._embedding_cache: Dict[str, Tuple[List[float], datetime]] = {}
        self._cache_lock = asyncio.Lock()
        
        # Search result cache
        self._search_cache: Dict[str, Tuple[List[Candidate], datetime]] = {}
        self._search_cache_lock = asyncio.Lock()
        
        # Query performance monitoring
        self._query_performance: List[Dict[str, Any]] = []
        self._performance_lock = asyncio.Lock()
        
        # Query caching
        self._query_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}
        self._query_cache_lock = asyncio.Lock()
        
        # Rate limiting
        self._rate_limiter: Dict[str, List[datetime]] = {}
        self._rate_limit_lock = asyncio.Lock()

        # Fusion weights/boosts
        self._fusion_weights, self._fusion_boosts = self._load_fusion_weights()
    
    def _do_initialize(self) -> None:
        """Initialize search adapters and fallback services."""
        try:
            # Try to initialize Elasticsearch components
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
                self.logger.info("✅ Elasticsearch adapters initialized successfully")
            except Exception as es_e:
                self.logger.warning(f"⚠️ Failed to initialize Elasticsearch adapters: {es_e}")
                self.logger.info("📝 Will use fallback services for search")
                # Don't raise - continue with fallback services

            # Initialize fallback services (always try these)
            try:
                self._ensure_fallback_services()
                self.logger.info("✅ Fallback services initialized")
            except Exception as fallback_e:
                self.logger.warning(f"⚠️ Failed to initialize fallback services: {fallback_e}")

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
            self.logger.info("✅ Hybrid search service initialized successfully (with available components)")

        except Exception as e:
            self.logger.error(f"❌ Failed to initialize hybrid search service: {e}")
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
        # Validate search mode (no modification needed)

        if not self._initialized:
            self.initialize()

        # Create dummy trace if none provided
        if search_trace is None:
            search_trace = SearchTrace(enabled=False)
        
        start_time = time.time()
        self._metrics.total_requests += 1
        
        # Validate and sanitize query
        text = self._validate_query(text)
        
        # Check rate limit
        client_id = getattr(opts, 'client_id', 'default')
        if not await self._check_rate_limit(client_id):
            raise Exception("Rate limit exceeded")
        
        # Structured logging for search operation
        search_log_data = {
            "operation": "find_candidates",
            "query": text,
            "normalized_text": normalized.normalized_text,
            "search_mode": opts.search_mode,
            "top_k": opts.top_k,
            "threshold": opts.threshold,
            "timestamp": datetime.now().isoformat(),
            "language": normalized.language,
            "confidence": normalized.confidence,
            "client_id": client_id
        }
        
        # Check cache first
        cache_key = self._generate_search_cache_key(text, opts)
        cached_candidates = await self._get_cached_search_result(cache_key)
        
        if cached_candidates is not None:
            # Return cached results
            search_log_data.update({
                "status": "cache_hit",
                "processing_time_ms": 0,
                "result_count": len(cached_candidates),
                "avg_score": sum(c.score for c in cached_candidates) / len(cached_candidates) if cached_candidates else 0.0,
                "search_modes_used": ["cache"]
            })
            self.logger.info("Search completed from cache", extra=search_log_data)
            
            # Record performance for cache hit
            await self._record_query_performance(
                query=text,
                search_mode=opts.search_mode,
                processing_time_ms=0,
                result_count=len(cached_candidates),
                cache_hit=True
            )
            
            return cached_candidates
        
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
            
            # Filter sensitive data
            candidates = self._filter_sensitive_data(candidates)
            
            # Limit payload size to prevent excessive memory usage
            search_trace.limit_payload_size(max_size_kb=200)
            
            # Update metrics
            processing_time = (time.time() - start_time) * 1000  # Convert to ms
            avg_score = sum(c.score for c in candidates) / len(candidates) if candidates else 0.0
            self._update_metrics(True, processing_time, len(candidates), avg_score)
            
            # Cache search results
            await self._cache_search_result(cache_key, candidates)
            
            # Record query performance
            await self._record_query_performance(
                query=text,
                search_mode=opts.search_mode,
                processing_time_ms=processing_time,
                result_count=len(candidates),
                cache_hit=False
            )
            
            # Log successful search
            search_log_data.update({
                "status": "success",
                "processing_time_ms": processing_time,
                "result_count": len(candidates),
                "avg_score": avg_score,
                "search_modes_used": [opts.search_mode]
            })
            self.logger.info("Search completed successfully", extra=search_log_data)
            
            # Log audit event
            self._log_audit_event("search_success", text, len(candidates), client_id)
            
            self.logger.info(
                f"Search completed: {len(candidates)} candidates found in {processing_time:.2f}ms"
            )

            print(f"🎯 find_candidates RESULT: {len(candidates)} candidates, {processing_time:.2f}ms")
            return candidates
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            self._update_metrics(False, processing_time, 0)
            
            # Log failed search
            search_log_data.update({
                "status": "error",
                "processing_time_ms": processing_time,
                "error": str(e),
                "error_type": type(e).__name__
            })
            self.logger.error("Search failed", extra=search_log_data)

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
        start_time = time.time()

        # Create dummy trace if none provided
        if search_trace is None:
            search_trace = SearchTrace(enabled=False)
        
        # Performance logging for AC search
        ac_log_data = {
            "operation": "ac_search",
            "query": text,
            "normalized_text": normalized.normalized_text,
            "top_k": opts.top_k,
            "threshold": opts.threshold,
            "timestamp": datetime.now().isoformat()
        }

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

            # Log AC search results
            ac_log_data.update({
                "status": "success",
                "processing_time_ms": search_time,
                "result_count": len(candidates),
                "avg_score": sum(c.score for c in candidates) / len(candidates) if candidates else 0.0
            })
            self.logger.info("AC search completed", extra=ac_log_data)

            return candidates

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            ac_log_data.update({
                "status": "error",
                "processing_time_ms": processing_time,
                "error": str(e),
                "error_type": type(e).__name__
            })
            self.logger.error("AC search failed", extra=ac_log_data)
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
        start_time = time.time()

        # Create dummy trace if none provided
        if search_trace is None:
            search_trace = SearchTrace(enabled=False)

        # Performance logging for vector search
        vector_log_data = {
            "operation": "vector_search",
            "query": text,
            "normalized_text": normalized.normalized_text,
            "top_k": opts.top_k,
            "threshold": opts.threshold,
            "timestamp": datetime.now().isoformat()
        }

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

            # Log vector search results
            vector_log_data.update({
                "status": "success",
                "processing_time_ms": search_time,
                "result_count": len(candidates),
                "avg_score": sum(c.score for c in candidates) / len(candidates) if candidates else 0.0
            })
            self.logger.info("Vector search completed", extra=vector_log_data)

            return candidates

        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            vector_log_data.update({
                "status": "error",
                "processing_time_ms": processing_time,
                "error": str(e),
                "error_type": type(e).__name__
            })
            self.logger.error("Vector search failed", extra=vector_log_data)
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
        ac_start_time = time.perf_counter()
        ac_candidates = await self._ac_search_only(normalized, text, opts, search_trace)
        ac_time = (time.perf_counter() - ac_start_time) * 1000

        # Add AC trace step
        ac_best_score = max((c.score for c in ac_candidates), default=0.0)
        search_trace.add_step(SearchTraceStep(
            stage="AC",
            query=query_text,
            topk=opts.top_k,
            took_ms=ac_time,
            hits=[SearchTraceHit(doc_id=c.doc_id, score=c.score, rank=i+1, source="AC")
                  for i, c in enumerate(ac_candidates[:10])],
            meta={
                "threshold": opts.threshold,
                "best_score": ac_best_score,
                "total_hits": len(ac_candidates)
            }
        ))

        # Check if AC results are sufficient
        should_escalate = self._should_escalate(ac_candidates, opts)
        print(f"🔥 ESCALATION DEBUG: ac_count={len(ac_candidates)}, should_escalate={should_escalate}, threshold={opts.escalation_threshold}")
        if should_escalate:
            print(f"🚀 ESCALATING: AC results insufficient, trying fuzzy search first")
            self.logger.info("AC results insufficient, trying fuzzy search first")
            self._metrics.escalation_triggered += 1

            # Step 2: Try fuzzy search before vector search
            fuzzy_start_time = time.perf_counter()
            fuzzy_candidates = await self._fuzzy_search(query_text, opts, search_trace)
            fuzzy_time = (time.perf_counter() - fuzzy_start_time) * 1000

            # Add fuzzy trace step
            fuzzy_best_score = max((c.score for c in fuzzy_candidates), default=0.0)
            search_trace.add_step(SearchTraceStep(
                stage="LEXICAL",  # Fuzzy is lexical search
                query=query_text,
                topk=opts.top_k,
                took_ms=fuzzy_time,
                hits=[SearchTraceHit(doc_id=c.doc_id, score=c.score, rank=i+1, source="LEXICAL")
                      for i, c in enumerate(fuzzy_candidates[:10])],
                meta={
                    "search_type": "fuzzy",
                    "best_score": fuzzy_best_score,
                    "total_hits": len(fuzzy_candidates),
                    "escalation_triggered": True
                }
            ))

            # Check if fuzzy results are good enough
            print(f"📊 CHECKING FUZZY SUFFICIENCY: {len(fuzzy_candidates)} candidates")
            if fuzzy_candidates:
                best_fuzzy_score = max(c.score for c in fuzzy_candidates)
                print(f"   Best fuzzy score: {best_fuzzy_score:.3f}")
                print(f"   High confidence threshold: {self._fuzzy_service.config.high_confidence_threshold}")
                print(f"   Min threshold: {self._fuzzy_service.config.min_score_threshold}")

            is_sufficient = self._fuzzy_results_sufficient(fuzzy_candidates, opts)
            print(f"   Is sufficient: {is_sufficient}")

            if is_sufficient:
                print("✅ FUZZY RESULTS SUFFICIENT - returning fuzzy results")
                self.logger.info(f"Fuzzy search found {len(fuzzy_candidates)} good matches - skipping vector search")
                # Combine AC and fuzzy results
                print(f"🔗 COMBINING RESULTS: ac={len(ac_candidates)}, fuzzy={len(fuzzy_candidates)}")
                all_candidates = self._combine_results(ac_candidates, fuzzy_candidates, opts)
                print(f"   Combined result: {len(all_candidates)} candidates")

                # Add hybrid step to trace
                hybrid_time = (time.perf_counter() - hybrid_start_time) * 1000
                self._add_hybrid_trace_step(search_trace, query_text, opts, all_candidates, hybrid_time, {
                    "escalation_triggered": True,
                    "fuzzy_search_used": True,
                    "vector_search_skipped": True,
                    "ac_candidates": len(ac_candidates),
                    "fuzzy_candidates": len(fuzzy_candidates),
                    "final_candidates": len(all_candidates)
                })

                return all_candidates
            else:
                self.logger.info("Fuzzy search insufficient, escalating to vector search")

            # Step 3: Execute vector search (fuzzy wasn't sufficient)
            vector_start_time = time.perf_counter()
            vector_candidates = await self._vector_search_only(normalized, text, opts, search_trace)
            vector_time = (time.perf_counter() - vector_start_time) * 1000

            # Add vector trace step
            vector_best_score = max((c.score for c in vector_candidates), default=0.0)
            search_trace.add_step(SearchTraceStep(
                stage="SEMANTIC",  # Vector is semantic search
                query=query_text,
                topk=opts.top_k,
                took_ms=vector_time,
                hits=[SearchTraceHit(doc_id=c.doc_id, score=c.score, rank=i+1, source="SEMANTIC")
                      for i, c in enumerate(vector_candidates[:10])],
                meta={
                    "search_type": "vector",
                    "best_score": vector_best_score,
                    "total_hits": len(vector_candidates),
                    "fuzzy_insufficient": True
                }
            ))

            # Combine all three result sets
            all_candidates = self._combine_results(ac_candidates, fuzzy_candidates, opts)
            all_candidates = self._combine_results(all_candidates, vector_candidates, opts)
            
            # Step 4: Check if vector fallback is needed
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
                    "fuzzy_search_used": True,
                    "vector_fallback_used": True,
                    "ac_candidates": len(ac_candidates),
                    "fuzzy_candidates": len(fuzzy_candidates),
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
                    "fuzzy_search_used": True,
                    "vector_fallback_used": False,
                    "ac_candidates": len(ac_candidates),
                    "fuzzy_candidates": len(fuzzy_candidates),
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
        self.logger.info(f"Checking escalation: enable={opts.enable_escalation}, ac_count={len(ac_candidates)}, threshold={opts.escalation_threshold}")

        if not opts.enable_escalation:
            self.logger.info("Escalation disabled in SearchOpts")
            return False

        if not ac_candidates:
            self.logger.info("No AC candidates found - escalating to fuzzy/vector search")
            return True

        # Check if best AC score is below escalation threshold
        best_score = max(candidate.score for candidate in ac_candidates)
        escalate = best_score < opts.escalation_threshold
        self.logger.info(f"AC best score: {best_score:.3f}, threshold: {opts.escalation_threshold:.3f}, escalate: {escalate}")
        return escalate

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
        print(f"📊 _combine_results INPUT: ac={len(ac_candidates)}, vector={len(vector_candidates)}")

        ac_weight = self._fusion_weights.get("ac", 0.6)
        vector_weight = self._fusion_weights.get("vector", 0.4)

        # If we have only vector/fuzzy candidates, don't degrade their scores
        if not ac_candidates and vector_candidates:
            vector_weight = 1.0
            print(f"   No AC candidates - using full vector weight: {vector_weight}")
        else:
            print(f"   Weights: ac={ac_weight}, vector={vector_weight}")

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

        final_results = results[:opts.top_k]
        print(f"📊 _combine_results OUTPUT: {len(final_results)} candidates")
        if final_results:
            for i, candidate in enumerate(final_results[:3]):
                print(f"   {i+1}. {candidate.text} (score: {candidate.score:.3f})")

        return final_results
    
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
    
    async def _get_cached_search_result(self, cache_key: str) -> Optional[List[Candidate]]:
        """Get cached search result if available and not expired."""
        if not self.config.enable_search_cache:
            return None
            
        async with self._search_cache_lock:
            if cache_key in self._search_cache:
                candidates, timestamp = self._search_cache[cache_key]
                
                # Check if cache entry is expired
                age_seconds = (datetime.now() - timestamp).total_seconds()
                if age_seconds < self.config.search_cache_ttl_seconds:
                    self.logger.debug(f"Cache hit for search key: {cache_key[:20]}...")
                    return candidates
                else:
                    # Remove expired entry
                    del self._search_cache[cache_key]
                    self.logger.debug(f"Cache expired for search key: {cache_key[:20]}...")
            
            return None
    
    async def _cache_search_result(self, cache_key: str, candidates: List[Candidate]) -> None:
        """Cache search result."""
        if not self.config.enable_search_cache:
            return
            
        async with self._search_cache_lock:
            # Check cache size limit
            if len(self._search_cache) >= self.config.search_cache_size:
                # Remove oldest entry
                oldest_key = min(self._search_cache.keys(), 
                               key=lambda k: self._search_cache[k][1])
                del self._search_cache[oldest_key]
                self.logger.debug(f"Cache evicted oldest entry: {oldest_key[:20]}...")
            
            self._search_cache[cache_key] = (candidates, datetime.now())
            self.logger.debug(f"Cached search result for key: {cache_key[:20]}...")
    
    def _generate_search_cache_key(self, query: str, opts: SearchOpts) -> str:
        """Generate cache key for search query."""
        import hashlib
        
        # Create a hash of the query and options
        key_data = {
            "query": query,
            "search_mode": opts.search_mode,
            "top_k": opts.top_k,
            "threshold": opts.threshold,
            "ac_boost": opts.ac_boost,
            "vector_boost": opts.vector_boost,
            "entity_types": opts.entity_types,
            "metadata_filters": opts.metadata_filters
        }
        
        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def clear_search_cache(self) -> None:
        """Clear the search result cache."""
        async with self._search_cache_lock:
            self._search_cache.clear()
            self.logger.info("Search result cache cleared")
    
    async def invalidate_search_cache(self, pattern: Optional[str] = None) -> int:
        """Invalidate search cache entries matching pattern or all if None."""
        async with self._search_cache_lock:
            if pattern is None:
                # Clear all cache
                count = len(self._search_cache)
                self._search_cache.clear()
                self.logger.info(f"Invalidated all {count} search cache entries")
                return count
            else:
                # Remove entries matching pattern
                keys_to_remove = [key for key in self._search_cache.keys() if pattern in key]
                for key in keys_to_remove:
                    del self._search_cache[key]
                self.logger.info(f"Invalidated {len(keys_to_remove)} search cache entries matching pattern: {pattern}")
                return len(keys_to_remove)
    
    async def cleanup_expired_cache_entries(self) -> int:
        """Clean up expired cache entries."""
        now = datetime.now()
        expired_count = 0
        
        async with self._search_cache_lock:
            keys_to_remove = []
            for key, (_, timestamp) in self._search_cache.items():
                age_seconds = (now - timestamp).total_seconds()
                if age_seconds >= self.config.search_cache_ttl_seconds:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._search_cache[key]
                expired_count += 1
            
            if expired_count > 0:
                self.logger.info(f"Cleaned up {expired_count} expired search cache entries")
        
        return expired_count
    
    async def _record_query_performance(self, query: str, search_mode: str, processing_time_ms: float, result_count: int, cache_hit: bool = False) -> None:
        """Record query performance metrics."""
        async with self._performance_lock:
            performance_record = {
                "timestamp": datetime.now().isoformat(),
                "query": query[:100],  # Truncate long queries
                "search_mode": search_mode,
                "processing_time_ms": processing_time_ms,
                "result_count": result_count,
                "cache_hit": cache_hit
            }
            
            self._query_performance.append(performance_record)
            
            # Keep only last 1000 records to prevent memory issues
            if len(self._query_performance) > 1000:
                self._query_performance = self._query_performance[-1000:]
    
    async def get_query_performance_stats(self) -> Dict[str, Any]:
        """Get query performance statistics."""
        async with self._performance_lock:
            if not self._query_performance:
                return {
                    "total_queries": 0,
                    "avg_processing_time_ms": 0,
                    "avg_result_count": 0,
                    "cache_hit_rate": 0,
                    "search_mode_distribution": {}
                }
            
            # Calculate statistics
            processing_times = [record["processing_time_ms"] for record in self._query_performance]
            result_counts = [record["result_count"] for record in self._query_performance]
            cache_hits = [record["cache_hit"] for record in self._query_performance]
            search_modes = [record["search_mode"] for record in self._query_performance]
            
            # Calculate averages
            avg_processing_time = sum(processing_times) / len(processing_times)
            avg_result_count = sum(result_counts) / len(result_counts)
            cache_hit_rate = sum(cache_hits) / len(cache_hits) if cache_hits else 0
            
            # Search mode distribution
            mode_distribution = {}
            for mode in search_modes:
                mode_distribution[mode] = mode_distribution.get(mode, 0) + 1
            
            return {
                "total_queries": len(self._query_performance),
                "avg_processing_time_ms": avg_processing_time,
                "avg_result_count": avg_result_count,
                "cache_hit_rate": cache_hit_rate,
                "search_mode_distribution": mode_distribution,
                "min_processing_time_ms": min(processing_times),
                "max_processing_time_ms": max(processing_times),
                "min_result_count": min(result_counts),
                "max_result_count": max(result_counts)
            }
    
    async def clear_query_performance(self) -> None:
        """Clear query performance records."""
        async with self._performance_lock:
            self._query_performance.clear()
            self.logger.info("Query performance records cleared")
    
    async def _get_cached_query(self, query_key: str) -> Optional[Dict[str, Any]]:
        """Get cached query if available and not expired."""
        if not self.config.enable_query_caching:
            return None
            
        async with self._query_cache_lock:
            if query_key in self._query_cache:
                query_data, timestamp = self._query_cache[query_key]
                
                # Check if cache entry is expired
                age_seconds = (datetime.now() - timestamp).total_seconds()
                if age_seconds < self.config.query_cache_ttl_seconds:
                    self.logger.debug(f"Query cache hit for key: {query_key[:20]}...")
                    return query_data
                else:
                    # Remove expired entry
                    del self._query_cache[query_key]
                    self.logger.debug(f"Query cache expired for key: {query_key[:20]}...")
            
            return None
    
    async def _cache_query(self, query_key: str, query_data: Dict[str, Any]) -> None:
        """Cache query data."""
        if not self.config.enable_query_caching:
            return
            
        async with self._query_cache_lock:
            # Check cache size limit
            if len(self._query_cache) >= self.config.query_cache_size:
                # Remove oldest entry
                oldest_key = min(self._query_cache.keys(), 
                               key=lambda k: self._query_cache[k][1])
                del self._query_cache[oldest_key]
                self.logger.debug(f"Query cache evicted oldest entry: {oldest_key[:20]}...")
            
            self._query_cache[query_key] = (query_data, datetime.now())
            self.logger.debug(f"Cached query data for key: {query_key[:20]}...")
    
    def _generate_query_cache_key(self, query: str, search_mode: str) -> str:
        """Generate cache key for query data."""
        import hashlib
        
        key_data = {
            "query": query,
            "search_mode": search_mode
        }
        
        key_string = str(sorted(key_data.items()))
        return hashlib.md5(key_string.encode()).hexdigest()
    
    async def clear_query_cache(self) -> None:
        """Clear the query cache."""
        async with self._query_cache_lock:
            self._query_cache.clear()
            self.logger.info("Query cache cleared")
    
    async def get_query_cache_stats(self) -> Dict[str, Any]:
        """Get query cache statistics."""
        async with self._query_cache_lock:
            if not self._query_cache:
                return {
                    "cache_size": 0,
                    "cache_enabled": self.config.enable_query_caching,
                    "max_cache_size": self.config.query_cache_size,
                    "cache_ttl_seconds": self.config.query_cache_ttl_seconds
                }
            
            now = datetime.now()
            ages = [(now - timestamp).total_seconds() for _, (_, timestamp) in self._query_cache.items()]
            
            return {
                "cache_size": len(self._query_cache),
                "cache_enabled": self.config.enable_query_caching,
                "max_cache_size": self.config.query_cache_size,
                "cache_ttl_seconds": self.config.query_cache_ttl_seconds,
                "avg_age_seconds": sum(ages) / len(ages) if ages else 0,
                "max_age_seconds": max(ages) if ages else 0,
                "min_age_seconds": min(ages) if ages else 0
            }
    
    def _validate_query(self, query: str) -> str:
        """Validate and sanitize search query."""
        if not self.config.enable_query_validation:
            return query
        
        # Remove potentially dangerous characters
        import re
        sanitized = re.sub(r'[<>"\']', '', query)
        
        # Limit query length
        max_length = 1000
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
            self.logger.warning(f"Query truncated to {max_length} characters")
        
        # Check for SQL injection patterns
        sql_patterns = [
            r'(union|select|insert|update|delete|drop|create|alter)\s+',
            r'(or|and)\s+\d+\s*=\s*\d+',
            r';\s*(drop|delete|insert|update)',
            r'--\s*',
            r'/\*.*?\*/'
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                self.logger.warning(f"Potential SQL injection pattern detected in query: {pattern}")
                sanitized = re.sub(pattern, '', sanitized, flags=re.IGNORECASE)
        
        return sanitized.strip()
    
    async def _check_rate_limit(self, client_id: str = "default") -> bool:
        """Check if client has exceeded rate limit."""
        if not self.config.enable_rate_limiting:
            return True
        
        now = datetime.now()
        minute_ago = now - timedelta(minutes=1)
        
        async with self._rate_limit_lock:
            if client_id not in self._rate_limiter:
                self._rate_limiter[client_id] = []
            
            # Remove old requests
            self._rate_limiter[client_id] = [
                req_time for req_time in self._rate_limiter[client_id]
                if req_time > minute_ago
            ]
            
            # Check if limit exceeded
            if len(self._rate_limiter[client_id]) >= self.config.rate_limit_requests_per_minute:
                return False
            
            # Add current request
            self._rate_limiter[client_id].append(now)
            return True
    
    def _filter_sensitive_data(self, candidates: List[Candidate]) -> List[Candidate]:
        """Filter sensitive data from search results."""
        if not self.config.enable_sensitive_data_filtering:
            return candidates
        
        filtered_candidates = []
        for candidate in candidates:
            # Create a copy to avoid modifying original
            filtered_candidate = Candidate(
                doc_id=candidate.doc_id,
                score=candidate.score,
                text=candidate.text,
                entity_type=candidate.entity_type,
                metadata=candidate.metadata.copy() if candidate.metadata else {},
                search_mode=candidate.search_mode,
                match_fields=candidate.match_fields,
                confidence=candidate.confidence
            )
            
            # Remove sensitive fields from metadata
            sensitive_fields = ['ssn', 'passport', 'credit_card', 'bank_account', 'phone', 'email']
            for field in sensitive_fields:
                if field in filtered_candidate.metadata:
                    filtered_candidate.metadata[field] = "***"
            
            filtered_candidates.append(filtered_candidate)
        
        return filtered_candidates
    
    def _log_audit_event(self, event_type: str, query: str, result_count: int, client_id: str = "default") -> None:
        """Log audit event for security monitoring."""
        if not self.config.enable_audit_logging:
            return
        
        audit_data = {
            "event_type": event_type,
            "query": query[:100],  # Truncate for privacy
            "result_count": result_count,
            "client_id": client_id,
            "timestamp": datetime.now().isoformat(),
            "service": "hybrid_search"
        }
        
        self.logger.info("Audit event", extra=audit_data)
    
    async def get_search_cache_stats(self) -> Dict[str, Any]:
        """Get search cache statistics."""
        async with self._search_cache_lock:
            if not self._search_cache:
                return {
                    "cache_size": 0,
                    "cache_enabled": self.config.enable_search_cache,
                    "max_cache_size": self.config.search_cache_size,
                    "cache_ttl_seconds": self.config.search_cache_ttl_seconds
                }
            
            now = datetime.now()
            ages = [(now - timestamp).total_seconds() for _, (_, timestamp) in self._search_cache.items()]
            
            return {
                "cache_size": len(self._search_cache),
                "cache_enabled": self.config.enable_search_cache,
                "max_cache_size": self.config.search_cache_size,
                "cache_ttl_seconds": self.config.search_cache_ttl_seconds,
                "avg_age_seconds": sum(ages) / len(ages) if ages else 0,
                "max_age_seconds": max(ages) if ages else 0,
                "min_age_seconds": min(ages) if ages else 0
            }
    
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
            
            # Update metrics service if available
            if hasattr(self, 'metrics_service') and self.metrics_service:
                try:
                    # Record search metrics
                    self.metrics_service.record_metric(
                        name="search_requests_total",
                        value=1,
                        metric_type="counter",
                        tags={"status": "success" if success else "failed"}
                    )
                    
                    self.metrics_service.record_metric(
                        name="search_latency_ms",
                        value=processing_time_ms,
                        metric_type="histogram",
                        tags={"operation": "hybrid_search"}
                    )
                    
                    self.metrics_service.record_metric(
                        name="search_results_count",
                        value=result_count,
                        metric_type="histogram",
                        tags={"operation": "hybrid_search"}
                    )
                    
                    if avg_score > 0:
                        self.metrics_service.record_metric(
                            name="search_avg_score",
                            value=avg_score,
                            metric_type="histogram",
                            tags={"operation": "hybrid_search"}
                        )
                        
                except Exception as e:
                    self.logger.warning(f"Failed to record metrics: {e}")
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
            
            # Add search cache information
            health_status["search_cache"] = await self.get_search_cache_stats()
            
            # Add connection pool statistics
            if self._client_factory:
                health_status["connection_pool"] = await self._client_factory.get_connection_stats()
            
            # Add query performance statistics
            health_status["query_performance"] = await self.get_query_performance_stats()
            
            # Add query cache statistics
            health_status["query_cache"] = await self.get_query_cache_stats()

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

    # ==========================================
    # Fuzzy Search Methods
    # ==========================================

    async def _fuzzy_search(
        self,
        query_text: str,
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
    ) -> List[Candidate]:
        """
        Execute fuzzy search for typo tolerance using Elasticsearch AC patterns.

        Args:
            query_text: The search query (potentially with typos)
            opts: Search options
            search_trace: Optional search trace for debugging

        Returns:
            List of fuzzy match candidates
        """
        start_time = time.perf_counter()

        try:
            # Try ES-based fuzzy search first (more efficient for 1M+ patterns)
            es_fuzzy_results = await self._elasticsearch_fuzzy_search(query_text, opts)
            if es_fuzzy_results:
                print(f"🎯 ES FUZZY SEARCH: Got {len(es_fuzzy_results)} results")
                return es_fuzzy_results

            # Fallback to in-memory fuzzy search
            return await self._in_memory_fuzzy_search(query_text, opts, search_trace)

        except Exception as e:
            self.logger.error(f"Fuzzy search failed: {e}")
            return []

    async def _elasticsearch_fuzzy_search(
        self,
        query_text: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """
        Execute fuzzy search using Elasticsearch on AC patterns index.
        Much more efficient than in-memory search for 1M+ patterns.
        """
        try:
            if not hasattr(self, '_ac_adapter') or not self._ac_adapter:
                self.logger.debug("AC adapter not available for ES fuzzy search")
                return []

            # Use ES fuzzy query on AC patterns index
            # Note: pattern field is keyword type, canonical is text type
            es_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "fuzzy": {
                                    "pattern": {
                                        "value": query_text,
                                        "fuzziness": 1,  # Limit to 1 character difference
                                        "prefix_length": 2,  # More strict prefix matching
                                        "max_expansions": 20,  # Reduce expansions
                                        "boost": 2.0  # Reduce boost
                                    }
                                }
                            },
                            {
                                "fuzzy": {
                                    "canonical": {
                                        "value": query_text,
                                        "fuzziness": 1,  # Limit to 1 character difference
                                        "prefix_length": 2,  # More strict prefix matching
                                        "max_expansions": 20,  # Reduce expansions
                                        "boost": 1.5  # Reduce boost
                                    }
                                }
                            },
                            {
                                "match": {
                                    "canonical": {
                                        "query": query_text,
                                        "fuzziness": 1,  # Limit fuzziness
                                        "boost": 1.2  # Reduce boost
                                    }
                                }
                            }
                        ],
                        "minimum_should_match": 1
                    }
                },
                "size": min(opts.top_k * 3, 100),
                "_source": ["pattern", "canonical", "entity_id", "entity_type", "confidence", "tier"],
                "timeout": "2s"
            }

            # Execute ES query through AC adapter
            client = await self._ac_adapter._ensure_connection()
            index_name = getattr(self._ac_adapter, 'index_name', self.config.elasticsearch.ac_index)
            response = await client.search(
                index=index_name,
                body=es_query
            )

            if not response or 'hits' not in response:
                self.logger.debug("No ES fuzzy results found")
                return []

            # Convert ES results to Candidates
            fuzzy_candidates = []
            for hit in response['hits']['hits']:
                source = hit.get('_source', {})
                score = hit.get('_score', 0.0)

                # More conservative ES score normalization with edit distance check
                result_text = source.get('canonical', source.get('pattern', ''))

                # Calculate edit distance (Levenshtein distance)
                def edit_distance(s1, s2):
                    s1, s2 = s1.lower(), s2.lower()
                    if len(s1) > len(s2):
                        s1, s2 = s2, s1
                    distances = range(len(s1) + 1)
                    for i2, c2 in enumerate(s2):
                        distances_ = [i2 + 1]
                        for i1, c1 in enumerate(s1):
                            if c1 == c2:
                                distances_.append(distances[i1])
                            else:
                                distances_.append(1 + min((distances[i1], distances[i1 + 1], distances_[-1])))
                        distances = distances_
                    return distances[-1]

                # Calculate edit distance and ratio
                edit_dist = edit_distance(query_text, result_text)
                max_len = max(len(query_text), len(result_text))
                edit_ratio = 1.0 - (edit_dist / max_len) if max_len > 0 else 0

                # Word-level similarity for additional validation
                query_parts = set(query_text.lower().split())
                result_parts = set(result_text.lower().split())
                if query_parts and result_parts:
                    overlap = len(query_parts.intersection(result_parts))
                    total_unique = len(query_parts.union(result_parts))
                    word_similarity = overlap / total_unique if total_unique > 0 else 0
                else:
                    word_similarity = 0

                # Strict filtering: require reasonable edit distance
                # For short queries (< 15 chars): allow up to 3 edits
                # For longer queries: allow 1 edit per 5 characters
                if len(query_text) < 15:
                    max_allowed_edits = 3
                else:
                    max_allowed_edits = max(3, len(query_text) // 5)

                if edit_dist > max_allowed_edits:
                    continue  # Skip if too many differences

                # Normalize ES score more conservatively
                es_normalized = min(score / 50.0, 1.0)

                # Combine different similarity measures
                normalized_score = (es_normalized * 0.2) + (edit_ratio * 0.5) + (word_similarity * 0.3)

                # Apply penalty for low edit ratio
                if edit_ratio < 0.6:  # Less than 60% character similarity
                    normalized_score *= 0.7

                # Skip candidates with very low similarity
                # Lower threshold for good fuzzy matches
                min_threshold = 0.4 if edit_ratio > 0.8 else 0.5
                if normalized_score < min_threshold:
                    continue

                candidate = Candidate(
                    doc_id=hit.get('_id', f"es_fuzzy_{len(fuzzy_candidates)}"),
                    score=normalized_score,
                    text=source.get('canonical', source.get('pattern', '')),
                    entity_type=source.get('entity_type', 'person'),
                    metadata={
                        "fuzzy_algorithm": "elasticsearch",
                        "original_query": query_text,
                        "es_score": score,
                        "es_normalized": es_normalized,
                        "edit_distance": edit_dist,
                        "edit_ratio": edit_ratio,
                        "word_similarity": word_similarity,
                        "pattern": source.get('pattern', ''),
                        "canonical": source.get('canonical', ''),
                        "tier": source.get('tier', 0),
                        "confidence": source.get('confidence', 0.0)
                    },
                    search_mode=SearchMode.FUZZY,
                    match_fields=["es_fuzzy"],
                    confidence=normalized_score,
                    trace={
                        "reason": "es_fuzzy_match",
                        "algorithm": "elasticsearch",
                        "original_query": query_text
                    }
                )
                fuzzy_candidates.append(candidate)

            # Filter by score threshold
            filtered_candidates = [
                c for c in fuzzy_candidates
                if c.score >= (opts.threshold * 0.8)  # Slightly lower for fuzzy
            ]

            self.logger.info(f"ES fuzzy search: {len(response['hits']['hits'])} hits, {len(filtered_candidates)} after filtering")
            return filtered_candidates[:opts.top_k]

        except Exception as e:
            self.logger.warning(f"ES fuzzy search failed, falling back: {e}")
            return []

    async def _in_memory_fuzzy_search(
        self,
        query_text: str,
        opts: SearchOpts,
        search_trace: Optional[SearchTrace] = None
    ) -> List[Candidate]:
        """
        Fallback in-memory fuzzy search using sanctions data.
        """
        start_time = time.perf_counter()

        if not self._fuzzy_service.enabled:
            self.logger.debug("Fuzzy search disabled - rapidfuzz not available")
            return []

        try:
            # Get candidates for fuzzy matching (from watchlist or cache)
            candidates = await self._get_fuzzy_candidates()
            print(f"🔍 FUZZY CANDIDATES: Got {len(candidates)} candidates")
            if candidates:
                print(f"   Sample candidates: {candidates[:3]}")

            if not candidates:
                print("❌ NO FUZZY CANDIDATES AVAILABLE")
                self.logger.debug("No candidates available for fuzzy search")
                return []

            # Perform fuzzy search
            print(f"🚀 PERFORMING FUZZY SEARCH: query='{query_text}'")
            fuzzy_results = await self._fuzzy_service.search_async(
                query=query_text,
                candidates=candidates,
                doc_mapping=None,  # We'll map later
                metadata_mapping=None
            )
            print(f"✅ FUZZY SEARCH RESULTS: Got {len(fuzzy_results)} results")

            # Convert fuzzy results to Candidates
            fuzzy_candidates = []
            for fuzzy_result in fuzzy_results:
                candidate = Candidate(
                    doc_id=f"fuzzy_{hash(fuzzy_result.matched_text)}",
                    score=fuzzy_result.score,
                    text=fuzzy_result.matched_text,
                    entity_type="person",  # Assume person names for now
                    metadata={
                        "fuzzy_algorithm": fuzzy_result.algorithm,
                        "original_query": fuzzy_result.original_query,
                        "fuzzy_score": fuzzy_result.score
                    },
                    search_mode=SearchMode.FUZZY,  # Use correct SearchMode for fuzzy
                    match_fields=["fuzzy_name"],
                    confidence=fuzzy_result.score,
                    trace={
                        "reason": "fuzzy_match",
                        "algorithm": fuzzy_result.algorithm,
                        "original_query": query_text
                    }
                )
                fuzzy_candidates.append(candidate)

            # Calculate timing for logging and tracing
            took_ms = (time.perf_counter() - start_time) * 1000

            # Add trace step if tracing enabled
            if search_trace and search_trace.enabled:
                trace_step = SearchTraceStep(
                    step="fuzzy_search",
                    took_ms=took_ms,
                    query=query_text,
                    total_hits=len(fuzzy_candidates),
                    candidates_count=len(candidates),
                    details={
                        "algorithm": "rapidfuzz",
                        "candidate_count": len(candidates),
                        "result_count": len(fuzzy_candidates),
                        "min_score": min(c.score for c in fuzzy_candidates) if fuzzy_candidates else 0,
                        "max_score": max(c.score for c in fuzzy_candidates) if fuzzy_candidates else 0
                    }
                )
                search_trace.steps.append(trace_step)

            self.logger.debug(f"Fuzzy search completed: {len(fuzzy_candidates)} results in {took_ms:.2f}ms")
            return fuzzy_candidates[:opts.max_results]  # Limit results

        except Exception as e:
            self.logger.error(f"Fuzzy search failed: {e}")
            return []

    async def _get_fuzzy_candidates(self) -> List[str]:
        """
        Get candidates for fuzzy matching from sanctions data.

        Priority:
        1. Sanctions data (primary source)
        2. Watchlist service (fallback)
        3. Common names (last resort)

        Returns:
            List of candidate strings for fuzzy matching
        """
        # Check cache first
        cache_key = "fuzzy_candidates"
        if cache_key in self._fuzzy_candidates_cache:
            return self._fuzzy_candidates_cache[cache_key]

        candidates = []

        # Primary source: Sanctions data
        try:
            self.logger.info("Loading fuzzy candidates from sanctions data...")

            # Check if force reload is needed
            import os
            force_reload = os.getenv("FORCE_RELOAD_SANCTIONS", "false").lower() == "true"
            if force_reload:
                await self._sanctions_loader.clear_cache()
                self.logger.warning("🗑️ Cleared sanctions cache due to FORCE_RELOAD_SANCTIONS")

            sanctions_candidates = await self._sanctions_loader.get_fuzzy_candidates()

            if sanctions_candidates:
                candidates.extend(sanctions_candidates)
                self._sanctions_loaded = True
                self.logger.info(f"✅ Loaded {len(sanctions_candidates)} names from sanctions data for fuzzy search")

                # Get additional stats
                stats = await self._sanctions_loader.get_stats()
                self.logger.info(f"Sanctions stats: {stats['persons']} persons, {stats['organizations']} orgs from {len(stats['sources'])} sources")

            else:
                self.logger.warning("❌ No sanctions candidates loaded from primary source")

        except Exception as e:
            self.logger.error(f"❌ Failed to load sanctions data for fuzzy search: {e}")
            import traceback
            self.logger.error(f"Full traceback: {traceback.format_exc()}")

        # Fallback: Try watchlist service
        if not candidates:
            try:
                if self._fallback_watchlist_service and self._fallback_watchlist_service.ready():
                    all_docs = await self._get_watchlist_names()
                    candidates.extend(all_docs)
                    self.logger.debug(f"Fallback: loaded {len(all_docs)} names from watchlist service")
            except Exception as e:
                self.logger.warning(f"Failed to load watchlist names for fuzzy search: {e}")

        # Last resort: Common names
        if not candidates:
            candidates = self._get_common_names()
            self.logger.warning(f"Using fallback common names: {len(candidates)} entries")

        # Cache the candidates (limit for performance)
        cached_candidates = candidates[:20000]  # Increased limit for sanctions data
        self._fuzzy_candidates_cache[cache_key] = cached_candidates

        self.logger.info(f"Fuzzy search initialized with {len(cached_candidates)} candidates")
        return cached_candidates

    async def _get_watchlist_names(self) -> List[str]:
        """Extract all names from watchlist for fuzzy matching."""
        try:
            # This is a placeholder - actual implementation would depend on watchlist service API
            # You might want to extract this from your sanctioned persons data
            return []
        except Exception as e:
            self.logger.warning(f"Failed to extract watchlist names: {e}")
            return []

    def _get_common_names(self) -> List[str]:
        """Get common Ukrainian/Russian names for fuzzy matching."""
        return [
            # Ukrainian politicians and public figures
            "Петро Порошенко", "Володимир Зеленський", "Юлія Тимошенко",
            "Віталій Кличко", "Ігор Коломойський", "Рінат Ахметов",
            "Павло Фукс", "Вадим Новинський", "Дмитро Фірташ",

            # Russian names
            "Владимир Путин", "Сергей Лавров", "Михаил Мишустин",
            "Дмитрий Медведев", "Алексей Навальный",

            # Common Ukrainian names
            "Андрій Іванов", "Олександр Петров", "Микола Сидоров",
            "Ігор Коваленко", "Сергій Бондаренко", "Олексій Мельник",
            "Катерина Шевченко", "Наталія Коваль", "Марія Петренко",
            "Оксана Ткачук", "Тетяна Білоус", "Інна Гавриленко",

            # Test names for fuzzy search
            "Ковриков Роман Валерійович", "Ковриков Роман", "Роман Ковриков"
        ]

    def _fuzzy_results_sufficient(self, fuzzy_candidates: List[Candidate], opts: SearchOpts) -> bool:
        """
        Determine if fuzzy search results are good enough to skip vector search.

        Args:
            fuzzy_candidates: Results from fuzzy search
            opts: Search options

        Returns:
            True if fuzzy results are sufficient, False otherwise
        """
        if not fuzzy_candidates:
            return False

        # Check if we have enough high-confidence results
        high_confidence_results = [
            c for c in fuzzy_candidates
            if c.score >= self._fuzzy_service.config.high_confidence_threshold
        ]

        if len(high_confidence_results) >= 1:  # At least one high-confidence match
            self.logger.debug(f"Fuzzy search found {len(high_confidence_results)} high-confidence matches")
            return True

        # Check if best score is above minimum threshold
        best_score = max(c.score for c in fuzzy_candidates)
        if best_score >= self._fuzzy_service.config.min_score_threshold * 1.1:  # 10% above minimum
            self.logger.debug(f"Fuzzy search best score {best_score:.3f} is sufficient")
            return True

        return False
