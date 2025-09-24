"""
Search layer contracts and data models.

Defines interfaces and data structures for hybrid search functionality.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union
from enum import Enum

from pydantic import BaseModel, Field

from ...contracts.base_contracts import NormalizationResult


class SearchMode(Enum):
    """Search mode enumeration"""
    AC = "ac"  # Exact/almost-exact search
    VECTOR = "vector"  # kNN vector search
    HYBRID = "hybrid"  # Both modes with escalation
    FUZZY = "fuzzy"  # Fuzzy search using rapidfuzz
    FALLBACK_AC = "fallback_ac"
    FALLBACK_VECTOR = "fallback_vector"


@dataclass
class Candidate:
    """Search candidate result"""
    
    doc_id: str
    score: float
    text: str
    entity_type: str
    metadata: Dict[str, Any]
    search_mode: SearchMode
    match_fields: List[str]  # Fields that matched
    confidence: float = 0.0
    trace: Optional[Dict[str, Any]] = None  # Trace information for debugging
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        result = {
            "doc_id": self.doc_id,
            "score": self.score,
            "text": self.text,
            "entity_type": self.entity_type,
            "metadata": self.metadata,
            "search_mode": self.search_mode.value,
            "match_fields": self.match_fields,
            "confidence": self.confidence,
        }
        if self.trace:
            result["trace"] = self.trace
        return result


class SearchOpts(BaseModel):
    """Search options and parameters"""
    
    # Basic search parameters
    top_k: int = Field(default=50, ge=1, le=1000, description="Maximum number of results")
    threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum score threshold")
    search_mode: SearchMode = Field(default=SearchMode.HYBRID, description="Search mode")

    @property
    def max_results(self) -> int:
        """Alias for top_k for backwards compatibility"""
        return self.top_k
    
    # AC search parameters
    ac_boost: float = Field(default=1.2, ge=0.1, le=5.0, description="AC search score boost")
    ac_fuzziness: int = Field(default=1, ge=0, le=3, description="AC search fuzziness level")
    ac_min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="AC minimum score")
    
    # Vector search parameters
    vector_boost: float = Field(default=1.0, ge=0.1, le=5.0, description="Vector search score boost")
    vector_min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Vector minimum score")
    vector_ef_search: int = Field(default=100, ge=10, le=1000, description="Vector search ef parameter")
    
    # Hybrid search parameters
    enable_escalation: bool = Field(default=True, description="Enable AC->Vector escalation")
    escalation_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="AC score threshold for escalation")
    max_escalation_results: int = Field(default=100, ge=10, le=500, description="Max results for escalation")
    
    # Filtering parameters
    entity_types: Optional[List[str]] = Field(default=None, description="Filter by entity types")
    metadata_filters: Optional[Dict[str, Any]] = Field(default=None, description="Metadata filters")
    
    # Performance parameters
    timeout_ms: int = Field(default=5000, ge=100, le=30000, description="Search timeout in milliseconds")
    enable_highlighting: bool = Field(default=False, description="Enable search result highlighting")
    
    class Config:
        use_enum_values = True


class SearchMetrics(BaseModel):
    """Search performance metrics"""
    
    # Request counters
    total_requests: int = 0
    ac_requests: int = 0
    vector_requests: int = 0
    hybrid_requests: int = 0
    
    # Success/failure counters
    successful_requests: int = 0
    failed_requests: int = 0
    escalation_triggered: int = 0
    
    # Performance metrics
    avg_ac_latency_ms: float = 0.0
    avg_vector_latency_ms: float = 0.0
    avg_hybrid_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    
    # Hit rate metrics
    ac_hit_rate: float = 0.0  # Percentage of AC requests with results above threshold
    vector_hit_rate: float = 0.0  # Percentage of vector requests with results above threshold
    hybrid_hit_rate: float = 0.0  # Overall hybrid hit rate
    
    # Result quality metrics
    avg_score: float = 0.0
    avg_results_per_request: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return self.model_dump()


class SearchService(ABC):
    """Base interface for search services"""
    
    @abstractmethod
    async def find_candidates(
        self, 
        normalized: NormalizationResult, 
        text: str, 
        opts: SearchOpts
    ) -> List[Candidate]:
        """
        Find search candidates based on normalized result and original text.
        
        Args:
            normalized: Normalized text result from normalization layer
            text: Original input text
            opts: Search options and parameters
            
        Returns:
            List of search candidates sorted by score (descending)
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check search service health status"""
        pass
    
    @abstractmethod
    def get_metrics(self) -> SearchMetrics:
        """Get current search metrics"""
        pass
    
    @abstractmethod
    def reset_metrics(self) -> None:
        """Reset search metrics"""
        pass


class ElasticsearchAdapter(ABC):
    """Base interface for Elasticsearch adapters"""
    
    @abstractmethod
    async def search(
        self,
        query: Any,
        opts: SearchOpts,
        index_name: str = "watchlist"
    ) -> List[Candidate]:
        """Execute search query"""
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """Check Elasticsearch connection health"""
        pass
    
    @abstractmethod
    def get_latency_stats(self) -> Dict[str, float]:
        """Get adapter-specific latency statistics"""
        pass
