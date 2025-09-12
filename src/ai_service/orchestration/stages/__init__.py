"""
Processing stages implementing Single Responsibility Principle.
Each stage handles one specific aspect of text processing.
"""

# Import stages
try:
    from .embedding_stage import EmbeddingGenerationStage
    from .language_detection_stage import LanguageDetectionStage
    from .normalization_service_stage import NormalizationServiceStage
    from .smart_filter_stage import SmartFilterStage
    from .unicode_stage import UnicodeNormalizationStage
    from .validation_stage import ValidationStage
    from .variant_generation_stage import VariantGenerationStage
except ImportError:
    # Fallback for when loaded via importlib
    import sys
    from pathlib import Path

    stages_path = Path(__file__).parent
    sys.path.insert(0, str(stages_path))

    from embedding_stage import EmbeddingGenerationStage
    from language_detection_stage import LanguageDetectionStage
    from normalization_service_stage import NormalizationServiceStage
    from smart_filter_stage import SmartFilterStage
    from unicode_stage import UnicodeNormalizationStage
    from validation_stage import ValidationStage
    from variant_generation_stage import VariantGenerationStage

__all__ = [
    "ValidationStage",
    "UnicodeNormalizationStage",
    "LanguageDetectionStage",
    "NormalizationServiceStage",
    "VariantGenerationStage",
    "EmbeddingGenerationStage",
    "SmartFilterStage",
]
