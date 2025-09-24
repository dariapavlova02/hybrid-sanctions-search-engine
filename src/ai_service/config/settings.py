"""
Configuration settings for AI Service
Structured configuration classes with validation and type hints
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

from ..constants import (
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL,
    DEFAULT_LANGUAGE,
    DEFAULT_MAX_INPUT_LENGTH,
    FALLBACK_LANGUAGE,
)
from ..constants import INTEGRATION_CONFIG as INT_CONSTANTS
from ..constants import LOGGING_CONFIG as LOG_CONSTANTS
from ..constants import PERFORMANCE_CONFIG as PERF_CONSTANTS
from ..constants import SECURITY_CONFIG as SEC_CONSTANTS
from ..constants import (
    SUPPORTED_LANGUAGES,
)
from .hot_reload import HotReloadableConfig


@dataclass
class ServiceConfig:
    """Service configuration settings"""

    max_input_length: int = DEFAULT_MAX_INPUT_LENGTH
    supported_languages: List[str] = field(
        default_factory=lambda: SUPPORTED_LANGUAGES.copy()
    )
    default_language: str = DEFAULT_LANGUAGE
    fallback_language: str = FALLBACK_LANGUAGE
    enable_advanced_features: bool = True
    enable_morphology: bool = True
    enable_transliterations: bool = True
    preserve_names: bool = True
    clean_unicode: bool = True

    # Feature Flags - управляемые из env
    enable_aho_corasick: bool = field(default_factory=lambda: os.getenv("ENABLE_AHO_CORASICK", "false").lower() == "true")
    aho_corasick_confidence_bonus: float = field(default_factory=lambda: float(os.getenv("AHO_CORASICK_CONFIDENCE_BONUS", "0.3")))
    prioritize_quality: bool = field(default_factory=lambda: os.getenv("PRIORITIZE_QUALITY", "true").lower() == "true")
    enable_faiss_index: bool = field(default_factory=lambda: os.getenv("ENABLE_FAISS_INDEX", "true").lower() == "true")
    enable_smart_filter: bool = field(default_factory=lambda: os.getenv("ENABLE_SMART_FILTER", "true").lower() == "true")
    enable_variants: bool = field(default_factory=lambda: os.getenv("ENABLE_VARIANTS", "false").lower() == "true")
    enable_embeddings: bool = field(default_factory=lambda: os.getenv("ENABLE_EMBEDDINGS", "false").lower() == "true")
    enable_decision_engine: bool = field(default_factory=lambda: os.getenv("ENABLE_DECISION_ENGINE", "false").lower() == "true")
    enable_search: bool = field(default_factory=lambda: os.getenv("ENABLE_SEARCH", "true").lower() == "true")
    enable_metrics: bool = field(default_factory=lambda: os.getenv("ENABLE_METRICS", "true").lower() == "true")
    allow_smart_filter_skip: bool = field(default_factory=lambda: os.getenv("ALLOW_SMART_FILTER_SKIP", "false").lower() == "true")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_input_length": self.max_input_length,
            "supported_languages": self.supported_languages,
            "default_language": self.default_language,
            "fallback_language": self.fallback_language,
            "enable_advanced_features": self.enable_advanced_features,
            "enable_morphology": self.enable_morphology,
            "enable_transliterations": self.enable_transliterations,
            "preserve_names": self.preserve_names,
            "clean_unicode": self.clean_unicode,
            "enable_aho_corasick": self.enable_aho_corasick,
            "aho_corasick_confidence_bonus": self.aho_corasick_confidence_bonus,
            "prioritize_quality": self.prioritize_quality,
            "enable_faiss_index": self.enable_faiss_index,
            "enable_smart_filter": self.enable_smart_filter,
            "enable_variants": self.enable_variants,
            "enable_embeddings": self.enable_embeddings,
            "enable_decision_engine": self.enable_decision_engine,
            "enable_search": self.enable_search,
            "enable_metrics": self.enable_metrics,
            "allow_smart_filter_skip": self.allow_smart_filter_skip,
        }


@dataclass
class DatabaseConfig:
    """Database configuration settings"""

    host: str = "localhost"
    port: int = 5432
    database: str = "ai_service"
    username: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "username": self.username,
            "password": "***" if self.password else "",
            "pool_size": self.pool_size,
            "max_overflow": self.max_overflow,
            "echo": self.echo,
        }


@dataclass
class LoggingConfig:
    """Logging configuration settings"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_logging: bool = True
    console_logging: bool = True
    log_dir: str = "logs"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    environment: str = "development"

    def __post_init__(self):
        """Post-initialization setup"""
        if self.environment == "production":
            self.level = "WARNING"
            self.console_logging = False
        elif self.environment == "staging":
            self.level = "INFO"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "level": self.level,
            "format": self.format,
            "date_format": self.date_format,
            "file_logging": self.file_logging,
            "console_logging": self.console_logging,
            "log_dir": self.log_dir,
            "max_file_size": self.max_file_size,
            "backup_count": self.backup_count,
            "environment": self.environment,
        }


