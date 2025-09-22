"""
Search layer for hybrid AC/Vector search using Elasticsearch backend.

This layer provides:
- HybridSearchService: Main service combining AC (exact) and Vector (kNN) search
- Elasticsearch adapters for both search modes
- Configuration management for search parameters
- Metrics and logging for search performance
"""

# Conditional imports to handle elasticsearch dependency issues
try:
    from .hybrid_search_service import HybridSearchService
    SEARCH_SERVICE_AVAILABLE = True
except ImportError as e:
    HybridSearchService = None
    SEARCH_SERVICE_AVAILABLE = False

try:
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
    from .elasticsearch_client import ElasticsearchClientFactory
except ImportError:
    # Provide dummy placeholders
    Candidate = None
    SearchOpts = None
    SearchService = None
    SearchMetrics = None
    SearchMode = None
    HybridSearchConfig = None
    ElasticsearchACAdapter = None
    ElasticsearchVectorAdapter = None
    ElasticsearchClientFactory = None

# Always available
from .mock_search_service import MockSearchService

__all__ = [
    "HybridSearchService",
    "MockSearchService",
    "SEARCH_SERVICE_AVAILABLE",
    "SearchService",
    "Candidate",
    "SearchOpts",
    "SearchMode",
    "HybridSearchConfig",
    "SearchMetrics",
    "ElasticsearchACAdapter",
    "ElasticsearchVectorAdapter",
    "ElasticsearchClientFactory",
]
