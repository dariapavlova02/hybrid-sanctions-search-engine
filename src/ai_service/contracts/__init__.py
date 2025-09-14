"""
Contracts and interfaces for the unified AI service architecture
"""

from .base_contracts import (
    # Core data structures
    TokenTrace,
    NormalizationResult,
    SignalsPerson,
    SignalsOrganization,
    SignalsExtras,
    SignalsResult,
    ProcessingContext,
    UnifiedProcessingResult,
    SmartFilterResult,

    # Service interfaces
    ProcessingStage,
    ValidationServiceInterface,
    SmartFilterInterface,
    LanguageDetectionInterface,
    UnicodeServiceInterface,
    NormalizationServiceInterface,
    SignalsServiceInterface,
    VariantsServiceInterface,
    EmbeddingsServiceInterface,
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