@dataclass
class SecurityConfig:
    """Security configuration settings"""

    max_input_length: int = 10000
    sanitize_input: bool = True
    rate_limit_enabled: bool = True
    max_requests_per_minute: int = 100
    admin_api_key: str = "your-secure-api-key-here"
    enable_cors: bool = True
    allowed_origins: List[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )
    enable_https: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_input_length": self.max_input_length,
            "sanitize_input": self.sanitize_input,
            "rate_limit_enabled": self.rate_limit_enabled,
            "max_requests_per_minute": self.max_requests_per_minute,
            "admin_api_key": "***" if self.admin_api_key else "",
            "enable_cors": self.enable_cors,
            "allowed_origins": self.allowed_origins,
            "enable_https": self.enable_https,
            "ssl_cert_path": self.ssl_cert_path,
            "ssl_key_path": self.ssl_key_path,
        }


@dataclass
class PerformanceConfig:
    """Performance configuration settings"""

    max_concurrent_requests: int = PERF_CONSTANTS["max_concurrent_requests"]
    batch_size: int = PERF_CONSTANTS["batch_size"]
    memory_limit_mb: int = PERF_CONSTANTS["memory_limit_mb"]
    cpu_limit_percent: int = PERF_CONSTANTS["cpu_limit_percent"]
    cache_size: int = DEFAULT_CACHE_SIZE
    cache_ttl: int = DEFAULT_CACHE_TTL
    enable_async: bool = True
    worker_timeout: int = 300
    request_timeout: int = 30

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "max_concurrent_requests": self.max_concurrent_requests,
            "batch_size": self.batch_size,
            "memory_limit_mb": self.memory_limit_mb,
            "cpu_limit_percent": self.cpu_limit_percent,
            "cache_size": self.cache_size,
            "cache_ttl": self.cache_ttl,
            "enable_async": self.enable_async,
            "worker_timeout": self.worker_timeout,
            "request_timeout": self.request_timeout,
        }


@dataclass
class IntegrationConfig:
    """Integration configuration settings"""

    api_version: str = "v1"
    cors_enabled: bool = True
    health_check_interval: int = 60
    metrics_enabled: bool = True
    allowed_origins: List[str] = field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:8080"]
    )
    enable_docs: bool = True
    docs_url: str = "/docs"
    redoc_url: str = "/redoc"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "api_version": self.api_version,
            "cors_enabled": self.cors_enabled,
            "health_check_interval": self.health_check_interval,
            "metrics_enabled": self.metrics_enabled,
            "allowed_origins": self.allowed_origins,
            "enable_docs": self.enable_docs,
            "docs_url": self.docs_url,
            "redoc_url": self.redoc_url,
        }


@dataclass
class LanguageConfig:
    """Language detection configuration settings"""
    
    # Пороги для долей символов
    min_cyr_ratio: float = field(default_factory=lambda: float(os.getenv("LANG_MIN_CYR_RATIO", "0.25")))
    min_lat_ratio: float = field(default_factory=lambda: float(os.getenv("LANG_MIN_LAT_RATIO", "0.25")))
    mixed_gap: float = field(default_factory=lambda: float(os.getenv("LANG_MIXED_GAP", "0.15")))
    
    # Бонусы за специфические буквы
    prefer_uk_chars_bonus: float = field(default_factory=lambda: float(os.getenv("LANG_UK_CHARS_BONUS", "0.05")))
    prefer_ru_chars_bonus: float = field(default_factory=lambda: float(os.getenv("LANG_RU_CHARS_BONUS", "0.05")))
    
    # Минимальная уверенность
    min_confidence: float = field(default_factory=lambda: float(os.getenv("LANG_MIN_CONFIDENCE", "0.55")))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "min_cyr_ratio": self.min_cyr_ratio,
            "min_lat_ratio": self.min_lat_ratio,
            "mixed_gap": self.mixed_gap,
            "prefer_uk_chars_bonus": self.prefer_uk_chars_bonus,
            "prefer_ru_chars_bonus": self.prefer_ru_chars_bonus,
            "min_confidence": self.min_confidence,
        }


