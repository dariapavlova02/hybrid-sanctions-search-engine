"""
Simplified Embedding Service with lazy initialization
"""

import logging
from typing import List, Union

import numpy as np
from sentence_transformers import SentenceTransformer

from ...config import EmbeddingConfig
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

    def encode(self, texts: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Encode texts to embeddings

        Args:
            texts: Single text string or list of text strings

        Returns:
            Single embedding vector or list of embedding vectors as 32-bit floats
        """
        # Convert single string to list
        if isinstance(texts, str):
            input_texts = [texts]
            single_input = True
        else:
            input_texts = texts
            single_input = False

        if not input_texts or (len(input_texts) == 1 and not input_texts[0].strip()):
            return [] if not single_input else []

        try:
            # Load model lazily
            model = self._load_model()

            # Generate embeddings
            embeddings = model.encode(
                input_texts,
                batch_size=self.config.batch_size,
                show_progress_bar=False,
                normalize_embeddings=True,
                convert_to_numpy=True
            )

            # Convert to 32-bit float and ensure it's a list
            if isinstance(embeddings, np.ndarray):
                embeddings = embeddings.astype(np.float32).tolist()

            # Return single vector for single input, list for multiple inputs
            if single_input:
                return embeddings[0] if embeddings else []
            else:
                return embeddings

        except Exception as e:
            self.logger.error(f"Failed to encode texts: {e}")
            raise

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
