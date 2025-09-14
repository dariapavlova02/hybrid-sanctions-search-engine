"""
DecisionEngine - Layer 9 of the unified architecture.

Makes final match/no-match decisions based on processing results from layers 1-8.
Combines confidence scores from signals, normalization quality, and optional
similarity search to make automated screening decisions.
"""

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..contracts.base_contracts import UnifiedProcessingResult
from ..contracts.decision_contracts import (
    ConfidenceLevel,
    DecisionContext,
    DecisionEngineInterface,
    DecisionMetrics,
    DecisionResult,
    MatchDecision,
    MatchEvidence,
)
from ..utils import get_logger

logger = get_logger(__name__)


class DecisionEngine(DecisionEngineInterface):
    """
    Production decision engine for sanctions screening.

    Implements intelligent match/no-match decisions based on:
    1. Signal confidence from Layer 6 (persons, organizations, IDs)
    2. Normalization quality from Layer 5
    3. Language detection confidence from Layer 3
    4. Optional embedding similarity scores from Layer 8
    5. Configurable risk tolerance and business rules
    """

    def __init__(
        self,
        # Configuration file path
        config_path: Optional[str] = None,

        # Decision thresholds (fallback defaults)
        match_threshold: float = 0.85,        # High confidence match
        weak_match_threshold: float = 0.65,   # Weak match
        review_threshold: float = 0.45,       # Needs manual review
        no_match_threshold: float = 0.25,     # Clear no match

        # Evidence weights (fallback defaults)
        signals_weight: float = 0.4,          # Signals (persons/orgs) weight
        normalization_weight: float = 0.3,    # Normalization quality weight
        language_weight: float = 0.2,         # Language confidence weight
        embedding_weight: float = 0.1,        # Embedding similarity weight

        # Risk and quality factors
        min_data_quality_score: float = 0.3,  # Minimum data quality for decisions
        enable_strict_mode: bool = False,      # Strict mode for high-risk scenarios
    ):
        # Load configuration from file if provided
        if config_path:
            config = self._load_config(config_path)
        else:
            # Try to find default config file
            project_root = Path(__file__).parent.parent.parent.parent
            default_config_path = project_root / "config" / "weights.json"
            if default_config_path.exists():
                config = self._load_config(str(default_config_path))
            else:
                config = {}

        # Apply configuration values with fallbacks
        decision_config = config.get("decision_engine", {})
        weights = decision_config.get("weights", {})
        thresholds = decision_config.get("thresholds", {})

        # Apply environment-specific overrides
        env = os.getenv("APP_ENV", "development")
        env_overrides = config.get("environment_overrides", {}).get(env, {})

        self.match_threshold = env_overrides.get("auto_hit", thresholds.get("auto_hit", match_threshold))
        self.weak_match_threshold = weak_match_threshold  # Not in config yet
        self.review_threshold = thresholds.get("review", review_threshold)
        self.no_match_threshold = thresholds.get("clear", no_match_threshold)

        self.signals_weight = weights.get("signals", signals_weight)
        self.normalization_weight = weights.get("normalization", normalization_weight)
        self.language_weight = weights.get("language", language_weight)
        self.embedding_weight = weights.get("embeddings", embedding_weight)

        self.min_data_quality_score = min_data_quality_score
        self.enable_strict_mode = env_overrides.get("enable_strict_matching", enable_strict_mode)

        # Store config for runtime use
        self.config = config
        self.boost_factors = decision_config.get("boost_factors", {})
        self.penalty_factors = decision_config.get("penalty_factors", {})

        # Metrics tracking
        self.metrics = DecisionMetrics()

        logger.info(
            f"DecisionEngine initialized from config: match_threshold={self.match_threshold:.2f}, "
            f"strict_mode={self.enable_strict_mode}, env={env}"
        )

    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            logger.info(f"Loaded DecisionEngine config from {config_path}")
            return config
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config file {config_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error loading config file {config_path}: {e}")
            return {}

    async def make_decision(
        self,
        processing_result: UnifiedProcessingResult,
        candidates: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> DecisionResult:
        """Make match/no-match decision based on processing results"""

        start_time = time.time()
        evidence: List[MatchEvidence] = []
        used_layers: List[str] = []
        risk_factors: List[str] = []

        try:
            # Parse decision context
            decision_context = self._parse_context(context or {})

            # ============================================================
            # 1. Data Quality Assessment
            # ============================================================

            data_quality, completeness = self._assess_data_quality(processing_result)

            if completeness < self.min_data_quality_score:
                return self._create_insufficient_data_decision(
                    processing_result, start_time, data_quality, completeness
                )

            # ============================================================
            # 2. Extract Evidence from Processing Results
            # ============================================================

            # Extract signals evidence (Layer 6)
            signals_evidence = self._extract_signals_evidence(processing_result)
            evidence.extend(signals_evidence)
            if signals_evidence:
                used_layers.append("signals")

            # Extract normalization evidence (Layer 5)
            norm_evidence = self._extract_normalization_evidence(processing_result)
            evidence.extend(norm_evidence)
            if norm_evidence:
                used_layers.append("normalization")

            # Extract language evidence (Layer 3)
            lang_evidence = self._extract_language_evidence(processing_result)
            evidence.extend(lang_evidence)
            if lang_evidence:
                used_layers.append("language_detection")

            # Extract embedding evidence (Layer 8) if available
            if processing_result.embeddings:
                emb_evidence = self._extract_embedding_evidence(
                    processing_result, candidates
                )
                evidence.extend(emb_evidence)
                if emb_evidence:
                    used_layers.append("embeddings")

            # ============================================================
            # 3. Calculate Weighted Confidence Score
            # ============================================================

            total_confidence = self._calculate_weighted_confidence(evidence)

            # ============================================================
            # 4. Risk Factor Analysis
            # ============================================================

            risk_factors = self._identify_risk_factors(
                processing_result, evidence, decision_context
            )

            # Apply risk adjustments
            adjusted_confidence = self._apply_risk_adjustments(
                total_confidence, risk_factors, decision_context
            )

            # ============================================================
            # 5. Make Final Decision
            # ============================================================

            decision, confidence_level = self._determine_decision(
                adjusted_confidence, risk_factors, decision_context
            )

            # ============================================================
            # 6. Generate Reasoning and Recommendations
            # ============================================================

            reasoning = self._generate_reasoning(
                decision, adjusted_confidence, evidence, risk_factors
            )

            next_steps = self._generate_recommendations(
                decision, adjusted_confidence, risk_factors, decision_context
            )

            # Update metrics
            self._update_metrics(decision, adjusted_confidence, time.time() - start_time)

            return DecisionResult(
                decision=decision,
                confidence=adjusted_confidence,
                confidence_level=confidence_level,
                evidence=evidence,
                reasoning=reasoning,
                risk_factors=risk_factors,
                matched_entity=self._extract_matched_entity(processing_result, evidence),
                match_score=adjusted_confidence,
                match_type=self._determine_match_type(processing_result),
                processing_time=time.time() - start_time,
                used_layers=used_layers,
                fallback_used=len(evidence) == 0,
                data_quality=data_quality,
                completeness=completeness,
                next_steps=next_steps,
                review_required=decision in [MatchDecision.NEEDS_REVIEW, MatchDecision.WEAK_MATCH]
            )

        except Exception as e:
            logger.error(f"Decision making failed: {e}", exc_info=True)

            # Fallback decision
            return DecisionResult(
                decision=MatchDecision.NEEDS_REVIEW,
                confidence=0.0,
                confidence_level=ConfidenceLevel.VERY_LOW,
                evidence=[],
                reasoning=f"Decision engine error: {str(e)}",
                risk_factors=["decision_engine_error"],
                processing_time=time.time() - start_time,
                used_layers=["fallback"],
                fallback_used=True,
                data_quality="poor",
                completeness=0.0,
                next_steps=["manual_review_required", "investigate_error"],
                review_required=True
            )

    def _parse_context(self, context: Dict[str, Any]) -> DecisionContext:
        """Parse and validate decision context"""
        return DecisionContext(
            risk_tolerance=context.get("risk_tolerance", "medium"),
            require_exact_match=context.get("require_exact_match", False),
            allow_weak_matches=context.get("allow_weak_matches", True),
            review_threshold=context.get("review_threshold", self.review_threshold),
            match_threshold=context.get("match_threshold", self.match_threshold),
            source_reliability=context.get("source_reliability", 1.0),
            **{k: v for k, v in context.items() if k not in [
                "risk_tolerance", "require_exact_match", "allow_weak_matches",
                "review_threshold", "match_threshold", "source_reliability"
            ]}
        )

    def _assess_data_quality(
        self, result: UnifiedProcessingResult
    ) -> tuple[str, float]:
        """Assess quality and completeness of input data"""

        completeness = 0.0
        quality_factors = []

        # Check if we have basic text
        if result.original_text and len(result.original_text.strip()) > 0:
            completeness += 0.2
            quality_factors.append("has_input_text")

        # Check language detection
        if result.language_confidence and result.language_confidence > 0.7:
            completeness += 0.2
            quality_factors.append("good_language_detection")
        elif result.language_confidence and result.language_confidence > 0.3:
            completeness += 0.1
            quality_factors.append("fair_language_detection")

        # Check normalization success
        if result.success and result.normalized_text:
            completeness += 0.3
            quality_factors.append("successful_normalization")

        # Check signals
        if result.signals and result.signals.confidence > 0.5:
            completeness += 0.2
            quality_factors.append("strong_signals")
        elif result.signals and result.signals.confidence > 0.2:
            completeness += 0.1
            quality_factors.append("weak_signals")

        # Check for processing errors
        if result.errors:
            completeness -= 0.1 * len(result.errors)
            quality_factors.append(f"{len(result.errors)}_errors")

        # Determine quality level
        if completeness >= 0.8:
            quality = "excellent"
        elif completeness >= 0.6:
            quality = "good"
        elif completeness >= 0.4:
            quality = "fair"
        else:
            quality = "poor"

        logger.debug(
            f"Data quality assessment: {quality} (completeness: {completeness:.2f})"
        )

        return quality, max(0.0, min(1.0, completeness))

    def _extract_signals_evidence(
        self, result: UnifiedProcessingResult
    ) -> List[MatchEvidence]:
        """Extract evidence from signals (persons, organizations, IDs)"""
        evidence = []

        if not result.signals:
            return evidence

        signals = result.signals

        # Person signals evidence
        if signals.persons:
            for person in signals.persons:
                confidence = getattr(person, 'confidence', 0.0)
                if confidence > 0.1:  # Only consider meaningful confidence
                    evidence.append(MatchEvidence(
                        source="signals",
                        evidence_type="person_detected",
                        confidence=confidence,
                        details={
                            "person_data": person.dict() if hasattr(person, 'dict') else str(person),
                            "signal_type": "person"
                        },
                        weight=self.signals_weight * 0.5  # 50% of signals weight for persons
                    ))

        # Organization signals evidence
        if signals.organizations:
            for org in signals.organizations:
                confidence = getattr(org, 'confidence', 0.0)
                if confidence > 0.1:
                    evidence.append(MatchEvidence(
                        source="signals",
                        evidence_type="organization_detected",
                        confidence=confidence,
                        details={
                            "organization_data": org.dict() if hasattr(org, 'dict') else str(org),
                            "signal_type": "organization"
                        },
                        weight=self.signals_weight * 0.5  # 50% of signals weight for orgs
                    ))

        # Overall signals confidence
        if signals.confidence > 0.1:
            evidence.append(MatchEvidence(
                source="signals",
                evidence_type="overall_signals_confidence",
                confidence=signals.confidence,
                details={
                    "persons_count": len(signals.persons) if signals.persons else 0,
                    "organizations_count": len(signals.organizations) if signals.organizations else 0
                },
                weight=self.signals_weight
            ))

        return evidence

    def _extract_normalization_evidence(
        self, result: UnifiedProcessingResult
    ) -> List[MatchEvidence]:
        """Extract evidence from normalization quality"""
        evidence = []

        if not result.success or not result.normalized_text:
            return evidence

        # Normalization success and quality
        norm_confidence = 0.5  # Base confidence for successful normalization

        # Bonus for having tokens and trace
        if result.tokens:
            norm_confidence += 0.2

        if result.trace:
            norm_confidence += 0.2

        # Penalty for errors
        if result.errors:
            norm_confidence -= 0.1 * len(result.errors)

        norm_confidence = max(0.0, min(1.0, norm_confidence))

        if norm_confidence > 0.1:
            evidence.append(MatchEvidence(
                source="normalization",
                evidence_type="normalization_quality",
                confidence=norm_confidence,
                details={
                    "normalized_text": result.normalized_text,
                    "token_count": len(result.tokens) if result.tokens else 0,
                    "trace_count": len(result.trace) if result.trace else 0,
                    "error_count": len(result.errors) if result.errors else 0
                },
                weight=self.normalization_weight
            ))

        return evidence

    def _extract_language_evidence(
        self, result: UnifiedProcessingResult
    ) -> List[MatchEvidence]:
        """Extract evidence from language detection confidence"""
        evidence = []

        if result.language_confidence and result.language_confidence > 0.1:
            evidence.append(MatchEvidence(
                source="language_detection",
                evidence_type="language_confidence",
                confidence=result.language_confidence,
                details={
                    "detected_language": result.language,
                    "confidence": result.language_confidence
                },
                weight=self.language_weight
            ))

        return evidence

    def _extract_embedding_evidence(
        self,
        result: UnifiedProcessingResult,
        candidates: Optional[List[Dict[str, Any]]]
    ) -> List[MatchEvidence]:
        """Extract evidence from embedding similarity (when available)"""
        evidence = []

        # This is a placeholder - actual implementation would depend on
        # how embedding similarity search is integrated
        if result.embeddings and candidates:
            # Calculate similarity with candidates
            # This would require actual embedding comparison logic
            similarity_score = 0.3  # Placeholder

            evidence.append(MatchEvidence(
                source="embeddings",
                evidence_type="embedding_similarity",
                confidence=similarity_score,
                details={
                    "candidate_count": len(candidates),
                    "best_similarity": similarity_score
                },
                weight=self.embedding_weight
            ))

        return evidence

    def _calculate_weighted_confidence(self, evidence: List[MatchEvidence]) -> float:
        """Calculate weighted confidence score from all evidence"""
        if not evidence:
            return 0.0

        total_weighted_score = 0.0
        total_weights = 0.0

        for ev in evidence:
            weighted_score = ev.confidence * ev.weight
            total_weighted_score += weighted_score
            total_weights += ev.weight

        if total_weights == 0:
            return 0.0

        return total_weighted_score / total_weights

    def _identify_risk_factors(
        self,
        result: UnifiedProcessingResult,
        evidence: List[MatchEvidence],
        context: DecisionContext
    ) -> List[str]:
        """Identify risk factors that might affect decision"""
        risk_factors = []

        # Processing errors
        if result.errors:
            risk_factors.append("processing_errors")

        # Low language confidence
        if result.language_confidence and result.language_confidence < 0.5:
            risk_factors.append("uncertain_language")

        # Missing key evidence
        if not any(ev.source == "signals" for ev in evidence):
            risk_factors.append("no_signal_evidence")

        # Poor normalization
        if not result.success or not result.normalized_text:
            risk_factors.append("normalization_failed")

        # Low overall evidence confidence
        avg_confidence = sum(ev.confidence for ev in evidence) / max(len(evidence), 1)
        if avg_confidence < 0.3:
            risk_factors.append("low_evidence_confidence")

        # Context-specific risks
        if context.risk_tolerance == "low":
            risk_factors.append("low_risk_tolerance")

        return risk_factors

    def _apply_risk_adjustments(
        self,
        confidence: float,
        risk_factors: List[str],
        context: DecisionContext
    ) -> float:
        """Apply risk-based adjustments to confidence score"""
        adjusted_confidence = confidence

        # Apply penalties for risk factors
        for risk_factor in risk_factors:
            if risk_factor == "processing_errors":
                adjusted_confidence *= 0.9
            elif risk_factor == "uncertain_language":
                adjusted_confidence *= 0.95
            elif risk_factor == "no_signal_evidence":
                adjusted_confidence *= 0.8
            elif risk_factor == "normalization_failed":
                adjusted_confidence *= 0.7
            elif risk_factor == "low_evidence_confidence":
                adjusted_confidence *= 0.85
            elif risk_factor == "low_risk_tolerance":
                adjusted_confidence *= 0.9

        # Apply strict mode penalty
        if self.enable_strict_mode:
            adjusted_confidence *= 0.9

        # Apply source reliability factor
        adjusted_confidence *= context.source_reliability

        return max(0.0, min(1.0, adjusted_confidence))

    def _determine_decision(
        self,
        confidence: float,
        risk_factors: List[str],
        context: DecisionContext
    ) -> tuple[MatchDecision, ConfidenceLevel]:
        """Determine final match decision based on confidence and context"""

        # Determine confidence level
        if confidence >= 0.95:
            conf_level = ConfidenceLevel.VERY_HIGH
        elif confidence >= 0.8:
            conf_level = ConfidenceLevel.HIGH
        elif confidence >= 0.6:
            conf_level = ConfidenceLevel.MEDIUM
        elif confidence >= 0.4:
            conf_level = ConfidenceLevel.LOW
        else:
            conf_level = ConfidenceLevel.VERY_LOW

        # Make decision based on thresholds and context
        if context.require_exact_match and conf_level != ConfidenceLevel.VERY_HIGH:
            return MatchDecision.NEEDS_REVIEW, conf_level

        if confidence >= context.match_threshold:
            return MatchDecision.MATCH, conf_level
        elif confidence >= self.weak_match_threshold and context.allow_weak_matches:
            return MatchDecision.WEAK_MATCH, conf_level
        elif confidence >= context.review_threshold:
            return MatchDecision.NEEDS_REVIEW, conf_level
        elif confidence >= self.no_match_threshold:
            return MatchDecision.NO_MATCH, conf_level
        else:
            # Very low confidence - could be no match or need review
            if "processing_errors" in risk_factors or "normalization_failed" in risk_factors:
                return MatchDecision.NEEDS_REVIEW, conf_level
            else:
                return MatchDecision.NO_MATCH, conf_level

    def _generate_reasoning(
        self,
        decision: MatchDecision,
        confidence: float,
        evidence: List[MatchEvidence],
        risk_factors: List[str]
    ) -> str:
        """Generate human-readable reasoning for the decision"""

        evidence_summary = []
        for ev in evidence:
            evidence_summary.append(
                f"{ev.source}:{ev.evidence_type}({ev.confidence:.2f})"
            )

        reasoning_parts = [
            f"Decision: {decision.value.upper()}",
            f"Confidence: {confidence:.2f}",
            f"Evidence: {', '.join(evidence_summary)}" if evidence_summary else "No evidence",
        ]

        if risk_factors:
            reasoning_parts.append(f"Risk factors: {', '.join(risk_factors)}")

        return " | ".join(reasoning_parts)

    def _generate_recommendations(
        self,
        decision: MatchDecision,
        confidence: float,
        risk_factors: List[str],
        context: DecisionContext
    ) -> List[str]:
        """Generate next step recommendations"""

        recommendations = []

        if decision == MatchDecision.MATCH:
            recommendations.extend([
                "proceed_with_match",
                "log_match_details",
                "update_match_statistics"
            ])

        elif decision == MatchDecision.WEAK_MATCH:
            recommendations.extend([
                "flag_for_review",
                "collect_additional_information",
                "consider_secondary_verification"
            ])

        elif decision == MatchDecision.NEEDS_REVIEW:
            recommendations.extend([
                "manual_review_required",
                "escalate_to_analyst",
                "gather_additional_context"
            ])

        elif decision == MatchDecision.NO_MATCH:
            recommendations.extend([
                "clear_for_processing",
                "log_no_match_decision"
            ])

        else:  # INSUFFICIENT_DATA
            recommendations.extend([
                "request_additional_data",
                "retry_with_more_context",
                "manual_review_required"
            ])

        # Add risk-specific recommendations
        if "processing_errors" in risk_factors:
            recommendations.append("investigate_processing_errors")
        if "uncertain_language" in risk_factors:
            recommendations.append("verify_language_detection")

        return recommendations

    def _extract_matched_entity(
        self, result: UnifiedProcessingResult, evidence: List[MatchEvidence]
    ) -> Optional[str]:
        """Extract the entity that was matched (if any)"""
        if result.normalized_text:
            return result.normalized_text
        return result.original_text[:100] if result.original_text else None

    def _determine_match_type(self, result: UnifiedProcessingResult) -> Optional[str]:
        """Determine whether this is a person or organization match"""
        if result.signals:
            if result.signals.persons:
                return "person"
            elif result.signals.organizations:
                return "organization"
        return None

    def _create_insufficient_data_decision(
        self,
        result: UnifiedProcessingResult,
        start_time: float,
        data_quality: str,
        completeness: float
    ) -> DecisionResult:
        """Create decision for insufficient data cases"""
        return DecisionResult(
            decision=MatchDecision.INSUFFICIENT_DATA,
            confidence=0.0,
            confidence_level=ConfidenceLevel.VERY_LOW,
            evidence=[],
            reasoning=f"Insufficient data quality: {data_quality} (completeness: {completeness:.2f})",
            risk_factors=["insufficient_data", "poor_data_quality"],
            processing_time=time.time() - start_time,
            used_layers=["data_quality_assessment"],
            fallback_used=True,
            data_quality=data_quality,
            completeness=completeness,
            next_steps=["request_additional_data", "manual_review_required"],
            review_required=True
        )

    def _update_metrics(
        self, decision: MatchDecision, confidence: float, processing_time: float
    ) -> None:
        """Update decision engine metrics"""
        self.metrics.total_decisions += 1

        if decision == MatchDecision.MATCH:
            self.metrics.match_decisions += 1
        elif decision == MatchDecision.NO_MATCH:
            self.metrics.no_match_decisions += 1
        elif decision == MatchDecision.WEAK_MATCH:
            self.metrics.weak_match_decisions += 1
        elif decision in [MatchDecision.NEEDS_REVIEW, MatchDecision.INSUFFICIENT_DATA]:
            self.metrics.review_decisions += 1

        # Update averages
        total = self.metrics.total_decisions
        self.metrics.avg_confidence = (
            (self.metrics.avg_confidence * (total - 1) + confidence) / total
        )
        self.metrics.avg_processing_time = (
            (self.metrics.avg_processing_time * (total - 1) + processing_time) / total
        )

        if confidence >= 0.8:
            self.metrics.high_confidence_decisions += 1
        elif confidence < 0.4:
            self.metrics.low_confidence_decisions += 1

    # Interface implementation methods

    async def batch_decisions(
        self,
        processing_results: List[UnifiedProcessingResult],
        candidates: Optional[List[Dict[str, Any]]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> List[DecisionResult]:
        """Make decisions for multiple processing results efficiently"""
        decisions = []

        for result in processing_results:
            decision = await self.make_decision(result, candidates, context)
            decisions.append(decision)

        return decisions

    def update_thresholds(self, new_thresholds: Dict[str, float]) -> None:
        """Update decision thresholds for tuning"""
        for key, value in new_thresholds.items():
            if hasattr(self, key):
                old_value = getattr(self, key)
                setattr(self, key, value)
                logger.info(f"Updated threshold {key}: {old_value:.3f} -> {value:.3f}")
            else:
                logger.warning(f"Unknown threshold key: {key}")

    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about recent decisions"""
        total = max(self.metrics.total_decisions, 1)

        return {
            "total_decisions": self.metrics.total_decisions,
            "decision_distribution": {
                "match": self.metrics.match_decisions / total,
                "no_match": self.metrics.no_match_decisions / total,
                "weak_match": self.metrics.weak_match_decisions / total,
                "needs_review": self.metrics.review_decisions / total,
            },
            "confidence_metrics": {
                "average_confidence": self.metrics.avg_confidence,
                "high_confidence_rate": self.metrics.high_confidence_decisions / total,
                "low_confidence_rate": self.metrics.low_confidence_decisions / total,
            },
            "performance_metrics": {
                "average_processing_time": self.metrics.avg_processing_time,
                "review_rate": self.metrics.review_decisions / total,
            },
            "thresholds": {
                "match_threshold": self.match_threshold,
                "weak_match_threshold": self.weak_match_threshold,
                "review_threshold": self.review_threshold,
                "no_match_threshold": self.no_match_threshold,
            }
        }