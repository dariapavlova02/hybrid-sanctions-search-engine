"""
Unit tests for FeatureFlags system.
"""

import pytest
import os
from unittest.mock import patch

from src.ai_service.utils.feature_flags import (
    FeatureFlags,
    FeatureFlagManager,
    NormalizationImplementation,
    get_feature_flag_manager,
    should_use_factory
)


class TestFeatureFlags:
    """Tests for FeatureFlags dataclass."""

    def test_default_values(self):
        """Test default feature flag values."""
        flags = FeatureFlags()

        # Test key defaults based on current settings
        assert flags.use_factory_normalizer is True  # Factory is default now
        assert flags.ascii_fastpath is True
        assert flags.enable_ac_tier0 is True
        assert flags.enable_vector_fallback is True
        assert flags.enforce_nominative is True
        assert flags.preserve_feminine_surnames is True

    def test_to_dict_method(self):
        """Test feature flags to_dict serialization."""
        flags = FeatureFlags()
        flags_dict = flags.to_dict()

        # Check required fields are present
        required_fields = [
            'use_factory_normalizer',
            'ascii_fastpath',
            'enable_ac_tier0',
            'enable_vector_fallback',
            'enforce_nominative',
            'preserve_feminine_surnames'
        ]

        for field in required_fields:
            assert field in flags_dict
            assert isinstance(flags_dict[field], bool)

    def test_language_overrides_initialization(self):
        """Test language overrides are properly initialized."""
        flags = FeatureFlags()
        assert flags.language_overrides == {}

        # Test with custom overrides
        overrides = {'ru': NormalizationImplementation.LEGACY}
        flags_with_overrides = FeatureFlags(language_overrides=overrides)
        assert flags_with_overrides.language_overrides == overrides


class TestFeatureFlagManager:
    """Tests for FeatureFlagManager."""

    def test_initialization(self):
        """Test manager initialization."""
        manager = FeatureFlagManager()
        assert hasattr(manager, '_flags')
        assert isinstance(manager._flags, FeatureFlags)

    @patch.dict(os.environ, {
        'AISVC_FLAG_USE_FACTORY_NORMALIZER': 'true',
        'AISVC_FLAG_ASCII_FASTPATH': 'false'
    })
    def test_environment_loading(self):
        """Test loading flags from environment variables."""
        manager = FeatureFlagManager()

        assert manager._flags.use_factory_normalizer is True
        assert manager._flags.ascii_fastpath is False

    def test_should_use_factory_default(self):
        """Test should_use_factory with default settings."""
        manager = FeatureFlagManager()

        # With factory flag enabled, should return True
        result = manager.should_use_factory()
        assert result is True

    def test_should_use_factory_with_language_override(self):
        """Test should_use_factory with language-specific override."""
        manager = FeatureFlagManager()
        manager._flags.language_overrides = {
            'ru': NormalizationImplementation.LEGACY
        }

        # Should respect language override
        result = manager.should_use_factory(language='ru')
        assert result is False

        # Should use default for other languages
        result = manager.should_use_factory(language='en')
        assert result is True

    def test_rollout_percentage(self):
        """Test rollout percentage logic."""
        manager = FeatureFlagManager()
        manager._flags.use_factory_normalizer = False
        manager._flags.normalization_implementation = NormalizationImplementation.FACTORY
        manager._flags.factory_rollout_percentage = 50

        # With consistent user_id, should be deterministic
        result1 = manager.should_use_factory(user_id='test_user_123')
        result2 = manager.should_use_factory(user_id='test_user_123')
        assert result1 == result2

    def test_monitoring_config(self):
        """Test monitoring configuration retrieval."""
        manager = FeatureFlagManager()
        config = manager.get_monitoring_config()

        required_keys = [
            'enable_dual_processing',
            'log_implementation_choice',
            'enable_performance_fallback',
            'max_latency_threshold_ms',
            'enable_accuracy_monitoring',
            'min_confidence_threshold'
        ]

        for key in required_keys:
            assert key in config

    def test_update_flags(self):
        """Test programmatic flag updates."""
        manager = FeatureFlagManager()

        original_value = manager._flags.ascii_fastpath
        manager.update_flags(ascii_fastpath=not original_value)

        assert manager._flags.ascii_fastpath != original_value

    def test_current_config(self):
        """Test current configuration retrieval."""
        manager = FeatureFlagManager()
        config = manager.get_current_config()

        assert 'normalization_implementation' in config
        assert 'factory_rollout_percentage' in config
        assert 'language_overrides' in config


class TestGlobalFunctions:
    """Tests for global convenience functions."""

    def test_get_feature_flag_manager_singleton(self):
        """Test global manager is singleton."""
        manager1 = get_feature_flag_manager()
        manager2 = get_feature_flag_manager()

        assert manager1 is manager2

    def test_should_use_factory_convenience(self):
        """Test convenience function."""
        result = should_use_factory()
        assert isinstance(result, bool)

        # Should match manager result
        manager = get_feature_flag_manager()
        manager_result = manager.should_use_factory()
        assert result == manager_result


class TestNormalizationImplementation:
    """Tests for NormalizationImplementation enum."""

    def test_enum_values(self):
        """Test enum has expected values."""
        assert NormalizationImplementation.LEGACY.value == "legacy"
        assert NormalizationImplementation.FACTORY.value == "factory"
        assert NormalizationImplementation.AUTO.value == "auto"

    def test_enum_from_string(self):
        """Test creating enum from string values."""
        assert NormalizationImplementation("legacy") == NormalizationImplementation.LEGACY
        assert NormalizationImplementation("factory") == NormalizationImplementation.FACTORY
        assert NormalizationImplementation("auto") == NormalizationImplementation.AUTO

    def test_invalid_enum_value(self):
        """Test invalid enum value raises ValueError."""
        with pytest.raises(ValueError):
            NormalizationImplementation("invalid")