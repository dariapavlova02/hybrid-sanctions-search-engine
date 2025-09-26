"""Search layer configuration models.

Defines configuration structures for hybrid search functionality and provides
helpers to load settings from environment variables or YAML files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Union

import yaml
from pydantic import BaseModel, Field, field_validator


class ElasticsearchConfig(BaseModel):
    """Elasticsearch connection configuration"""

    # Connection settings
    hosts: List[str] = Field(default=["localhost:9200"], description="Elasticsearch hosts")
    username: Optional[str] = Field(default=None, description="Elasticsearch username")
    password: Optional[str] = Field(default=None, description="Elasticsearch password")
    api_key: Optional[str] = Field(default=None, description="Elasticsearch API key")
    ca_certs: Optional[str] = Field(default=None, description="Path to CA certificates")
    verify_certs: bool = Field(default=True, description="Verify SSL certificates")
    scheme: Optional[str] = Field(default=None, description="Explicit connection scheme (http/https)")

    # Connection pool settings
    max_retries: int = Field(default=3, ge=0, le=10, description="Maximum retry attempts")
    retry_on_timeout: bool = Field(default=True, description="Retry on timeout")
    timeout: int = Field(default=30, ge=1, le=300, description="Connection timeout in seconds")
    healthcheck_path: str = Field(default="/_cluster/health", description="Path used for health checks")
    smoke_test_timeout: float = Field(default=5.0, ge=0.1, le=30.0, description="Timeout (seconds) for smoke tests")

    # Index settings
    default_index: str = Field(default="watchlist", description="Default index name")
    ac_index: str = Field(default="ai_service_ac_patterns", description="AC search index name")
    vector_index: str = Field(default="vectors", description="Vector search index name")
    
    @field_validator("hosts")
    @classmethod
    def validate_hosts(cls, v):
        """Validate hosts format"""
        if not v:
            raise ValueError("At least one host must be specified")
        for host in v:
            if ":" not in host and not host.startswith("http"):
                raise ValueError(f"Host must include port or scheme: {host}")
        return v

    def normalized_hosts(self) -> List[str]:
        """Return hosts with explicit scheme."""
        normalized = []
        for host in self.hosts:
            if host.startswith("http://") or host.startswith("https://"):
                normalized.append(host.rstrip("/"))
                continue
            # Use explicit scheme if set, otherwise default to http
            # Note: verify_certs is about certificate validation, not connection scheme
            base_scheme = self.scheme or "http"
            normalized.append(f"{base_scheme}://{host.strip('/')}".rstrip("/"))
        return normalized

    @staticmethod
    def _parse_bool(value: str) -> bool:
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    @classmethod
    def from_sources(
        cls,
        data: Optional[Dict[str, Any]] = None,
        env: Optional[Mapping[str, str]] = None,
    ) -> "ElasticsearchConfig":
        """Create configuration from combined YAML/env sources."""

        env = dict(env or {})
        payload: Dict[str, Any] = dict(data or {})

        # Environment overrides
        if env.get("ES_HOSTS"):
            payload["hosts"] = [h.strip() for h in env["ES_HOSTS"].split(",") if h.strip()]
        elif env.get("ELASTICSEARCH_HOSTS"):
            # Support ELASTICSEARCH_HOSTS for backward compatibility
            hosts_str = env["ELASTICSEARCH_HOSTS"]
            if hosts_str.startswith("http://") or hosts_str.startswith("https://"):
                payload["hosts"] = [hosts_str.strip()]
            else:
                payload["hosts"] = [h.strip() for h in hosts_str.split(",") if h.strip()]
        else:
            # Auto-detect environment and set appropriate Elasticsearch host
            import socket
            import os

            try:
                # First check if we're running in Docker (production)
                if os.path.exists('/.dockerenv') or os.environ.get('APP_ENV') == 'production':
                    # Inside Docker container - use service name for internal communication
                    payload["hosts"] = ["http://elasticsearch:9200"]
                else:
                    # Local development - check if we can detect production server
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)

                    if local_ip == "95.217.84.234":
                        # On production server but outside Docker - use external IP
                        payload["hosts"] = ["http://95.217.84.234:9200"]
                    else:
                        # Local development environment
                        payload["hosts"] = ["http://localhost:9200"]
            except Exception:
                # Fallback for any detection issues
                payload["hosts"] = ["http://localhost:9200"]

        str_overrides = {
            "username": "ES_USERNAME",
            "password": "ES_PASSWORD",
            "api_key": "ES_API_KEY",
            "ca_certs": "ES_CA_CERTS",
            "default_index": "ES_DEFAULT_INDEX",
            "ac_index": "ES_AC_INDEX",
            "vector_index": "ES_VECTOR_INDEX",
            "scheme": "ES_SCHEME",
            "healthcheck_path": "ES_HEALTHCHECK_PATH",
        }

        for field_name, env_key in str_overrides.items():
            if env_key in env and env[env_key]:
                payload[field_name] = env[env_key]

        int_overrides = {
            "timeout": "ES_TIMEOUT",
            "max_retries": "ES_MAX_RETRIES",
        }
        for field_name, env_key in int_overrides.items():
            if env_key in env and env[env_key]:
                try:
                    payload[field_name] = int(env[env_key])
                except ValueError:
                    raise ValueError(f"Invalid integer value for {env_key}: {env[env_key]}") from None

        float_overrides = {"smoke_test_timeout": "ES_SMOKE_TEST_TIMEOUT"}
        for field_name, env_key in float_overrides.items():
            if env_key in env and env[env_key]:
                try:
                    payload[field_name] = float(env[env_key])
                except ValueError:
                    raise ValueError(f"Invalid float value for {env_key}: {env[env_key]}") from None

        bool_overrides = {
            "verify_certs": "ES_VERIFY_CERTS",
            "retry_on_timeout": "ES_RETRY_ON_TIMEOUT",
        }
        for field_name, env_key in bool_overrides.items():
            if env_key in env and env[env_key]:
                payload[field_name] = cls._parse_bool(env[env_key])

        return cls(**payload)


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
    vector_field: str = Field(default="vector", description="Vector field name")
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
    escalation_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="AC score threshold for escalation")
    max_escalation_results: int = Field(default=100, ge=10, le=500, description="Max results for escalation")
    
    # AC patterns in Elasticsearch
    enable_ac_es: bool = Field(default=True, description="Enable AC patterns search in Elasticsearch")
    
    # Vector fallback settings
    enable_vector_fallback: bool = Field(default=True, description="Enable vector fallback when AC search fails")
    vector_cos_threshold: float = Field(default=0.45, ge=0.0, le=1.0, description="Cosine similarity threshold for vector fallback")
    vector_fallback_max_results: int = Field(default=50, ge=5, le=200, description="Maximum results for vector fallback")
    enable_rapidfuzz_rerank: bool = Field(default=True, description="Enable RapidFuzz reranking for vector results")
    enable_dob_id_anchors: bool = Field(default=True, description="Enable DoB/ID anchor checking for vector results")
    
    # Contract validation
    strict_candidate_contract: bool = Field(default=True, description="Enforce strict candidate contract validation")
    
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
    fallback_timeout_ms: int = Field(default=2000, ge=100, le=10000, description="Fallback search timeout in milliseconds")
    fallback_max_results: int = Field(default=100, ge=10, le=500, description="Maximum results from fallback search")
    enable_fallback_health_check: bool = Field(default=True, description="Enable health checks for fallback services")
    
    # Vector fallback settings
    enable_vector_fallback: bool = Field(default=True, description="Enable vector search fallback")
    vector_fallback_threshold: float = Field(default=0.4, ge=0.0, le=1.0, description="Score threshold for vector fallback")
    vector_fallback_timeout_ms: int = Field(default=3000, ge=100, le=15000, description="Vector fallback search timeout in milliseconds")
    vector_fallback_max_results: int = Field(default=50, ge=5, le=200, description="Maximum results from vector fallback search")
    
    # Embeddings integration settings
    enable_embedding_cache: bool = Field(default=True, description="Enable caching for generated query vectors")
    embedding_cache_size: int = Field(default=1000, ge=100, le=10000, description="Maximum number of cached embeddings")
    embedding_cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400, description="Embedding cache TTL in seconds")
    enable_embedding_preprocessing: bool = Field(default=True, description="Enable query preprocessing for embeddings")
    embedding_batch_size: int = Field(default=1, ge=1, le=32, description="Batch size for embedding generation")
    
    # Search result caching settings
    enable_search_cache: bool = Field(default=True, description="Enable caching for search results")
    search_cache_size: int = Field(default=500, ge=50, le=5000, description="Maximum number of cached search results")
    search_cache_ttl_seconds: int = Field(default=1800, ge=60, le=86400, description="Search result cache TTL in seconds")
    
    # Query optimization settings
    enable_query_optimization: bool = Field(default=True, description="Enable query optimization features")
    ac_query_boost_factor: float = Field(default=1.0, ge=0.1, le=5.0, description="AC query boost factor")
    vector_query_boost_factor: float = Field(default=1.0, ge=0.1, le=5.0, description="Vector query boost factor")
    bm25_query_boost_factor: float = Field(default=1.0, ge=0.1, le=5.0, description="BM25 query boost factor")
    enable_query_caching: bool = Field(default=True, description="Enable query result caching")
    query_cache_size: int = Field(default=1000, ge=100, le=10000, description="Maximum number of cached queries")
    query_cache_ttl_seconds: int = Field(default=3600, ge=60, le=86400, description="Query cache TTL in seconds")
    
    # Security settings
    enable_elasticsearch_auth: bool = Field(default=False, description="Enable Elasticsearch authentication")
    es_auth_type: str = Field(default="basic", description="Elasticsearch authentication type (basic, api_key, ssl)")
    es_username: Optional[str] = Field(default=None, description="Elasticsearch username")
    es_password: Optional[str] = Field(default=None, description="Elasticsearch password")
    es_api_key: Optional[str] = Field(default=None, description="Elasticsearch API key")
    es_ca_certs: Optional[str] = Field(default=None, description="Elasticsearch CA certificates path")
    enable_ssl_verification: bool = Field(default=True, description="Enable SSL certificate verification")
    enable_audit_logging: bool = Field(default=False, description="Enable audit logging for search operations")
    enable_rate_limiting: bool = Field(default=False, description="Enable rate limiting for search requests")
    rate_limit_requests_per_minute: int = Field(default=100, ge=10, le=10000, description="Rate limit requests per minute")
    enable_query_validation: bool = Field(default=True, description="Enable query validation and sanitization")
    enable_sensitive_data_filtering: bool = Field(default=True, description="Enable sensitive data filtering in results")
    
    # Elasticsearch configuration
    elasticsearch: ElasticsearchConfig = Field(default_factory=ElasticsearchConfig)
    
    # Search mode configurations
    ac_search: ACSearchConfig = Field(default_factory=ACSearchConfig)
    vector_search: VectorSearchConfig = Field(default_factory=VectorSearchConfig)
    
    # Metrics configuration
    metrics_window_size: int = Field(default=1000, ge=100, le=10000, description="Metrics rolling window size")
    metrics_retention_hours: int = Field(default=24, ge=1, le=168, description="Metrics retention in hours")
    
    @field_validator("default_mode")
    @classmethod
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

    @classmethod
    def from_env(
        cls,
        env: Optional[Mapping[str, str]] = None,
        settings_path: Optional[Union[str, Path]] = None,
    ) -> "HybridSearchConfig":
        """Load configuration from YAML and environment overrides."""

        env_map = dict(env or os.environ)
        settings_locations: List[Path] = []

        if settings_path:
            settings_locations.append(Path(settings_path))
        elif env_map.get("AI_SEARCH_SETTINGS_PATH"):
            settings_locations.append(Path(env_map["AI_SEARCH_SETTINGS_PATH"]))

        settings_locations.extend(
            [
                Path("config/settings.yaml"),
                Path("config/search_settings.yaml"),
                Path("settings.yaml"),
            ]
        )

        yaml_payload: Dict[str, Any] = {}
        for candidate in settings_locations:
            if candidate and candidate.exists():
                with candidate.open("r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f) or {}
                yaml_payload = raw.get("search", raw)
                break

        es_settings = yaml_payload.get("elasticsearch", {})
        ac_settings = yaml_payload.get("ac_search", {})
        vector_settings = yaml_payload.get("vector_search", {})

        config_payload: Dict[str, Any] = yaml_payload.copy()
        config_payload["elasticsearch"] = ElasticsearchConfig.from_sources(
            es_settings,
            env=env_map,
        )

        if env_map.get("ES_AC_FIELD_WEIGHTS"):
            weights = {}
            for item in env_map["ES_AC_FIELD_WEIGHTS"].split(","):
                if not item:
                    continue
                name, _, weight = item.partition(":")
                if name and weight:
                    try:
                        weights[name.strip()] = float(weight)
                    except ValueError:
                        continue
            if weights:
                ac_settings = dict(ac_settings)
                ac_settings["field_weights"] = weights

        if env_map.get("ES_VECTOR_DIMENSION"):
            vector_settings = dict(vector_settings)
            try:
                vector_settings["vector_dimension"] = int(env_map["ES_VECTOR_DIMENSION"])
            except ValueError:
                pass

        if ac_settings:
            config_payload["ac_search"] = {**ac_settings}
        if vector_settings:
            config_payload["vector_search"] = {**vector_settings}

        return cls(**config_payload)


# Default configuration instance
DEFAULT_HYBRID_SEARCH_CONFIG = HybridSearchConfig()
