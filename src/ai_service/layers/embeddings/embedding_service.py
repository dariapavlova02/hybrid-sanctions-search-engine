"""
Embedding Service - Pure Vector Generation for AI Service

This service provides multilingual text embeddings using sentence transformers.
It follows the architectural principle of separation of concerns:

- VECTOR GENERATION → This service (pure embeddings)
- INDEXING/SIMILARITY → Downstream services (VectorIndex, Decision)

Key Features:
1. Multilingual support (ru/uk/en) with consistent embeddings
2. Automatic preprocessing (removes dates/IDs, keeps names/organizations)
3. Lazy model loading for memory efficiency
4. Batch processing optimization
5. Configurable model switching

Default Model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
- 384-dimensional vectors
- Balanced performance and quality
- Proven multilingual capabilities

Usage:
    from ai_service.config import EmbeddingConfig
    from ai_service.layers.embeddings.embedding_service import EmbeddingService

    config = EmbeddingConfig()
    service = EmbeddingService(config)

    # Single text
    vector = service.encode_one("Ivan Petrov")  # 384 floats

    # Batch processing (recommended)
    vectors = service.encode_batch(["Ivan Petrov", "Anna Smith"])  # 2x384 floats
"""

import logging
import time
from typing import List, Union, Optional, Dict, Any

import numpy as np
from sentence_transformers import SentenceTransformer

from ...config import EmbeddingConfig
from ...services.embedding_preprocessor import EmbeddingPreprocessor
from ...utils.logging_config import get_logger


