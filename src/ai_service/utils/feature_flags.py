"""
Feature flag system for controlling normalization implementation.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class NormalizationImplementation(Enum):
    """Available normalization implementations."""
    LEGACY = "legacy"
    FACTORY = "factory"
    AUTO = "auto"  # Automatic selection based on conditions

@dataclass
class FeatureFlags:
    """Feature flags configuration."""

    # Primary normalization implementation
    normalization_implementation: NormalizationImplementation = NormalizationImplementation.FACTORY

    # Gradual rollout percentage (0-100)
    factory_rollout_percentage: int = 100

    # Performance-based fallback
    enable_performance_fallback: bool = True
    max_latency_threshold_ms: float = 100.0

    # Accuracy-based fallback
    enable_accuracy_monitoring: bool = True
    min_confidence_threshold: float = 0.8

    # Debug and monitoring
    enable_dual_processing: bool = False  # Process with both implementations for comparison
    log_implementation_choice: bool = True
    debug_tracing: bool = False  # Enable debug tracing

    # New feature flags for safe rollout
    use_factory_normalizer: bool = True  # Default to factory implementation
    fix_initials_double_dot: bool = False  # Collapse И.. → И.
    preserve_hyphenated_case: bool = False  # Петрова-сидорова → Петрова-Сидорова
    strict_stopwords: bool = False  # Filter stopwords from tokens
    enable_ac_tier0: bool = True
    enable_vector_fallback: bool = True
    
    # Morphology flags
    morphology_custom_rules_first: bool = True  # Apply custom rules before pymorphy3
    
    # English-specific flags
    enable_nameparser_en: bool = True  # Enable nameparser for English name parsing
    enable_en_nicknames: bool = True  # Enable English nickname resolution

    # Validation and NER flags
    enable_spacy_ner: bool = True   # Enable spaCy NER processing - ВАЖНО для качества!
    enable_spacy_uk_ner: bool = True  # Enable spaCy Ukrainian NER - КРИТИЧНО для украинского!
    enable_spacy_en_ner: bool = True  # Enable spaCy English NER - ВАЖНО для английского!
    enable_fsm_tuned_roles: bool = True  # Use FSM-tuned role detection - улучшенная логика
    enable_enhanced_diminutives: bool = True  # Enhanced diminutive handling
    enable_enhanced_gender_rules: bool = True  # Enhanced gender rule processing - ВАЖНО!
    preserve_feminine_suffix_uk: bool = True  # Preserve Ukrainian feminine suffixes - КРИТИЧНО!
    en_use_nameparser: bool = True  # Use nameparser for English names
    enable_en_nickname_expansion: bool = True  # Expand English nicknames
    filter_titles_suffixes: bool = True  # Filter out titles and suffixes from EN names

    # Business gates
    require_tin_dob_gate: bool = True  # Require TIN/DOB for strong name matches

    # Nominative and gender enforcement flags
    enforce_nominative: bool = True
    preserve_feminine_surnames: bool = True
    
    # ASCII fastpath optimization
    enable_ascii_fastpath: bool = True

    # Diminutive resolution
    use_diminutives_dictionary_only: bool = False
    diminutives_allow_cross_lang: bool = False

    # Language-specific overrides
    language_overrides: Dict[str, NormalizationImplementation] = None

    def __post_init__(self):
        if self.language_overrides is None:
            self.language_overrides = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feature flags to dictionary for tracing and serialization."""
        return {
            "use_factory_normalizer": self.use_factory_normalizer,
            "fix_initials_double_dot": self.fix_initials_double_dot,
            "preserve_hyphenated_case": self.preserve_hyphenated_case,
            "strict_stopwords": self.strict_stopwords,
            "enable_ac_tier0": self.enable_ac_tier0,
            "enable_vector_fallback": self.enable_vector_fallback,
            "enable_nameparser_en": self.enable_nameparser_en,
            "enable_en_nicknames": self.enable_en_nicknames,
            "enable_spacy_ner": self.enable_spacy_ner,
            "enable_spacy_uk_ner": self.enable_spacy_uk_ner,
            "enable_spacy_en_ner": self.enable_spacy_en_ner,
            "enable_fsm_tuned_roles": self.enable_fsm_tuned_roles,
            "enable_enhanced_diminutives": self.enable_enhanced_diminutives,
            "enable_enhanced_gender_rules": self.enable_enhanced_gender_rules,
            "preserve_feminine_suffix_uk": self.preserve_feminine_suffix_uk,
            "en_use_nameparser": self.en_use_nameparser,
            "enable_en_nickname_expansion": self.enable_en_nickname_expansion,
            "filter_titles_suffixes": self.filter_titles_suffixes,
            "require_tin_dob_gate": self.require_tin_dob_gate,
            "enforce_nominative": self.enforce_nominative,
            "preserve_feminine_surnames": self.preserve_feminine_surnames,
            "enable_ascii_fastpath": self.enable_ascii_fastpath,
        }

