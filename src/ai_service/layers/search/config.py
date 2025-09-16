"""
Search layer configuration models.

Defines configuration structures for hybrid search functionality.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator


class ElasticsearchConfig(BaseModel):
    """Elasticsearch connection configuration"""
    
    # Connection settings
    hosts: List[str] = Field(default=["localhost:9200"], description="Elasticsearch hosts")
    username: Optional[str] = Field(default=None, description="Elasticsearch username")
    password: Optional[str] = Field(default=None, description="Elasticsearch password")
    api_key: Optional[str] = Field(default=None, description="Elasticsearch API key")
    ca_certs: Optional[str] = Field(default=None, description="Path to CA certificates")
    verify_certs: bool = Field(default=True, description="Verify SSL certificates")
    
    # Connection pool settings
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    timeout: int = Field(default=30, ge=1, le=300, description="Connection timeout in seconds")
    
    # Index settings
    default_index: str = Field(default="watchlist", description="Default index name")
    ac_index: str = Field(default="watchlist_ac", description="AC search index name")
    vector_index: str = Field(default="watchlist_vector", description="Vector search index name")
    
    @validator("hosts")
    def validate_hosts(cls, v):
        """Validate hosts format"""
        if not v:
            raise ValueError("At least one host must be specified")
        for host in v:
            if ":" not in host:
                raise ValueError(f"Host must include port: {host}")
        return v


class ACSearchConfig(BaseModel):
    """AC (exact/almost-exact) search configuration"""
    
    # Search parameters
    boost: float = Field(default=1.2, ge=0.1, le=5.0, description="Score boost for AC matches")
    fuzziness: int = Field(default=1, ge=0, le=3, description="Fuzziness level (0=exact, 1-3=fuzzy)")
    min_score: float = Field(default=0.6, ge=0.0, le=1.0, description="Minimum score threshold")
    
    # Field weights for multi-field search
    field_weights: Dict[str, float] = Field(
        default={
            "normalized_text": 2.0,
            "aliases": 1.5,
            "legal_names": 1.8,
            "original_text": 1.0,
        },
        description="Field weights for scoring"
    )
    
    # Query settings
    enable_phrase_queries: bool = Field(default=True, description="Enable phrase queries")
    enable_wildcard_queries: bool = Field(default=False, description="Enable wildcard queries")
    enable_regex_queries: bool = Field(default=False, description="Enable regex queries")
    
    # Performance settings
    max_query_terms: int = Field(default=25, ge=1, le=100, description="Maximum query terms")
    tie_breaker: float = Field(default=0.3, ge=0.0, le=1.0, description="DisMax tie breaker")


class VectorSearchConfig(BaseModel):
    """Vector (kNN) search configuration"""
    
    # Vector search parameters
    boost: float = Field(default=1.0, ge=0.1, le=5.0, description="Score boost for vector matches")
    min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum score threshold")
    ef_search: int = Field(default=100, ge=10, le=1000, description="HNSW ef_search parameter")
    
    # Vector field settings
    vector_field: str = Field(default="dense_vector", description="Vector field name")
    vector_dimension: int = Field(default=384, ge=64, le=4096, description="Vector dimension")
    
    # Similarity settings
    similarity_type: str = Field(default="cosine", description="Similarity type (cosine, dot_product, l2_norm)")
    similarity_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Similarity threshold")
    
    # Performance settings
    max_candidates: int = Field(default=1000, ge=10, le=10000, description="Maximum candidates to evaluate")
    enable_reranking: bool = Field(default=True, description="Enable result reranking")


class HybridSearchConfig(BaseModel):
    """Hybrid search configuration combining AC and Vector search"""
    
    # Service configuration
    service_name: str = Field(default="hybrid_search", description="Service name for logging")
    enable_logging: bool = Field(default=True, description="Enable detailed logging")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    
    # Search mode settings
    default_mode: str = Field(default="hybrid", description="Default search mode")
    enable_escalation: bool = Field(default=True, description="Enable AC->Vector escalation")
    escalation_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="AC score threshold for escalation")
    max_escalation_results: int = Field(default=100, ge=10, le=500, description="Max results for escalation")
    
    # Result processing
    enable_deduplication: bool = Field(default=True, description="Enable result deduplication")
    dedup_field: str = Field(default="doc_id", description="Field to use for deduplication")
    enable_reranking: bool = Field(default=True, description="Enable final result reranking")
    
    # Performance settings
    request_timeout_ms: int = Field(default=5000, ge=100, le=30000, description="Request timeout in milliseconds")
    max_concurrent_requests: int = Field(default=10, ge=1, le=100, description="Maximum concurrent requests")
    
    # Fallback settings
    enable_fallback: bool = Field(default=True, description="Enable fallback to local indexes")
    fallback_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Score threshold for fallback")
    
    # Elasticsearch configuration
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    
    # Search mode configurations
    ac_search: ACSearchConfig = Field(default_factory=ACSearchConfig)
    vector_search: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    
    # Metrics configuration
    metrics_window_size: int = Field(default=1000, ge=100, le=10000, description="Metrics rolling window size")
    metrics_retention_hours: int = Field(default=24, ge=1, le=168, description="Metrics retention in hours")
    
    @validator("default_mode")
    def validate_default_mode(cls, v):
        """Validate default search mode"""
        valid_modes = ["ac", "vector", "hybrid"]
        if v not in valid_modes:
            raise ValueError(f"default_mode must be one of {valid_modes}")
        return v
    
    def get_elasticsearch_config(self) -> Dict[str, Any]:
        """Get Elasticsearch configuration as dictionary"""
        return self.elasticsearch.model_dump()
    
    def get_ac_config(self) -> Dict[str, Any]:
        """Get AC search configuration as dictionary"""
        return self.ac_search.model_dump()
    
    def get_vector_config(self) -> Dict[str, Any]:
        """Get vector search configuration as dictionary"""
        return self.vector_search.model_dump()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert entire configuration to dictionary"""
        return self.model_dump()


# Default configuration instance
DEFAULT_HYBRID_SEARCH_CONFIG = HybridSearchConfig()
