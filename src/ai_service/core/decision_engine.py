"""
Decision Engine for risk assessment and decision making.
"""

from typing import Any, Dict, List, Optional

from ..contracts.decision_contracts import DecisionInput, DecisionOutput, RiskLevel, SmartFilterInfo, SignalsInfo, SimilarityInfo
from ..contracts.trace_models import SearchTrace
from ..config.settings import DecisionConfig, DECISION_CONFIG
from ..utils.logging_config import get_logger

logger = get_logger(__name__)
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
    
    def decide(self, inp: DecisionInput, search_trace: Optional[SearchTrace] = None) -> DecisionOutput:
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
            similarity=similarity,
            search=inp.search
        )
        
        # Calculate weighted score
        score = self._calculate_weighted_score(safe_input)
        
        # Determine risk level based on thresholds and special conditions
        risk = self._determine_risk_level(score, inp)
        
        # Generate reasons based on contributing factors
        reasons = self._generate_reasons(safe_input, score, risk)
        
        # Extract details with used features and weights
        details = self._extract_details(safe_input, score)
        
        # Apply business gates (TIN/DOB requirement)
        review_required, required_fields = self._should_request_additional_fields(safe_input, risk, score)
        
        # Log decision details at DEBUG level
        self.logger.debug(
            f"Decision made: risk={risk.value}, score={score:.3f}, "
            f"smartfilter_conf={smartfilter.confidence:.3f}, "
            f"person_conf={signals.person_confidence:.3f}, "
            f"org_conf={signals.org_confidence:.3f}, "
            f"similarity={similarity.cos_top}, "
            f"date_match={signals.date_match}, id_match={signals.id_match}, "
            f"review_required={review_required}, required_fields={required_fields}"
        )
        
        # Record metrics if available
        if self.metrics_service:
            self._record_decision_metrics(risk, score, inp)
        
        # Add search trace to details if available (only in debug mode)
        if search_trace and search_trace.enabled and getattr(self.config, 'debug_mode', False):
            details["search_trace"] = search_trace.to_dict()
        
        return DecisionOutput(
            risk=risk,
            score=score,
            reasons=reasons,
            details=details,
            review_required=review_required,
            required_additional_fields=required_fields
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
                # Exact match bonus
                if search.has_exact_matches and search.exact_confidence >= 0.95:
                    score += self.config.bonus_exact_match

                if search.total_matches > 1:
                    score += self.config.bonus_multiple_matches

                if search.high_confidence_matches > 0:
                    score += self.config.bonus_high_confidence
        
        # Bonus factors
        if inp.signals.date_match:
            score += self.config.bonus_date_match
        if inp.signals.id_match:
            score += self.config.bonus_id_match

        # CRITICAL: Homoglyph attack detected = major score boost
        if (inp and hasattr(inp, 'normalization') and hasattr(inp.normalization, 'homoglyph_detected') and
            inp.normalization.homoglyph_detected):
            score += 0.85  # Boost score to ensure HIGH risk classification
            self.logger.warning(f"🚨 HOMOGLYPH ATTACK - adding +0.85 to score (now: {score:.3f})")

        return score
    
    def _determine_risk_level(self, score: float, inp: Optional[DecisionInput] = None) -> RiskLevel:
        """Determine risk level based on score and special conditions"""

        # CRITICAL: Exact match in sanctions = automatic HIGH RISK
        if inp and inp.search:
            if (inp.search.has_exact_matches and
                inp.search.exact_confidence >= 0.95 and
                inp.search.total_matches >= 1):
                self.logger.info(f"🚨 EXACT SANCTIONS MATCH - forcing HIGH RISK (score: {score:.3f})")
                return RiskLevel.HIGH

        # CRITICAL: Homoglyph attack detected = automatic HIGH RISK
        # Homoglyph attacks are security threats that should always be flagged as high risk
        if inp and hasattr(inp, 'normalization') and hasattr(inp.normalization, 'homoglyph_detected'):
            if inp.normalization.homoglyph_detected:
                self.logger.warning(f"🚨 HOMOGLYPH ATTACK DETECTED - forcing HIGH RISK (score: {score:.3f})")
                return RiskLevel.HIGH

        # Standard score-based thresholds
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

        # CRITICAL: Check for exact sanctions match first
        if (inp.search and inp.search.has_exact_matches and
            inp.search.exact_confidence >= 0.95 and risk == RiskLevel.HIGH):
            reasons.append("🚨 EXACT MATCH IN SANCTIONS LIST - HIGH RISK")

        # CRITICAL: Check for homoglyph attack
        if (inp and hasattr(inp, 'normalization') and hasattr(inp.normalization, 'homoglyph_detected') and
            inp.normalization.homoglyph_detected):
            reasons.append("🚨 HOMOGLYPH ATTACK DETECTED - HIGH RISK")

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
        
        # Calculate search contribution
        search_contribution = 0.0
        logger.info(f"DEBUG: inp.search = {inp.search}")
        if inp.search:
            search = inp.search
            # Exact matches (highest priority)
            if search.has_exact_matches and search.exact_confidence >= self.config.thr_search_exact:
                search_contribution += self.config.w_search_exact * search.exact_confidence
            # Phrase matches
            if search.has_phrase_matches and search.phrase_confidence >= self.config.thr_search_phrase:
                search_contribution += self.config.w_search_phrase * search.phrase_confidence
            # N-gram matches
            if search.has_ngram_matches and search.ngram_confidence >= self.config.thr_search_ngram:
                search_contribution += self.config.w_search_ngram * search.ngram_confidence
            # Vector matches
            if search.has_vector_matches and search.vector_confidence >= self.config.thr_search_vector:
                search_contribution += self.config.w_search_vector * search.vector_confidence
            # Search bonuses
            if search_contribution > 0:  # Only if at least one search component passed threshold
                if search.total_matches > 1:
                    search_contribution += self.config.bonus_multiple_matches
                if search.high_confidence_matches > 0:
                    search_contribution += self.config.bonus_high_confidence

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
            "id_match": inp.signals.id_match,
            "search_exact_matches": inp.search.has_exact_matches if inp.search else False,
            "search_exact_confidence": inp.search.exact_confidence if inp.search else 0.0,
            "search_total_matches": inp.search.total_matches if inp.search else 0
        }

        # Evidence strength indicators
        evidence_strength = {
            "smartfilter_strong": inp.smartfilter.confidence >= 0.7,
            "person_strong": inp.signals.person_confidence >= 0.7,
            "org_strong": inp.signals.org_confidence >= 0.7,
            "similarity_high": inp.similarity.cos_top and inp.similarity.cos_top >= 0.9,
            "exact_id_match": inp.signals.id_match,
            "exact_dob_match": inp.signals.date_match,
            "search_exact_match": inp.search and inp.search.has_exact_matches and inp.search.exact_confidence >= 0.95,
            "search_high_confidence": inp.search and inp.search.high_confidence_matches > 0
        }

        return {
            "calculated_score": score,
            "score_breakdown": {
                "smartfilter_contribution": smartfilter_contribution,
                "person_contribution": person_contribution,
                "org_contribution": org_contribution,
                "similarity_contribution": similarity_contribution,
                "search_contribution": search_contribution,
                "date_bonus": date_bonus,
                "id_bonus": id_bonus,
                "total": smartfilter_contribution + person_contribution + org_contribution +
                        similarity_contribution + search_contribution + date_bonus + id_bonus
            },
            "weights_used": {
                "w_smartfilter": self.config.w_smartfilter,
                "w_person": self.config.w_person,
                "w_org": self.config.w_org,
                "w_similarity": self.config.w_similarity,
                "w_search_exact": self.config.w_search_exact,
                "w_search_phrase": self.config.w_search_phrase,
                "w_search_ngram": self.config.w_search_ngram,
                "w_search_vector": self.config.w_search_vector,
                "bonus_date_match": self.config.bonus_date_match,
                "bonus_id_match": self.config.bonus_id_match,
                "bonus_multiple_matches": self.config.bonus_multiple_matches,
                "bonus_high_confidence": self.config.bonus_high_confidence
            },
            "thresholds": {
                "thr_high": self.config.thr_high,
                "thr_medium": self.config.thr_medium,
                "thr_search_exact": self.config.thr_search_exact,
                "thr_search_phrase": self.config.thr_search_phrase,
                "thr_search_ngram": self.config.thr_search_ngram,
                "thr_search_vector": self.config.thr_search_vector
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
            "search_info": {
                "has_exact_matches": inp.search.has_exact_matches if inp.search else False,
                "exact_confidence": inp.search.exact_confidence if inp.search else 0.0,
                "has_phrase_matches": inp.search.has_phrase_matches if inp.search else False,
                "phrase_confidence": inp.search.phrase_confidence if inp.search else 0.0,
                "has_ngram_matches": inp.search.has_ngram_matches if inp.search else False,
                "ngram_confidence": inp.search.ngram_confidence if inp.search else 0.0,
                "has_vector_matches": inp.search.has_vector_matches if inp.search else False,
                "vector_confidence": inp.search.vector_confidence if inp.search else 0.0,
                "total_matches": inp.search.total_matches if inp.search else 0,
                "high_confidence_matches": inp.search.high_confidence_matches if inp.search else 0
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
    
    def _should_request_additional_fields(self, inp: DecisionInput, risk: RiskLevel, score: float) -> tuple[bool, List[str]]:
        """
        Determine if additional fields (TIN/DOB) are required for decision.
        
        Business rule:
        - If strong name match but missing TIN/DOB → mark REVIEW and request fields
        - Exception: if sanction record has neither TIN nor DOB → allow reject by full name
        
        Args:
            inp: Decision input with signals
            risk: Current risk level
            score: Current decision score
            
        Returns:
            Tuple of (review_required, required_fields)
        """
        # Check if TIN/DOB gate is enabled
        if not getattr(self.config, 'require_tin_dob_gate', True):
            return False, []
        
        # Only apply to high-risk decisions (strong matches)
        if risk != RiskLevel.HIGH:
            return False, []
        
        # Check if we have strong name match indicators
        has_strong_name_match = (
            inp.signals.person_confidence >= 0.8 or 
            inp.signals.org_confidence >= 0.8 or
            (inp.similarity.cos_top and inp.similarity.cos_top >= 0.8)
        )
        
        if not has_strong_name_match:
            return False, []
        
        # Check if we have TIN/DOB evidence
        has_tin = inp.signals.id_match or 'inn' in inp.signals.evidence.get('extracted_ids', [])
        has_dob = inp.signals.date_match or 'dob' in inp.signals.evidence.get('extracted_dates', [])
        
        # If we have both TIN and DOB, no additional fields needed
        if has_tin and has_dob:
            return False, []
        
        # Check if sanction record lacks both TIN and DOB (exception case)
        sanction_has_no_identifiers = (
            'sanction_record' in inp.signals.evidence and
            not inp.signals.evidence.get('sanction_record', {}).get('has_tin', False) and
            not inp.signals.evidence.get('sanction_record', {}).get('has_dob', False)
        )
        
        if sanction_has_no_identifiers:
            # Allow reject by full name - no additional fields required
            return False, []
        
        # Request missing fields
        required_fields = []
        if not has_tin:
            required_fields.append('TIN')
        if not has_dob:
            required_fields.append('DOB')
        
        return True, required_fields
