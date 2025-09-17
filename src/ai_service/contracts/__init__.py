"""
Contracts and interfaces for the unified AI service architecture
"""

from .base_contracts import (  # Core data structures; Service interfaces
    EmbeddingsServiceInterface,
    LanguageDetectionInterface,
    NormalizationResult,
    NormalizationServiceInterface,
    ProcessingContext,
    ProcessingStage,
    SignalsExtras,
    SignalsOrganization,
    SignalsPerson,
    SignalsResult,
    SignalsServiceInterface,
    SmartFilterInterface,
    SmartFilterResult,
    TokenTrace,
    UnicodeServiceInterface,
    UnifiedProcessingResult,
    ValidationServiceInterface,
    VariantsServiceInterface,
)

from .decision_contracts import (  # Decision engine contracts
    DecisionInput,
    DecisionOutput,
    RiskLevel,
    SmartFilterInfo,
    SignalsInfo,
    SimilarityInfo,
)

from .trace_models import (  # Search trace models
    SearchStage,
    SearchTrace,
    SearchTraceBuilder,
    SearchTraceHit,
    SearchTraceStep,
    create_ac_hit,
    create_hybrid_hit,
    create_lexical_hit,
    create_rerank_hit,
    create_search_hit,
    create_semantic_hit,
    create_watchlist_hit,
)

__all__ = [
    # Data structures
    "TokenTrace",
    "NormalizationResult",
    "SignalsPerson",
    "SignalsOrganization",
    "SignalsExtras",
    "SignalsResult",
    "ProcessingContext",
    "UnifiedProcessingResult",
    "SmartFilterResult",
    # Decision engine structures
    "DecisionInput",
    "DecisionOutput",
    "RiskLevel",
    "SmartFilterInfo",
    "SignalsInfo",
    "SimilarityInfo",
    # Search trace structures
    "SearchStage",
    "SearchTrace",
    "SearchTraceBuilder",
    "SearchTraceHit",
    "SearchTraceStep",
    "create_ac_hit",
    "create_hybrid_hit",
    "create_lexical_hit",
    "create_rerank_hit",
    "create_search_hit",
    "create_semantic_hit",
    "create_watchlist_hit",
    # Interfaces
    "ProcessingStage",
    "ValidationServiceInterface",
    "SmartFilterInterface",
    "LanguageDetectionInterface",
    "UnicodeServiceInterface",
    "NormalizationServiceInterface",
    "SignalsServiceInterface",
    "VariantsServiceInterface",
    "EmbeddingsServiceInterface",
]
