"""
Embedding Model Manager

Manages loading, caching, and lifecycle of embedding models.
"""

import logging
import threading
import time
from typing import Dict, Optional, List, Any, Union
from concurrent.futures import ThreadPoolExecutor
import gc

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False

from .model_config import ModelConfig, get_model_config


class EmbeddingModelManager:
    """Manages embedding models with caching and lifecycle management"""
    
    def __init__(
        self,
        max_models: int = 3,
        enable_gpu: bool = False,
        cache_dir: Optional[str] = None,
        thread_pool_size: int = 2
    ):
        """
        Initialize model manager
        
        Args:
            max_models: Maximum number of models to keep in memory
            enable_gpu: Enable GPU acceleration if available
            cache_dir: Directory for model caching
            thread_pool_size: Size of thread pool for model loading
        """
        self.logger = logging.getLogger(__name__)
        self.max_models = max_models
        self.enable_gpu = enable_gpu and TORCH_AVAILABLE
        self.cache_dir = cache_dir
        self.thread_pool_size = thread_pool_size
        
        # Model cache
        self._models: Dict[str, Any] = {}
        self._model_configs: Dict[str, ModelConfig] = {}
        self._model_usage: Dict[str, float] = {}  # Last access time
        self._lock = threading.RLock()
        
        # Thread pool for async model loading
        self._executor = ThreadPoolExecutor(max_workers=thread_pool_size)
        
        # Device detection
        self.device = self._detect_device()
        self.logger.info(f"ModelManager initialized on device: {self.device}")
    
    def _detect_device(self) -> str:
        """Detect best available device"""
        if not self.enable_gpu:
            return "cpu"
        
        if not TORCH_AVAILABLE:
            return "cpu"
        
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"
    
    def get_model(self, model_name: str, config: Optional[ModelConfig] = None) -> Any:
        """
        Get model by name, loading if necessary
        
        Args:
            model_name: Name of the model
            config: Optional model configuration
            
        Returns:
            Loaded model instance
        """
        with self._lock:
            # Check if model is already loaded
            if model_name in self._models:
                self._model_usage[model_name] = time.time()
                return self._models[model_name]
            
            # Load model
            return self._load_model(model_name, config)
    
    def _load_model(self, model_name: str, config: Optional[ModelConfig] = None) -> Any:
        """Load model with configuration"""
        if config is None:
            config = get_model_config(model_name)
        
        self.logger.info(f"Loading model: {model_name}")
        
        try:
            if not SENTENCE_TRANSFORMERS_AVAILABLE:
                raise ImportError("sentence-transformers not available")
            
            # Configure device
            device = config.device if config.device != "cpu" else self.device
            
            # Load model
            model = SentenceTransformer(
                config.model_path or model_name,
                device=device,
                cache_folder=self.cache_dir
            )
            
            # Apply model-specific configurations
            if config.use_fp16 and device != "cpu":
                try:
                    model = model.half()
                    self.logger.info(f"Enabled FP16 for {model_name}")
                except Exception as e:
                    self.logger.warning(f"FP16 not available for {model_name}: {e}")
            
            # Cache model
            self._models[model_name] = model
            self._model_configs[model_name] = config
            self._model_usage[model_name] = time.time()
            
            # Cleanup if we have too many models
            self._cleanup_models()
            
            self.logger.info(f"Model {model_name} loaded successfully on {device}")
            return model
            
        except Exception as e:
            self.logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def _cleanup_models(self):
        """Remove least recently used models if cache is full"""
        if len(self._models) <= self.max_models:
            return
        
        # Sort by usage time (oldest first)
        sorted_models = sorted(
            self._model_usage.items(),
            key=lambda x: x[1]
        )
        
        # Remove oldest models
        models_to_remove = len(self._models) - self.max_models
        for model_name, _ in sorted_models[:models_to_remove]:
            self._remove_model(model_name)
    
    def _remove_model(self, model_name: str):
        """Remove model from cache"""
        if model_name in self._models:
            del self._models[model_name]
            del self._model_configs[model_name]
            del self._model_usage[model_name]
            
            # Force garbage collection
            gc.collect()
            
            self.logger.info(f"Removed model {model_name} from cache")
    
    def preload_model(self, model_name: str, config: Optional[ModelConfig] = None):
        """Preload model in background"""
        def _preload():
            try:
                self.get_model(model_name, config)
            except Exception as e:
                self.logger.error(f"Failed to preload {model_name}: {e}")
        
        self._executor.submit(_preload)
    
    def get_model_info(self, model_name: str) -> Dict[str, Any]:
        """Get information about a model"""
        with self._lock:
            if model_name not in self._models:
                return {"loaded": False}
            
            config = self._model_configs.get(model_name)
            usage_time = self._model_usage.get(model_name, 0)
            
            return {
                "loaded": True,
                "config": config.__dict__ if config else None,
                "last_used": usage_time,
                "device": getattr(self._models[model_name], 'device', 'unknown')
            }
    
    def list_loaded_models(self) -> List[str]:
        """List currently loaded models"""
        with self._lock:
            return list(self._models.keys())
    
    def clear_cache(self):
        """Clear all loaded models"""
        with self._lock:
            self._models.clear()
            self._model_configs.clear()
            self._model_usage.clear()
            gc.collect()
            self.logger.info("Model cache cleared")
    
    def shutdown(self):
        """Shutdown model manager"""
        self.clear_cache()
        self._executor.shutdown(wait=True)
        self.logger.info("ModelManager shutdown completed")
    
    def __del__(self):
        """Cleanup on destruction"""
        try:
            self.shutdown()
        except:
            pass
