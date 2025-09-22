"""
Mock Search Service for testing when elasticsearch is not available.
"""

from typing import Any, Dict, List, Optional
from .contracts import SearchService, Candidate, SearchOpts, SearchMetrics
from ...contracts.base_contracts import NormalizationResult


class MockSearchService(SearchService):
    """Mock search service that provides empty results when elasticsearch is unavailable."""

    def __init__(self, config=None):
        self.config = config

    def initialize(self):
        """Mock initialization."""
        pass

    async def health_check(self) -> Dict[str, Any]:
        """Mock health check."""
        return {
            "status": "mock",
            "message": "Mock search service - elasticsearch not available"
        }

    async def search(
        self,
        query: str,
        *,
        limit: int = 10,
        opts: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock search that returns empty results."""
        return {
            "query": query,
            "results": [],
            "total_hits": 0,
            "search_type": "mock",
            "processing_time_ms": 1,
            "warnings": ["Search service not available - using mock"],
        }

    async def find_candidates(
        self,
        normalized: NormalizationResult,
        text: str,
        opts: SearchOpts
    ) -> List[Candidate]:
        """Find search candidates (mock implementation)."""
        return []  # Empty list of candidates

    async def search_similar(
        self,
        normalized_text: str,
        *,
        limit: int = 10,
        threshold: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """Mock similarity search."""
        return {
            "query": normalized_text,
            "results": [],
            "total_hits": 0,
            "threshold": threshold,
            "search_type": "similarity_mock",
            "processing_time_ms": 1,
            "warnings": ["Similarity search not available - using mock"],
        }

    def get_metrics(self) -> SearchMetrics:
        """Get mock search metrics."""
        return SearchMetrics()

    def reset_metrics(self) -> None:
        """Reset mock search metrics."""
        pass