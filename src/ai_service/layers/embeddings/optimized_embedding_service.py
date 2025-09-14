"""
Optimized Embedding Service with performance enhancements
"""

import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Union, Tuple
import threading
from collections import deque

import numpy as np

from ...utils.logging_config import get_logger
from .embedding_service import EmbeddingService


class OptimizedEmbeddingService(EmbeddingService):
    """Optimized embedding service with performance enhancements"""

    def __init__(
        self,
        default_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        max_cache_size: int = 1000,
        enable_batch_optimization: bool = True,
        enable_gpu: bool = True,
        thread_pool_size: int = 4,
        precompute_common_patterns: bool = True,
    ):
        """
        Initialize optimized embedding service

        Args:
            default_model: Default model
            max_cache_size: Maximum cache size for embeddings
            enable_batch_optimization: Enable automatic batch optimization
            enable_gpu: Enable GPU acceleration if available
            thread_pool_size: Size of thread pool for parallel processing
            precompute_common_patterns: Precompute embeddings for common patterns
        """
        super().__init__(default_model)

        self.max_cache_size = max_cache_size
        self.enable_batch_optimization = enable_batch_optimization
        self.enable_gpu = enable_gpu
        self.thread_pool_size = thread_pool_size
        self.precompute_common_patterns = precompute_common_patterns

        # Performance optimization features
        self.embedding_cache: Dict[str, Tuple[List[float], float]] = {}  # text -> (embedding, timestamp)
        self.cache_lock = threading.RLock()

        # Batch processing queue
        self.batch_queue = deque()
        self.batch_lock = threading.Lock()

        # Thread pool for parallel processing
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)

        # Performance metrics
        self.performance_metrics = {
            "cache_hits": 0,
            "cache_misses": 0,
            "batch_optimizations": 0,
            "total_embeddings_generated": 0,
            "total_processing_time": 0.0,
            "gpu_accelerated": 0,
        }

        # GPU acceleration setup
        self.gpu_available = self._check_gpu_availability()

        # Precompute common patterns
        if precompute_common_patterns:
            self._precompute_common_patterns()

        self.logger.info(
            f"OptimizedEmbeddingService initialized (GPU: {self.gpu_available}, "
            f"Cache: {max_cache_size}, Threads: {thread_pool_size})"
        )

    def _check_gpu_availability(self) -> bool:
        """Check if GPU acceleration is available"""
        try:
            if not self.enable_gpu:
                return False

            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _precompute_common_patterns(self):
        """Precompute embeddings for common patterns"""
        common_patterns = [
            "payment", "платіж", "платеж",
            "company", "компанія", "компания",
            "person", "персона", "особа",
            "contract", "договір", "договор",
            "invoice", "рахунок", "счет",
            "transfer", "переказ", "перевод",
        ]

        try:
            self.logger.info("Precomputing embeddings for common patterns...")
            start_time = time.time()

            # Generate embeddings for common patterns
            result = self.get_embeddings(common_patterns)
            if result["success"]:
                # Cache the embeddings
                embeddings = result["embeddings"]
                timestamp = time.time()

                with self.cache_lock:
                    for i, pattern in enumerate(common_patterns):
                        cache_key = self._get_cache_key(pattern, self.default_model)
                        self.embedding_cache[cache_key] = (embeddings[i], timestamp)

                precompute_time = time.time() - start_time
                self.logger.info(f"Precomputed {len(common_patterns)} patterns in {precompute_time:.3f}s")

        except Exception as e:
            self.logger.warning(f"Failed to precompute common patterns: {e}")

    def _get_cache_key(self, text: str, model_name: str) -> str:
        """Generate cache key for text and model"""
        return f"{model_name}:{hash(text)}"

    def _get_cached_embedding(self, text: str, model_name: str) -> Optional[List[float]]:
        """Get cached embedding if available and not expired"""
        cache_key = self._get_cache_key(text, model_name)

        with self.cache_lock:
            if cache_key in self.embedding_cache:
                embedding, timestamp = self.embedding_cache[cache_key]

                # Check if cache entry is not too old (1 hour expiry)
                if time.time() - timestamp < 3600:
                    self.performance_metrics["cache_hits"] += 1
                    return embedding
                else:
                    # Remove expired entry
                    del self.embedding_cache[cache_key]

        self.performance_metrics["cache_misses"] += 1
        return None

    def _cache_embedding(self, text: str, model_name: str, embedding: List[float]):
        """Cache embedding with LRU eviction"""
        cache_key = self._get_cache_key(text, model_name)
        timestamp = time.time()

        with self.cache_lock:
            # LRU eviction if cache is full
            if len(self.embedding_cache) >= self.max_cache_size:
                # Remove oldest entry
                oldest_key = min(
                    self.embedding_cache.keys(),
                    key=lambda k: self.embedding_cache[k][1]
                )
                del self.embedding_cache[oldest_key]

            self.embedding_cache[cache_key] = (embedding, timestamp)

    def _load_model_optimized(self, model_name: str):
        """Load model with GPU acceleration if available"""
        try:
            if model_name not in self.model_cache:
                from sentence_transformers import SentenceTransformer

                self.logger.info(f"Loading optimized model: {model_name}")

                # Configure device
                device = "cuda" if self.gpu_available else "cpu"

                model = SentenceTransformer(model_name, device=device)

                # Enable half precision for GPU if available
                if self.gpu_available:
                    try:
                        model = model.half()  # Use FP16 for faster inference
                        self.logger.info(f"Enabled FP16 for model {model_name}")
                    except Exception as e:
                        self.logger.warning(f"FP16 not available: {e}")

                self.model_cache[model_name] = model
                self.logger.info(f"Model {model_name} loaded on {device}")

            return self.model_cache[model_name]

        except Exception as e:
            self.logger.error(f"Failed to load optimized model {model_name}: {e}")
            # Fallback to parent implementation
            return super()._load_model(model_name)

    def get_embeddings_optimized(
        self,
        texts: Union[str, List[str]],
        model_name: Optional[str] = None,
        normalize: bool = True,
        batch_size: int = 32,
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """
        Optimized embedding generation with caching and performance enhancements

        Args:
            texts: Text or list of texts
            model_name: Model name
            normalize: Normalize embeddings (L2)
            batch_size: Batch size
            use_cache: Use embedding cache

        Returns:
            Dict with embeddings and metadata
        """
        start_time = time.time()

        # Normalize input
        if isinstance(texts, str):
            texts = [texts]

        if not texts:
            return self._create_empty_result()

        if model_name is None:
            model_name = self.default_model

        try:
            cached_embeddings = []
            texts_to_compute = []
            cache_indices = []

            # Check cache if enabled
            if use_cache:
                for i, text in enumerate(texts):
                    cached = self._get_cached_embedding(text, model_name)
                    if cached is not None:
                        cached_embeddings.append((i, cached))
                    else:
                        texts_to_compute.append(text)
                        cache_indices.append(i)
            else:
                texts_to_compute = texts
                cache_indices = list(range(len(texts)))

            # Generate embeddings for uncached texts
            new_embeddings = []
            if texts_to_compute:
                # Use optimized model loading
                model = self._load_model_optimized(model_name)

                # Optimize batch size based on GPU memory
                if self.gpu_available and len(texts_to_compute) > batch_size * 2:
                    optimized_batch_size = min(batch_size * 2, 64)
                    self.performance_metrics["batch_optimizations"] += 1
                else:
                    optimized_batch_size = batch_size

                # Generate embeddings
                embeddings = model.encode(
                    texts_to_compute,
                    batch_size=optimized_batch_size,
                    show_progress_bar=False,
                    normalize_embeddings=normalize,
                    convert_to_numpy=True,
                )

                # Convert to list and cache
                if isinstance(embeddings, np.ndarray):
                    new_embeddings = embeddings.tolist()
                else:
                    new_embeddings = embeddings

                # Cache new embeddings
                if use_cache:
                    for text, embedding in zip(texts_to_compute, new_embeddings):
                        self._cache_embedding(text, model_name, embedding)

                # Track GPU usage
                if self.gpu_available:
                    self.performance_metrics["gpu_accelerated"] += len(texts_to_compute)

            # Combine cached and new embeddings
            final_embeddings = [None] * len(texts)

            # Insert cached embeddings
            for i, embedding in cached_embeddings:
                final_embeddings[i] = embedding

            # Insert new embeddings
            for i, embedding in zip(cache_indices, new_embeddings):
                final_embeddings[i] = embedding

            # Update metrics
            processing_time = time.time() - start_time
            self.performance_metrics["total_embeddings_generated"] += len(texts)
            self.performance_metrics["total_processing_time"] += processing_time

            result = {
                "success": True,
                "embeddings": final_embeddings,
                "model_name": model_name,
                "text_count": len(texts),
                "embedding_dimension": len(final_embeddings[0]) if final_embeddings else 0,
                "processing_time": processing_time,
                "normalized": normalize,
                "batch_size": optimized_batch_size if texts_to_compute else batch_size,
                "timestamp": datetime.now().isoformat(),
                "cache_hits": len(cached_embeddings),
                "cache_misses": len(texts_to_compute),
                "gpu_accelerated": self.gpu_available and bool(texts_to_compute),
            }

            self.logger.info(
                f"Generated embeddings for {len(texts)} texts "
                f"(cached: {len(cached_embeddings)}, computed: {len(texts_to_compute)}) "
                f"in {processing_time:.3f}s"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed to generate optimized embeddings: {e}")
            return self._create_error_result(str(e))

    def find_similar_texts_optimized(
        self,
        query: str,
        candidates: List[str],
        model_name: Optional[str] = None,
        threshold: float = 0.7,
        top_k: int = 10,
        metric: str = "cosine",
        use_faiss: bool = True,
    ) -> Dict[str, Any]:
        """
        Optimized similarity search with FAISS acceleration if available

        Args:
            query: Search query
            candidates: List of candidates
            model_name: Model name
            threshold: Similarity threshold
            top_k: Number of best results
            metric: Similarity metric
            use_faiss: Use FAISS for acceleration

        Returns:
            Dict with search results
        """
        try:
            start_time = time.time()

            # Get embeddings for all texts using optimized method
            all_texts = [query] + candidates
            embeddings_result = self.get_embeddings_optimized(all_texts, model_name)

            if not embeddings_result["success"]:
                return self._create_error_result("Failed to generate embeddings")

            embeddings = embeddings_result["embeddings"]
            query_embedding = embeddings[0]
            candidate_embeddings = embeddings[1:]

            # Use FAISS for large candidate sets if available
            if use_faiss and len(candidates) > 100:
                try:
                    similarities = self._faiss_similarity_search(
                        query_embedding, candidate_embeddings, candidates, top_k, threshold
                    )
                except Exception as e:
                    self.logger.warning(f"FAISS search failed, falling back to numpy: {e}")
                    similarities = self._numpy_similarity_search(
                        query_embedding, candidate_embeddings, candidates, top_k, threshold, metric
                    )
            else:
                similarities = self._numpy_similarity_search(
                    query_embedding, candidate_embeddings, candidates, top_k, threshold, metric
                )

            processing_time = time.time() - start_time

            result = {
                "success": True,
                "query": query,
                "total_candidates": len(candidates),
                "threshold": threshold,
                "top_k": top_k,
                "metric": metric,
                "results": similarities,
                "model_name": embeddings_result["model_name"],
                "processing_time": processing_time,
                "optimized": True,
                "faiss_accelerated": use_faiss and len(candidates) > 100,
                "timestamp": datetime.now().isoformat(),
            }

            self.logger.info(
                f"Found {len(similarities)} similar texts for query "
                f"from {len(candidates)} candidates in {processing_time:.3f}s"
            )

            return result

        except Exception as e:
            self.logger.error(f"Failed optimized similarity search: {e}")
            return self._create_error_result(str(e))

    def _faiss_similarity_search(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        candidates: List[str],
        top_k: int,
        threshold: float,
    ) -> List[Dict[str, Any]]:
        """Use FAISS for accelerated similarity search"""
        try:
            import faiss

            # Convert to numpy arrays
            query_vec = np.array([query_embedding], dtype=np.float32)
            candidate_matrix = np.array(candidate_embeddings, dtype=np.float32)

            # Normalize vectors for cosine similarity
            faiss.normalize_L2(query_vec)
            faiss.normalize_L2(candidate_matrix)

            # Build FAISS index
            dimension = candidate_matrix.shape[1]
            index = faiss.IndexFlatIP(dimension)  # Inner product for normalized vectors
            index.add(candidate_matrix)

            # Search
            scores, indices = index.search(query_vec, min(top_k * 2, len(candidates)))

            # Filter by threshold and format results
            results = []
            for i, (score, idx) in enumerate(zip(scores[0], indices[0])):
                if score >= threshold and idx >= 0:
                    results.append({
                        "text": candidates[idx],
                        "similarity_score": float(score),
                        "rank": len(results) + 1,
                    })

                    if len(results) >= top_k:
                        break

            return results

        except ImportError:
            raise Exception("FAISS not available")

    def _numpy_similarity_search(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        candidates: List[str],
        top_k: int,
        threshold: float,
        metric: str,
    ) -> List[Dict[str, Any]]:
        """Use numpy for similarity search"""
        query_vec = np.array(query_embedding)
        candidate_matrix = np.array(candidate_embeddings)

        if metric == "cosine":
            # Normalize for cosine similarity
            query_norm = query_vec / np.linalg.norm(query_vec)
            candidate_norms = candidate_matrix / np.linalg.norm(candidate_matrix, axis=1, keepdims=True)

            # Calculate similarities
            similarities = np.dot(candidate_norms, query_norm)
        else:
            # Use original method for other metrics
            similarities = []
            for candidate_emb in candidate_embeddings:
                sim = self._calculate_embedding_similarity(query_embedding, candidate_emb, metric)
                similarities.append(sim)
            similarities = np.array(similarities)

        # Filter and sort
        valid_indices = np.where(similarities >= threshold)[0]
        valid_similarities = similarities[valid_indices]

        # Sort by similarity (descending)
        sorted_indices = np.argsort(-valid_similarities)[:top_k]

        results = []
        for i, sort_idx in enumerate(sorted_indices):
            orig_idx = valid_indices[sort_idx]
            results.append({
                "text": candidates[orig_idx],
                "similarity_score": float(valid_similarities[sort_idx]),
                "rank": i + 1,
            })

        return results

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get performance metrics"""
        with self.cache_lock:
            cache_hit_rate = (
                self.performance_metrics["cache_hits"] /
                (self.performance_metrics["cache_hits"] + self.performance_metrics["cache_misses"])
                if (self.performance_metrics["cache_hits"] + self.performance_metrics["cache_misses"]) > 0
                else 0.0
            )

            avg_processing_time = (
                self.performance_metrics["total_processing_time"] /
                self.performance_metrics["total_embeddings_generated"]
                if self.performance_metrics["total_embeddings_generated"] > 0
                else 0.0
            )

            return {
                "cache_hit_rate": cache_hit_rate,
                "cache_size": len(self.embedding_cache),
                "max_cache_size": self.max_cache_size,
                "gpu_available": self.gpu_available,
                "gpu_accelerated_embeddings": self.performance_metrics["gpu_accelerated"],
                "batch_optimizations": self.performance_metrics["batch_optimizations"],
                "total_embeddings_generated": self.performance_metrics["total_embeddings_generated"],
                "average_processing_time": avg_processing_time,
                "total_processing_time": self.performance_metrics["total_processing_time"],
            }

    def clear_cache(self):
        """Clear embedding cache"""
        with self.cache_lock:
            self.embedding_cache.clear()
            self.logger.info("Embedding cache cleared")

    def warm_up_cache(self, texts: List[str], model_name: Optional[str] = None):
        """Warm up cache with common texts"""
        self.logger.info(f"Warming up cache with {len(texts)} texts")
        self.get_embeddings_optimized(texts, model_name, use_cache=True)

    # Override parent methods to use optimized versions
    def get_embeddings(
        self,
        texts: Union[str, List[str]],
        model_name: Optional[str] = None,
        normalize: bool = True,
        batch_size: int = 32,
    ) -> Dict[str, Any]:
        """Override to use optimized version"""
        return self.get_embeddings_optimized(texts, model_name, normalize, batch_size)

    def find_similar_texts(
        self,
        query: str,
        candidates: List[str],
        model_name: Optional[str] = None,
        threshold: float = 0.7,
        top_k: int = 10,
        metric: str = "cosine",
    ) -> Dict[str, Any]:
        """Override to use optimized version"""
        return self.find_similar_texts_optimized(
            query, candidates, model_name, threshold, top_k, metric
        )

    def _load_model(self, model_name: str):
        """Override to use optimized loading"""
        return self._load_model_optimized(model_name)

    # Enhanced async methods
    async def get_embeddings_async_optimized(
        self,
        texts: Union[str, List[str]],
        model_name: Optional[str] = None,
        normalize: bool = True,
        batch_size: int = 32,
    ) -> Dict[str, Any]:
        """Optimized async embedding generation"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool,
            self.get_embeddings_optimized,
            texts, model_name, normalize, batch_size
        )

    async def find_similar_texts_async_optimized(
        self,
        query: str,
        candidates: List[str],
        model_name: Optional[str] = None,
        threshold: float = 0.7,
        top_k: int = 10,
        metric: str = "cosine",
    ) -> Dict[str, Any]:
        """Optimized async similarity search"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.thread_pool,
            self.find_similar_texts_optimized,
            query, candidates, model_name, threshold, top_k, metric
        )

    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
        except Exception:
            pass