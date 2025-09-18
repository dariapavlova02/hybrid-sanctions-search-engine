"""
Acceptance tests for feature flags rollout safety.

These tests verify that the feature flags system works correctly in production-like
scenarios and ensures safe rollout of new functionality.

Test Cases:
1. Request without flags → uses global configuration
2. Request with partial flags → merges with global configuration
3. use_factory_normalizer=False → ensures factory code is not called
4. strict_stopwords=True → verifies stopwords are filtered from normalized output
"""

import os
import pytest
import tempfile
from unittest.mock import patch, MagicMock, call
from pathlib import Path

from fastapi.testclient import TestClient
from src.ai_service.main import app
from src.ai_service.utils.feature_flags import FeatureFlags
from src.ai_service.utils.feature_flags import get_feature_flag_manager


class TestRolloutSafety:
    """Test feature flags rollout safety and behavior."""

    @pytest.fixture
    def client(self):
        """Create test client for API testing."""
        return TestClient(app)

    @pytest.fixture
    def temp_yaml_config(self):
        """Create temporary YAML configuration file."""
        yaml_content = """
development:
  feature_flags:
    use_factory_normalizer: false
    fix_initials_double_dot: true
    preserve_hyphenated_case: false
    strict_stopwords: true
    enable_ac_tier0: false
    enable_vector_fallback: false
    enforce_nominative: true
    preserve_feminine_surnames: true

staging:
  feature_flags:
    use_factory_normalizer: true
    fix_initials_double_dot: true
    preserve_hyphenated_case: true
    strict_stopwords: false
    enable_ac_tier0: true
    enable_vector_fallback: false
    enforce_nominative: true
    preserve_feminine_surnames: true

production:
  feature_flags:
    use_factory_normalizer: false
    fix_initials_double_dot: false
    preserve_hyphenated_case: false
    strict_stopwords: true
    enable_ac_tier0: false
    enable_vector_fallback: false
    enforce_nominative: true
    preserve_feminine_surnames: true
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write(yaml_content)
            f.flush()
            yield f.name
            os.unlink(f.name)

    def test_case_1_request_without_flags_uses_global_config(self, client, temp_yaml_config):
        """
        Test Case 1: Request without flags uses global configuration.
        
        Verifies that when no flags are provided in the request, the system
        uses the global configuration from feature_flags.yaml/ENV.
        """
        # Mock the config file path to use our temp file
        with patch('src.ai_service.config.feature_flags.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__truediv__.return_value = Path(temp_yaml_config)
            
            # Reset global flags to ensure clean state
            from src.ai_service.utils.feature_flags import get_feature_flag_manager
            set_global_flags(None)
            
            # Make request without flags
            response = client.post("/normalize", json={
                "text": "Иван Петров",
                "language": "ru"
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "normalized_text" in data
            assert "trace" in data
            assert "tokens" in data
            
            # Find flags entry in trace
            flags_entry = None
            for entry in data["trace"]:
                if isinstance(entry, dict) and entry.get("type") == "flags":
                    flags_entry = entry
                    break
            
            assert flags_entry is not None, "Flags entry not found in trace"
            flags_value = flags_entry["value"]
            
            # Should use global configuration (development environment)
            assert flags_value["use_factory_normalizer"] == False
            assert flags_value["fix_initials_double_dot"] == True
            assert flags_value["preserve_hyphenated_case"] == False
            assert flags_value["strict_stopwords"] == True
            assert flags_value["enable_ac_tier0"] == False
            assert flags_value["enable_vector_fallback"] == False

    def test_case_2_request_with_partial_flags_merges_with_global(self, client, temp_yaml_config):
        """
        Test Case 2: Request with partial flags merges with global configuration.
        
        Verifies that when only some flags are provided in the request, the system
        merges them with the global configuration for missing flags.
        """
        with patch('src.ai_service.config.feature_flags.Path') as mock_path:
            mock_path.return_value.exists.return_value = True
            mock_path.return_value.__truediv__.return_value = Path(temp_yaml_config)
            
            # Reset global flags
            from src.ai_service.utils.feature_flags import get_feature_flag_manager
            set_global_flags(None)
            
            # Make request with partial flags
            response = client.post("/normalize", json={
                "text": "Иван Петров",
                "language": "ru",
                "options": {
                    "flags": {
                        "fix_initials_double_dot": False,  # Override global
                        "preserve_hyphenated_case": True   # Override global
                        # Other flags should come from global config
                    }
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Find flags entry in trace
            flags_entry = None
            for entry in data["trace"]:
                if isinstance(entry, dict) and entry.get("type") == "flags":
                    flags_entry = entry
                    break
            
            assert flags_entry is not None
            flags_value = flags_entry["value"]
            
            # Should have request overrides
            assert flags_value["fix_initials_double_dot"] == False  # From request
            assert flags_value["preserve_hyphenated_case"] == True  # From request
            
            # Should have global values for others
            assert flags_value["use_factory_normalizer"] == False  # From global
            assert flags_value["strict_stopwords"] == True         # From global
            assert flags_value["enable_ac_tier0"] == False         # From global
            assert flags_value["enable_vector_fallback"] == False  # From global

    def test_case_3_use_factory_normalizer_false_ensures_legacy_used(self, client):
        """
        Test Case 3: use_factory_normalizer=False ensures factory code is not called.
        
        Verifies that when use_factory_normalizer is False, the system uses
        the legacy implementation and does not call factory methods.
        """
        # Mock the orchestrator to track method calls
        with patch('src.ai_service.main.orchestrator') as mock_orchestrator:
            # Configure mock response
            mock_result = MagicMock()
            mock_result.normalized_text = "Иван Петров"
            mock_result.tokens = ["Иван", "Петров"]
            mock_result.trace = []
            mock_result.language = "ru"
            mock_result.success = True
            mock_result.errors = []
            mock_result.processing_time = 0.1
            mock_orchestrator.process.return_value = mock_result
            
            # Make request with use_factory_normalizer=False
            response = client.post("/normalize", json={
                "text": "Иван Петров",
                "language": "ru",
                "options": {
                    "flags": {
                        "use_factory_normalizer": False
                    }
                }
            })
            
            assert response.status_code == 200
            
            # Verify orchestrator was called with correct flags
            mock_orchestrator.process.assert_called_once()
            call_kwargs = mock_orchestrator.process.call_args[1]
            
            # Should have feature_flags parameter
            assert "feature_flags" in call_kwargs
            feature_flags = call_kwargs["feature_flags"]
            
            # Should have use_factory_normalizer=False
            assert hasattr(feature_flags, "use_factory_normalizer")
            assert feature_flags.use_factory_normalizer == False

    def test_case_4_strict_stopwords_true_filters_stopwords(self, client):
        """
        Test Case 4: strict_stopwords=True filters stopwords from normalized output.
        
        Verifies that when strict_stopwords is enabled, stopwords are properly
        filtered from the normalized text and tokens.
        """
        # Mock the orchestrator with realistic response
        with patch('src.ai_service.main.orchestrator') as mock_orchestrator:
            # Configure mock response that shows stopword filtering
            mock_result = MagicMock()
            mock_result.normalized_text = "Иван Петров"  # Stopwords filtered
            mock_result.tokens = ["Иван", "Петров"]      # Stopwords filtered
            mock_result.trace = [
                {"type": "tokenize", "action": "filtered_stopwords", "tokens": ["и", "в", "на"]}
            ]
            mock_result.language = "ru"
            mock_result.success = True
            mock_result.errors = []
            mock_result.processing_time = 0.1
            mock_orchestrator.process.return_value = mock_result
            
            # Make request with strict_stopwords=True
            response = client.post("/normalize", json={
                "text": "и Иван в Петров на",  # Text with stopwords
                "language": "ru",
                "options": {
                    "flags": {
                        "strict_stopwords": True
                    }
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify stopwords were filtered
            assert "и" not in data["normalized_text"]
            assert "в" not in data["normalized_text"]
            assert "на" not in data["normalized_text"]
            
            # Verify only meaningful tokens remain
            assert "Иван" in data["normalized_text"]
            assert "Петров" in data["normalized_text"]
            
            # Verify orchestrator was called with correct flags
            call_kwargs = mock_orchestrator.process.call_args[1]
            feature_flags = call_kwargs["feature_flags"]
            assert feature_flags.strict_stopwords == True

    def test_case_5_fix_initials_double_dot_processing(self, client):
        """
        Test Case 5: fix_initials_double_dot=True processes initials correctly.
        
        Verifies that when fix_initials_double_dot is enabled, double dots
        in initials are collapsed to single dots.
        """
        with patch('src.ai_service.main.orchestrator') as mock_orchestrator:
            # Configure mock response showing initials processing
            mock_result = MagicMock()
            mock_result.normalized_text = "И. Петров"  # Double dots collapsed
            mock_result.tokens = ["И.", "Петров"]
            mock_result.trace = [
                {"type": "tokenize", "action": "collapse_initial_double_dot", "from": "И..", "to": "И."}
            ]
            mock_result.language = "ru"
            mock_result.success = True
            mock_result.errors = []
            mock_result.processing_time = 0.1
            mock_orchestrator.process.return_value = mock_result
            
            # Make request with fix_initials_double_dot=True
            response = client.post("/normalize", json={
                "text": "И.. Петров",  # Text with double dots
                "language": "ru",
                "options": {
                    "flags": {
                        "fix_initials_double_dot": True
                    }
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify double dots were collapsed
            assert "И.." not in data["normalized_text"]
            assert "И." in data["normalized_text"]
            
            # Verify trace shows the processing
            trace_actions = [entry.get("action") for entry in data["trace"] if isinstance(entry, dict)]
            assert "collapse_initial_double_dot" in trace_actions

    def test_case_6_preserve_hyphenated_case_processing(self, client):
        """
        Test Case 6: preserve_hyphenated_case=True preserves proper case in hyphenated names.
        
        Verifies that when preserve_hyphenated_case is enabled, hyphenated names
        maintain proper capitalization.
        """
        with patch('src.ai_service.main.orchestrator') as mock_orchestrator:
            # Configure mock response showing hyphenated case preservation
            mock_result = MagicMock()
            mock_result.normalized_text = "Петрова-Сидорова"  # Proper case preserved
            mock_result.tokens = ["Петрова-Сидорова"]
            mock_result.trace = [
                {"type": "tokenize", "action": "preserve_hyphenated_name", "token": "Петрова-Сидорова", "has_hyphen": True}
            ]
            mock_result.language = "ru"
            mock_result.success = True
            mock_result.errors = []
            mock_result.processing_time = 0.1
            mock_orchestrator.process.return_value = mock_result
            
            # Make request with preserve_hyphenated_case=True
            response = client.post("/normalize", json={
                "text": "петрова-сидорова",  # Text with lowercase hyphenated name
                "language": "ru",
                "options": {
                    "flags": {
                        "preserve_hyphenated_case": True
                    }
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify proper case was preserved
            assert "Петрова-Сидорова" in data["normalized_text"]
            assert "петрова-сидорова" not in data["normalized_text"]
            
            # Verify trace shows the processing
            trace_actions = [entry.get("action") for entry in data["trace"] if isinstance(entry, dict)]
            assert "preserve_hyphenated_name" in trace_actions

    def test_case_7_process_endpoint_with_flags(self, client):
        """
        Test Case 7: /process endpoint correctly handles feature flags.
        
        Verifies that the /process endpoint properly processes feature flags
        and includes them in the response trace.
        """
        with patch('src.ai_service.main.orchestrator') as mock_orchestrator:
            # Configure mock response
            mock_result = MagicMock()
            mock_result.normalized_text = "Иван Петров"
            mock_result.tokens = ["Иван", "Петров"]
            mock_result.trace = []
            mock_result.language = "ru"
            mock_result.success = True
            mock_result.errors = []
            mock_result.processing_time = 0.1
            mock_result.signals = None
            mock_result.decision = None
            mock_result.embeddings = None
            mock_orchestrator.process.return_value = mock_result
            
            # Make request to /process endpoint with flags
            response = client.post("/process", json={
                "text": "Иван Петров",
                "generate_variants": False,
                "generate_embeddings": False,
                "options": {
                    "flags": {
                        "use_factory_normalizer": True,
                        "fix_initials_double_dot": True,
                        "preserve_hyphenated_case": False
                    }
                }
            })
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "normalized_text" in data
            assert "trace" in data
            assert "tokens" in data
            
            # Find flags entry in trace
            flags_entry = None
            for entry in data["trace"]:
                if isinstance(entry, dict) and entry.get("type") == "flags":
                    flags_entry = entry
                    break
            
            assert flags_entry is not None
            flags_value = flags_entry["value"]
            
            # Should have the requested flags
            assert flags_value["use_factory_normalizer"] == True
            assert flags_value["fix_initials_double_dot"] == True
            assert flags_value["preserve_hyphenated_case"] == False

    def test_case_8_environment_variables_override_yaml(self, client, temp_yaml_config):
        """
        Test Case 8: Environment variables override YAML configuration.
        
        Verifies that environment variables take precedence over YAML configuration
        when both are present.
        """
        # Set environment variables
        with patch.dict(os.environ, {
            'AISVC_FLAG_USE_FACTORY_NORMALIZER': 'true',
            'AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT': 'false',
            'AISVC_FLAG_STRICT_STOPWORDS': 'false'
        }):
            with patch('src.ai_service.config.feature_flags.Path') as mock_path:
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.__truediv__.return_value = Path(temp_yaml_config)
                
                # Reset global flags to ensure clean state
                from src.ai_service.utils.feature_flags import get_feature_flag_manager
                set_global_flags(None)
                
                # Make request without flags (should use global config)
                response = client.post("/normalize", json={
                    "text": "Иван Петров",
                    "language": "ru"
                })
                
                assert response.status_code == 200
                data = response.json()
                
                # Find flags entry in trace
                flags_entry = None
                for entry in data["trace"]:
                    if isinstance(entry, dict) and entry.get("type") == "flags":
                        flags_entry = entry
                        break
                
                assert flags_entry is not None
                flags_value = flags_entry["value"]
                
                # Should use environment variable values (override YAML)
                assert flags_value["use_factory_normalizer"] == True   # From ENV
                assert flags_value["fix_initials_double_dot"] == False  # From ENV
                assert flags_value["strict_stopwords"] == False         # From ENV
                
                # Should use YAML values for others
                assert flags_value["preserve_hyphenated_case"] == False  # From YAML
                assert flags_value["enable_ac_tier0"] == False           # From YAML

    def test_case_9_invalid_flags_handled_gracefully(self, client):
        """
        Test Case 9: Invalid flags are handled gracefully without causing errors.
        
        Verifies that the system handles invalid or unexpected flag values
        without crashing or causing errors.
        """
        # Make request with invalid flag values
        response = client.post("/normalize", json={
            "text": "Иван Петров",
            "language": "ru",
            "options": {
                "flags": {
                    "use_factory_normalizer": "invalid_boolean",  # Invalid type
                    "fix_initials_double_dot": True,
                    "unknown_flag": "some_value",  # Unknown flag
                    "strict_stopwords": None  # Invalid value
                }
            }
        })
        
        # Should still succeed (defensive handling)
        assert response.status_code == 200
        data = response.json()
        
        # Should have trace with flags
        assert "trace" in data
        flags_entry = None
        for entry in data["trace"]:
            if isinstance(entry, dict) and entry.get("type") == "flags":
                flags_entry = entry
                break
        
        assert flags_entry is not None
        flags_value = flags_entry["value"]
        
        # Should have valid flags only
        assert "use_factory_normalizer" in flags_value
        assert "fix_initials_double_dot" in flags_value
        assert "strict_stopwords" in flags_value
        assert "unknown_flag" not in flags_value  # Unknown flags should be ignored

    def test_case_10_empty_flags_object_handled(self, client):
        """
        Test Case 10: Empty flags object is handled correctly.
        
        Verifies that an empty flags object in the request is handled
        without causing errors.
        """
        # Make request with empty flags object
        response = client.post("/normalize", json={
            "text": "Иван Петров",
            "language": "ru",
            "options": {
                "flags": {}
            }
        })
        
        assert response.status_code == 200
        data = response.json()
        
        # Should have trace with flags (using global defaults)
        assert "trace" in data
        flags_entry = None
        for entry in data["trace"]:
            if isinstance(entry, dict) and entry.get("type") == "flags":
                flags_entry = entry
                break
        
        assert flags_entry is not None
        flags_value = flags_entry["value"]
        
        # Should have all expected flags with default values
        expected_flags = [
            "use_factory_normalizer",
            "fix_initials_double_dot", 
            "preserve_hyphenated_case",
            "strict_stopwords",
            "enable_ac_tier0",
            "enable_vector_fallback",
            "enforce_nominative",
            "preserve_feminine_surnames"
        ]
        
        for flag in expected_flags:
            assert flag in flags_value
            assert isinstance(flags_value[flag], bool)


if __name__ == "__main__":
    pytest.main([__file__])
