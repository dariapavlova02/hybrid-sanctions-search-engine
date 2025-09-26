"""
Asynchronous model loader to prevent blocking during startup.
"""

import asyncio
import logging
import threading
import time
from typing import Any, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

class AsyncModelLoader:
    """Asynchronous model loader with caching and background initialization."""

    def __init__(self):
        self._models: Dict[str, Optional[Any]] = {}
        self._loading: Dict[str, bool] = {}
        self._lock = threading.Lock()
        self._executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="ModelLoader")

    def _load_spacy_model(self, model_name: str, package_name: str) -> Optional[Any]:
        """Load a spaCy model synchronously."""
        try:
            start_time = time.time()
            logger.info(f"Loading {model_name} model...")

            # Dynamic import to avoid blocking on module import
            module = __import__(package_name)
            model = module.load()

            load_time = time.time() - start_time
            logger.info(f"Loaded {model_name} model in {load_time:.2f}s")
            return model
        except ImportError as e:
            logger.warning(f"Model {package_name} not installed: {e}")
            return None
        except Exception as e:
            logger.error(f"Failed to load {model_name} model: {e}")
            return None

    async def load_model_async(self, model_name: str, package_name: str) -> Optional[Any]:
        """Load a model asynchronously."""
        with self._lock:
            # Return cached model if available
            if model_name in self._models:
                return self._models[model_name]

            # Check if already loading
            if self._loading.get(model_name, False):
                # Wait for loading to complete
                while self._loading.get(model_name, False):
                    await asyncio.sleep(0.1)
                return self._models.get(model_name)

            # Mark as loading
            self._loading[model_name] = True

        try:
            # Load model in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            model = await loop.run_in_executor(
                self._executor,
                self._load_spacy_model,
                model_name,
                package_name
            )

            with self._lock:
                self._models[model_name] = model
                self._loading[model_name] = False

            return model

        except Exception as e:
            logger.error(f"Async loading failed for {model_name}: {e}")
            with self._lock:
                self._models[model_name] = None
                self._loading[model_name] = False
            return None

    def get_model_sync(self, model_name: str) -> Optional[Any]:
        """Get model synchronously (returns None if not loaded)."""
        with self._lock:
            return self._models.get(model_name)

    async def get_or_load_model(self, model_name: str, package_name: str) -> Optional[Any]:
        """Get model if available, otherwise load it asynchronously."""
        model = self.get_model_sync(model_name)
        if model is not None:
            return model

        return await self.load_model_async(model_name, package_name)

    async def preload_all_models(self):
        """Preload all common models in background."""
        models_to_load = [
            ("en", "en_core_web_sm"),
            ("uk", "uk_core_news_sm"),
            ("ru", "ru_core_news_sm")
        ]

        tasks = []
        for model_name, package_name in models_to_load:
            task = asyncio.create_task(
                self.load_model_async(model_name, package_name)
            )
            tasks.append(task)

        # Load all models concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)

        loaded_count = sum(1 for result in results if result is not None and not isinstance(result, Exception))
        logger.info(f"Preloaded {loaded_count}/{len(models_to_load)} spaCy models")

    def start_background_loading(self):
        """Start background model loading (fire and forget)."""
        def background_load():
            try:
                # Create new event loop for background thread
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.preload_all_models())
                loop.close()
            except Exception as e:
                logger.error(f"Background model loading failed: {e}")

        thread = threading.Thread(target=background_load, daemon=True, name="ModelPreloader")
        thread.start()
        logger.info("Started background model loading")

# Global instance
_model_loader = AsyncModelLoader()

# Backward compatibility functions
async def get_spacy_en_async() -> Optional[Any]:
    """Get English spaCy model asynchronously."""
    return await _model_loader.get_or_load_model("en", "en_core_web_sm")

async def get_spacy_uk_async() -> Optional[Any]:
    """Get Ukrainian spaCy model asynchronously."""
    return await _model_loader.get_or_load_model("uk", "uk_core_news_sm")

async def get_spacy_ru_async() -> Optional[Any]:
    """Get Russian spaCy model asynchronously."""
    return await _model_loader.get_or_load_model("ru", "ru_core_news_sm")

def get_spacy_en_sync() -> Optional[Any]:
    """Get English spaCy model if already loaded."""
    return _model_loader.get_model_sync("en")

def get_spacy_uk_sync() -> Optional[Any]:
    """Get Ukrainian spaCy model if already loaded."""
    return _model_loader.get_model_sync("uk")

def get_spacy_ru_sync() -> Optional[Any]:
    """Get Russian spaCy model if already loaded."""
    return _model_loader.get_model_sync("ru")

def start_model_preloading():
    """Start background model preloading."""
    _model_loader.start_background_loading()

# Auto-start background loading when module is imported
start_model_preloading()