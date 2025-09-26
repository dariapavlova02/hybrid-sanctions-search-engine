"""
AI Service - Name normalization and signals extraction service.

This module automatically applies performance and security improvements:
- Memory-aware caching with pressure handling
- Asynchronous model loading
- Security hardening
"""

# Apply memory-aware caching system-wide for better performance
try:
    from .utils.memory_aware_cache import patch_lru_cache_with_memory_awareness
    patch_lru_cache_with_memory_awareness()
except ImportError:
    # Fallback gracefully if memory_aware_cache is not available
    pass

__version__ = "0.0.1"
__all__ = ["__version__"]