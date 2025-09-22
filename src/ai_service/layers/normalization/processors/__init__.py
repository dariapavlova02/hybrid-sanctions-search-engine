"""Normalization processors module."""

from .config import NormalizationConfig
from .english_processor import EnglishNameProcessor
from .person_extraction import PersonExtractor, PersonCandidate
from .result_builder import ResultBuilder, ProcessingMetrics
# from .normalization_factory_refactored import NormalizationFactoryRefactored  # Disabled due to circular import
from .token_processor import TokenProcessor
from .role_classifier import RoleClassifier
from .morphology_processor import MorphologyProcessor
from .gender_processor import GenderProcessor

# Keep original for backward compatibility
# from .normalization_factory import NormalizationFactory  # Disabled due to circular import

__all__ = [
    'NormalizationConfig',
    'EnglishNameProcessor',
    'PersonExtractor',
    'PersonCandidate',
    'ResultBuilder',
    'ProcessingMetrics',
    # 'NormalizationFactoryRefactored',  # Disabled due to circular import
    'TokenProcessor',
    'RoleClassifier',
    'MorphologyProcessor',
    'GenderProcessor',
    # 'NormalizationFactory',  # Original for backward compatibility, disabled due to circular import
]