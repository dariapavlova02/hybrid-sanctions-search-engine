"""
Decision contracts for risk assessment and decision making.

Defines the unified contract for decision input/output and risk levels
as specified in the decision engine architecture.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class RiskLevel(Enum):
    """Risk levels for decision making"""
    
    HIGH = "high"
    MEDIUM = "medium" 
    LOW = "low"
    SKIP = "skip"


@dataclass
class SmartFilterInfo:
    """Smart filter information"""
    
    should_process: bool
    confidence: float
    estimated_complexity: Optional[str] = None


@dataclass
class SignalsInfo:
    """Signals information for decision making"""
    
    person_confidence: float  # 0..1
    org_confidence: float     # 0..1
    date_match: Optional[bool] = None
    id_match: Optional[bool] = None  # ИНН/паспорт exact match
    evidence: Dict[str, Any] = field(default_factory=dict)  # произвольные поля


@dataclass
class SimilarityInfo:
    """Similarity information from embeddings"""
    
    cos_top: Optional[float] = None    # cosine similarity to top match
    cos_p95: Optional[float] = None    # cosine similarity to 95th percentile


@dataclass
class DecisionInput:
    """Input contract for decision engine"""
    
    text: str
    language: Optional[str] = None
    smartfilter: SmartFilterInfo = field(default_factory=lambda: SmartFilterInfo(should_process=True, confidence=1.0))
    signals: SignalsInfo = field(default_factory=lambda: SignalsInfo(person_confidence=0.0, org_confidence=0.0))
    similarity: SimilarityInfo = field(default_factory=SimilarityInfo)


@dataclass
class DecisionOutput:
    """Output contract for decision engine"""
    
    risk: RiskLevel
    score: float  # итоговый 0..1
    reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)  # упаковать используемые признаки

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "risk": self.risk.value,
            "score": self.score,
            "reasons": self.reasons,
            "details": self.details
        }