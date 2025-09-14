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
