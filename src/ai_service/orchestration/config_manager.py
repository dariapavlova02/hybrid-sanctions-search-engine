"""
Centralized configuration management for orchestration system.
Single Responsibility: Manages all configuration for processing pipeline.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

# Import interfaces
try:
    from ..interfaces import ConfigurationInterface, ProcessingStage
except ImportError:
    # Fallback for when loaded via importlib
    import sys

    orchestration_path = Path(__file__).parent
    sys.path.insert(0, str(orchestration_path))

    from interfaces import ConfigurationInterface, ProcessingStage


class ConfigSource(str, Enum):
    """Configuration sources in priority order"""

    ENVIRONMENT = "environment"
    FILE = "file"
    DEFAULT = "default"


@dataclass
class StageConfig:
    """Configuration for a processing stage"""

    enabled: bool = True
    timeout_ms: int = 5000
    retry_count: int = 3
    cache_results: bool = True
    specific_params: Dict[str, Any] = None

    def __post_init__(self):
        if self.specific_params is None:
            self.specific_params = {}


@dataclass
class PipelineConfig:
    """Configuration for the entire pipeline"""

    max_concurrent_stages: int = 1
    enable_caching: bool = True
    cache_ttl_seconds: int = 3600
    enable_metrics: bool = True
    enable_error_recovery: bool = True
    processing_timeout_ms: int = 30000
    batch_size: int = 100

    # Stage configurations
    validation: StageConfig = None
    unicode_normalization: StageConfig = None
    language_detection: StageConfig = None
    text_normalization: StageConfig = None
    variant_generation: StageConfig = None
    embedding_generation: StageConfig = None
    smart_filtering: StageConfig = None

    def __post_init__(self):
        # Initialize stage configs with defaults
        if self.validation is None:
            self.validation = StageConfig(
                specific_params={
                    "min_length": 1,
                    "max_length": 10000,
                    "allowed_chars": None,
                }
            )

        if self.unicode_normalization is None:
            self.unicode_normalization = StageConfig(
                specific_params={
                    "normalization_form": "NFC",
                    "remove_control_chars": True,
                }
            )

        if self.language_detection is None:
            self.language_detection = StageConfig(
                specific_params={"confidence_threshold": 0.8, "default_language": "en"}
            )

        if self.text_normalization is None:
            self.text_normalization = StageConfig(
                specific_params={
                    "lowercase": False,
                    "remove_extra_whitespace": True,
                    "preserve_names": True,
                }
            )

        if self.variant_generation is None:
            self.variant_generation = StageConfig(
                enabled=False,  # Expensive, disabled by default
                specific_params={
                    "max_variants": 100,
                    "enable_transliteration": True,
                    "enable_morphology": True,
                },
            )

        if self.embedding_generation is None:
            self.embedding_generation = StageConfig(
                enabled=False,  # Expensive, disabled by default
                specific_params={
                    "model_name": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                    "dimension": 384,
                },
            )

        if self.smart_filtering is None:
            self.smart_filtering = StageConfig(
                enabled=True,  # Enable by default for better performance
                specific_params={
                    "confidence_threshold": 0.7,
                    "enable_terrorism_detection": True,
                },
            )


class CentralizedConfigManager(ConfigurationInterface):
    """
    Centralized configuration manager implementing clean architecture.
    Single Responsibility: Manages configuration from multiple sources.
    """

    def __init__(self, config_file: Optional[str] = None):
        self.logger = logging.getLogger(f"{__name__}.CentralizedConfigManager")
        self.config_file = config_file
        self._config: Optional[PipelineConfig] = None
        self._config_sources: Dict[str, ConfigSource] = {}

        # Load configuration
        self._load_configuration()

    def _load_configuration(self) -> None:
        """Load configuration from all sources with priority"""
        self.logger.info("Loading configuration from multiple sources")

        # Start with defaults
        config_dict = asdict(PipelineConfig())
        self._config_sources = {key: ConfigSource.DEFAULT for key in config_dict.keys()}

        # Override with file configuration
        if self.config_file and Path(self.config_file).exists():
            try:
                with open(self.config_file, "r") as f:
                    file_config = json.load(f)

                config_dict.update(file_config)
                for key in file_config.keys():
                    self._config_sources[key] = ConfigSource.FILE

                self.logger.info(f"Loaded configuration from file: {self.config_file}")
            except Exception as e:
                self.logger.error(f"Failed to load config file {self.config_file}: {e}")

        # Override with environment variables
        env_config = self._load_from_environment()
        config_dict.update(env_config)
        for key in env_config.keys():
            self._config_sources[key] = ConfigSource.ENVIRONMENT

        # Create final configuration object
        try:
            self._config = self._dict_to_pipeline_config(config_dict)
            self.logger.info("Configuration loaded successfully")
        except Exception as e:
            self.logger.error(f"Failed to create configuration object: {e}")
            # Fallback to defaults
            self._config = PipelineConfig()

    def _load_from_environment(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}

        # Pipeline-level settings
        env_mappings = {
            "AI_PIPELINE_MAX_CONCURRENT": ("max_concurrent_stages", int),
            "AI_PIPELINE_ENABLE_CACHING": (
                "enable_caching",
                lambda x: x.lower() == "true",
            ),
            "AI_PIPELINE_CACHE_TTL": ("cache_ttl_seconds", int),
            "AI_PIPELINE_ENABLE_METRICS": (
                "enable_metrics",
                lambda x: x.lower() == "true",
            ),
            "AI_PIPELINE_TIMEOUT": ("processing_timeout_ms", int),
            "AI_PIPELINE_BATCH_SIZE": ("batch_size", int),
        }

        for env_var, (config_key, converter) in env_mappings.items():
            if env_var in os.environ:
                try:
                    env_config[config_key] = converter(os.environ[env_var])
                except Exception as e:
                    self.logger.warning(f"Invalid environment value for {env_var}: {e}")

        # Stage-specific settings
        stages = [
            "validation",
            "language_detection",
            "text_normalization",
            "variant_generation",
            "embedding_generation",
            "smart_filtering",
        ]

        for stage in stages:
            stage_enabled = f"AI_STAGE_{stage.upper()}_ENABLED"
            if stage_enabled in os.environ:
                stage_config = env_config.setdefault(stage, {})
                stage_config["enabled"] = os.environ[stage_enabled].lower() == "true"

        return env_config

    def _dict_to_pipeline_config(self, config_dict: Dict[str, Any]) -> PipelineConfig:
        """Convert dictionary to PipelineConfig object"""
        # Extract stage configs
        stage_configs = {}
        for stage in [
            "validation",
            "unicode_normalization",
            "language_detection",
            "text_normalization",
            "variant_generation",
            "embedding_generation",
            "smart_filtering",
        ]:
            if stage in config_dict:
                stage_data = config_dict.pop(stage, {})
                if isinstance(stage_data, dict):
                    stage_configs[stage] = StageConfig(
                        enabled=stage_data.get("enabled", True),
                        timeout_ms=stage_data.get("timeout_ms", 5000),
                        retry_count=stage_data.get("retry_count", 3),
                        cache_results=stage_data.get("cache_results", True),
                        specific_params=stage_data.get("specific_params", {}),
                    )

        # Create pipeline config
        pipeline_config = PipelineConfig(**config_dict)

        # Set stage configs
        for stage, config in stage_configs.items():
            setattr(pipeline_config, stage, config)

        return pipeline_config

    def get_stage_config(self, stage) -> Dict[str, Any]:
        """Get configuration for specific stage"""
        if not self._config:
            return {}

        # Handle both enum and string inputs
        if hasattr(stage, "value"):
            stage_name = stage.value
        else:
            stage_name = stage
        stage_config = getattr(self._config, stage_name, None)

        if stage_config is None:
            # Return default stage config
            stage_config = StageConfig()

        return {
            "enabled": stage_config.enabled,
            "timeout_ms": stage_config.timeout_ms,
            "retry_count": stage_config.retry_count,
            "cache_results": stage_config.cache_results,
            **stage_config.specific_params,
        }

    def get_pipeline_config(self) -> Dict[str, Any]:
        """Get pipeline configuration"""
        if not self._config:
            return {}

        return {
            "max_concurrent_stages": self._config.max_concurrent_stages,
            "enable_caching": self._config.enable_caching,
            "cache_ttl_seconds": self._config.cache_ttl_seconds,
            "enable_metrics": self._config.enable_metrics,
            "enable_error_recovery": self._config.enable_error_recovery,
            "processing_timeout_ms": self._config.processing_timeout_ms,
            "batch_size": self._config.batch_size,
        }

    def is_stage_enabled(self, stage: ProcessingStage) -> bool:
        """Check if stage is enabled"""
        stage_config = self.get_stage_config(stage)
        return stage_config.get("enabled", True)

    def reload_configuration(self) -> None:
        """Reload configuration from all sources"""
        self.logger.info("Reloading configuration")
        self._load_configuration()

    def get_configuration_info(self) -> Dict[str, Any]:
        """Get information about current configuration"""
        return {
            "config_file": self.config_file,
            "config_sources": self._config_sources,
            "pipeline_config": self.get_pipeline_config(),
            "enabled_stages": [
                stage.value for stage in ProcessingStage if self.is_stage_enabled(stage)
            ],
        }

    def save_configuration(self, file_path: str) -> bool:
        """Save current configuration to file"""
        if not self._config:
            return False

        try:
            config_dict = asdict(self._config)
            with open(file_path, "w") as f:
                json.dump(config_dict, f, indent=2)

            self.logger.info(f"Configuration saved to: {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            return False
