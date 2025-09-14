"""
Simplified Embedding Service with lazy initialization
"""

import logging
import time
from typing import List, Union

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

        self.logger.info(
            f"EmbeddingService initialized with model: {config.model_name}"
        )

    def _load_model(self) -> SentenceTransformer:
        """Lazy load the SentenceTransformer model"""
        if self._model is None:
            self.logger.info(f"Loading embedding model: {self.config.model_name}")
            self._model = SentenceTransformer(
                self.config.model_name,
                device=self.config.device
            )
            self.logger.info(f"Model loaded successfully on device: {self.config.device}")
        return self._model

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
                convert_to_numpy=True
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
                convert_to_numpy=True
            )

            # Convert to 32-bit float and ensure it's a list
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.astype(np.float32).tolist()

            # Log timing
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.logger.debug(f"encode_batch({len(texts)} texts): {duration_ms:.2f}ms")
            
            if duration_ms > 100:
                self.logger.warning(f"Slow encode_batch({len(texts)} texts): {duration_ms:.2f}ms > 100ms")

            return embeddings

        except Exception as e:
            self.logger.error(f"Failed to encode texts: {e}")
            raise

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Encode texts to embeddings (legacy method for backward compatibility)

        Args:
            texts: Single text string or list of text strings

        Returns:
            Single embedding vector or list of embedding vectors as 32-bit floats
        """
        if isinstance(texts, str):
            return self.encode_one(texts)
        else:
            return self.encode_batch(texts)

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
