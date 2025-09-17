"""
Feature flags configuration for safe rollout of new functionality.

This module provides a centralized way to manage feature flags across the AI service,
allowing for safe deployment and gradual rollout of new features.
"""

import os
import yaml
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlags:
    """
    Feature flags configuration for the AI normalization service.
    
    All flags default to False for safe rollout. Flags can be overridden via
    environment variables (AISVC_FLAG_*) or configuration file.
    """
    
    # Normalization pipeline flags
    use_factory_normalizer: bool = False
    fix_initials_double_dot: bool = False
    preserve_hyphenated_case: bool = False
    strict_stopwords: bool = False
    
    # Search integration flags
    enable_ac_tier0: bool = False
    enable_vector_fallback: bool = False
    
    # Nominative and gender enforcement flags
    enforce_nominative: bool = True
    preserve_feminine_surnames: bool = True
    
    # ASCII fastpath optimization
    ascii_fastpath: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feature flags to dictionary for tracing and serialization."""
        return {
            "use_factory_normalizer": self.use_factory_normalizer,
            "fix_initials_double_dot": self.fix_initials_double_dot,
            "preserve_hyphenated_case": self.preserve_hyphenated_case,
            "strict_stopwords": self.strict_stopwords,
            "enable_ac_tier0": self.enable_ac_tier0,
            "enable_vector_fallback": self.enable_vector_fallback,
            "enforce_nominative": self.enforce_nominative,
            "preserve_feminine_surnames": self.preserve_feminine_surnames,
            "ascii_fastpath": self.ascii_fastpath,
        }
    
    def __str__(self) -> str:
        """String representation for logging."""
        enabled_flags = [k for k, v in self.to_dict().items() if v]
        if enabled_flags:
            return f"FeatureFlags(enabled: {', '.join(enabled_flags)})"
        return "FeatureFlags(all disabled)"


def from_env_and_file(app_env: str = "development") -> FeatureFlags:
    """
    Load feature flags from environment variables and configuration file.
    
    Priority order:
    1. Environment variables (AISVC_FLAG_*)
    2. Configuration file (src/ai_service/config/feature_flags.yaml)
    3. Default values (all False)
    
    Args:
        app_env: Application environment (development, staging, production)
        
    Returns:
        FeatureFlags instance with loaded configuration
    """
    # Start with default values
    flags = FeatureFlags()
    
    # Load from environment variables
    env_flags = _load_from_env()
    if env_flags:
        flags = _merge_flags(flags, env_flags)
        logger.info(f"Loaded feature flags from environment: {env_flags}")
    
    # Load from configuration file if it exists
    config_file = Path(__file__).parent / "feature_flags.yaml"
    if config_file.exists():
        file_flags = _load_from_file(config_file, app_env)
        if file_flags:
            flags = _merge_flags(flags, file_flags)
            logger.info(f"Loaded feature flags from config file: {file_flags}")
    
    # Log final configuration
    logger.info(f"Final feature flags configuration: {flags}")
    
    return flags


def _load_from_env() -> Dict[str, Any]:
    """Load feature flags from environment variables with AISVC_FLAG_ prefix."""
    env_flags = {}
    
    for key, value in os.environ.items():
        if key.startswith("AISVC_FLAG_"):
            flag_name = key[11:].lower()  # Remove AISVC_FLAG_ prefix and convert to lowercase
            
            # Convert string value to boolean
            if value.lower() in ("true", "1", "yes", "on"):
                env_flags[flag_name] = True
            elif value.lower() in ("false", "0", "no", "off"):
                env_flags[flag_name] = False
            else:
                logger.warning(f"Invalid boolean value for {key}: {value}, skipping")
    
    return env_flags


def _load_from_file(config_file: Path, app_env: str) -> Dict[str, Any]:
    """Load feature flags from YAML configuration file."""
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Get environment-specific configuration
        env_config = config.get(app_env, {})
        flags_config = env_config.get('feature_flags', {})
        
        return flags_config
        
    except Exception as e:
        logger.warning(f"Failed to load feature flags from {config_file}: {e}")
        return {}


def _merge_flags(base_flags: FeatureFlags, override_flags: Dict[str, Any]) -> FeatureFlags:
    """Merge override flags into base flags, creating a new instance."""
    flags_dict = base_flags.to_dict()
    flags_dict.update(override_flags)
    
    return FeatureFlags(
        use_factory_normalizer=flags_dict.get("use_factory_normalizer", False),
        fix_initials_double_dot=flags_dict.get("fix_initials_double_dot", False),
        preserve_hyphenated_case=flags_dict.get("preserve_hyphenated_case", False),
        strict_stopwords=flags_dict.get("strict_stopwords", False),
        enable_ac_tier0=flags_dict.get("enable_ac_tier0", False),
        enable_vector_fallback=flags_dict.get("enable_vector_fallback", False),
        enforce_nominative=flags_dict.get("enforce_nominative", True),
        preserve_feminine_surnames=flags_dict.get("preserve_feminine_surnames", True),
    )


# Global feature flags instance
_global_flags: Optional[FeatureFlags] = None


def get_global_flags() -> FeatureFlags:
    """Get the global feature flags instance, loading if not already loaded."""
    global _global_flags
    if _global_flags is None:
        app_env = os.getenv("APP_ENV", "development")
        _global_flags = from_env_and_file(app_env)
    return _global_flags


def set_global_flags(flags: FeatureFlags) -> None:
    """Set the global feature flags instance (mainly for testing)."""
    global _global_flags
    _global_flags = flags
