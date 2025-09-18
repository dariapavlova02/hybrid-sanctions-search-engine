"""
Integration tests for HTTP flag integration.

This module tests that feature flags are properly propagated from HTTP requests
through the entire processing pipeline.
"""

import pytest
import asyncio
from typing import Dict, Any

from src.ai_service.utils.feature_flags import FeatureFlags
from src.ai_service.main import _merge_feature_flags
from src.ai_service.utils.feature_flags import get_feature_flag_manager


class TestHttpFlagIntegration:
    """Test HTTP flag integration and propagation."""
    
    def test_merge_feature_flags_with_validation_flags(self):
        """Test merging feature flags with new validation flags."""
        # Create request flags with validation flags enabled
        request_flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True
        )
        
        # Merge with global flags
        merged_flags = _merge_feature_flags(request_flags)
        
        # Check that validation flags were merged
        assert merged_flags.enable_spacy_ner is True
        assert merged_flags.enable_nameparser_en is True
        assert merged_flags.strict_stopwords is True
        assert merged_flags.fsm_tuned_roles is True
        assert merged_flags.enhanced_diminutives is True
        assert merged_flags.enhanced_gender_rules is True
        assert merged_flags.enable_ac_tier0 is True
        assert merged_flags.enable_vector_fallback is True
        assert merged_flags.ascii_fastpath is True
    
    def test_merge_feature_flags_with_none_request(self):
        """Test merging feature flags with None request flags."""
        # Merge with None request flags
        merged_flags = _merge_feature_flags(None)
        
        # Should return global flags
        global_flags = get_feature_flag_manager()._flags
        assert merged_flags == global_flags
    
    def test_merge_feature_flags_partial_override(self):
        """Test merging feature flags with partial override."""
        # Create request flags with only some validation flags enabled
        request_flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=False,  # Explicitly False
            strict_stopwords=True,
            fsm_tuned_roles=False,  # Explicitly False
            enhanced_diminutives=True,
            enhanced_gender_rules=False,  # Explicitly False
            enable_ac_tier0=True,
            enable_vector_fallback=False,  # Explicitly False
            ascii_fastpath=True
        )
        
        # Merge with global flags
        merged_flags = _merge_feature_flags(request_flags)
        
        # Check that only enabled flags were set
        assert merged_flags.enable_spacy_ner is True
        assert merged_flags.enable_nameparser_en is False
        assert merged_flags.strict_stopwords is True
        assert merged_flags.fsm_tuned_roles is False
        assert merged_flags.enhanced_diminutives is True
        assert merged_flags.enhanced_gender_rules is False
        assert merged_flags.enable_ac_tier0 is True
        assert merged_flags.enable_vector_fallback is False
        assert merged_flags.ascii_fastpath is True
    
    def test_feature_flags_to_dict(self):
        """Test that feature flags are properly serialized to dict."""
        flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True
        )
        
        flags_dict = flags.to_dict()
        
        # Check that all validation flags are in the dict
        assert 'enable_spacy_ner' in flags_dict
        assert 'enable_nameparser_en' in flags_dict
        assert 'strict_stopwords' in flags_dict
        assert 'fsm_tuned_roles' in flags_dict
        assert 'enhanced_diminutives' in flags_dict
        assert 'enhanced_gender_rules' in flags_dict
        assert 'enable_ac_tier0' in flags_dict
        assert 'enable_vector_fallback' in flags_dict
        assert 'ascii_fastpath' in flags_dict
        
        # Check that values are correct
        assert flags_dict['enable_spacy_ner'] is True
        assert flags_dict['enable_nameparser_en'] is True
        assert flags_dict['strict_stopwords'] is True
        assert flags_dict['fsm_tuned_roles'] is True
        assert flags_dict['enhanced_diminutives'] is True
        assert flags_dict['enhanced_gender_rules'] is True
        assert flags_dict['enable_ac_tier0'] is True
        assert flags_dict['enable_vector_fallback'] is True
        assert flags_dict['ascii_fastpath'] is True
    
    def test_feature_flags_default_values(self):
        """Test that feature flags have correct default values."""
        flags = FeatureFlags()
        
        # Check that validation flags default to False
        assert flags.enable_spacy_ner is False
        assert flags.enable_nameparser_en is False
        assert flags.strict_stopwords is False
        assert flags.fsm_tuned_roles is False
        assert flags.enhanced_diminutives is False
        assert flags.enhanced_gender_rules is False
        assert flags.enable_ac_tier0 is False
        assert flags.enable_vector_fallback is False
        assert flags.ascii_fastpath is False
    
    def test_feature_flags_string_representation(self):
        """Test feature flags string representation."""
        flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True
        )
        
        flags_str = str(flags)
        
        # Should contain enabled flags
        assert 'enable_spacy_ner' in flags_str
        assert 'enable_nameparser_en' in flags_str
        assert 'strict_stopwords' in flags_str
    
    def test_feature_flags_environment_variable_mapping(self):
        """Test that feature flags can be loaded from environment variables."""
        import os
        
        # Set environment variables
        os.environ['AISVC_FLAG_ENABLE_SPACY_NER'] = 'true'
        os.environ['AISVC_FLAG_ENABLE_NAMEPARSER_EN'] = 'true'
        os.environ['AISVC_FLAG_STRICT_STOPWORDS'] = 'true'
        os.environ['AISVC_FLAG_FSM_TUNED_ROLES'] = 'true'
        os.environ['AISVC_FLAG_ENHANCED_DIMINUTIVES'] = 'true'
        os.environ['AISVC_FLAG_ENHANCED_GENDER_RULES'] = 'true'
        os.environ['AISVC_FLAG_ENABLE_AC_TIER0'] = 'true'
        os.environ['AISVC_FLAG_ENABLE_VECTOR_FALLBACK'] = 'true'
        os.environ['AISVC_FLAG_ASCII_FASTPATH'] = 'true'
        
        try:
            # Load flags from environment
            from src.ai_service.utils.feature_flags import get_feature_flag_manager
            flags = get_feature_flag_manager()._flags
            
            # Check that flags were loaded from environment
            assert flags.enable_spacy_ner is True
            assert flags.enable_nameparser_en is True
            assert flags.strict_stopwords is True
            assert flags.fsm_tuned_roles is True
            assert flags.enhanced_diminutives is True
            assert flags.enhanced_gender_rules is True
            assert flags.enable_ac_tier0 is True
            assert flags.enable_vector_fallback is True
            assert flags.ascii_fastpath is True
            
        finally:
            # Clean up environment variables
            for key in [
                'AISVC_FLAG_ENABLE_SPACY_NER',
                'AISVC_FLAG_ENABLE_NAMEPARSER_EN',
                'AISVC_FLAG_STRICT_STOPWORDS',
                'AISVC_FLAG_FSM_TUNED_ROLES',
                'AISVC_FLAG_ENHANCED_DIMINUTIVES',
                'AISVC_FLAG_ENHANCED_GENDER_RULES',
                'AISVC_FLAG_ENABLE_AC_TIER0',
                'AISVC_FLAG_ENABLE_VECTOR_FALLBACK',
                'AISVC_FLAG_ASCII_FASTPATH'
            ]:
                os.environ.pop(key, None)
    
    def test_feature_flags_validation_scope(self):
        """Test that validation flags are properly scoped."""
        flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True
        )
        
        # All validation flags should be present
        flags_dict = flags.to_dict()
        
        validation_flags = [
            'enable_spacy_ner',
            'enable_nameparser_en',
            'strict_stopwords',
            'fsm_tuned_roles',
            'enhanced_diminutives',
            'enhanced_gender_rules',
            'enable_ac_tier0',
            'enable_vector_fallback',
            'ascii_fastpath'
        ]
        
        for flag in validation_flags:
            assert flag in flags_dict
            assert flags_dict[flag] is True
    
    def test_feature_flags_backward_compatibility(self):
        """Test that existing flags are not affected by new validation flags."""
        flags = FeatureFlags(
            use_factory_normalizer=True,
            fix_initials_double_dot=True,
            preserve_hyphenated_case=True,
            # Validation flags
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True,
            ascii_fastpath=True
        )
        
        flags_dict = flags.to_dict()
        
        # Check that existing flags are still present
        assert 'use_factory_normalizer' in flags_dict
        assert 'fix_initials_double_dot' in flags_dict
        assert 'preserve_hyphenated_case' in flags_dict
        
        # Check that validation flags are present
        assert 'enable_spacy_ner' in flags_dict
        assert 'enable_nameparser_en' in flags_dict
        assert 'strict_stopwords' in flags_dict
        assert 'fsm_tuned_roles' in flags_dict
        assert 'enhanced_diminutives' in flags_dict
        assert 'enhanced_gender_rules' in flags_dict
        assert 'enable_ac_tier0' in flags_dict
        assert 'enable_vector_fallback' in flags_dict
        assert 'ascii_fastpath' in flags_dict


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
