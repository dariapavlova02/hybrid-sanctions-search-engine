"""
Model Configuration for Embedding Services
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any
from enum import Enum


class ModelType(str, Enum):
    """Supported model types"""
    SENTENCE_TRANSFORMER = "sentence_transformer"
    HUGGINGFACE = "huggingface"
    CUSTOM = "custom"


@dataclass
class ModelConfig:
    """Configuration for embedding models"""
    
    name: str
    model_type: ModelType = ModelType.SENTENCE_TRANSFORMER
    model_path: str = ""
    dimension: int = 384
    max_sequence_length: int = 512
    device: str = "cpu"
    batch_size: int = 32
    normalize_embeddings: bool = True
    use_fp16: bool = False
    cache_dir: Optional[str] = None
    
    # Performance settings
    enable_gpu: bool = False
    thread_pool_size: int = 4
    max_memory_usage: float = 0.8  # 80% of available memory
    
    # Model-specific settings
    model_kwargs: Dict[str, Any] = None
    
    def __post_init__(self):
        """Post-initialization validation"""
        if self.model_kwargs is None:
            self.model_kwargs = {}
        
        if not self.model_path and self.name:
            self.model_path = self.name


# Predefined model configurations
DEFAULT_MODELS = {
    "multilingual": ModelConfig(
        name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
        dimension=384,
        max_sequence_length=128,
        normalize_embeddings=True
    ),
    "english": ModelConfig(
        name="sentence-transformers/all-MiniLM-L6-v2",
        dimension=384,
        max_sequence_length=256,
        normalize_embeddings=True
    ),
    "multilingual_large": ModelConfig(
        name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        dimension=768,
        max_sequence_length=128,
        normalize_embeddings=True
    )
}


def get_model_config(model_name: str) -> ModelConfig:
    """Get model configuration by name"""
    if model_name in DEFAULT_MODELS:
        return DEFAULT_MODELS[model_name]
    
    # Create default config for unknown models
    return ModelConfig(
        name=model_name,
        model_path=model_name,
        dimension=384,  # Default dimension
        normalize_embeddings=True
    )
