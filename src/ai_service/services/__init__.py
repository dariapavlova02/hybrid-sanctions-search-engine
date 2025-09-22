"""
Services module for AI Service

This module provides both current services and legacy re-exports
for backward compatibility.
"""

from .embedding_preprocessor import EmbeddingPreprocessor

# Legacy re-exports for backward compatibility
from ..adapters.legacy_normalization_adapter import LegacyNormalizationAdapter
from ..layers.normalization.normalization_service import NormalizationService as ModernNormalizationService
# UnifiedOrchestrator removed to avoid circular import

# Legacy aliases for backward compatibility
NormalizationService = LegacyNormalizationAdapter
AdvancedNormalizationService = LegacyNormalizationAdapter  # Legacy alias

__all__ = [
    "EmbeddingPreprocessor",
    # Legacy re-exports
    "LegacyNormalizationAdapter",
    "NormalizationService",
    "AdvancedNormalizationService",
    "ModernNormalizationService",
]
