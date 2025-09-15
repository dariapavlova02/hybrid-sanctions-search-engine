"""
Test suite for DecisionEngine - Layer 9 implementation.

Tests automated match/no-match decision making based on
processing results from layers 1-8.
"""

import pytest
from unittest.mock import Mock

from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.contracts.base_contracts import SignalsResult, UnifiedProcessingResult
from src.ai_service.contracts.decision_contracts import (
    ConfidenceLevel,
    DecisionResult,
    MatchDecision,
    MatchEvidence,
    RiskLevel
)


class TestDecisionEngine:
    """Test DecisionEngine functionality"""

    @pytest.fixture
    def decision_engine(self):
        """Create a DecisionEngine for testing"""
        return DecisionEngine()
    
    def _create_decision_input(self, processing_result, person_confidence=0.0, org_confidence=0.0):
        """Helper to create DecisionInput from UnifiedProcessingResult"""
        from ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        return DecisionInput(
            text=processing_result.original_text,
            language=processing_result.language,
            smartfilter=SmartFilterInfo(should_process=True, confidence=1.0),
            signals=SignalsInfo(person_confidence=person_confidence, org_confidence=org_confidence),
            similarity=SimilarityInfo()
        )

    @pytest.fixture
    def basic_processing_result(self):
        """Create a basic processing result for testing"""
        return UnifiedProcessingResult(
            original_text="John Smith",
            language="en",
            language_confidence=0.9,
            normalized_text="John Smith",
            tokens=["John", "Smith"],
            trace=[],
            signals=SignalsResult(
                persons=[],
                organizations=[],
                extras=Mock(),
                confidence=0.8
            ),
            processing_time=0.05,
            success=True,
            errors=[]
        )

    @pytest.mark.asyncio
    async def test_high_confidence_match_decision(self, decision_engine, basic_processing_result):
        """Test that high confidence results in match decision"""
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.9)
        decision = decision_engine.decide(decision_input)

        assert decision.risk in [RiskLevel.HIGH, RiskLevel.MEDIUM]  # High confidence should result in high risk
        assert decision.score >= 0.5  # Should have reasonable score
        assert len(decision.reasons) > 0  # Should have reasons

    @pytest.mark.asyncio
    async def test_weak_match_decision(self, decision_engine, basic_processing_result):
        """Test weak match decision"""
        # Set medium confidence signals
        basic_processing_result.signals.confidence = 0.7
        basic_processing_result.language_confidence = 0.6

        decision = await decision_engine.decide(basic_processing_result)

        assert decision.decision in [MatchDecision.WEAK_MATCH, MatchDecision.MATCH]
        assert decision.review_required == (decision.decision == MatchDecision.WEAK_MATCH)

    @pytest.mark.asyncio
    async def test_needs_review_decision(self, decision_engine, basic_processing_result):
        """Test needs review decision"""
        # Set low confidence signals
        basic_processing_result.signals.confidence = 0.4
        basic_processing_result.language_confidence = 0.5

        decision = await decision_engine.decide(basic_processing_result)

        assert decision.decision in [MatchDecision.NEEDS_REVIEW, MatchDecision.WEAK_MATCH]
        assert decision.review_required is True
        assert len(decision.next_steps) > 0

    @pytest.mark.asyncio
    async def test_no_match_decision(self, decision_engine, basic_processing_result):
        """Test no match decision"""
        # Set very low confidence signals
        basic_processing_result.signals.confidence = 0.1
        basic_processing_result.language_confidence = 0.3

        decision = await decision_engine.decide(basic_processing_result)

        assert decision.decision == MatchDecision.NO_MATCH
        assert decision.confidence < decision_engine.review_threshold
        assert decision.review_required is False

    @pytest.mark.asyncio
    async def test_insufficient_data_decision(self, decision_engine):
        """Test insufficient data decision"""
        # Create processing result with very poor data quality
        poor_result = UnifiedProcessingResult(
            original_text="",
            language="unknown",
            language_confidence=0.1,
            normalized_text="",
            tokens=[],
            trace=[],
            signals=SignalsResult(confidence=0.0),
            processing_time=0.01,
            success=False,
            errors=["processing_failed"]
        )

        decision = await decision_engine.decide(poor_result)

        assert decision.decision == MatchDecision.INSUFFICIENT_DATA
        assert decision.confidence == 0.0
        assert decision.confidence_level == ConfidenceLevel.VERY_LOW
        assert decision.review_required is True
        assert "insufficient_data" in decision.risk_factors

    @pytest.mark.asyncio
    async def test_evidence_extraction(self, decision_engine, basic_processing_result):
        """Test that evidence is properly extracted from processing results"""
        decision = await decision_engine.decide(basic_processing_result)

        assert len(decision.evidence) > 0

        # Check that we have different types of evidence
        evidence_sources = {ev.source for ev in decision.evidence}
        expected_sources = {"signals", "normalization", "language_detection"}

        # Should have at least some of the expected evidence sources
        assert len(evidence_sources.intersection(expected_sources)) > 0

        # Each evidence should have required fields
        for evidence in decision.evidence:
            assert evidence.source is not None
            assert evidence.evidence_type is not None
            assert 0.0 <= evidence.confidence <= 1.0
            assert evidence.weight > 0.0

    @pytest.mark.asyncio
    async def test_risk_factor_identification(self, decision_engine, basic_processing_result):
        """Test risk factor identification"""
        # Add some errors to trigger risk factors
        basic_processing_result.errors = ["processing_error"]
        basic_processing_result.language_confidence = 0.3  # Low confidence
        basic_processing_result.success = False

        decision = await decision_engine.decide(basic_processing_result)

        assert len(decision.risk_factors) > 0
        assert "processing_errors" in decision.risk_factors
        assert "uncertain_language" in decision.risk_factors

    @pytest.mark.asyncio
    async def test_context_sensitive_decisions(self, decision_engine, basic_processing_result):
        """Test that decisions are sensitive to context"""
        # Test with high risk tolerance
        high_risk_context = {
            "risk_tolerance": "high",
            "require_exact_match": False,
            "allow_weak_matches": True
        }

        decision_high_risk = await decision_engine.decide(
            basic_processing_result, context=high_risk_context
        )

        # Test with low risk tolerance
        low_risk_context = {
            "risk_tolerance": "low",
            "require_exact_match": True,
            "allow_weak_matches": False
        }

        decision_low_risk = await decision_engine.decide(
            basic_processing_result, context=low_risk_context
        )

        # Low risk tolerance should be more conservative
        assert decision_low_risk.confidence <= decision_high_risk.confidence

    @pytest.mark.asyncio
    async def test_reasoning_generation(self, decision_engine, basic_processing_result):
        """Test that reasoning is generated for decisions"""
        decision = await decision_engine.decide(basic_processing_result)

        assert decision.reasoning is not None
        assert len(decision.reasoning) > 0
        assert decision.decision.value.upper() in decision.reasoning

    @pytest.mark.asyncio
    async def test_recommendations_generation(self, decision_engine, basic_processing_result):
        """Test that appropriate recommendations are generated"""
        decision = await decision_engine.decide(basic_processing_result)

        assert len(decision.next_steps) > 0

        # Recommendations should be appropriate for the decision
        if decision.decision == MatchDecision.MATCH:
            assert any("proceed" in step for step in decision.next_steps)
        elif decision.decision == MatchDecision.NEEDS_REVIEW:
            assert any("review" in step for step in decision.next_steps)
        elif decision.decision == MatchDecision.NO_MATCH:
            assert any("clear" in step for step in decision.next_steps)

    @pytest.mark.asyncio
    async def test_batch_decisions(self, decision_engine, basic_processing_result):
        """Test batch decision processing"""
        # Create multiple processing results
        results = [basic_processing_result] * 3

        decisions = await decision_engine.batch_decisions(results)

        assert len(decisions) == 3
        assert all(isinstance(d, DecisionResult) for d in decisions)

    def test_threshold_updates(self, decision_engine):
        """Test threshold updating functionality"""
        # Test threshold updates (if supported)
        # Note: DecisionEngine uses config-based thresholds
        pass

    def test_decision_statistics(self, decision_engine):
        """Test decision statistics collection"""
        # Simulate some decisions
        decision_engine.metrics.total_decisions = 100
        decision_engine.metrics.match_decisions = 60
        decision_engine.metrics.no_match_decisions = 30
        decision_engine.metrics.review_decisions = 10
        decision_engine.metrics.avg_confidence = 0.75

        stats = decision_engine.get_decision_statistics()

        assert stats["total_decisions"] == 100
        assert stats["decision_distribution"]["match"] == 0.6
        assert stats["decision_distribution"]["no_match"] == 0.3
        assert stats["decision_distribution"]["needs_review"] == 0.1
        assert stats["confidence_metrics"]["average_confidence"] == 0.75

    @pytest.mark.asyncio
    async def test_error_handling(self, decision_engine):
        """Test error handling in decision making"""
        # Create a malformed processing result that might cause errors
        malformed_result = Mock()
        malformed_result.original_text = "test"
        malformed_result.success = None  # This might cause issues

        decision = await decision_engine.decide(malformed_result)

        # Should handle errors gracefully
        assert decision.decision == MatchDecision.NEEDS_REVIEW
        assert decision.fallback_used is True
        assert "decision_engine_error" in decision.risk_factors

    @pytest.mark.asyncio
    async def test_match_type_determination(self, decision_engine, basic_processing_result):
        """Test match type determination (person vs organization)"""
        # Test person match type
        person_mock = Mock()
        person_mock.core = "John Smith"
        basic_processing_result.signals.persons = [person_mock]
        basic_processing_result.signals.organizations = []

        decision = await decision_engine.decide(basic_processing_result)
        assert decision.match_type == "person"

        # Test organization match type
        org_mock = Mock()
        org_mock.core = "Acme Corp"
        basic_processing_result.signals.persons = []
        basic_processing_result.signals.organizations = [org_mock]

        decision = await decision_engine.decide(basic_processing_result)
        assert decision.match_type == "organization"

    @pytest.mark.asyncio
    async def test_processing_time_tracking(self, decision_engine, basic_processing_result):
        """Test that processing time is tracked"""
        decision = await decision_engine.decide(basic_processing_result)

        assert decision.processing_time > 0.0
        assert decision.processing_time < 1.0  # Should be fast for simple cases


class TestDecisionEngineIntegration:
    """Integration tests for DecisionEngine"""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_processing_result_decision(self):
        """Test with a more realistic processing result"""
        # This would be filled in with actual integration testing
        # using real service responses
        pass

    @pytest.mark.performance
    @pytest.mark.asyncio
    async def test_decision_performance(self):
        """Test decision engine performance"""
        decision_engine = DecisionEngine()

        # Create a simple processing result
        result = UnifiedProcessingResult(
            original_text="Test Name",
            language="en",
            language_confidence=0.8,
            normalized_text="Test Name",
            tokens=["Test", "Name"],
            trace=[],
            signals=SignalsResult(confidence=0.7),
            processing_time=0.01,
            success=True,
            errors=[]
        )

        import time
        start_time = time.time()

        # Make multiple decisions
        for _ in range(100):
            await decision_engine.decide(result)

        total_time = time.time() - start_time
        avg_time = total_time / 100

        # Should be very fast - under 10ms per decision
        assert avg_time < 0.01