class EmbeddingService:
    """Simplified embedding service with lazy initialization"""

    def __init__(self, config: EmbeddingConfig):
        """
        Initialize embedding service with configuration

        Args:
            config: Embedding configuration
        """
        self.logger = get_logger(__name__)
        self.config = config
        self._model: SentenceTransformer = None
        self.preprocessor = EmbeddingPreprocessor()
        
        # Add expected attributes for backward compatibility
        self.model_cache: Dict[str, SentenceTransformer] = {}
        self.default_model = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

        self.logger.info(
            f"EmbeddingService initialized with model: {config.model_name}"
        )

    def _load_model(self, model_name: Optional[str] = None) -> SentenceTransformer:
        """Lazy load the SentenceTransformer model with caching"""
        model_name = model_name or self.config.model_name
        
        # Check cache first
        if model_name in self.model_cache:
            return self.model_cache[model_name]
        
        # Load new model
        self.logger.info(f"Loading embedding model: {model_name}")
        model = SentenceTransformer(model_name, device=self.config.device)
        
        # Cache the model
        self.model_cache[model_name] = model
        
        # Set as default model if it's the config model
        if model_name == self.config.model_name:
            self._model = model
            
        self.logger.info(
            f"Model loaded successfully on device: {self.config.device}"
        )
        return model

    def encode_one(self, text: str) -> List[float]:
        """
        Encode a single text to embedding vector

        Args:
            text: Single text string

        Returns:
            Single embedding vector as 32-bit floats
        """
        if not text or not text.strip():
            return []

        # Preprocess text to remove dates/IDs
        normalized_text = self.preprocessor.normalize_for_embedding(text)
        if not normalized_text:
            return []

        try:
            # Load model lazily
            model = self._load_model()

            # Generate embedding
            embedding = model.encode(
                [normalized_text],
                batch_size=1,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )

            # Convert to 32-bit float and ensure it's a list
            if isinstance(embedding, np.ndarray):
                embedding = embedding.astype(np.float32).tolist()

            return embedding[0] if len(embedding) > 0 else []

        except Exception as e:
            self.logger.error(f"Failed to encode text: {e}")
            raise

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Encode multiple texts to embedding vectors

        Args:
            texts: List of text strings

        Returns:
            List of embedding vectors as 32-bit floats
        """
        start_time = time.perf_counter()

        if not texts:
            return []

        # Preprocess texts to remove dates/IDs
        normalized_texts = []
        for text in texts:
            if text and text.strip():
                normalized = self.preprocessor.normalize_for_embedding(text)
                if normalized:  # Only include non-empty normalized texts
                    normalized_texts.append(normalized)

        if not normalized_texts:
            return []

        try:
            # Load model lazily
            model = self._load_model()

            # Generate embeddings
            embeddings = model.encode(
                normalized_texts,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )

            # Convert to 32-bit float and ensure it's a list
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.astype(np.float32).tolist()

            # Log timing
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.debug(f"encode_batch({len(texts)} texts): {duration_ms:.2f}ms")

            if duration_ms > 100:
                self.logger.warning(
                    f"Slow encode_batch({len(texts)} texts): {duration_ms:.2f}ms > 100ms"
                )

            return embeddings

        except Exception as e:
            self.logger.error(f"Failed to encode texts: {e}")
            raise

    def encode(
        self, 
        texts: Union[str, List[str]], 
        normalize: bool = False, 
        batch_size: Optional[int] = None, 
        to_numpy: bool = True,
        model_name: Optional[str] = None,
        normalize_embeddings: bool = True
    ) -> Union[List[float], List[List[float]], Dict[str, Any]]:
        """
        Encode texts to embeddings with backward compatibility

        Args:
            texts: Single text string or list of text strings
            normalize: Whether to normalize embeddings (legacy parameter)
            batch_size: Batch size for processing (legacy parameter)
            to_numpy: Whether to convert to numpy (legacy parameter)
            model_name: Model name to use (legacy parameter)
            normalize_embeddings: Whether to normalize embeddings

        Returns:
            For single text: List[float] or Dict with metadata
            For multiple texts: List[List[float]] or Dict with metadata
        """
        start_time = time.perf_counter()
        
        # Handle None or empty input
        if texts is None:
            texts = []
        elif isinstance(texts, str) and not texts.strip():
            texts = []
        elif isinstance(texts, list) and not texts:
            texts = []
        
        # Determine if we're processing single or multiple texts
        is_single = isinstance(texts, str)
        if is_single:
            text_list = [texts]
        else:
            text_list = texts
            
        if not text_list:
            # Return empty result with metadata
            return {
                "success": True,
                "embeddings": [],
                "model_name": model_name or self.config.model_name,
                "text_count": 0,
                "embedding_dimension": 0,
                "processing_time": 0.0,
                "normalized": normalize_embeddings,
                "batch_size": batch_size or self.config.batch_size,
                "timestamp": time.time()
            }
        
        try:
            # Load model
            model = self._load_model(model_name)
            
            # Preprocess texts
            normalized_texts = []
            for text in text_list:
                if text and text.strip():
                    normalized = self.preprocessor.normalize_for_embedding(text)
                    if normalized:
                        normalized_texts.append(normalized)
            
            if not normalized_texts:
                return {
                    "success": True,
                    "embeddings": [],
                    "model_name": model_name or self.config.model_name,
                    "text_count": 0,
                    "embedding_dimension": 0,
                    "processing_time": 0.0,
                    "normalized": normalize_embeddings,
                    "batch_size": batch_size or self.config.batch_size,
                    "timestamp": time.time()
                }
            
            # Generate embeddings
            embeddings = model.encode(
                normalized_texts,
                batch_size=batch_size or self.config.batch_size,
                show_progress_bar=False,
                normalize_embeddings=normalize_embeddings,
                convert_to_numpy=to_numpy,
            )
            
            # Convert to 32-bit float and ensure it's a list
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.astype(np.float32).tolist()
            
            processing_time = time.perf_counter() - start_time
            
            # Return format with metadata for backward compatibility
            return {
                "success": True,
                "embeddings": embeddings,
                "model_name": model_name or self.config.model_name,
                "text_count": len(normalized_texts),
                "embedding_dimension": len(embeddings[0]) if embeddings else 0,
                "processing_time": processing_time,
                "normalized": normalize_embeddings,
                "batch_size": batch_size or self.config.batch_size,
                "timestamp": time.time()
            }
                
        except Exception as e:
            self.logger.error(f"Failed to encode texts: {e}")
            # Return empty result on error with metadata
            return {
                "success": False,
                "embeddings": [],
                "model_name": model_name or self.config.model_name,
                "text_count": 0,
                "embedding_dimension": 0,
                "processing_time": 0.0,
                "normalized": normalize_embeddings,
                "batch_size": batch_size or self.config.batch_size,
                "timestamp": time.time(),
                "error": str(e)
            }

    def get_embeddings(
        self, 
        texts: Union[str, List[str]], 
        model_name: Optional[str] = None, 
        normalize: bool = True, 
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Get embeddings for texts (alias for encode method with different signature)
        
        Args:
            texts: Single text string or list of text strings
            model_name: Model name to use
            normalize: Whether to normalize embeddings
            batch_size: Batch size for processing
            
        Returns:
            Dictionary with embeddings and metadata
        """
        return self.encode(
            texts=texts,
            model_name=model_name,
            normalize_embeddings=normalize,
            batch_size=batch_size
        )

    async def get_embeddings_async(
        self, 
        texts: Union[str, List[str]], 
        model_name: Optional[str] = None, 
        normalize: bool = True, 
        batch_size: int = 32
    ) -> Dict[str, Any]:
        """
        Get embeddings for texts asynchronously
        
        Args:
            texts: Single text string or list of text strings
            model_name: Model name to use
            normalize: Whether to normalize embeddings
            batch_size: Batch size for processing
            
        Returns:
            Dictionary with embeddings and metadata
        """
        # Run the synchronous method in a thread pool
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.get_embeddings, 
            texts, 
            model_name, 
            normalize, 
            batch_size
        )

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by the model

        Returns:
            Embedding dimension
        """
        model = self._load_model()
        return model.get_sentence_embedding_dimension()

    def get_model_info(self) -> dict:
        """
        Get information about the loaded model

        Returns:
            Dictionary with model information
        """
        model = self._load_model()
        return {
            "model_name": self.config.model_name,
            "device": str(model.device),
            "embedding_dimension": model.get_sentence_embedding_dimension(),
            "max_seq_length": getattr(model, "max_seq_length", 512),
        }

    def calculate_similarity(
        self, 
        text1: str, 
        text2: str, 
        metric: str = "cosine"
    ) -> Dict[str, Any]:
        """
        Calculate similarity between two texts

        Args:
            text1: First text
            text2: Second text
            metric: Similarity metric ("cosine" or "dot")

        Returns:
            Dictionary with similarity result
        """
        try:
            # Get embeddings for both texts
            emb1 = self.encode_one(text1)
            emb2 = self.encode_one(text2)
            
            if not emb1 or not emb2:
                return {
                    "success": False,
                    "similarity": 0.0,
                    "metric": metric,
                    "model_name": self.config.model_name,
                    "error": "Failed to generate embeddings"
                }
            
            # Convert to numpy arrays for calculation
            vec1 = np.array(emb1)
            vec2 = np.array(emb2)
            
            # Calculate similarity
            if metric == "cosine":
                similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
            elif metric == "dot":
                similarity = np.dot(vec1, vec2)
            else:
                raise ValueError(f"Unsupported metric: {metric}")
            
            return {
                "success": True,
                "similarity": float(similarity),
                "metric": metric,
                "model_name": self.config.model_name
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate similarity: {e}")
            return {
                "success": False,
                "similarity": 0.0,
                "metric": metric,
                "model_name": self.config.model_name,
                "error": str(e)
            }

    def find_similar_texts(
        self, 
        query: str, 
        candidates: List[str], 
        top_k: int = 5, 
        threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        Find most similar texts from candidates

        Args:
            query: Query text
            candidates: List of candidate texts
            top_k: Number of top results to return
            threshold: Minimum similarity threshold

        Returns:
            Dictionary with similarity results
        """
        try:
            if not candidates:
                return {
                    "success": True,
                    "results": [],
                    "query": query,
                    "total_candidates": 0,
                    "model_name": self.config.model_name
                }
            
            # Get query embedding
            query_emb = self.encode_one(query)
            if not query_emb:
                return {
                    "success": False,
                    "results": [],
                    "query": query,
                    "total_candidates": len(candidates),
                    "model_name": self.config.model_name,
                    "error": "Failed to generate query embedding"
                }
            
            # Get candidate embeddings
            candidate_embs = self.encode_batch(candidates)
            if not candidate_embs:
                return {
                    "success": False,
                    "results": [],
                    "query": query,
                    "total_candidates": len(candidates),
                    "model_name": self.config.model_name,
                    "error": "Failed to generate candidate embeddings"
                }
            
            # Calculate similarities
            similarities = []
            for i, cand_emb in enumerate(candidate_embs):
                if cand_emb:
                    vec1 = np.array(query_emb)
                    vec2 = np.array(cand_emb)
                    similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                    similarities.append({
                        "text": candidates[i],
                        "similarity": float(similarity),
                        "index": i
                    })
            
            # Filter by threshold and sort
            filtered_results = [r for r in similarities if r["similarity"] >= threshold]
            filtered_results.sort(key=lambda x: x["similarity"], reverse=True)
            
            # Take top_k results
            top_results = filtered_results[:top_k]
            
            return {
                "success": True,
                "results": top_results,
                "query": query,
                "total_candidates": len(candidates),
                "model_name": self.config.model_name
            }
            
        except Exception as e:
            self.logger.error(f"Failed to find similar texts: {e}")
            return {
                "success": False,
                "results": [],
                "query": query,
                "total_candidates": len(candidates),
                "model_name": self.config.model_name,
                "error": str(e)
            }

    def calculate_batch_similarity(
        self, 
        queries: List[str], 
        candidates: List[str]
    ) -> Dict[str, Any]:
        """
        Calculate similarity matrix between queries and candidates

        Args:
            queries: List of query texts
            candidates: List of candidate texts

        Returns:
            Dictionary with similarity matrix
        """
        try:
            if not queries or not candidates:
                return {
                    "success": True,
                    "similarity_matrix": [],
                    "queries": queries,
                    "candidates": candidates,
                    "model_name": self.config.model_name
                }
            
            # Get embeddings
            query_embs = self.encode_batch(queries)
            candidate_embs = self.encode_batch(candidates)
            
            if not query_embs or not candidate_embs:
                return {
                    "success": False,
                    "similarity_matrix": [],
                    "queries": queries,
                    "candidates": candidates,
                    "model_name": self.config.model_name,
                    "error": "Failed to generate embeddings"
                }
            
            # Calculate similarity matrix
            similarity_matrix = []
            for query_emb in query_embs:
                if query_emb:
                    query_vec = np.array(query_emb)
                    query_similarities = []
                    for cand_emb in candidate_embs:
                        if cand_emb:
                            cand_vec = np.array(cand_emb)
                            similarity = np.dot(query_vec, cand_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(cand_vec))
                            query_similarities.append(float(similarity))
                        else:
                            query_similarities.append(0.0)
                    similarity_matrix.append(query_similarities)
                else:
                    similarity_matrix.append([0.0] * len(candidates))
            
            return {
                "success": True,
                "similarity_matrix": similarity_matrix,
                "queries": queries,
                "candidates": candidates,
                "model_name": self.config.model_name
            }
            
        except Exception as e:
            self.logger.error(f"Failed to calculate batch similarity: {e}")
            return {
                "success": False,
                "similarity_matrix": [],
                "queries": queries,
                "candidates": candidates,
                "model_name": self.config.model_name,
                "error": str(e)
            }
