"""
Embedding Models Module

This module provides model management and configuration for embedding services.
"""

from .embedding_model_manager import EmbeddingModelManager
from .model_config import ModelConfig

__all__ = [
    'EmbeddingModelManager',
    'ModelConfig'
]
