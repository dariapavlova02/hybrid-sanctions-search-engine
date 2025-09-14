"""
Decision Engine for risk assessment and decision making.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ..contracts.decision_contracts import DecisionInput, DecisionOutput, RiskLevel


@dataclass
class DecisionConfig:
    """Configuration for decision engine"""
    
    high_risk_threshold: float = 0.8
    medium_risk_threshold: float = 0.5
    low_risk_threshold: float = 0.2
    person_confidence_weight: float = 0.4
    org_confidence_weight: float = 0.3
    similarity_weight: float = 0.2
    smartfilter_weight: float = 0.1


class DecisionEngine:
    """Decision engine for risk assessment and processing decisions."""
    
    def __init__(self, config: Optional[DecisionConfig] = None):
        """Initialize decision engine with configuration."""
        self.config = config or DecisionConfig()
    
    def decide(self, inp: DecisionInput) -> DecisionOutput:
        """
        Make a decision based on input signals and data.
        
        This is a stub implementation that will be expanded with
        actual decision logic in future iterations.
        """
        # Stub implementation - basic risk assessment
        score = self._calculate_base_score(inp)
        risk = self._determine_risk_level(score)
        reasons = self._generate_reasons(inp, score, risk)
        details = self._extract_details(inp)
        
        return DecisionOutput(
            risk=risk,
            score=score,
            reasons=reasons,
            details=details
        )
    
    def _calculate_base_score(self, inp: DecisionInput) -> float:
        """Calculate base risk score from input signals"""
        score = 0.0
        
        # Weighted combination of different signals
        score += inp.signals.person_confidence * self.config.person_confidence_weight
        score += inp.signals.org_confidence * self.config.org_confidence_weight
        
        # Similarity contribution (if available)
        if inp.similarity.cos_top is not None:
            similarity_score = min(inp.similarity.cos_top, 1.0)
            score += similarity_score * self.config.similarity_weight
        
        # Smart filter confidence contribution
        score += inp.smartfilter.confidence * self.config.smartfilter_weight
        
        # Additional factors
        if inp.signals.id_match:
            score += 0.2
        if inp.signals.date_match:
            score += 0.1
            
        return min(score, 1.0)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level based on score"""
        if score >= self.config.high_risk_threshold:
            return RiskLevel.HIGH
        elif score >= self.config.medium_risk_threshold:
            return RiskLevel.MEDIUM
        elif score >= self.config.low_risk_threshold:
            return RiskLevel.LOW
        else:
            return RiskLevel.SKIP
    
    def _generate_reasons(self, inp: DecisionInput, score: float, risk: RiskLevel) -> List[str]:
        """Generate human-readable reasons for the decision"""
        reasons = []
        reasons.append(f"Overall risk score: {score:.3f}")
        
        if inp.signals.person_confidence > 0.5:
            reasons.append(f"High person confidence: {inp.signals.person_confidence:.3f}")
        if inp.signals.org_confidence > 0.5:
            reasons.append(f"High organization confidence: {inp.signals.org_confidence:.3f}")
        if inp.similarity.cos_top and inp.similarity.cos_top > 0.7:
            reasons.append(f"High similarity match: {inp.similarity.cos_top:.3f}")
        if inp.signals.id_match:
            reasons.append("Exact ID match detected")
        if inp.signals.date_match:
            reasons.append("Date match detected")
            
        reasons.append(f"Risk level: {risk.value}")
        return reasons
    
    def _extract_details(self, inp: DecisionInput) -> Dict[str, Any]:
        """Extract detailed information for debugging and analysis"""
        return {
            "input_signals": {
                "person_confidence": inp.signals.person_confidence,
                "org_confidence": inp.signals.org_confidence,
                "date_match": inp.signals.date_match,
                "id_match": inp.signals.id_match,
                "evidence_count": len(inp.signals.evidence)
            },
            "similarity": {
                "cos_top": inp.similarity.cos_top,
                "cos_p95": inp.similarity.cos_p95
            },
            "smartfilter": {
                "should_process": inp.smartfilter.should_process,
                "confidence": inp.smartfilter.confidence,
                "estimated_complexity": inp.smartfilter.estimated_complexity
            }
        }
