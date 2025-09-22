"""
Template modules for variant generation.

This package contains refactored components for high-recall pattern generation,
broken down from the original monolithic high_recall_ac_generator.py file.
"""

from .pattern_types import RecallOptimizedPattern
from .text_normalization import TextNormalizer
from .transliteration import Transliterator
from .high_recall_ac_generator_refactored import HighRecallACGeneratorRefactored

# Keep original for backward compatibility
from .high_recall_ac_generator import HighRecallACGenerator

__all__ = [
    "RecallOptimizedPattern",
    "TextNormalizer",
    "Transliterator",
    "HighRecallACGeneratorRefactored",
    "HighRecallACGenerator",  # Original for backward compatibility
]