@dataclass
class DeploymentConfig:
    """Deployment configuration settings"""

    environment: str = "development"
    debug_mode: bool = True
    auto_reload: bool = True
    workers: int = 1
    host: str = "0.0.0.0"
    port: int = 8000
    enable_uvicorn_logging: bool = True
    log_level: str = "info"

    def __post_init__(self):
        """Post-initialization setup"""
        if self.environment == "production":
            self.debug_mode = False
            self.auto_reload = False
            self.workers = int(os.getenv("WORKERS", "4"))
            self.log_level = "warning"
        elif self.environment == "staging":
            self.debug_mode = False
            self.auto_reload = False
            self.workers = int(os.getenv("WORKERS", "2"))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "environment": self.environment,
            "debug_mode": self.debug_mode,
            "auto_reload": self.auto_reload,
            "workers": self.workers,
            "host": self.host,
            "port": self.port,
            "enable_uvicorn_logging": self.enable_uvicorn_logging,
            "log_level": self.log_level,
        }


class EmbeddingConfig(BaseModel):
    """Embedding configuration settings"""

    model_config = {"validate_assignment": True}

    model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    device: str = "cpu"
    batch_size: int = 64
    enable_index: bool = False  # индексацию оставляем как опцию
    extra_models: List[str] = []  # опционально разрешённые альтернативы
    warmup_on_init: bool = False  # Pre-load model and run dummy encoding on initialization
    
    def model_dump(self) -> Dict[str, Any]:
        """Return model as dictionary"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size,
            "enable_index": self.enable_index,
            "extra_models": self.extra_models,
            "warmup_on_init": self.warmup_on_init
        }


class NormalizationConfig(BaseModel):
    """Normalization service configuration settings"""
    
    model_config = {"validate_assignment": True}
    
    max_tokens: int = Field(default_factory=lambda: int(os.getenv("NORMALIZATION_MAX_TOKENS", "100")))
    preserve_names: bool = Field(default_factory=lambda: os.getenv("NORMALIZATION_PRESERVE_NAMES", "true").lower() == "true")
    clean_unicode: bool = Field(default_factory=lambda: os.getenv("NORMALIZATION_CLEAN_UNICODE", "true").lower() == "true")
    enable_morphology: bool = Field(default_factory=lambda: os.getenv("NORMALIZATION_ENABLE_MORPHOLOGY", "true").lower() == "true")
    enable_transliterations: bool = Field(default_factory=lambda: os.getenv("NORMALIZATION_ENABLE_TRANSLITERATIONS", "true").lower() == "true")
    remove_stop_words: bool = Field(default_factory=lambda: os.getenv("NORMALIZATION_REMOVE_STOP_WORDS", "true").lower() == "true")
    enable_advanced_features: bool = Field(default_factory=lambda: os.getenv("NORMALIZATION_ENABLE_ADVANCED_FEATURES", "true").lower() == "true")
    
    def model_dump(self) -> Dict[str, Any]:
        """Return model as dictionary"""
        return {
            "max_tokens": self.max_tokens,
            "preserve_names": self.preserve_names,
            "clean_unicode": self.clean_unicode,
            "enable_morphology": self.enable_morphology,
            "enable_transliterations": self.enable_transliterations,
            "remove_stop_words": self.remove_stop_words,
            "enable_advanced_features": self.enable_advanced_features
        }


class SearchConfig(BaseModel, HotReloadableConfig):
    """Search layer configuration settings with hot-reloading support"""
    
    model_config = {"validate_assignment": True}
    
    # Hot reload configuration
    config_path: Optional[Path] = Field(default=None, exclude=True)
    
    # Elasticsearch connection
    es_hosts: List[str] = Field(default_factory=lambda: os.getenv("ES_HOSTS", "localhost:9200").split(","))
    es_username: Optional[str] = Field(default_factory=lambda: os.getenv("ES_USERNAME"))
    es_password: Optional[str] = Field(default_factory=lambda: os.getenv("ES_PASSWORD"))
    es_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("ES_API_KEY"))
    es_verify_certs: bool = Field(default_factory=lambda: os.getenv("ES_VERIFY_CERTS", "true").lower() == "true")
    es_timeout: int = Field(default_factory=lambda: int(os.getenv("ES_TIMEOUT", "30")))
    
    # Search settings
    enable_hybrid_search: bool = Field(default_factory=lambda: os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true")
    enable_escalation: bool = Field(default_factory=lambda: os.getenv("ENABLE_ESCALATION", "true").lower() == "true")
    escalation_threshold: float = Field(default_factory=lambda: float(os.getenv("ESCALATION_THRESHOLD", "0.8")))
    
    # Fallback settings
    enable_fallback: bool = Field(default_factory=lambda: os.getenv("ENABLE_FALLBACK", "true").lower() == "true")
    fallback_threshold: float = Field(default_factory=lambda: float(os.getenv("FALLBACK_THRESHOLD", "0.3")))
    
    # Vector search settings
    vector_dimension: int = Field(default_factory=lambda: int(os.getenv("VECTOR_DIMENSION", "384")))
    vector_similarity_threshold: float = Field(default_factory=lambda: float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.7")))
    
    # Performance settings
    max_concurrent_requests: int = Field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REQUESTS", "10")))
    request_timeout_ms: int = Field(default_factory=lambda: int(os.getenv("REQUEST_TIMEOUT_MS", "5000")))
    
    # Cache settings
    enable_embedding_cache: bool = Field(default_factory=lambda: os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true")
    embedding_cache_size: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_CACHE_SIZE", "1000")))
    embedding_cache_ttl_seconds: int = Field(default_factory=lambda: int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", "3600")))
    
    def __init__(self, **data):
        super().__init__(**data)
        # Initialize HotReloadableConfig attributes to avoid _watcher errors
        self._watcher = None
        self._last_reload = None
        self._reload_count = 0

    @property
    def elasticsearch(self):
        """Compatibility property to provide elasticsearch config for search services"""
        from ..layers.search.config import ElasticsearchConfig
        return ElasticsearchConfig(
            hosts=self.es_hosts,
            username=self.es_username,
            password=self.es_password,
            api_key=self.es_api_key,
            verify_certs=self.es_verify_certs,
            timeout=self.es_timeout
        )
    
    @field_validator('es_hosts')
    @classmethod
    def validate_hosts(cls, v: List[str]) -> List[str]:
        """Validate Elasticsearch hosts"""
        if not v:
            raise ValueError("At least one Elasticsearch host must be specified")
        
        # Validate host format
        for host in v:
            if not host or not isinstance(host, str):
                raise ValueError(f"Invalid host format: {host}")
            
            # Basic host validation (host:port format)
            if ':' not in host:
                raise ValueError(f"Host must include port: {host}")
            
            host_part, port_part = host.split(':', 1)
            if not host_part or not port_part:
                raise ValueError(f"Invalid host:port format: {host}")
            
            try:
                port = int(port_part)
                if not (1 <= port <= 65535):
                    raise ValueError(f"Port must be between 1 and 65535: {port}")
            except ValueError as e:
                raise ValueError(f"Invalid port number: {port_part}")
        
        return v
    
    @field_validator('es_timeout')
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout value"""
        if v <= 0:
            raise ValueError("Timeout must be positive")
        if v > 300:  # 5 minutes max
            raise ValueError("Timeout must not exceed 300 seconds")
        return v
    
    @field_validator('escalation_threshold', 'fallback_threshold', 'vector_similarity_threshold')
    @classmethod
    def validate_thresholds(cls, v: float) -> float:
        """Validate threshold values"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Thresholds must be between 0.0 and 1.0")
        return v
    
    @field_validator('vector_dimension')
    @classmethod
    def validate_vector_dimension(cls, v: int) -> int:
        """Validate vector dimension"""
        if v <= 0:
            raise ValueError("Vector dimension must be positive")
        if v > 4096:
            raise ValueError("Vector dimension must not exceed 4096")
        return v
    
    @field_validator('max_concurrent_requests')
    @classmethod
    def validate_max_concurrent_requests(cls, v: int) -> int:
        """Validate max concurrent requests"""
        if v <= 0:
            raise ValueError("Max concurrent requests must be positive")
        if v > 100:
            raise ValueError("Max concurrent requests must not exceed 100")
        return v
    
    @field_validator('request_timeout_ms')
    @classmethod
    def validate_request_timeout_ms(cls, v: int) -> int:
        """Validate request timeout in milliseconds"""
        if v <= 0:
            raise ValueError("Request timeout must be positive")
        if v > 30000:  # 30 seconds max
            raise ValueError("Request timeout must not exceed 30000 milliseconds")
        return v
    
    @field_validator('embedding_cache_size')
    @classmethod
    def validate_embedding_cache_size(cls, v: int) -> int:
        """Validate embedding cache size"""
        if v <= 0:
            raise ValueError("Embedding cache size must be positive")
        if v > 100000:
            raise ValueError("Embedding cache size must not exceed 100000")
        return v
    
    @field_validator('embedding_cache_ttl_seconds')
    @classmethod
    def validate_embedding_cache_ttl_seconds(cls, v: int) -> int:
        """Validate embedding cache TTL in seconds"""
        if v <= 0:
            raise ValueError("Embedding cache TTL must be positive")
        if v > 86400:  # 24 hours max
            raise ValueError("Embedding cache TTL must not exceed 86400 seconds")
        return v
    
    @model_validator(mode='after')
    def validate_configuration_consistency(self) -> 'SearchConfig':
        """Validate configuration consistency"""
        # Validate that escalation threshold is reasonable
        if self.enable_escalation and self.escalation_threshold <= 0.5:
            raise ValueError("Escalation threshold should be greater than 0.5 for meaningful escalation")
        
        # Validate that fallback threshold is reasonable
        if self.enable_fallback and self.fallback_threshold <= 0.1:
            raise ValueError("Fallback threshold should be greater than 0.1 for meaningful fallback")
        
        # Validate that vector similarity threshold is reasonable
        if self.vector_similarity_threshold <= 0.3:
            raise ValueError("Vector similarity threshold should be greater than 0.3 for meaningful similarity")
        
        # Validate that cache settings are reasonable
        if self.enable_embedding_cache and self.embedding_cache_size < 100:
            raise ValueError("Embedding cache size should be at least 100 for meaningful caching")
        
        return self
    
    def _reload_configuration(self) -> None:
        """Reload configuration from environment variables."""
        # Re-read all environment variables
        self.es_hosts = os.getenv("ES_HOSTS", "localhost:9200").split(",")
        self.es_username = os.getenv("ES_USERNAME")
        self.es_password = os.getenv("ES_PASSWORD")
        self.es_api_key = os.getenv("ES_API_KEY")
        self.es_verify_certs = os.getenv("ES_VERIFY_CERTS", "true").lower() == "true"
        self.es_timeout = int(os.getenv("ES_TIMEOUT", "30"))
        
        self.enable_hybrid_search = os.getenv("ENABLE_HYBRID_SEARCH", "true").lower() == "true"
        self.enable_escalation = os.getenv("ENABLE_ESCALATION", "true").lower() == "true"
        self.escalation_threshold = float(os.getenv("ESCALATION_THRESHOLD", "0.8"))
        
        self.enable_fallback = os.getenv("ENABLE_FALLBACK", "true").lower() == "true"
        self.fallback_threshold = float(os.getenv("FALLBACK_THRESHOLD", "0.3"))
        
        self.vector_dimension = int(os.getenv("VECTOR_DIMENSION", "384"))
        self.vector_similarity_threshold = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD", "0.7"))
        
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", "10"))
        self.request_timeout_ms = int(os.getenv("REQUEST_TIMEOUT_MS", "5000"))
        
        self.enable_embedding_cache = os.getenv("ENABLE_EMBEDDING_CACHE", "true").lower() == "true"
        self.embedding_cache_size = int(os.getenv("EMBEDDING_CACHE_SIZE", "1000"))
        self.embedding_cache_ttl_seconds = int(os.getenv("EMBEDDING_CACHE_TTL_SECONDS", "3600"))
        
        # Validate the reloaded configuration
        try:
            self.validate(self)
        except Exception as e:
            logger.error(f"Invalid configuration after reload: {e}")
            # Revert to previous values or use defaults
            # This is a simplified approach - in production, you might want more sophisticated rollback
    
    def model_dump(self) -> Dict[str, Any]:
        """Return model as dictionary"""
        return {
            "es_hosts": self.es_hosts,
            "es_username": self.es_username,
            "es_password": "***" if self.es_password else None,  # Hide password
            "es_api_key": "***" if self.es_api_key else None,  # Hide API key
            "es_verify_certs": self.es_verify_certs,
            "es_timeout": self.es_timeout,
            "enable_hybrid_search": self.enable_hybrid_search,
            "enable_escalation": self.enable_escalation,
            "escalation_threshold": self.escalation_threshold,
            "enable_fallback": self.enable_fallback,
            "fallback_threshold": self.fallback_threshold,
            "vector_dimension": self.vector_dimension,
            "vector_similarity_threshold": self.vector_similarity_threshold,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout_ms": self.request_timeout_ms,
            "enable_embedding_cache": self.enable_embedding_cache,
            "embedding_cache_size": self.embedding_cache_size,
            "embedding_cache_ttl_seconds": self.embedding_cache_ttl_seconds
        }


class DecisionConfig(BaseModel):
    """Decision engine configuration settings with ENV override support"""
    
    model_config = {"validate_assignment": True}
    
    # Weights for different components (with ENV overrides)
    w_smartfilter: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SMARTFILTER", "0.25")))
    w_person: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_PERSON", "0.3")))
    w_org: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_ORG", "0.15")))
    w_similarity: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SIMILARITY", "0.25")))
    bonus_date_match: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__BONUS_DATE_MATCH", "0.07")))
    bonus_id_match: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__BONUS_ID_MATCH", "0.15")))
    
    # Search weights (NEW)
    w_search_exact: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SEARCH_EXACT", "0.4")))
    w_search_phrase: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SEARCH_PHRASE", "0.25")))
    w_search_ngram: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SEARCH_NGRAM", "0.2")))
    w_search_fuzzy: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SEARCH_FUZZY", "0.18")))
    w_search_vector: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__W_SEARCH_VECTOR", "0.15")))

    # Search thresholds (NEW)
    thr_search_exact: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_SEARCH_EXACT", "0.8")))
    thr_search_phrase: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_SEARCH_PHRASE", "0.7")))
    thr_search_ngram: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_SEARCH_NGRAM", "0.6")))
    thr_search_fuzzy: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_SEARCH_FUZZY", "0.65")))
    thr_search_vector: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_SEARCH_VECTOR", "0.5")))
    
    # Search bonuses (NEW)
    bonus_multiple_matches: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__BONUS_MULTIPLE_MATCHES", "0.1")))
    bonus_high_confidence: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__BONUS_HIGH_CONFIDENCE", "0.05")))
    bonus_exact_match: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__BONUS_EXACT_MATCH", "0.2")))
    
    # Thresholds for risk levels (with ENV overrides)
    thr_high: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_HIGH", "0.85")))
    thr_medium: float = Field(default_factory=lambda: float(os.getenv("AI_DECISION__THR_MEDIUM", "0.5")))
    
    # Business gates
    require_tin_dob_gate: bool = Field(default_factory=lambda: os.getenv("AI_DECISION__REQUIRE_TIN_DOB_GATE", "true").lower() == "true")
    
    def model_dump(self) -> Dict[str, Any]:
        """Return model as dictionary"""
        return {
            "w_smartfilter": self.w_smartfilter,
            "w_person": self.w_person,
            "w_org": self.w_org,
            "w_similarity": self.w_similarity,
            "bonus_date_match": self.bonus_date_match,
            "bonus_id_match": self.bonus_id_match,
            "w_search_exact": self.w_search_exact,
            "w_search_phrase": self.w_search_phrase,
            "w_search_ngram": self.w_search_ngram,
            "w_search_fuzzy": self.w_search_fuzzy,
            "w_search_vector": self.w_search_vector,
            "thr_search_exact": self.thr_search_exact,
            "thr_search_phrase": self.thr_search_phrase,
            "thr_search_ngram": self.thr_search_ngram,
            "thr_search_fuzzy": self.thr_search_fuzzy,
            "thr_search_vector": self.thr_search_vector,
            "bonus_multiple_matches": self.bonus_multiple_matches,
            "bonus_high_confidence": self.bonus_high_confidence,
            "bonus_exact_match": self.bonus_exact_match,
            "thr_high": self.thr_high,
            "thr_medium": self.thr_medium,
            "require_tin_dob_gate": self.require_tin_dob_gate
        }


# Unified Configuration System
# Priority: ENV variables → YAML config → defaults

# Service configuration instances
SERVICE_CONFIG = ServiceConfig()
INTEGRATION_CONFIG = IntegrationConfig()
SECURITY_CONFIG = SecurityConfig()
DEPLOYMENT_CONFIG = DeploymentConfig()
LOGGING_CONFIG = LoggingConfig()
LANGUAGE_CONFIG = LanguageConfig()
PERFORMANCE_CONFIG = PerformanceConfig()
EMBEDDING_CONFIG = EmbeddingConfig()
NORMALIZATION_CONFIG = NormalizationConfig()
SEARCH_CONFIG = SearchConfig()  # Search layer configuration
DECISION_CONFIG = DecisionConfig()  # Now supports ENV overrides
    