class FeatureFlagManager:
    """Manages feature flags for normalization service."""

    def __init__(self):
        self._flags = self._load_from_environment()

    def _load_from_environment(self) -> FeatureFlags:
        """Load feature flags from environment variables."""

        # Primary implementation
        impl_str = os.getenv("NORMALIZATION_IMPLEMENTATION", "factory").lower()
        try:
            implementation = NormalizationImplementation(impl_str)
        except ValueError:
            implementation = NormalizationImplementation.FACTORY

        # Rollout percentage
        rollout_percentage = int(os.getenv("FACTORY_ROLLOUT_PERCENTAGE", "100"))
        rollout_percentage = max(0, min(100, rollout_percentage))

        # Performance settings
        enable_perf_fallback = os.getenv("ENABLE_PERFORMANCE_FALLBACK", "true").lower() == "true"
        max_latency = float(os.getenv("MAX_LATENCY_THRESHOLD_MS", "100.0"))

        # Accuracy settings
        enable_accuracy_monitoring = os.getenv("ENABLE_ACCURACY_MONITORING", "true").lower() == "true"
        min_confidence = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", "0.8"))

        # Debug settings
        enable_dual = os.getenv("ENABLE_DUAL_PROCESSING", "false").lower() == "true"
        log_choice = os.getenv("LOG_IMPLEMENTATION_CHOICE", "true").lower() == "true"

        # New feature flags for safe rollout with legacy ENV key fallback
        use_factory_normalizer = os.getenv("AISVC_FLAG_USE_FACTORY_NORMALIZER", "false").lower() == "true"
        fix_initials_double_dot = os.getenv("AISVC_FLAG_FIX_INITIALS_DOUBLE_DOT", os.getenv("FIX_INITIALS_DOUBLE_DOT", "false")).lower() == "true"
        preserve_hyphenated_case = os.getenv("AISVC_FLAG_PRESERVE_HYPHENATED_CASE", os.getenv("PRESERVE_HYPHENATED_CASE", "false")).lower() == "true"
        strict_stopwords = os.getenv("AISVC_FLAG_STRICT_STOPWORDS", "false").lower() == "true"
        enable_ac_tier0 = os.getenv("AISVC_FLAG_ENABLE_AC_TIER0", "true").lower() == "true"
        enable_vector_fallback = os.getenv("AISVC_FLAG_ENABLE_VECTOR_FALLBACK", "true").lower() == "true"
        
        # Nominative and gender enforcement flags
        enforce_nominative = os.getenv("AISVC_FLAG_ENFORCE_NOMINATIVE", "true").lower() == "true"
        preserve_feminine_surnames = os.getenv("AISVC_FLAG_PRESERVE_FEMININE_SURNAMES", "true").lower() == "true"

        # ASCII fastpath optimization
        ascii_fastpath = os.getenv("AISVC_FLAG_ASCII_FASTPATH", "true").lower() == "true"

        # Use default values for diminutive features
        DIMINUTIVE_FEATURE_DEFAULTS = type('DIMINUTIVE_FEATURE_DEFAULTS', (), {
            'use_diminutives_dictionary_only': True,
            'diminutives_allow_cross_lang': False
        })()

        # Diminutive resolution flags
        dim_dict_only_env = os.getenv("USE_DIMINUTIVES_DICTIONARY_ONLY")
        if dim_dict_only_env is None:
            use_dim_dict_only = DIMINUTIVE_FEATURE_DEFAULTS.use_diminutives_dictionary_only
        else:
            use_dim_dict_only = dim_dict_only_env.lower() == "true"

        dim_cross_lang_env = os.getenv("DIMINUTIVES_ALLOW_CROSS_LANG")
        if dim_cross_lang_env is None:
            dim_cross_lang = DIMINUTIVE_FEATURE_DEFAULTS.diminutives_allow_cross_lang
        else:
            dim_cross_lang = dim_cross_lang_env.lower() == "true"

        # Language overrides
        language_overrides = {}
        for lang in ["ru", "uk", "en"]:
            env_key = f"NORMALIZATION_IMPLEMENTATION_{lang.upper()}"
            lang_impl = os.getenv(env_key)
            if lang_impl:
                try:
                    language_overrides[lang] = NormalizationImplementation(lang_impl.lower())
                except ValueError:
                    pass

        return FeatureFlags(
            normalization_implementation=implementation,
            factory_rollout_percentage=rollout_percentage,
            enable_performance_fallback=enable_perf_fallback,
            max_latency_threshold_ms=max_latency,
            enable_accuracy_monitoring=enable_accuracy_monitoring,
            min_confidence_threshold=min_confidence,
            enable_dual_processing=enable_dual,
            log_implementation_choice=log_choice,
            use_factory_normalizer=use_factory_normalizer,
            fix_initials_double_dot=fix_initials_double_dot,
            preserve_hyphenated_case=preserve_hyphenated_case,
            strict_stopwords=strict_stopwords,
            enable_ac_tier0=enable_ac_tier0,
            enable_vector_fallback=enable_vector_fallback,
            enforce_nominative=enforce_nominative,
            preserve_feminine_surnames=preserve_feminine_surnames,
            enable_ascii_fastpath=ascii_fastpath,
            use_diminutives_dictionary_only=use_dim_dict_only,
            diminutives_allow_cross_lang=dim_cross_lang,
            language_overrides=language_overrides,
        )

    def should_use_factory(
        self,
        language: Optional[str] = None,
        user_id: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Determine if factory implementation should be used.

        Args:
            language: Language code for language-specific overrides
            user_id: User ID for percentage rollout
            request_context: Additional context for decision making

        Returns:
            True if factory should be used, False for legacy
        """

        # Check new use_factory_normalizer flag first (highest priority)
        if self._flags.use_factory_normalizer:
            return True

        # Check language-specific override
        if language and language in self._flags.language_overrides:
            override_impl = self._flags.language_overrides[language]
            if override_impl == NormalizationImplementation.LEGACY:
                return False
            elif override_impl == NormalizationImplementation.FACTORY:
                return True
            # AUTO continues to main logic

        # Check primary implementation setting
        if self._flags.normalization_implementation == NormalizationImplementation.LEGACY:
            return False
        elif self._flags.normalization_implementation == NormalizationImplementation.FACTORY:
            # Still subject to rollout percentage
            return self._check_rollout_percentage(user_id)
        elif self._flags.normalization_implementation == NormalizationImplementation.AUTO:
            # Auto mode: use performance and accuracy criteria
            return self._auto_select_implementation(language, request_context)

        # Default to legacy for safety
        return False

    def _check_rollout_percentage(self, user_id: Optional[str] = None) -> bool:
        """Check if user falls within rollout percentage."""
        if self._flags.factory_rollout_percentage >= 100:
            return True
        if self._flags.factory_rollout_percentage <= 0:
            return False

        # Use consistent hash-based rollout if user_id available
        if user_id:
            # Simple hash-based percentage
            hash_value = hash(user_id) % 100
            return hash_value < self._flags.factory_rollout_percentage

        # Fallback: use simple percentage (not user-consistent)
        import random
        return random.randint(1, 100) <= self._flags.factory_rollout_percentage

    def _auto_select_implementation(
        self,
        language: Optional[str] = None,
        request_context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Auto-select implementation based on current performance and accuracy."""
        # This would typically use real-time metrics
        # For now, use simple heuristics

        # Prefer legacy for high-performance requirements
        if request_context and request_context.get("high_performance_required"):
            return False

        # Prefer factory for new features
        if request_context and request_context.get("requires_new_features"):
            return True

        # Default to current rollout percentage
        return self._check_rollout_percentage()

    def get_monitoring_config(self) -> Dict[str, Any]:
        """Get configuration for monitoring and dual processing."""
        return {
            "enable_dual_processing": self._flags.enable_dual_processing,
            "log_implementation_choice": self._flags.log_implementation_choice,
            "enable_performance_fallback": self._flags.enable_performance_fallback,
            "max_latency_threshold_ms": self._flags.max_latency_threshold_ms,
            "enable_accuracy_monitoring": self._flags.enable_accuracy_monitoring,
            "min_confidence_threshold": self._flags.min_confidence_threshold,
        }

    def update_flags(self, **kwargs) -> None:
        """Update feature flags programmatically."""
        for key, value in kwargs.items():
            if hasattr(self._flags, key):
                setattr(self._flags, key, value)

    def get_current_config(self) -> Dict[str, Any]:
        """Get current feature flag configuration."""
        return {
            "normalization_implementation": self._flags.normalization_implementation.value,
            "factory_rollout_percentage": self._flags.factory_rollout_percentage,
            "enable_performance_fallback": self._flags.enable_performance_fallback,
            "max_latency_threshold_ms": self._flags.max_latency_threshold_ms,
            "enable_accuracy_monitoring": self._flags.enable_accuracy_monitoring,
            "min_confidence_threshold": self._flags.min_confidence_threshold,
            "enable_dual_processing": self._flags.enable_dual_processing,
            "log_implementation_choice": self._flags.log_implementation_choice,
            "use_diminutives_dictionary_only": self._flags.use_diminutives_dictionary_only,
            "diminutives_allow_cross_lang": self._flags.diminutives_allow_cross_lang,
            "language_overrides": {k: v.value for k, v in self._flags.language_overrides.items()},
        }

    def use_diminutives_dictionary_only(self) -> bool:
        """Return whether diminutive resolution should rely solely on dictionaries."""
        return self._flags.use_diminutives_dictionary_only

    def allow_diminutives_cross_lang(self) -> bool:
        """Return whether cross-language diminutive lookup is permitted."""
        return self._flags.diminutives_allow_cross_lang

    def enforce_nominative(self) -> bool:
        """Return whether nominative case enforcement is enabled."""
        return self._flags.enforce_nominative

    def preserve_feminine_surnames(self) -> bool:
        """Return whether feminine surname preservation is enabled."""
        return self._flags.preserve_feminine_surnames

# Global feature flag manager instance
_feature_flag_manager = None

def get_feature_flag_manager() -> FeatureFlagManager:
    """Get global feature flag manager instance."""
    global _feature_flag_manager
    if _feature_flag_manager is None:
        _feature_flag_manager = FeatureFlagManager()
    return _feature_flag_manager

def should_use_factory(
    language: Optional[str] = None,
    user_id: Optional[str] = None,
    request_context: Optional[Dict[str, Any]] = None
) -> bool:
    """Convenience function to check if factory should be used."""
    return get_feature_flag_manager().should_use_factory(language, user_id, request_context)
