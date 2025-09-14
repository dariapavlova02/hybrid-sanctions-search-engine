"""
Enhanced Vector Index Service with performance optimizations
Combines TF-IDF char n-grams with semantic embeddings for better accuracy
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np

try:
    import faiss
    _FAISS_AVAILABLE = True
except Exception:
    _FAISS_AVAILABLE = False

from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize

from ....utils.logging_config import get_logger
from .vector_index_service import VectorIndexConfig, CharTfidfVectorIndex
from ..optimized_embedding_service import OptimizedEmbeddingService


@dataclass
class EnhancedVectorIndexConfig(VectorIndexConfig):
    """Enhanced configuration with semantic features"""
    use_semantic_embeddings: bool = True
    semantic_weight: float = 0.6  # Weight for semantic vs lexical features
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    enable_hybrid_search: bool = True
    min_semantic_similarity: float = 0.3
    max_candidates_for_reranking: int = 100


class EnhancedVectorIndex(CharTfidfVectorIndex):
    """Enhanced vector index combining lexical and semantic features"""

    def __init__(self, config: Optional[EnhancedVectorIndexConfig] = None):
        """Initialize enhanced vector index"""
        self.cfg = config or EnhancedVectorIndexConfig()
        super().__init__(self.cfg)

        self.logger = get_logger(__name__)

        # Semantic embedding components
        self.embedding_service = None
        self.semantic_embeddings: Optional[np.ndarray] = None
        self.semantic_faiss_index = None

        # Performance optimization
        self.index_lock = threading.RLock()
        self.thread_pool = ThreadPoolExecutor(max_workers=2)

        # Metrics
        self.search_metrics = {
            "total_searches": 0,
            "lexical_searches": 0,
            "semantic_searches": 0,
            "hybrid_searches": 0,
            "avg_search_time": 0.0,
        }

        if self.cfg.use_semantic_embeddings:
            self.embedding_service = OptimizedEmbeddingService(
                default_model=self.cfg.embedding_model,
                enable_batch_optimization=True,
            )

    def rebuild(self, docs: List[Tuple[str, str]]) -> None:
        """Rebuild both lexical and semantic indices"""
        start_time = time.time()

        with self.index_lock:
            # Build lexical index (parent functionality)
            super().rebuild(docs)

            # Build semantic index if enabled
            if self.cfg.use_semantic_embeddings and docs and self.embedding_service:
                self._rebuild_semantic_index(docs)

        build_time = time.time() - start_time
        self.logger.info(
            f"Rebuilt enhanced index with {len(docs)} documents in {build_time:.3f}s "
            f"(semantic: {self.cfg.use_semantic_embeddings})"
        )

    def _rebuild_semantic_index(self, docs: List[Tuple[str, str]]) -> None:
        """Build semantic embedding index"""
        try:
            texts = [doc[1] for doc in docs]

            # Generate embeddings
            embedding_result = self.embedding_service.get_embeddings_optimized(
                texts, batch_size=64, use_cache=True
            )

            if not embedding_result["success"]:
                self.logger.error("Failed to generate semantic embeddings")
                return

            embeddings = np.array(embedding_result["embeddings"], dtype=np.float32)

            # L2 normalize embeddings for cosine similarity
            embeddings = normalize(embeddings, norm='l2')
            self.semantic_embeddings = embeddings

            # Build FAISS index if available
            if _FAISS_AVAILABLE and self.cfg.use_faiss:
                self._build_semantic_faiss_index(embeddings)

        except Exception as e:
            self.logger.error(f"Failed to build semantic index: {e}")
            self.semantic_embeddings = None
            self.semantic_faiss_index = None

    def _build_semantic_faiss_index(self, embeddings: np.ndarray) -> None:
        """Build FAISS index for semantic embeddings"""
        try:
            dimension = embeddings.shape[1]

            if len(embeddings) < 1000:
                # Use flat index for small datasets
                self.semantic_faiss_index = faiss.IndexFlatIP(dimension)
            else:
                # Use HNSW for larger datasets
                self.semantic_faiss_index = faiss.IndexHNSWFlat(dimension, 32)
                if hasattr(self.semantic_faiss_index, 'hnsw'):
                    self.semantic_faiss_index.hnsw.efSearch = 64

            self.semantic_faiss_index.add(embeddings)
            self.logger.info(f"Built semantic FAISS index with {len(embeddings)} vectors")

        except Exception as e:
            self.logger.warning(f"Failed to build semantic FAISS index: {e}")
            self.semantic_faiss_index = None

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """Enhanced search combining lexical and semantic approaches"""
        if not self.doc_ids:
            return []

        start_time = time.time()

        try:
            with self.index_lock:
                if self.cfg.enable_hybrid_search and self.cfg.use_semantic_embeddings:
                    results = self._hybrid_search(query, top_k)
                    self.search_metrics["hybrid_searches"] += 1
                elif self.cfg.use_semantic_embeddings and self.semantic_embeddings is not None:
                    results = self._semantic_search(query, top_k)
                    self.search_metrics["semantic_searches"] += 1
                else:
                    results = super().search(query, top_k)
                    self.search_metrics["lexical_searches"] += 1

            # Update metrics
            search_time = time.time() - start_time
            self.search_metrics["total_searches"] += 1

            # Update average search time
            total = self.search_metrics["total_searches"]
            current_avg = self.search_metrics["avg_search_time"]
            self.search_metrics["avg_search_time"] = (current_avg * (total - 1) + search_time) / total

            return results

        except Exception as e:
            self.logger.error(f"Enhanced search failed: {e}")
            # Fallback to lexical search
            return super().search(query, top_k)

    def _semantic_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Pure semantic search using embeddings"""
        if not self.embedding_service or self.semantic_embeddings is None:
            return []

        try:
            # Get query embedding
            query_result = self.embedding_service.get_embeddings_optimized([query])
            if not query_result["success"]:
                return []

            query_embedding = np.array([query_result["embeddings"][0]], dtype=np.float32)
            query_embedding = normalize(query_embedding, norm='l2')

            # Search using FAISS if available
            if self.semantic_faiss_index is not None:
                scores, indices = self.semantic_faiss_index.search(query_embedding, min(top_k, len(self.doc_ids)))

                results = []
                for score, idx in zip(scores[0], indices[0]):
                    if idx >= 0 and score >= self.cfg.min_semantic_similarity:
                        results.append((self.doc_ids[idx], float(score)))

                return results
            else:
                # Fallback to brute force
                similarities = np.dot(self.semantic_embeddings, query_embedding.T).flatten()

                # Filter by minimum similarity
                valid_indices = np.where(similarities >= self.cfg.min_semantic_similarity)[0]
                valid_similarities = similarities[valid_indices]

                # Sort and take top_k
                sorted_indices = np.argsort(-valid_similarities)[:top_k]

                return [(self.doc_ids[valid_indices[i]], float(valid_similarities[i]))
                       for i in sorted_indices]

        except Exception as e:
            self.logger.error(f"Semantic search failed: {e}")
            return []

    def _hybrid_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Hybrid search combining lexical and semantic results"""
        try:
            # Get more candidates from each method
            candidate_k = min(self.cfg.max_candidates_for_reranking, max(top_k * 3, 50))

            # Parallel search execution
            future_lexical = self.thread_pool.submit(super().search, query, candidate_k)
            future_semantic = self.thread_pool.submit(self._semantic_search, query, candidate_k)

            # Get results
            lexical_results = future_lexical.result(timeout=5.0)  # 5 second timeout
            semantic_results = future_semantic.result(timeout=5.0)

            # Combine and rerank results
            return self._combine_and_rerank(lexical_results, semantic_results, top_k)

        except Exception as e:
            self.logger.error(f"Hybrid search failed: {e}")
            # Fallback to lexical search
            return super().search(query, top_k)

    def _combine_and_rerank(
        self,
        lexical_results: List[Tuple[str, float]],
        semantic_results: List[Tuple[str, float]],
        top_k: int
    ) -> List[Tuple[str, float]]:
        """Combine lexical and semantic results with weighted scoring"""
        try:
            # Create score dictionaries
            lexical_scores = {doc_id: score for doc_id, score in lexical_results}
            semantic_scores = {doc_id: score for doc_id, score in semantic_results}

            # Get all unique document IDs
            all_doc_ids = set(lexical_scores.keys()) | set(semantic_scores.keys())

            # Calculate combined scores
            combined_scores = []
            lexical_weight = 1.0 - self.cfg.semantic_weight
            semantic_weight = self.cfg.semantic_weight

            for doc_id in all_doc_ids:
                lexical_score = lexical_scores.get(doc_id, 0.0)
                semantic_score = semantic_scores.get(doc_id, 0.0)

                # Normalize scores to [0, 1] range
                normalized_lexical = max(0.0, min(1.0, lexical_score))
                normalized_semantic = max(0.0, min(1.0, semantic_score))

                # Combined weighted score
                combined_score = (
                    lexical_weight * normalized_lexical +
                    semantic_weight * normalized_semantic
                )

                # Boost if both methods found the document
                if lexical_score > 0 and semantic_score > 0:
                    combined_score *= 1.2  # 20% boost for consensus

                combined_scores.append((doc_id, combined_score))

            # Sort by combined score and return top_k
            combined_scores.sort(key=lambda x: x[1], reverse=True)
            return combined_scores[:top_k]

        except Exception as e:
            self.logger.error(f"Failed to combine results: {e}")
            # Return lexical results as fallback
            return lexical_results[:top_k]

    def get_index_statistics(self) -> Dict[str, any]:
        """Get comprehensive index statistics"""
        stats = {
            "document_count": len(self.doc_ids),
            "lexical_index_built": self.X_vec is not None,
            "semantic_index_built": self.semantic_embeddings is not None,
            "faiss_lexical_available": self.faiss_index is not None,
            "faiss_semantic_available": self.semantic_faiss_index is not None,
            "config": {
                "use_semantic_embeddings": self.cfg.use_semantic_embeddings,
                "semantic_weight": self.cfg.semantic_weight,
                "enable_hybrid_search": self.cfg.enable_hybrid_search,
                "embedding_model": self.cfg.embedding_model,
            },
            "search_metrics": self.search_metrics.copy(),
        }

        # Add embedding service metrics if available
        if self.embedding_service:
            stats["embedding_metrics"] = self.embedding_service.get_performance_metrics()

        return stats

    def optimize_index(self) -> None:
        """Optimize index performance"""
        with self.index_lock:
            try:
                # Optimize FAISS indices if available
                if self.faiss_index is not None:
                    self.logger.info("Optimizing lexical FAISS index...")
                    # For HNSW indices, we could adjust ef parameters
                    if hasattr(self.faiss_index, 'hnsw'):
                        self.faiss_index.hnsw.efSearch = min(self.cfg.ef_search * 2, 128)

                if self.semantic_faiss_index is not None:
                    self.logger.info("Optimizing semantic FAISS index...")
                    if hasattr(self.semantic_faiss_index, 'hnsw'):
                        self.semantic_faiss_index.hnsw.efSearch = 64

                # Clear embedding cache periodically
                if self.embedding_service:
                    metrics = self.embedding_service.get_performance_metrics()
                    if metrics["cache_hit_rate"] < 0.3:  # Low hit rate
                        self.embedding_service.clear_cache()
                        self.logger.info("Cleared embedding cache due to low hit rate")

                self.logger.info("Index optimization completed")

            except Exception as e:
                self.logger.error(f"Index optimization failed: {e}")

    def warm_up(self, sample_queries: Optional[List[str]] = None) -> None:
        """Warm up the index with sample queries"""
        if not sample_queries:
            sample_queries = [
                "test query",
                "sample search",
                "example text",
            ]

        self.logger.info(f"Warming up index with {len(sample_queries)} sample queries...")

        for query in sample_queries:
            try:
                self.search(query, top_k=5)
            except Exception as e:
                self.logger.warning(f"Warmup query failed: {e}")

        self.logger.info("Index warmup completed")

    def __del__(self):
        """Cleanup resources"""
        try:
            if hasattr(self, 'thread_pool'):
                self.thread_pool.shutdown(wait=False)
        except Exception:
            pass