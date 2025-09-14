"""
Decision Engine for risk assessment and decision making.
"""

from typing import Any, Dict, List, Optional

from ..contracts.decision_contracts import DecisionInput, DecisionOutput, RiskLevel
from ..config.settings import DecisionConfig


class DecisionEngine:
    """Decision engine for risk assessment and processing decisions."""
    
    def __init__(self, config: Optional[DecisionConfig] = None):
        """Initialize decision engine with configuration."""
        self.config = config or DecisionConfig()
    
    def decide(self, inp: DecisionInput) -> DecisionOutput:
        """
        Make a decision based on input signals and data.
        
        Implements deterministic scoring with configurable weights and thresholds.
        """
        # Check if smart filter says to skip processing
        if not inp.smartfilter.should_process:
            return DecisionOutput(
                risk=RiskLevel.SKIP,
                score=0.0,
                reasons=["smartfilter_skip"],
                details={"smartfilter_should_process": False}
            )
        
        # Calculate weighted score
        score = self._calculate_weighted_score(inp)
        
        # Determine risk level based on thresholds
        risk = self._determine_risk_level(score)
        
        # Generate reasons based on contributing factors
        reasons = self._generate_reasons(inp, score, risk)
        
        # Extract details with used features and weights
        details = self._extract_details(inp, score)
        
        return DecisionOutput(
            risk=risk,
            score=score,
            reasons=reasons,
            details=details
        )
    
    def _calculate_weighted_score(self, inp: DecisionInput) -> float:
        """Calculate weighted score using deterministic formula"""
        score = 0.0
        
        # Core weighted components
        score += self.config.w_smartfilter * inp.smartfilter.confidence
        score += self.config.w_person * inp.signals.person_confidence
        score += self.config.w_org * inp.signals.org_confidence
        
        # Similarity contribution (use 0 if None)
        similarity_value = inp.similarity.cos_top if inp.similarity.cos_top is not None else 0.0
        score += self.config.w_similarity * similarity_value
        
        # Bonus factors
        if inp.signals.date_match:
            score += self.config.bonus_date_match
        if inp.signals.id_match:
            score += self.config.bonus_id_match
            
        return min(score, 1.0)
    
    def _determine_risk_level(self, score: float) -> RiskLevel:
        """Determine risk level based on score"""
        if score >= self.config.thr_high:
            return RiskLevel.HIGH
        elif score >= self.config.thr_medium:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def _generate_reasons(self, inp: DecisionInput, score: float, risk: RiskLevel) -> List[str]:
        """Generate human-readable reasons for the decision"""
        reasons = []
        reasons.append(f"Overall risk score: {score:.3f}")
        
        # Smart filter contribution
        if inp.smartfilter.confidence > 0.5:
            reasons.append(f"Smart filter confidence: {inp.smartfilter.confidence:.3f}")
        
        # Person signals contribution
        if inp.signals.person_confidence > 0.3:
            reasons.append(f"Person confidence: {inp.signals.person_confidence:.3f}")
        
        # Organization signals contribution
        if inp.signals.org_confidence > 0.3:
            reasons.append(f"Organization confidence: {inp.signals.org_confidence:.3f}")
        
        # Similarity contribution
        if inp.similarity.cos_top and inp.similarity.cos_top > 0.5:
            reasons.append(f"Similarity match: {inp.similarity.cos_top:.3f}")
        
        # Bonus factors
        if inp.signals.id_match:
            reasons.append("ID match bonus applied")
        if inp.signals.date_match:
            reasons.append("Date match bonus applied")
            
        reasons.append(f"Risk level: {risk.value}")
        return reasons
    
    def _extract_details(self, inp: DecisionInput, score: float) -> Dict[str, Any]:
        """Extract detailed information for debugging and analysis"""
        return {
            "calculated_score": score,
            "weights_used": {
                "w_smartfilter": self.config.w_smartfilter,
                "w_person": self.config.w_person,
                "w_org": self.config.w_org,
                "w_similarity": self.config.w_similarity,
                "bonus_date_match": self.config.bonus_date_match,
                "bonus_id_match": self.config.bonus_id_match
            },
            "thresholds": {
                "thr_high": self.config.thr_high,
                "thr_medium": self.config.thr_medium
            },
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
