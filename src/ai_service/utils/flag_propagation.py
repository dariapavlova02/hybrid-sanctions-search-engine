"""
Flag propagation utilities for passing feature flags through all layers.

This module provides utilities for propagating feature flags from HTTP requests
through the orchestrator to all processing layers while maintaining traceability.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from ..utils.feature_flags import FeatureFlags
from ..utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class FlagContext:
    """Context for flag propagation through processing layers."""
    flags: FeatureFlags
    layer_name: str
    debug_trace: bool = False
    reasons: List[str] = None
    
    def __post_init__(self):
        if self.reasons is None:
            self.reasons = []
    
    def add_reason(self, reason: str):
        """Add a reason to the trace when debug_trace is enabled."""
        if self.debug_trace:
            self.reasons.append(f"[{self.layer_name}] {reason}")
    
    def get_reasons(self) -> List[str]:
        """Get all reasons collected during processing."""
        return self.reasons.copy()


class FlagPropagator:
    """Handles flag propagation through processing layers."""
    
    def __init__(self):
        self.logger = get_logger(__name__)
    
    def create_context(
        self, 
        flags: FeatureFlags, 
        layer_name: str, 
        debug_trace: bool = False
    ) -> FlagContext:
        """Create a flag context for a specific layer."""
        return FlagContext(
            flags=flags,
            layer_name=layer_name,
            debug_trace=debug_trace
        )
    
    def propagate_to_normalization(
        self, 
        context: FlagContext,
        config: Any
    ) -> Any:
        """Propagate flags to normalization layer."""
        # Map feature flags to normalization config
        if hasattr(config, 'enable_spacy_ner'):
            config.enable_spacy_ner = context.flags.enable_spacy_ner
            if context.flags.enable_spacy_ner:
                context.add_reason("spacy_ner: enabled spaCy NER processing")
        
        if hasattr(config, 'enable_nameparser_en'):
            config.enable_nameparser_en = context.flags.enable_nameparser_en
            if context.flags.enable_nameparser_en:
                context.add_reason("nameparser_en: enabled English nameparser")
        
        if hasattr(config, 'strict_stopwords'):
            config.strict_stopwords = context.flags.strict_stopwords
            if context.flags.strict_stopwords:
                context.add_reason("strict_stopwords: enabled strict stopword filtering")
        
        if hasattr(config, "enable_fsm_tuned_roles"):
            config.enable_fsm_tuned_roles = context.flags.enable_fsm_tuned_roles
            if context.flags.enable_fsm_tuned_roles:
                context.add_reason("enable_fsm_tuned_roles: enabled FSM tuned role classification")
        
        if hasattr(config, "enable_enhanced_diminutives"):
            config.enable_enhanced_diminutives = context.flags.enable_enhanced_diminutives
            if context.flags.enable_enhanced_diminutives:
                context.add_reason("enable_enhanced_diminutives: enabled enhanced diminutive resolution")
        
        if hasattr(config, "enable_enhanced_gender_rules"):
            config.enable_enhanced_gender_rules = context.flags.enable_enhanced_gender_rules
            if context.flags.enable_enhanced_gender_rules:
                context.add_reason("enable_enhanced_gender_rules: enabled enhanced gender rules")
        
        if hasattr(config, 'enable_ac_tier0'):
            config.enable_ac_tier0 = context.flags.enable_ac_tier0
            if context.flags.enable_ac_tier0:
                context.add_reason("ac_tier0: enabled AC tier 0 processing")
        
        if hasattr(config, 'enable_vector_fallback'):
            config.enable_vector_fallback = context.flags.enable_vector_fallback
            if context.flags.enable_vector_fallback:
                context.add_reason("vector_fallback: enabled vector fallback processing")
        
        return config
    
    def propagate_to_search(
        self, 
        context: FlagContext,
        search_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Propagate flags to search layer."""
        if context.flags.enable_ac_tier0:
            search_config['enable_ac_tier0'] = True
            context.add_reason("ac_tier0: enabled AC tier 0 search")
        
        if context.flags.enable_vector_fallback:
            search_config['enable_vector_fallback'] = True
            context.add_reason("vector_fallback: enabled vector fallback search")
        
        return search_config
    
    def propagate_to_embeddings(
        self, 
        context: FlagContext,
        embedding_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Propagate flags to embeddings layer."""
        if context.flags.enable_vector_fallback:
            embedding_config['enable_vector_fallback'] = True
            context.add_reason("vector_fallback: enabled vector fallback embeddings")
        
        return embedding_config
    
    def propagate_to_ner(
        self, 
        context: FlagContext,
        ner_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Propagate flags to NER layer."""
        if context.flags.enable_spacy_ner:
            ner_config['enable_spacy_ner'] = True
            context.add_reason("spacy_ner: enabled spaCy NER processing")
        
        return ner_config
    
    def propagate_to_morphology(
        self, 
        context: FlagContext,
        morph_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Propagate flags to morphology layer."""
        if context.flags.enable_enhanced_diminutives:
            morph_config["enable_enhanced_diminutives"] = True
            context.add_reason("enable_enhanced_diminutives: enabled enhanced diminutive resolution")
        
        if context.flags.enable_enhanced_gender_rules:
            morph_config["enable_enhanced_gender_rules"] = True
            context.add_reason("enable_enhanced_gender_rules: enabled enhanced gender rules")
        
        return morph_config
    
    def propagate_to_role_tagger(
        self, 
        context: FlagContext,
        role_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Propagate flags to role tagger layer."""
        if context.flags.enable_fsm_tuned_roles:
            role_config["enable_fsm_tuned_roles"] = True
            context.add_reason("enable_fsm_tuned_roles: enabled FSM tuned role classification")
        
        if context.flags.strict_stopwords:
            role_config['strict_stopwords'] = True
            context.add_reason("strict_stopwords: enabled strict stopword filtering")
        
        return role_config
    
    def propagate_to_tokenizer(
        self, 
        context: FlagContext,
        tokenizer_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Propagate flags to tokenizer layer."""
        if context.flags.strict_stopwords:
            tokenizer_config['strict_stopwords'] = True
            context.add_reason("strict_stopwords: enabled strict stopword filtering")
        
        return tokenizer_config
    
    def get_effective_flags(
        self, 
        context: FlagContext
    ) -> Dict[str, Any]:
        """Get effective flags for the current context."""
        effective_flags = {}
        
        # Map all flags to their effective values
        flag_mapping = {
            'enable_spacy_ner': context.flags.enable_spacy_ner,
            'enable_nameparser_en': context.flags.enable_nameparser_en,
            'strict_stopwords': context.flags.strict_stopwords,
            "enable_fsm_tuned_roles": context.flags.enable_fsm_tuned_roles,
            "enable_enhanced_diminutives": context.flags.enable_enhanced_diminutives,
            "enable_enhanced_gender_rules": context.flags.enable_enhanced_gender_rules,
            'enable_ac_tier0': context.flags.enable_ac_tier0,
            'enable_vector_fallback': context.flags.enable_vector_fallback,
        }
        
        # Only include enabled flags
        for flag_name, flag_value in flag_mapping.items():
            if flag_value:
                effective_flags[flag_name] = flag_value
        
        return effective_flags
    
    def log_flag_usage(
        self, 
        context: FlagContext,
        layer_name: str
    ):
        """Log flag usage for monitoring and debugging."""
        effective_flags = self.get_effective_flags(context)
        
        if effective_flags:
            self.logger.info(
                f"Flags active in {layer_name}: {effective_flags}"
            )
        
        if context.debug_trace and context.reasons:
            self.logger.debug(
                f"Flag reasons for {layer_name}: {context.reasons}"
            )


# Global flag propagator instance
flag_propagator = FlagPropagator()


def create_flag_context(
    flags: FeatureFlags, 
    layer_name: str, 
    debug_trace: bool = False
) -> FlagContext:
    """Create a flag context for a specific layer."""
    return flag_propagator.create_context(flags, layer_name, debug_trace)


def propagate_flags_to_layer(
    context: FlagContext,
    layer_name: str,
    config: Any
) -> Any:
    """Propagate flags to a specific layer."""
    if layer_name == "normalization":
        return flag_propagator.propagate_to_normalization(context, config)
    elif layer_name == "search":
        return flag_propagator.propagate_to_search(context, config)
    elif layer_name == "embeddings":
        return flag_propagator.propagate_to_embeddings(context, config)
    elif layer_name == "ner":
        return flag_propagator.propagate_to_ner(context, config)
    elif layer_name == "morphology":
        return flag_propagator.propagate_to_morphology(context, config)
    elif layer_name == "role_tagger":
        return flag_propagator.propagate_to_role_tagger(context, config)
    elif layer_name == "tokenizer":
        return flag_propagator.propagate_to_tokenizer(context, config)
    else:
        logger.warning(f"Unknown layer: {layer_name}")
        return config
