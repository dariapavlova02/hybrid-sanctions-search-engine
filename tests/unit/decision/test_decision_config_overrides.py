"""
Unit tests for decision configuration overrides.

Tests environment variable overrides for DecisionConfig
with AI_DECISION__ prefix support.
"""

import os
import pytest
from unittest.mock import patch

from src.ai_service.config.settings import DecisionConfig, DECISION_CONFIG
from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo


class TestDecisionConfigOverrides:
    """Test decision configuration environment variable overrides"""
    
    def test_default_config_values(self):
        """Test that default configuration values are correct"""
        config = DecisionConfig()
        
        # Test default weights
        assert config.w_smartfilter == 0.25
        assert config.w_person == 0.3
        assert config.w_org == 0.15
        assert config.w_similarity == 0.25
        assert config.bonus_date_match == 0.07
        assert config.bonus_id_match == 0.15
        
        # Test default thresholds
        assert config.thr_high == 0.85
        assert config.thr_medium == 0.65
    
    def test_env_override_thr_high(self):
        """Test that AI_DECISION__THR_HIGH environment variable overrides thr_high"""
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.9'}):
            config = DecisionConfig()
            assert config.thr_high == 0.9
            # Other values should remain default
            assert config.thr_medium == 0.65
            assert config.w_smartfilter == 0.25
    
    def test_env_override_thr_medium(self):
        """Test that AI_DECISION__THR_MEDIUM environment variable overrides thr_medium"""
        with patch.dict(os.environ, {'AI_DECISION__THR_MEDIUM': '0.7'}):
            config = DecisionConfig()
            assert config.thr_medium == 0.7
            # Other values should remain default
            assert config.thr_high == 0.85
            assert config.w_smartfilter == 0.25
    
    def test_env_override_weights(self):
        """Test that weight environment variables override default values"""
        env_overrides = {
            'AI_DECISION__W_SMARTFILTER': '0.3',
            'AI_DECISION__W_PERSON': '0.4',
            'AI_DECISION__W_ORG': '0.2',
            'AI_DECISION__W_SIMILARITY': '0.3',
            'AI_DECISION__BONUS_DATE_MATCH': '0.1',
            'AI_DECISION__BONUS_ID_MATCH': '0.2'
        }
        
        with patch.dict(os.environ, env_overrides):
            config = DecisionConfig()
            assert config.w_smartfilter == 0.3
            assert config.w_person == 0.4
            assert config.w_org == 0.2
            assert config.w_similarity == 0.3
            assert config.bonus_date_match == 0.1
            assert config.bonus_id_match == 0.2
    
    def test_env_override_all_values(self):
        """Test that all environment variables can be overridden simultaneously"""
        env_overrides = {
            'AI_DECISION__W_SMARTFILTER': '0.35',
            'AI_DECISION__W_PERSON': '0.45',
            'AI_DECISION__W_ORG': '0.25',
            'AI_DECISION__W_SIMILARITY': '0.35',
            'AI_DECISION__BONUS_DATE_MATCH': '0.12',
            'AI_DECISION__BONUS_ID_MATCH': '0.22',
            'AI_DECISION__THR_HIGH': '0.9',
            'AI_DECISION__THR_MEDIUM': '0.7'
        }
        
        with patch.dict(os.environ, env_overrides):
            config = DecisionConfig()
            
            # Verify all weights
            assert config.w_smartfilter == 0.35
            assert config.w_person == 0.45
            assert config.w_org == 0.25
            assert config.w_similarity == 0.35
            assert config.bonus_date_match == 0.12
            assert config.bonus_id_match == 0.22
            
            # Verify all thresholds
            assert config.thr_high == 0.9
            assert config.thr_medium == 0.7
    
    def test_env_override_invalid_values(self):
        """Test that invalid environment variable values raise appropriate errors"""
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': 'invalid'}):
            with pytest.raises(ValueError):
                DecisionConfig()
    
    def test_env_override_partial_values(self):
        """Test that only some environment variables can be overridden"""
        with patch.dict(os.environ, {
            'AI_DECISION__THR_HIGH': '0.9',
            'AI_DECISION__W_PERSON': '0.4'
        }):
            config = DecisionConfig()
            
            # Overridden values
            assert config.thr_high == 0.9
            assert config.w_person == 0.4
            
            # Default values should remain
            assert config.thr_medium == 0.65
            assert config.w_smartfilter == 0.25
            assert config.w_org == 0.15
            assert config.w_similarity == 0.25
            assert config.bonus_date_match == 0.07
            assert config.bonus_id_match == 0.15
    
    def test_unified_config_uses_env_overrides(self):
        """Test that DECISION_CONFIG uses environment variable overrides"""
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.9'}):
            # Re-import to get fresh config with ENV overrides
            import importlib
            from src.ai_service.config import settings
            importlib.reload(settings)
            
            assert settings.DECISION_CONFIG.thr_high == 0.9
            assert settings.DECISION_CONFIG.thr_medium == 0.65  # Default
    
    def test_decision_engine_uses_unified_config(self):
        """Test that DecisionEngine uses unified config with ENV overrides"""
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.9'}):
            # Create fresh config with ENV overrides
            config = DecisionConfig()
            assert config.thr_high == 0.9
            assert config.thr_medium == 0.65  # Default
            
            # Test that DecisionEngine can use this config
            engine = DecisionEngine(config=config)
            assert engine.config.thr_high == 0.9
    
    def test_decision_engine_custom_config_overrides_env(self):
        """Test that custom config passed to DecisionEngine overrides ENV config"""
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.9'}):
            # Re-import to get fresh config with ENV overrides
            import importlib
            from src.ai_service.config import settings
            from src.ai_service.core.decision_engine import DecisionEngine
            importlib.reload(settings)
            
            # Create custom config
            custom_config = DecisionConfig()
            custom_config.thr_high = 0.95  # Override ENV value
            
            engine = DecisionEngine(config=custom_config)
            assert engine.config.thr_high == 0.95  # Custom config wins
            assert engine.config.thr_medium == 0.65  # Default
    
    def test_decision_engine_functionality_with_env_overrides(self):
        """Test that DecisionEngine works correctly with ENV overrides"""
        with patch.dict(os.environ, {
            'AI_DECISION__THR_HIGH': '0.9',
            'AI_DECISION__W_PERSON': '0.4'
        }):
            # Create fresh config with ENV overrides
            config = DecisionConfig()
            engine = DecisionEngine(config=config)
            
            # Test that the overridden values are used in decision making
            assert engine.config.thr_high == 0.9
            assert engine.config.w_person == 0.4
            
            # Create test input
            inp = DecisionInput(
                text="John Doe",
                smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
                signals=SignalsInfo(person_confidence=0.8, org_confidence=0.0),
                similarity=SimilarityInfo(cos_top=None)
            )
            
            # Make decision
            output = engine.decide(inp)
            
            # Verify decision uses overridden values
            assert output.risk.value in ['low', 'medium', 'high']
            assert 0.0 <= output.score <= 1.0
            
            # Verify details contain overridden values
            assert output.details['thresholds']['thr_high'] == 0.9
            assert output.details['weights_used']['w_person'] == 0.4
    
    def test_env_override_edge_cases(self):
        """Test edge cases for environment variable overrides"""
        
        # Test empty string (should use default)
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': ''}):
            with pytest.raises(ValueError):
                DecisionConfig()
        
        # Test very small values
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.001'}):
            config = DecisionConfig()
            assert config.thr_high == 0.001
        
        # Test very large values
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.999'}):
            config = DecisionConfig()
            assert config.thr_high == 0.999
        
        # Test negative values (should be allowed for weights)
        with patch.dict(os.environ, {'AI_DECISION__W_PERSON': '-0.1'}):
            config = DecisionConfig()
            assert config.w_person == -0.1
    
    def test_config_model_dump_with_env_overrides(self):
        """Test that model_dump() reflects environment variable overrides"""
        with patch.dict(os.environ, {
            'AI_DECISION__THR_HIGH': '0.9',
            'AI_DECISION__W_PERSON': '0.4'
        }):
            config = DecisionConfig()
            config_dict = config.model_dump()
            
            assert config_dict['thr_high'] == 0.9
            assert config_dict['w_person'] == 0.4
            assert config_dict['thr_medium'] == 0.65  # Default
            assert config_dict['w_smartfilter'] == 0.25  # Default
    
    def test_env_override_case_sensitivity(self):
        """Test that environment variable names are case sensitive"""
        with patch.dict(os.environ, {
            'ai_decision__thr_high': '0.9',  # lowercase
            'AI_DECISION__W_PERSON': '0.4'   # uppercase
        }):
            config = DecisionConfig()
            
            # Only uppercase should work
            assert config.thr_high == 0.85  # Default (lowercase didn't work)
            assert config.w_person == 0.4   # Override worked
    
    def test_env_override_priority(self):
        """Test that environment variables take priority over defaults"""
        # First test without ENV
        config1 = DecisionConfig()
        assert config1.thr_high == 0.85
        
        # Then test with ENV
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.9'}):
            config2 = DecisionConfig()
            assert config2.thr_high == 0.9  # ENV overrides default
    
    def test_multiple_instances_consistency(self):
        """Test that multiple DecisionConfig instances use same ENV values"""
        with patch.dict(os.environ, {'AI_DECISION__THR_HIGH': '0.9'}):
            config1 = DecisionConfig()
            config2 = DecisionConfig()
            
            assert config1.thr_high == config2.thr_high == 0.9
            assert config1.thr_medium == config2.thr_medium == 0.65
