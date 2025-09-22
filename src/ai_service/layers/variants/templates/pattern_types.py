"""
Pattern types and data models for high-recall AC pattern generation.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class RecallOptimizedPattern:
    """Паттерн, оптимизированный для максимального Recall"""

    pattern: str
    pattern_type: str
    recall_tier: int  # 0=exact, 1=high_recall, 2=medium_recall, 3=broad_recall
    precision_hint: float  # Expected precision (for subsequent filtering)
    variants: List[str]  # Automatic variants
    language: str
    source_confidence: float = 1.0