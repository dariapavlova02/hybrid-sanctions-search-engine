"""
Decision Engine Contracts - Layer 9 of the unified architecture.

Defines interfaces for making match/no-match decisions based on
processing results from all previous layers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .base_contracts import NormalizationResult, SignalsResult, UnifiedProcessingResult


class MatchDecision(Enum):
    """Final match decision types"""

    MATCH = "match"                    # Confirmed match
    NO_MATCH = "no_match"             # Confirmed no match
    WEAK_MATCH = "weak_match"         # Low confidence match
    NEEDS_REVIEW = "needs_review"     # Manual review required
    INSUFFICIENT_DATA = "insufficient_data"  # Not enough data to decide


class ConfidenceLevel(Enum):
    """Confidence levels for decisions"""

    VERY_HIGH = "very_high"   # 95%+
    HIGH = "high"             # 80-95%
    MEDIUM = "medium"         # 60-80%
    LOW = "low"               # 40-60%
    VERY_LOW = "very_low"     # <40%


@dataclass
class MatchEvidence:
    """Evidence supporting a match decision"""

    source: str                    # signals | normalization | embedding | etc.
    evidence_type: str            # name_similarity | legal_form_match | etc.
    confidence: float             # 0.0 - 1.0
    details: Dict[str, Any]       # source-specific details
    weight: float = 1.0           # evidence weight in final decision


class DecisionResult(BaseModel):
    """Result of decision engine analysis"""

    # Core decision
    decision: MatchDecision
    confidence: float             # 0.0 - 1.0
    confidence_level: ConfidenceLevel

    # Evidence and reasoning
    evidence: List[MatchEvidence]
    reasoning: str               # Human-readable explanation
    risk_factors: List[str] = []  # Identified risk factors

    # Match details (if applicable)
    matched_entity: Optional[str] = None      # Entity that matched
    match_score: Optional[float] = None       # Similarity score
    match_type: Optional[str] = None          # person | organization

    # Processing metadata
    processing_time: float
    used_layers: List[str]       # Which processing layers contributed
    fallback_used: bool = False  # Whether fallback logic was used

    # Quality indicators
    data_quality: str = "unknown"    # excellent | good | fair | poor
    completeness: float = 0.0        # How complete the input data is

    # Recommendations
    next_steps: List[str] = []       # Recommended follow-up actions
    review_required: bool = False    # Whether human review is needed


class DecisionEngineInterface(ABC):
    """Interface for the decision engine (Layer 9)"""

    @abstractmethod
    async def make_decision(
        self,
        processing_result: UnifiedProcessingResult,
        candidates: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DecisionResult:
        """
        Make a match/no-match decision based on processing results.

        Args:
            processing_result: Result from layers 1-8
            candidates: Optional list of potential matches to compare against
            context: Additional context (transaction data, risk tolerance, etc.)

        Returns:
            Decision with evidence and reasoning
        """
        pass

    @abstractmethod
    async def batch_decisions(
        self,
        processing_results: List[UnifiedProcessingResult],
        candidates: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DecisionResult]:
        """Make decisions for multiple processing results efficiently"""
        pass

    @abstractmethod
    def update_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        """Update decision thresholds for tuning"""
        pass

    @abstractmethod
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about recent decisions"""
        pass


class DecisionContext:
    """Context information for decision making"""

    def __init__(
        self,
        risk_tolerance: str = "medium",      # low | medium | high
        require_exact_match: bool = False,   # Require exact matches only
        allow_weak_matches: bool = True,     # Allow weak matches
        review_threshold: float = 0.5,       # Confidence threshold for review
        match_threshold: float = 0.8,        # Confidence threshold for match
        source_reliability: float = 1.0,     # Reliability of input data
        **kwargs
    ):
        self.risk_tolerance = risk_tolerance
        self.require_exact_match = require_exact_match
        self.allow_weak_matches = allow_weak_matches
        self.review_threshold = review_threshold
        self.match_threshold = match_threshold
        self.source_reliability = source_reliability
        self.additional_context = kwargs


@dataclass
class DecisionMetrics:
    """Metrics for decision engine performance"""

    total_decisions: int = 0
    match_decisions: int = 0
    no_match_decisions: int = 0
    weak_match_decisions: int = 0
    review_decisions: int = 0

    avg_confidence: float = 0.0
    avg_processing_time: float = 0.0

    high_confidence_decisions: int = 0
    low_confidence_decisions: int = 0

    fallback_usage_rate: float = 0.0
    review_rate: float = 0.0

    accuracy_metrics: Optional[Dict[str, float]] = None  # When ground truth is available