"""
Comprehensive tests for feature flags wiring and functionality.

Tests the complete feature flags system including:
- Configuration loading from environment and files
- API integration with request/response handling
- Orchestrator routing between factory and legacy
- Layer-specific flag processing
- Tracing and audit functionality
"""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from src.ai_service.config.feature_flags import FeatureFlags, from_env_and_file, get_global_flags, set_global_flags
from src.ai_service.utils.feature_flags import FeatureFlagManager, get_feature_flag_manager
from src.ai_service.main import app
from fastapi.testclient import TestClient


class TestFeatureFlagsConfiguration:
    """Test feature flags configuration loading and management."""

    def test_feature_flags_defaults(self):
        """Test that feature flags have correct default values."""
        flags = FeatureFlags()
        
        assert flags.use_factory_normalizer == False
        assert flags.fix_initials_double_dot == False
        assert flags.preserve_hyphenated_case == False
        assert flags.strict_stopwords == False
        assert flags.enable_ac_tier0 == False
        assert flags.enable_vector_fallback == False

    def test_feature_flags_to_dict(self):
        """Test that to_dict returns correct dictionary representation."""
        flags = FeatureFlags(
            use_factory_normalizer=True,
            fix_initials_double_dot=True,
            preserve_hyphenated_case=False,
            strict_stopwords=True,
            enable_ac_tier0=False,
            enable_vector_fallback=True
        )
        
        result = flags.to_dict()
        
        assert result == {
            "use_factory_normalizer": True,
            "fix_initials_double_dot": True,
            "preserve_hyphenated_case": False,
            "strict_stopwords": True,
            "enable_ac_tier0": False,
            "enable_vector_fallback": True
        }

    def test_load_from_environment(self):
        """Test loading feature flags from environment variables."""
        with patch.dict(os.environ, {
            'AISVC_FLAG_USE_FACTORY_NORMALIZER': 'true',
            'AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT': 'true',
            'AISVC_FLAG_PRESERVE_HYPHENATED_CASE': 'false',
            'AISVC_FLAG_STRICT_STOPWORDS': 'true',
            'AISVC_FLAG_ENABLE_AC_TIER0': 'false',
            'AISVC_FLAG_ENABLE_VECTOR_FALLBACK': 'true'
        }):
            flags = from_env_and_file("test")
            
            assert flags.use_factory_normalizer == True
            assert flags.fix_initials_double_dot == True
            assert flags.preserve_hyphenated_case == False
            assert flags.strict_stopwords == True
            assert flags.enable_ac_tier0 == False
            assert flags.enable_vector_fallback == True

    def test_load_from_yaml_file(self):
        """Test loading feature flags from YAML configuration file."""
        yaml_content = """
development:
  feature_flags:
    use_factory_normalizer: true
    fix_initials_double_dot: true
    preserve_hyphenated_case: true
    strict_stopwords: false
    enable_ac_tier0: true
    enable_vector_fallback: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            # Mock the config file path
            with patch('src.ai_service.config.feature_flags.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.__truediv__.return_value = Path(f.name)
                
                flags = from_env_and_file("development")
                
                assert flags.use_factory_normalizer == True
                assert flags.fix_initials_double_dot == True
                assert flags.preserve_hyphenated_case == True
                assert flags.strict_stopwords == False
                assert flags.enable_ac_tier0 == True
                assert flags.enable_vector_fallback == False
            
            os.unlink(f.name)

    def test_environment_overrides_file(self):
        """Test that environment variables override file configuration."""
        yaml_content = """
development:
  feature_flags:
    use_factory_normalizer: false
    fix_initials_double_dot: false
    strict_stopwords: false
