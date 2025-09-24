"""
API Models and Request/Response schemas.
"""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from enum import Enum

from ..utils.feature_flags import FeatureFlags, NormalizationImplementation


class ProcessingMode(str, Enum):
    """Processing mode options."""
    FAST = "fast"
    BALANCED = "balanced"
    ACCURATE = "accurate"
    CUSTOM = "custom"


class LanguageOptions(str, Enum):
    """Supported languages."""
    UKRAINIAN = "uk"
    RUSSIAN = "ru"
    ENGLISH = "en"
    AUTO = "auto"


class SearchMode(str, Enum):
    """Search mode options."""
    AC = "ac"
    VECTOR = "vector"
    HYBRID = "hybrid"
    DISABLED = "disabled"


class FlagOverrides(BaseModel):
    """Feature flag overrides for request."""

    # Core implementation
    normalization_implementation: Optional[NormalizationImplementation] = None
    factory_rollout_percentage: Optional[int] = Field(None, ge=0, le=100)

    # Performance flags
    enable_performance_fallback: Optional[bool] = None
    max_latency_threshold_ms: Optional[float] = Field(None, gt=0, le=10000)
    enable_accuracy_monitoring: Optional[bool] = None
    min_confidence_threshold: Optional[float] = Field(None, ge=0.0, le=1.0)

    # Debug flags
    enable_dual_processing: Optional[bool] = None
    log_implementation_choice: Optional[bool] = None
    debug_tracing: Optional[bool] = None

    # Normalization behavior
    use_factory_normalizer: Optional[bool] = None
    fix_initials_double_dot: Optional[bool] = None
    preserve_hyphenated_case: Optional[bool] = None
    strict_stopwords: Optional[bool] = None

    # Search features
    enable_ac_tier0: Optional[bool] = None
    enable_vector_fallback: Optional[bool] = None

    # Morphology
    morphology_custom_rules_first: Optional[bool] = None

    # English processing
    enable_nameparser_en: Optional[bool] = None
    enable_en_nicknames: Optional[bool] = None
    en_use_nameparser: Optional[bool] = None
    enable_en_nickname_expansion: Optional[bool] = None
    filter_titles_suffixes: Optional[bool] = None

    # NER and validation
    enable_spacy_ner: Optional[bool] = None
    enable_spacy_uk_ner: Optional[bool] = None
    enable_spacy_en_ner: Optional[bool] = None
    enable_fsm_tuned_roles: Optional[bool] = None

    # Advanced features
    enable_enhanced_diminutives: Optional[bool] = None
    enable_enhanced_gender_rules: Optional[bool] = None
    preserve_feminine_suffix_uk: Optional[bool] = None

    # Business rules
    require_tin_dob_gate: Optional[bool] = None
    enforce_nominative: Optional[bool] = None
    preserve_feminine_surnames: Optional[bool] = None

    # Performance optimizations
    enable_ascii_fastpath: Optional[bool] = None

    # Diminutive handling
    use_diminutives_dictionary_only: Optional[bool] = None
    diminutives_allow_cross_lang: Optional[bool] = None

    # Language overrides
    language_overrides: Optional[Dict[str, NormalizationImplementation]] = None


class ProcessingOptions(BaseModel):
    """Processing options for requests."""

    # Language settings
    language: Optional[LanguageOptions] = Field(default=LanguageOptions.AUTO, description="Input language")
    fallback_language: Optional[LanguageOptions] = Field(default=LanguageOptions.UKRAINIAN, description="Fallback language")

    # Processing mode
    mode: ProcessingMode = Field(default=ProcessingMode.BALANCED, description="Processing mode")

    # Search configuration
    search_mode: SearchMode = Field(default=SearchMode.HYBRID, description="Search mode")
    enable_search: bool = Field(default=True, description="Enable search functionality")
    search_threshold: float = Field(default=0.3, ge=0.0, le=1.0, description="Search similarity threshold")
    search_escalation_threshold: float = Field(default=0.6, ge=0.0, le=1.0, description="AC->Vector escalation threshold")

    # Output options
    generate_variants: bool = Field(default=True, description="Generate name variants")
    generate_embeddings: bool = Field(default=True, description="Generate embeddings for vector search")
    include_trace: bool = Field(default=False, description="Include processing trace")
    include_metrics: bool = Field(default=False, description="Include performance metrics")

    # Caching
    cache_result: bool = Field(default=True, description="Cache processing results")
    cache_ttl_seconds: Optional[int] = Field(default=3600, ge=60, le=86400, description="Cache TTL in seconds")

    # Feature flags
    flags: Optional[FlagOverrides] = Field(default=None, description="Feature flag overrides")

    def get_effective_flags(self, base_flags: FeatureFlags) -> FeatureFlags:
        """Get effective flags by applying overrides to base flags."""
        if not self.flags:
            return base_flags

        # Create a copy of base flags
        effective = FeatureFlags(**base_flags.__dict__)

        # Apply overrides
        for field_name, value in self.flags.__dict__.items():
            if value is not None and hasattr(effective, field_name):
                setattr(effective, field_name, value)

        return effective


