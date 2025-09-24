"""
Decision contracts for risk assessment and decision making.

Defines the unified contract for decision input/output and risk levels
as specified in the decision engine architecture.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .search_contracts import SearchInfo


class RiskLevel(Enum):
    """Risk levels for decision making"""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    SKIP = "skip"


class MatchDecision(Enum):
    """Match decision types for sanctions screening"""

    HIT = "hit"          # Strong match - requires review/blocking
    REVIEW = "review"    # Potential match - needs manual review
    NO_MATCH = "no_match"  # No significant match found
    MATCH = "match"      # Strong match
    WEAK_MATCH = "weak_match"  # Weak match
    NEEDS_REVIEW = "needs_review"  # Needs review


class ConfidenceLevel(Enum):
    """Confidence levels for decision making"""

    VERY_LOW = "very_low"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


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
    search: Optional[SearchInfo] = None
    normalization: Optional[Any] = None  # NormalizationResult for homoglyph detection


@dataclass
class DecisionOutput:
    """Output contract for decision engine"""
    
    risk: RiskLevel
    score: float  # итоговый 0..1
    reasons: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)  # упаковать используемые признаки
    review_required: bool = False  # Whether manual review is required
    required_additional_fields: List[str] = field(default_factory=list)  # Fields required for decision

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "risk": self.risk.value,
            "score": self.score,
            "reasons": self.reasons,
            "details": self.details,
            "review_required": self.review_required,
            "required_additional_fields": self.required_additional_fields
        }


@dataclass
class DecisionResult:
    """Decision result for test compatibility"""
    
    decision: MatchDecision
    confidence: float
    confidence_level: ConfidenceLevel
    review_required: bool
    risk_factors: List[str] = field(default_factory=list)
    evidence: List["MatchEvidence"] = field(default_factory=list)
    reasoning: str = ""
    processing_time: float = 0.0
    risk: RiskLevel = RiskLevel.LOW
    score: float = 0.0


@dataclass
class MatchEvidence:
    """Evidence for match decisions"""
    
    source: str
    evidence_type: str
    confidence: float
    weight: float
    description: str = ""