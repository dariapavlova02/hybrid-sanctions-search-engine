"""
Search layer for hybrid AC/Vector search using Elasticsearch backend.

This layer provides:
- HybridSearchService: Main service combining AC (exact) and Vector (kNN) search
- Elasticsearch adapters for both search modes
- Configuration management for search parameters
- Metrics and logging for search performance
"""

from .hybrid_search_service import HybridSearchService
from .contracts import (
    Candidate,
    SearchOpts,
    SearchService,
    SearchMetrics,
    SearchMode,
)
from .config import HybridSearchConfig
from .elasticsearch_adapters import (
    ElasticsearchACAdapter,
    ElasticsearchVectorAdapter,
)

__all__ = [
    "HybridSearchService",
    "SearchService", 
    "Candidate",
    "SearchOpts",
    "SearchMode",
    "HybridSearchConfig",
    "SearchMetrics",
    "ElasticsearchACAdapter",
    "ElasticsearchVectorAdapter",
]
