"""
Decision Engine for risk assessment and decision making.
"""

from typing import Any, Dict, List, Optional

from ..contracts.decision_contracts import DecisionInput, DecisionOutput, RiskLevel, SmartFilterInfo, SignalsInfo, SimilarityInfo
from ..config.settings import DecisionConfig, DECISION_CONFIG
from ..utils.logging_config import get_logger
from ..monitoring.metrics_service import MetricsService, MetricDefinition, MetricType


class DecisionEngine:
    """Decision engine for risk assessment and processing decisions."""
    
    def __init__(self, config: Optional[DecisionConfig] = None, metrics_service: Optional[MetricsService] = None):
        """Initialize decision engine with configuration."""
        # Use provided config, or fall back to unified config with ENV overrides
        self.config = config or DECISION_CONFIG
        self.metrics_service = metrics_service
        self.logger = get_logger(__name__)
        
        # Register decision-specific metrics if metrics service is available
        if self.metrics_service:
            self._register_decision_metrics()
    
    def decide(self, inp: DecisionInput) -> DecisionOutput:
        """
        Make a decision based on input signals and data.
        
        Implements deterministic scoring with configurable weights and thresholds.
        Robustly handles None/empty evidence with safe defaults.
        """
        # Safely extract smart filter info with defaults
        smartfilter = self._safe_smartfilter(inp.smartfilter)
        
        # Check if smart filter says to skip processing
        if not smartfilter.should_process:
            return DecisionOutput(
                risk=RiskLevel.SKIP,
                score=0.0,
                reasons=["smartfilter_skip"],
                details={"smartfilter_should_process": False}
            )
        
        # Safely extract signals info with defaults
        signals = self._safe_signals(inp.signals)
        
        # Safely extract similarity info with defaults
        similarity = self._safe_similarity(inp.similarity)
        
        # Create safe input for calculation
        safe_input = DecisionInput(
            text=inp.text,
            language=inp.language,
            smartfilter=smartfilter,
            signals=signals,
            similarity=similarity
        )
        
        # Calculate weighted score
        score = self._calculate_weighted_score(safe_input)
        
        # Determine risk level based on thresholds
        risk = self._determine_risk_level(score)
        
        # Generate reasons based on contributing factors
        reasons = self._generate_reasons(safe_input, score, risk)
        
        # Extract details with used features and weights
        details = self._extract_details(safe_input, score)
        
        # Log decision details at DEBUG level
        self.logger.debug(
            f"Decision made: risk={risk.value}, score={score:.3f}, "
            f"smartfilter_conf={smartfilter.confidence:.3f}, "
            f"person_conf={signals.person_confidence:.3f}, "
            f"org_conf={signals.org_confidence:.3f}, "
            f"similarity={similarity.cos_top}, "
            f"date_match={signals.date_match}, id_match={signals.id_match}"
        )
        
        # Record metrics if available
        if self.metrics_service:
            self._record_decision_metrics(risk, score, inp)
        
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
        
        # Search contribution (NEW)
        if inp.search:
            search = inp.search
            search_components_added = False

            # Exact matches (highest priority)
            if search.has_exact_matches and search.exact_confidence >= self.config.thr_search_exact:
                score += self.config.w_search_exact * search.exact_confidence
                search_components_added = True

            # Phrase matches
            if search.has_phrase_matches and search.phrase_confidence >= self.config.thr_search_phrase:
                score += self.config.w_search_phrase * search.phrase_confidence
                search_components_added = True

            # N-gram matches
            if search.has_ngram_matches and search.ngram_confidence >= self.config.thr_search_ngram:
                score += self.config.w_search_ngram * search.ngram_confidence
                search_components_added = True

            # Vector matches
            if search.has_vector_matches and search.vector_confidence >= self.config.thr_search_vector:
                score += self.config.w_search_vector * search.vector_confidence
                search_components_added = True

            # Search bonuses (only if at least one search component passed threshold)
            if search_components_added:
                if search.total_matches > 1:
                    score += self.config.bonus_multiple_matches

                if search.high_confidence_matches > 0:
                    score += self.config.bonus_high_confidence
        
        # Bonus factors
        if inp.signals.date_match:
            score += self.config.bonus_date_match
        if inp.signals.id_match:
            score += self.config.bonus_id_match
            
        return score
    
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
        
        # Smart filter evidence
        if inp.smartfilter.confidence >= 0.7:
            reasons.append("strong_smartfilter_signal")
        elif inp.smartfilter.confidence > 0.5:
            reasons.append(f"Smart filter confidence: {inp.smartfilter.confidence:.3f}")
        
        # Person evidence
        if inp.signals.person_confidence >= 0.7:
            reasons.append("person_evidence_strong")
        elif inp.signals.person_confidence > 0.3:
            reasons.append(f"Person confidence: {inp.signals.person_confidence:.3f}")
        
        # Organization evidence
        if inp.signals.org_confidence >= 0.7:
            reasons.append("org_evidence_strong")
        elif inp.signals.org_confidence > 0.3:
            reasons.append(f"Organization confidence: {inp.signals.org_confidence:.3f}")
        
        # Similarity evidence
        if inp.similarity.cos_top and inp.similarity.cos_top >= 0.9:
            reasons.append("high_vector_similarity")
        elif inp.similarity.cos_top and inp.similarity.cos_top > 0.5:
            reasons.append(f"Similarity match: {inp.similarity.cos_top:.3f}")
        
        # Exact match evidence
        if inp.signals.id_match:
            reasons.append("id_exact_match")
        if inp.signals.date_match:
            reasons.append("dob_match")
            
        reasons.append(f"Risk level: {risk.value}")
        return reasons
    
    def _extract_details(self, inp: DecisionInput, score: float) -> Dict[str, Any]:
        """Extract detailed information for debugging and analysis"""
        
        # Calculate individual contributions
        smartfilter_contribution = self.config.w_smartfilter * inp.smartfilter.confidence
        person_contribution = self.config.w_person * inp.signals.person_confidence
        org_contribution = self.config.w_org * inp.signals.org_confidence
        similarity_value = inp.similarity.cos_top if inp.similarity.cos_top is not None else 0.0
        similarity_contribution = self.config.w_similarity * similarity_value
        
        # Calculate bonus contributions
        date_bonus = self.config.bonus_date_match if inp.signals.date_match else 0.0
        id_bonus = self.config.bonus_id_match if inp.signals.id_match else 0.0
        
        # Normalize features for audit trail
        normalized_features = {
            "smartfilter_confidence": inp.smartfilter.confidence,
            "person_confidence": inp.signals.person_confidence,
            "org_confidence": inp.signals.org_confidence,
            "similarity_cos_top": similarity_value,
            "date_match": inp.signals.date_match,
            "id_match": inp.signals.id_match
        }
        
        # Evidence strength indicators
        evidence_strength = {
            "smartfilter_strong": inp.smartfilter.confidence >= 0.7,
            "person_strong": inp.signals.person_confidence >= 0.7,
            "org_strong": inp.signals.org_confidence >= 0.7,
            "similarity_high": inp.similarity.cos_top and inp.similarity.cos_top >= 0.9,
            "exact_id_match": inp.signals.id_match,
            "exact_dob_match": inp.signals.date_match
        }

        return {
            "calculated_score": score,
            "score_breakdown": {
                "smartfilter_contribution": smartfilter_contribution,
                "person_contribution": person_contribution,
                "org_contribution": org_contribution,
                "similarity_contribution": similarity_contribution,
                "date_bonus": date_bonus,
                "id_bonus": id_bonus,
                "total": smartfilter_contribution + person_contribution + org_contribution + 
                        similarity_contribution + date_bonus + id_bonus
            },
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
            "normalized_features": normalized_features,
            "evidence_strength": evidence_strength,
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
    
    def _safe_smartfilter(self, smartfilter: Optional[SmartFilterInfo]) -> SmartFilterInfo:
        """Safely extract smart filter info with defaults for None values"""
        if smartfilter is None:
            return SmartFilterInfo(should_process=True, confidence=0.0)
        
        return SmartFilterInfo(
            should_process=smartfilter.should_process if smartfilter.should_process is not None else True,
            confidence=smartfilter.confidence if smartfilter.confidence is not None else 0.0,
            estimated_complexity=smartfilter.estimated_complexity
        )
    
    def _safe_signals(self, signals: Optional[SignalsInfo]) -> SignalsInfo:
        """Safely extract signals info with defaults for None values"""
        if signals is None:
            return SignalsInfo(
                person_confidence=0.0,
                org_confidence=0.0,
                date_match=False,
                id_match=False,
                evidence={}
            )
        
        return SignalsInfo(
            person_confidence=signals.person_confidence if signals.person_confidence is not None else 0.0,
            org_confidence=signals.org_confidence if signals.org_confidence is not None else 0.0,
            date_match=signals.date_match if signals.date_match is not None else False,
            id_match=signals.id_match if signals.id_match is not None else False,
            evidence=signals.evidence if signals.evidence is not None else {}
        )
    
    def _safe_similarity(self, similarity: Optional[SimilarityInfo]) -> SimilarityInfo:
        """Safely extract similarity info with defaults for None values"""
        if similarity is None:
            return SimilarityInfo(cos_top=None, cos_p95=None)
        
        return SimilarityInfo(
            cos_top=similarity.cos_top,
            cos_p95=similarity.cos_p95
        )
    
    def _register_decision_metrics(self):
        """Register decision-specific metrics"""
        decision_metrics = [
            MetricDefinition(
                "decision_total",
                MetricType.COUNTER,
                "Total number of decisions made",
                labels={"risk"}
            ),
            MetricDefinition(
                "decision_score",
                MetricType.HISTOGRAM,
                "Decision scores distribution",
                labels={"risk"}
            ),
            MetricDefinition(
                "decision_confidence_smartfilter",
                MetricType.HISTOGRAM,
                "Smart filter confidence scores"
            ),
            MetricDefinition(
                "decision_confidence_person",
                MetricType.HISTOGRAM,
                "Person confidence scores"
            ),
            MetricDefinition(
                "decision_confidence_org",
                MetricType.HISTOGRAM,
                "Organization confidence scores"
            ),
            MetricDefinition(
                "decision_similarity",
                MetricType.HISTOGRAM,
                "Similarity scores (cos_top)"
            ),
            MetricDefinition(
                "decision_evidence_matches",
                MetricType.COUNTER,
                "Evidence match counts",
                labels={"match_type"}  # date_match, id_match
            )
        ]
        
        for metric_def in decision_metrics:
            self.metrics_service.register_metric(metric_def)
        
        self.logger.info("Registered decision-specific metrics")
    
    def _record_decision_metrics(self, risk: RiskLevel, score: float, inp: DecisionInput):
        """Record decision metrics"""
        # Record total decisions with risk label
        self.metrics_service.increment_counter(
            "decision_total",
            labels={"risk": risk.value}
        )
        
        # Record score histogram with risk label
        self.metrics_service.record_histogram(
            "decision_score",
            score,
            labels={"risk": risk.value}
        )
        
        # Record confidence scores
        self.metrics_service.record_histogram(
            "decision_confidence_smartfilter",
            inp.smartfilter.confidence
        )
        
        self.metrics_service.record_histogram(
            "decision_confidence_person",
            inp.signals.person_confidence
        )
        
        self.metrics_service.record_histogram(
            "decision_confidence_org",
            inp.signals.org_confidence
        )
        
        # Record similarity if available
        if inp.similarity.cos_top is not None:
            self.metrics_service.record_histogram(
                "decision_similarity",
                inp.similarity.cos_top
            )
        
        # Record evidence matches
        if inp.signals.date_match:
            self.metrics_service.increment_counter(
                "decision_evidence_matches",
                labels={"match_type": "date_match"}
            )
        
        if inp.signals.id_match:
            self.metrics_service.increment_counter(
                "decision_evidence_matches",
                labels={"match_type": "id_match"}
            )
