"""
Integration tests for flag propagation through all layers.

This module tests that feature flags are properly propagated from HTTP requests
through the orchestrator to all processing layers.
"""

import pytest
import asyncio
from typing import Dict, Any, List

from src.ai_service.config.feature_flags import FeatureFlags
from src.ai_service.utils.flag_propagation import FlagPropagator, FlagContext
from src.ai_service.layers.normalization.processors.normalization_factory import (
    NormalizationFactory, 
    NormalizationConfig
)
from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator


class TestFlagPropagationIntegration:
    """Test flag propagation through all processing layers."""
    
    @pytest.fixture(scope="class")
    def flag_propagator(self):
        """Create flag propagator for testing."""
        return FlagPropagator()
    
    @pytest.fixture(scope="class")
    def normalization_factory(self):
        """Create normalization factory for testing."""
        return NormalizationFactory()
    
    @pytest.fixture(scope="class")
    def orchestrator(self):
        """Create orchestrator for testing."""
        return UnifiedOrchestrator()
    
    def test_flag_context_creation(self, flag_propagator: FlagPropagator):
        """Test flag context creation."""
        flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True
        )
        
        context = flag_propagator.create_context(flags, "test_layer", True)
        
        assert context.flags == flags
        assert context.layer_name == "test_layer"
        assert context.debug_trace is True
        assert context.reasons == []
    
    def test_flag_context_reasons(self, flag_propagator: FlagPropagator):
        """Test flag context reason collection."""
        flags = FeatureFlags(enable_spacy_ner=True)
        context = flag_propagator.create_context(flags, "test_layer", True)
        
        context.add_reason("Test reason 1")
        context.add_reason("Test reason 2")
        
        reasons = context.get_reasons()
        assert len(reasons) == 2
        assert "[test_layer] Test reason 1" in reasons
        assert "[test_layer] Test reason 2" in reasons
    
    def test_normalization_flag_propagation(self, flag_propagator: FlagPropagator):
        """Test flag propagation to normalization layer."""
        flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True
        )
        
        context = flag_propagator.create_context(flags, "normalization", True)
        config = NormalizationConfig()
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_normalization(context, config)
        
        # Check that flags were propagated
        assert updated_config.enable_spacy_ner is True
        assert updated_config.enable_nameparser_en is True
        assert updated_config.strict_stopwords is True
        assert updated_config.fsm_tuned_roles is True
        assert updated_config.enhanced_diminutives is True
        assert updated_config.enhanced_gender_rules is True
        assert updated_config.enable_ac_tier0 is True
        assert updated_config.enable_vector_fallback is True
        
        # Check that reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 8
        assert any("spacy_ner: enabled spaCy NER processing" in reason for reason in reasons)
        assert any("nameparser_en: enabled English nameparser" in reason for reason in reasons)
        assert any("strict_stopwords: enabled strict stopword filtering" in reason for reason in reasons)
        assert any("fsm_tuned_roles: enabled FSM tuned role classification" in reason for reason in reasons)
        assert any("enhanced_diminutives: enabled enhanced diminutive resolution" in reason for reason in reasons)
        assert any("enhanced_gender_rules: enabled enhanced gender rules" in reason for reason in reasons)
        assert any("ac_tier0: enabled AC tier 0 processing" in reason for reason in reasons)
        assert any("vector_fallback: enabled vector fallback processing" in reason for reason in reasons)
    
    def test_search_flag_propagation(self, flag_propagator: FlagPropagator):
        """Test flag propagation to search layer."""
        flags = FeatureFlags(
            enable_ac_tier0=True,
            enable_vector_fallback=True
        )
        
        context = flag_propagator.create_context(flags, "search", True)
        search_config = {}
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_search(context, search_config)
        
        # Check that flags were propagated
        assert updated_config['enable_ac_tier0'] is True
        assert updated_config['enable_vector_fallback'] is True
        
        # Check that reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 2
        assert any("ac_tier0: enabled AC tier 0 search" in reason for reason in reasons)
        assert any("vector_fallback: enabled vector fallback search" in reason for reason in reasons)
    
    def test_embeddings_flag_propagation(self, flag_propagator: FlagPropagator):
        """Test flag propagation to embeddings layer."""
        flags = FeatureFlags(enable_vector_fallback=True)
        
        context = flag_propagator.create_context(flags, "embeddings", True)
        embedding_config = {}
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_embeddings(context, embedding_config)
        
        # Check that flags were propagated
        assert updated_config['enable_vector_fallback'] is True
        
        # Check that reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 1
        assert any("vector_fallback: enabled vector fallback embeddings" in reason for reason in reasons)
    
    def test_ner_flag_propagation(self, flag_propagator: FlagPropagator):
        """Test flag propagation to NER layer."""
        flags = FeatureFlags(enable_spacy_ner=True)
        
        context = flag_propagator.create_context(flags, "ner", True)
        ner_config = {}
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_ner(context, ner_config)
        
        # Check that flags were propagated
        assert updated_config['enable_spacy_ner'] is True
        
        # Check that reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 1
        assert any("spacy_ner: enabled spaCy NER processing" in reason for reason in reasons)
    
    def test_morphology_flag_propagation(self, flag_propagator: FlagPropagator):
        """Test flag propagation to morphology layer."""
        flags = FeatureFlags(
            enhanced_diminutives=True,
            enhanced_gender_rules=True
        )
        
        context = flag_propagator.create_context(flags, "morphology", True)
        morph_config = {}
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_morphology(context, morph_config)
        
        # Check that flags were propagated
        assert updated_config['enhanced_diminutives'] is True
        assert updated_config['enhanced_gender_rules'] is True
        
        # Check that reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 2
        assert any("enhanced_diminutives: enabled enhanced diminutive resolution" in reason for reason in reasons)
        assert any("enhanced_gender_rules: enabled enhanced gender rules" in reason for reason in reasons)
    
    def test_role_tagger_flag_propagation(self, flag_propagator: FlagPropagator):
        """Test flag propagation to role tagger layer."""
        flags = FeatureFlags(
            fsm_tuned_roles=True,
            strict_stopwords=True
        )
        
        context = flag_propagator.create_context(flags, "role_tagger", True)
        role_config = {}
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_role_tagger(context, role_config)
        
        # Check that flags were propagated
        assert updated_config['fsm_tuned_roles'] is True
        assert updated_config['strict_stopwords'] is True
        
        # Check that reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 2
        assert any("fsm_tuned_roles: enabled FSM tuned role classification" in reason for reason in reasons)
        assert any("strict_stopwords: enabled strict stopword filtering" in reason for reason in reasons)
    
    def test_tokenizer_flag_propagation(self, flag_propagator: FlagPropagator):
        """Test flag propagation to tokenizer layer."""
        flags = FeatureFlags(strict_stopwords=True)
        
        context = flag_propagator.create_context(flags, "tokenizer", True)
        tokenizer_config = {}
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_tokenizer(context, tokenizer_config)
        
        # Check that flags were propagated
        assert updated_config['strict_stopwords'] is True
        
        # Check that reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 1
        assert any("strict_stopwords: enabled strict stopword filtering" in reason for reason in reasons)
    
    def test_get_effective_flags(self, flag_propagator: FlagPropagator):
        """Test getting effective flags."""
        flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=False,  # Disabled
            strict_stopwords=True,
            fsm_tuned_roles=False,  # Disabled
            enhanced_diminutives=True,
            enhanced_gender_rules=False,  # Disabled
            enable_ac_tier0=True,
            enable_vector_fallback=False  # Disabled
        )
        
        context = flag_propagator.create_context(flags, "test_layer", True)
        effective_flags = flag_propagator.get_effective_flags(context)
        
        # Should only include enabled flags
        expected_flags = {
            'enable_spacy_ner': True,
            'strict_stopwords': True,
            'enhanced_diminutives': True,
            'enable_ac_tier0': True
        }
        
        assert effective_flags == expected_flags
    
    @pytest.mark.asyncio
    async def test_normalization_factory_flag_propagation(
        self, 
        normalization_factory: NormalizationFactory
    ):
        """Test flag propagation in normalization factory."""
        flags = FeatureFlags(
            enable_spacy_ner=True,
            enable_nameparser_en=True,
            strict_stopwords=True,
            fsm_tuned_roles=True,
            enhanced_diminutives=True,
            enhanced_gender_rules=True,
            enable_ac_tier0=True,
            enable_vector_fallback=True
        )
        
        config = NormalizationConfig(debug_tracing=True)
        text = "John Smith"
        
        # Test normalization with flags
        result = await normalization_factory.normalize_text(text, config, flags)
        
        # Check that result was successful
        assert result.success
        
        # Check that flags were propagated to config
        assert config.enable_spacy_ner is True
        assert config.enable_nameparser_en is True
        assert config.strict_stopwords is True
        assert config.fsm_tuned_roles is True
        assert config.enhanced_diminutives is True
        assert config.enhanced_gender_rules is True
        assert config.enable_ac_tier0 is True
        assert config.enable_vector_fallback is True
    
    def test_flag_propagation_without_debug_trace(self, flag_propagator: FlagPropagator):
        """Test flag propagation without debug trace."""
        flags = FeatureFlags(enable_spacy_ner=True)
        
        context = flag_propagator.create_context(flags, "test_layer", False)
        config = NormalizationConfig()
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_normalization(context, config)
        
        # Check that flags were propagated
        assert updated_config.enable_spacy_ner is True
        
        # Check that no reasons were added (debug_trace=False)
        reasons = context.get_reasons()
        assert len(reasons) == 0
    
    def test_flag_propagation_unknown_layer(self, flag_propagator: FlagPropagator):
        """Test flag propagation to unknown layer."""
        flags = FeatureFlags(enable_spacy_ner=True)
        
        context = flag_propagator.create_context(flags, "unknown_layer", True)
        config = {}
        
        # Propagate flags to unknown layer
        updated_config = flag_propagator.propagate_to_normalization(context, config)
        
        # Should return original config unchanged
        assert updated_config == config
        
        # Should log warning
        # Note: This test verifies the behavior, actual logging verification would require more complex setup
    
    def test_flag_propagation_empty_flags(self, flag_propagator: FlagPropagator):
        """Test flag propagation with empty flags."""
        flags = FeatureFlags()  # All flags default to False
        
        context = flag_propagator.create_context(flags, "normalization", True)
        config = NormalizationConfig()
        
        # Propagate flags
        updated_config = flag_propagator.propagate_to_normalization(context, config)
        
        # Check that no flags were set
        assert updated_config.enable_spacy_ner is False
        assert updated_config.enable_nameparser_en is False
        assert updated_config.strict_stopwords is False
        assert updated_config.fsm_tuned_roles is False
        assert updated_config.enhanced_diminutives is False
        assert updated_config.enhanced_gender_rules is False
        assert updated_config.enable_ac_tier0 is False
        assert updated_config.enable_vector_fallback is False
        
        # Check that no reasons were added
        reasons = context.get_reasons()
        assert len(reasons) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