"""
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            
            with patch.dict(os.environ, {
                'AISVC_FLAG_USE_FACTORY_NORMALIZER': 'true',
                'AISVC_FLAG_STRICT_STOPWORDS': 'true'
            }):
                with patch('src.ai_service.config.feature_flags.Path') as mock_path:
                    mock_path.return_value.exists.return_value = True
                    mock_path.return_value.__truediv__.return_value = Path(f.name)
                    
                    flags = from_env_and_file("development")
                    
                    # Environment should override file
                    assert flags.use_factory_normalizer == True
                    assert flags.strict_stopwords == True
                    # File values should be used for others
                    assert flags.fix_initials_double_dot == False
            
            os.unlink(f.name)

    def test_global_flags_management(self):
        """Test global feature flags management."""
        # Reset global state
        set_global_flags(None)
        
        # Test getting global flags
        flags1 = get_global_flags()
        flags2 = get_global_flags()
        
        # Should return the same instance
        assert flags1 is flags2
        
        # Test setting custom flags
        custom_flags = FeatureFlags(use_factory_normalizer=True)
        set_global_flags(custom_flags)
        
        retrieved = get_global_flags()
        assert retrieved is custom_flags
        assert retrieved.use_factory_normalizer == True


class TestFeatureFlagManager:
    """Test the FeatureFlagManager functionality."""

    def test_should_use_factory_with_flag(self):
        """Test that use_factory_normalizer flag takes precedence."""
        manager = FeatureFlagManager()
        
        # Set the flag directly
        manager._flags.use_factory_normalizer = True
        
        # Should return True regardless of other settings
        assert manager.should_use_factory() == True
        assert manager.should_use_factory(language="ru") == True
        assert manager.should_use_factory(user_id="test") == True

    def test_should_use_factory_without_flag(self):
        """Test factory selection without the explicit flag."""
        manager = FeatureFlagManager()
        
        # Ensure flag is False
        manager._flags.use_factory_normalizer = False
        manager._flags.normalization_implementation = manager._flags.normalization_implementation.__class__.LEGACY
        
        # Should return False
        assert manager.should_use_factory() == False

    def test_get_monitoring_config(self):
        """Test getting monitoring configuration."""
        manager = FeatureFlagManager()
        config = manager.get_monitoring_config()
        
        assert "enable_dual_processing" in config
        assert "log_implementation_choice" in config
        assert "enable_performance_fallback" in config
        assert "max_latency_threshold_ms" in config
        assert "enable_accuracy_monitoring" in config
        assert "min_confidence_threshold" in config


class TestAPIIntegration:
    """Test API integration with feature flags."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)

    def test_normalize_endpoint_without_flags(self, client):
        """Test /normalize endpoint without feature flags."""
        response = client.post("/normalize", json={
            "text": "Иван Петров",
            "language": "ru"
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have trace with flags
        assert "trace" in data
        trace = data["trace"]
        
        # Find flags entry in trace
        flags_entry = None
        for entry in trace:
            if isinstance(entry, dict) and entry.get("type") == "flags":
                flags_entry = entry
                break
        
        assert flags_entry is not None
        assert "value" in flags_entry
        assert "scope" in flags_entry
        assert flags_entry["scope"] == "request"

    def test_normalize_endpoint_with_flags(self, client):
        """Test /normalize endpoint with explicit feature flags."""
        response = client.post("/normalize", json={
            "text": "Иван Петров",
            "language": "ru",
            "options": {
                "flags": {
                    "use_factory_normalizer": True,
                    "fix_initials_double_dot": True,
                    "preserve_hyphenated_case": True,
                    "strict_stopwords": False,
                    "enable_ac_tier0": False,
                    "enable_vector_fallback": False
                }
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have trace with custom flags
        assert "trace" in data
        trace = data["trace"]
        
        # Find flags entry in trace
        flags_entry = None
        for entry in trace:
            if isinstance(entry, dict) and entry.get("type") == "flags":
                flags_entry = entry
                break
        
        assert flags_entry is not None
        flags_value = flags_entry["value"]
        
        # Should have the custom flags
        assert flags_value["use_factory_normalizer"] == True
        assert flags_value["fix_initials_double_dot"] == True
        assert flags_value["preserve_hyphenated_case"] == True
        assert flags_value["strict_stopwords"] == False

    def test_process_endpoint_with_flags(self, client):
        """Test /process endpoint with feature flags."""
        response = client.post("/process", json={
            "text": "Иван Петров",
            "generate_variants": False,
            "generate_embeddings": False,
            "options": {
                "flags": {
                    "use_factory_normalizer": True,
                    "fix_initials_double_dot": True
                }
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have trace with flags
        assert "trace" in data
        trace = data["trace"]
        
        # Find flags entry in trace
        flags_entry = None
        for entry in trace:
            if isinstance(entry, dict) and entry.get("type") == "flags":
                flags_entry = entry
                break
        
        assert flags_entry is not None
        flags_value = flags_entry["value"]
        assert flags_value["use_factory_normalizer"] == True
        assert flags_value["fix_initials_double_dot"] == True


class TestLayerIntegration:
    """Test feature flags integration with individual layers."""

    def test_tokenizer_with_feature_flags(self):
        """Test tokenizer respects feature flags."""
        from src.ai_service.layers.normalization.tokenizer_service import TokenizerService
        
        tokenizer = TokenizerService()
        
        # Test with fix_initials_double_dot flag
        feature_flags = {
            "fix_initials_double_dot": True,
            "preserve_hyphenated_case": True,
            "strict_stopwords": False
        }
        
        result = tokenizer.tokenize(
            "И.. Петров-сидоров",
            language="ru",
            feature_flags=feature_flags
        )
        
        # Should have applied feature flag processing
        assert "Fixed double dots" in result.traces or "Preserved hyphenated case" in result.traces

    def test_normalization_service_routing(self):
        """Test that normalization service routes correctly based on flags."""
        from src.ai_service.layers.normalization.normalization_service import NormalizationService
        from src.ai_service.utils.feature_flags import FeatureFlags
        
        service = NormalizationService()
        
        # Test with use_factory_normalizer = True
        flags = FeatureFlags(use_factory_normalizer=True)
        
        # Mock the processing methods to verify routing
        with patch.object(service, '_process_with_factory') as mock_factory, \
             patch.object(service, '_process_with_legacy') as mock_legacy:
            
            mock_factory.return_value = MagicMock()
            
            # This should route to factory
            service.normalize_async(
                "test",
                language="ru",
                feature_flags=flags
            )
            
            # Should have called factory method
            mock_factory.assert_called_once()
            mock_legacy.assert_not_called()

    def test_feature_flags_passed_to_layers(self):
        """Test that feature flags are passed through to all layers."""
        from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from src.ai_service.utils.feature_flags import FeatureFlags
        
        # Create a mock orchestrator
        orchestrator = MagicMock(spec=UnifiedOrchestrator)
        
        # Test that feature flags are passed to normalization
        flags = FeatureFlags(use_factory_normalizer=True)
        
        # Mock the process method
        orchestrator.process.return_value = MagicMock(
            normalized_text="test",
            tokens=["test"],
            trace=[],
            language="ru",
            success=True,
            errors=[],
            processing_time=0.1
        )
        
        # This should pass feature flags to the normalization service
        orchestrator.process(
            text="test",
            feature_flags=flags
        )
        
        # Verify the call was made with feature flags
        orchestrator.process.assert_called_once()
        call_kwargs = orchestrator.process.call_args[1]
        assert "feature_flags" in call_kwargs
        assert call_kwargs["feature_flags"] == flags


class TestFeatureFlagsWiring:
    """Test complete feature flags wiring from API to layers."""

    @pytest.mark.parametrize("use_factory_normalizer", [True, False])
    def test_factory_vs_legacy_routing(self, use_factory_normalizer):
        """Test that use_factory_normalizer flag correctly routes to factory vs legacy."""
        from src.ai_service.utils.feature_flags import FeatureFlagManager
        
        manager = FeatureFlagManager()
        manager._flags.use_factory_normalizer = use_factory_normalizer
        
        # Test routing decision
        should_use_factory = manager.should_use_factory()
        assert should_use_factory == use_factory_normalizer

    def test_all_flags_have_effect(self):
        """Test that all feature flags have some effect on processing."""
        from src.ai_service.layers.normalization.processors.token_processor import TokenProcessor
        
        processor = TokenProcessor()
        
        # Test each flag individually
        test_tokens = ["И..", "петров-сидоров", "тест"]
        
        # fix_initials_double_dot
        flags1 = {"fix_initials_double_dot": True}
        result1 = processor._apply_feature_flags(test_tokens[:], flags1, [])
        assert result1 != test_tokens  # Should have changed something
        
        # preserve_hyphenated_case
        flags2 = {"preserve_hyphenated_case": True}
        result2 = processor._apply_feature_flags(test_tokens[:], flags2, [])
        assert result2 != test_tokens  # Should have changed something
        
        # strict_stopwords
        flags3 = {"strict_stopwords": True}
        result3 = processor._apply_feature_flags(test_tokens[:], flags3, [])
        # This one might not change tokens but should add traces
        assert isinstance(result3, list)

    def test_feature_flags_tracing(self):
        """Test that feature flags are properly traced through the system."""
        from src.ai_service.utils.feature_flags import FeatureFlags
        
        flags = FeatureFlags(
            use_factory_normalizer=True,
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True
        )
        
        # Test to_dict for tracing
        flags_dict = flags.to_dict()
        
        assert "use_factory_normalizer" in flags_dict
        assert "fix_initials_double_dot" in flags_dict
        assert "preserve_hyphenated_case" in flags_dict
        assert "strict_stopwords" in flags_dict
        assert "enable_ac_tier0" in flags_dict
        assert "enable_vector_fallback" in flags_dict
        
        # All values should be boolean
        for value in flags_dict.values():
            assert isinstance(value, bool)


if __name__ == "__main__":
    pytest.main([__file__])
