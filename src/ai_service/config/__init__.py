"""
Configuration module for AI Service
Centralized configuration management with environment-specific settings
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .settings import (
    DatabaseConfig,
    DeploymentConfig,
    EmbeddingConfig,
    IntegrationConfig,
    LanguageConfig,
    LoggingConfig,
    PerformanceConfig,
    SecurityConfig,
    ServiceConfig,
)


class Config:
    """Main configuration class for AI Service"""

    def __init__(self, environment: Optional[str] = None):
        """
        Initialize configuration

        Args:
            environment: Environment name (development, staging, production)
        """
        self.environment = environment or os.getenv("APP_ENV", "development")
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration based on environment"""
        # Base configuration
        self.service = ServiceConfig()
        self.database = DatabaseConfig()
        self.logging = LoggingConfig(environment=self.environment)
        self.security = SecurityConfig()
        self.performance = PerformanceConfig()
        self.integration = IntegrationConfig()
        self.language = LanguageConfig()
        self.deployment = DeploymentConfig(environment=self.environment)
        self.embedding = EmbeddingConfig()

    def get_all_config(self) -> Dict[str, Any]:
        """Get all configuration as dictionary"""
        return {
            "service": self.service.to_dict(),
            "database": self.database.to_dict(),
            "logging": self.logging.to_dict(),
            "security": self.security.to_dict(),
            "performance": self.performance.to_dict(),
            "integration": self.integration.to_dict(),
            "language": self.language.to_dict(),
            "deployment": self.deployment.to_dict(),
            "embedding": self.embedding.model_dump(),
        }

    def validate(self) -> bool:
        """Validate configuration"""
        try:
            # Validate required settings
            assert self.service.max_input_length > 0
            assert self.security.max_input_length > 0
            assert self.performance.max_concurrent_requests > 0
            return True
        except AssertionError:
            return False


# Global configuration instance
config = Config()

# Export commonly used configurations
SERVICE_CONFIG = config.service
SECURITY_CONFIG = config.security
INTEGRATION_CONFIG = config.integration
LANGUAGE_CONFIG = config.language
DEPLOYMENT_CONFIG = config.deployment
PERFORMANCE_CONFIG = config.performance
LOGGING_CONFIG = config.logging

__all__ = [
    "Config",
    "config",
    "SERVICE_CONFIG",
    "SECURITY_CONFIG",
    "INTEGRATION_CONFIG",
    "LANGUAGE_CONFIG",
    "DEPLOYMENT_CONFIG",
    "PERFORMANCE_CONFIG",
    "LOGGING_CONFIG",
]
