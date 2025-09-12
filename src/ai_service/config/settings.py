"""
Configuration settings for AI Service
Structured configuration classes with validation and type hints
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
import os

from ..constants import (
    DEFAULT_MAX_INPUT_LENGTH,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    FALLBACK_LANGUAGE,
    DEFAULT_CACHE_SIZE,
    DEFAULT_CACHE_TTL,
    PERFORMANCE_CONFIG as PERF_CONSTANTS,
    SECURITY_CONFIG as SEC_CONSTANTS,
    INTEGRATION_CONFIG as INT_CONSTANTS,
    LOGGING_CONFIG as LOG_CONSTANTS
)


@dataclass
class ServiceConfig:
    """Service configuration settings"""
    max_input_length: int = DEFAULT_MAX_INPUT_LENGTH
    supported_languages: List[str] = field(default_factory=lambda: SUPPORTED_LANGUAGES.copy())
    default_language: str = DEFAULT_LANGUAGE
    fallback_language: str = FALLBACK_LANGUAGE
    enable_advanced_features: bool = True
    enable_morphology: bool = True
    enable_transliterations: bool = True
    preserve_names: bool = True
    clean_unicode: bool = True
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'max_input_length': self.max_input_length,
            'supported_languages': self.supported_languages,
            'default_language': self.default_language,
            'fallback_language': self.fallback_language,
            'enable_advanced_features': self.enable_advanced_features,
            'enable_morphology': self.enable_morphology,
            'enable_transliterations': self.enable_transliterations,
            'preserve_names': self.preserve_names,
            'clean_unicode': self.clean_unicode
        }


@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str = 'localhost'
    port: int = 5432
    database: str = 'ai_service'
    username: str = 'postgres'
    password: str = ''
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'host': self.host,
            'port': self.port,
            'database': self.database,
            'username': self.username,
            'password': '***' if self.password else '',
            'pool_size': self.pool_size,
            'max_overflow': self.max_overflow,
            'echo': self.echo
        }


@dataclass
class LoggingConfig:
    """Logging configuration settings"""
    level: str = 'INFO'
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format: str = '%Y-%m-%d %H:%M:%S'
    file_logging: bool = True
    console_logging: bool = True
    log_dir: str = 'logs'
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5
    environment: str = 'development'
    
    def __post_init__(self):
        """Post-initialization setup"""
        if self.environment == 'production':
            self.level = 'WARNING'
            self.console_logging = False
        elif self.environment == 'staging':
            self.level = 'INFO'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'level': self.level,
            'format': self.format,
            'date_format': self.date_format,
            'file_logging': self.file_logging,
            'console_logging': self.console_logging,
            'log_dir': self.log_dir,
            'max_file_size': self.max_file_size,
            'backup_count': self.backup_count,
            'environment': self.environment
        }


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    max_input_length: int = 10000
    sanitize_input: bool = True
    rate_limit_enabled: bool = True
    max_requests_per_minute: int = 100
    admin_api_key: str = 'your-secure-api-key-here'
    enable_cors: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: [
        'http://localhost:3000',
        'http://localhost:8080'
    ])
    enable_https: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'max_input_length': self.max_input_length,
            'sanitize_input': self.sanitize_input,
            'rate_limit_enabled': self.rate_limit_enabled,
            'max_requests_per_minute': self.max_requests_per_minute,
            'admin_api_key': '***' if self.admin_api_key else '',
            'enable_cors': self.enable_cors,
            'allowed_origins': self.allowed_origins,
            'enable_https': self.enable_https,
            'ssl_cert_path': self.ssl_cert_path,
            'ssl_key_path': self.ssl_key_path
        }


@dataclass
class PerformanceConfig:
    """Performance configuration settings"""
    max_concurrent_requests: int = PERF_CONSTANTS['max_concurrent_requests']
    batch_size: int = PERF_CONSTANTS['batch_size']
    memory_limit_mb: int = PERF_CONSTANTS['memory_limit_mb']
    cpu_limit_percent: int = PERF_CONSTANTS['cpu_limit_percent']
    cache_size: int = DEFAULT_CACHE_SIZE
    cache_ttl: int = DEFAULT_CACHE_TTL
    enable_async: bool = True
    worker_timeout: int = 300
    request_timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'max_concurrent_requests': self.max_concurrent_requests,
            'batch_size': self.batch_size,
            'memory_limit_mb': self.memory_limit_mb,
            'cpu_limit_percent': self.cpu_limit_percent,
            'cache_size': self.cache_size,
            'cache_ttl': self.cache_ttl,
            'enable_async': self.enable_async,
            'worker_timeout': self.worker_timeout,
            'request_timeout': self.request_timeout
        }


@dataclass
class IntegrationConfig:
    """Integration configuration settings"""
    api_version: str = 'v1'
    cors_enabled: bool = True
    health_check_interval: int = 60
    metrics_enabled: bool = True
    allowed_origins: List[str] = field(default_factory=lambda: [
        'http://localhost:3000',
        'http://localhost:8080'
    ])
    enable_docs: bool = True
    docs_url: str = '/docs'
    redoc_url: str = '/redoc'
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'api_version': self.api_version,
            'cors_enabled': self.cors_enabled,
            'health_check_interval': self.health_check_interval,
            'metrics_enabled': self.metrics_enabled,
            'allowed_origins': self.allowed_origins,
            'enable_docs': self.enable_docs,
            'docs_url': self.docs_url,
            'redoc_url': self.redoc_url
        }


@dataclass
class DeploymentConfig:
    """Deployment configuration settings"""
    environment: str = 'development'
    debug_mode: bool = True
    auto_reload: bool = True
    workers: int = 1
    host: str = '0.0.0.0'
    port: int = 8000
    enable_uvicorn_logging: bool = True
    log_level: str = 'info'
    
    def __post_init__(self):
        """Post-initialization setup"""
        if self.environment == 'production':
            self.debug_mode = False
            self.auto_reload = False
            self.workers = int(os.getenv('WORKERS', '4'))
            self.log_level = 'warning'
        elif self.environment == 'staging':
            self.debug_mode = False
            self.auto_reload = False
            self.workers = int(os.getenv('WORKERS', '2'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'environment': self.environment,
            'debug_mode': self.debug_mode,
            'auto_reload': self.auto_reload,
            'workers': self.workers,
            'host': self.host,
            'port': self.port,
            'enable_uvicorn_logging': self.enable_uvicorn_logging,
            'log_level': self.log_level
        }