class ProcessRequest(BaseModel):
    """Main processing request model."""

    text: str = Field(..., min_length=1, max_length=10000, description="Text to process")
    options: Optional[ProcessingOptions] = Field(default_factory=ProcessingOptions, description="Processing options")

    # Backward compatibility
    generate_variants: Optional[bool] = Field(default=None, description="DEPRECATED: Use options.generate_variants")
    generate_embeddings: Optional[bool] = Field(default=None, description="DEPRECATED: Use options.generate_embeddings")
    cache_result: Optional[bool] = Field(default=None, description="DEPRECATED: Use options.cache_result")

    def model_post_init(self, __context) -> None:
        """Apply backward compatibility mappings."""
        if not self.options:
            self.options = ProcessingOptions()

        # Apply backward compatibility
        if self.generate_variants is not None:
            self.options.generate_variants = self.generate_variants
        if self.generate_embeddings is not None:
            self.options.generate_embeddings = self.generate_embeddings
        if self.cache_result is not None:
            self.options.cache_result = self.cache_result


class ProcessingModePresets:
    """Predefined processing mode configurations."""

    FAST = FlagOverrides(
        enable_spacy_ner=False,
        enable_spacy_uk_ner=False,
        enable_spacy_en_ner=False,
        enable_enhanced_gender_rules=False,
        enable_enhanced_diminutives=False,
        enable_ascii_fastpath=True,
        morphology_custom_rules_first=True,
        debug_tracing=False
    )

    BALANCED = FlagOverrides(
        enable_spacy_ner=True,
        enable_spacy_uk_ner=True,
        enable_spacy_en_ner=False,  # Only UK for performance
        enable_enhanced_gender_rules=True,
        enable_enhanced_diminutives=True,
        enable_ascii_fastpath=True,
        morphology_custom_rules_first=True,
        debug_tracing=False
    )

    ACCURATE = FlagOverrides(
        enable_spacy_ner=True,
        enable_spacy_uk_ner=True,
        enable_spacy_en_ner=True,
        enable_enhanced_gender_rules=True,
        enable_enhanced_diminutives=True,
        enable_fsm_tuned_roles=True,
        preserve_feminine_suffix_uk=True,
        enable_ascii_fastpath=False,
        debug_tracing=False
    )

    @classmethod
    def get_preset(cls, mode: ProcessingMode) -> Optional[FlagOverrides]:
        """Get flag preset for processing mode."""
        presets = {
            ProcessingMode.FAST: cls.FAST,
            ProcessingMode.BALANCED: cls.BALANCED,
            ProcessingMode.ACCURATE: cls.ACCURATE
        }
        return presets.get(mode)


class PersonResult(BaseModel):
    """Person extraction result."""
    core: List[str]
    full_name: str
    dob: Optional[str] = None
    ids: List[Dict[str, Any]] = []
    confidence: float
    evidence: List[str] = []


class OrganizationResult(BaseModel):
    """Organization extraction result."""
    core: str
    legal_form: Optional[str] = None
    full_name: str
    ids: List[Dict[str, Any]] = []
    confidence: float
    evidence: List[str] = []


class SignalsResult(BaseModel):
    """Signals extraction result."""
    persons: List[PersonResult] = []
    organizations: List[OrganizationResult] = []
    confidence: float


class SearchResult(BaseModel):
    """Search result."""
    query: str
    results: List[Dict[str, Any]] = []
    total_hits: int
    search_type: str
    processing_time_ms: float
    escalated: bool = False
    vector_results: List[Dict[str, Any]] = []


class ProcessResponse(BaseModel):
    """Main processing response model."""

    # Core results
    normalized_text: str
    tokens: List[str]
    language: str
    confidence: float

    # Optional results
    signals: Optional[SignalsResult] = None
    search_results: Optional[SearchResult] = None
    variants: Optional[List[str]] = None
    embeddings: Optional[List[float]] = None

    # Processing metadata
    processing_time_ms: float
    success: bool
    errors: List[str] = []
    warnings: List[str] = []

    # Debug information
    trace: Optional[List[Dict[str, Any]]] = None
    metrics: Optional[Dict[str, Any]] = None
    flags_used: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    services: Dict[str, str]
    performance: Dict[str, float]


class MetricsResponse(BaseModel):
    """Metrics response."""
    pipeline_metrics: Dict[str, Any]
    cache_stats: Dict[str, Any]
    performance_stats: Dict[str, Any]