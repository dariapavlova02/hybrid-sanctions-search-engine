"""
Type definitions for AI Service
"""

from dataclasses import dataclass
from typing import Any, Dict, Literal


@dataclass
class LanguageDetectionResult:
    """
    Result of language detection with detailed information
    
    Attributes:
        language: Detected language code ("ru", "uk", "en", "mixed", "unknown")
        confidence: Confidence score between 0.0 and 1.0
        details: Dictionary with detailed detection information including ratios, counts, and bonuses
    """
    language: Literal["ru", "uk", "en", "mixed", "unknown"]
    confidence: float
    details: Dict[str, Any]
    
    def __post_init__(self):
        """Validate the result after initialization"""
        if self.confidence < 0.0 or self.confidence > 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
        
        valid_languages = {"ru", "uk", "en", "mixed", "unknown"}
        if self.language not in valid_languages:
            raise ValueError(f"Language must be one of {valid_languages}, got {self.language}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "language": self.language,
            "confidence": self.confidence,
            "details": self.details,
        }
    
    def is_confident(self, threshold: float = 0.6) -> bool:
        """Check if the detection is confident enough"""
        return self.confidence >= threshold
    
    def is_mixed(self) -> bool:
        """Check if the language is mixed"""
        return self.language == "mixed"
    
    def is_unknown(self) -> bool:
        """Check if the language is unknown"""
        return self.language == "unknown"
