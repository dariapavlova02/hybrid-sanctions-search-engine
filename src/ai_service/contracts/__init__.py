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
