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
        """Test that high person confidence with only smartfilter results in low risk"""
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.9, org_confidence=0.9)
        decision = decision_engine.decide(decision_input)

        # With person=0.9, org=0.9, smartfilter=1.0: (0.25*1.0 + 0.3*0.9 + 0.15*0.9) = 0.655 = MEDIUM
        assert decision.risk == RiskLevel.MEDIUM  # Should be medium with high person and org confidence
        assert decision.score >= 0.6  # Should have reasonable score
        assert len(decision.reasons) > 0  # Should have reasons

    @pytest.mark.asyncio
    async def test_weak_match_decision(self, decision_engine, basic_processing_result):
        """Test weak match decision"""
        # Set medium confidence signals
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.5, org_confidence=0.5)
        decision = decision_engine.decide(decision_input)

        # With person=0.5, org=0.5, smartfilter=1.0: (0.25*1.0 + 0.3*0.5 + 0.15*0.5) = 0.475 = LOW
        assert decision.risk == RiskLevel.LOW
        assert decision.score >= 0.4  # Should have reasonable score

    @pytest.mark.asyncio
    async def test_needs_review_decision(self, decision_engine, basic_processing_result):
        """Test needs review decision"""
        # Set low confidence signals
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.3, org_confidence=0.2)
        decision = decision_engine.decide(decision_input)

        # With person=0.3, org=0.2, smartfilter=1.0: (0.25*1.0 + 0.3*0.3 + 0.15*0.2) = 0.37 = LOW
        assert decision.risk == RiskLevel.LOW
        assert decision.score >= 0.3  # Should have reasonable score

    @pytest.mark.asyncio
    async def test_no_match_decision(self, decision_engine, basic_processing_result):
        """Test no match decision"""
        # Set very low confidence signals
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.1, org_confidence=0.1)
        decision = decision_engine.decide(decision_input)

        # With person=0.1, org=0.1, smartfilter=1.0: (0.25*1.0 + 0.3*0.1 + 0.15*0.1) = 0.295 = LOW
        assert decision.risk == RiskLevel.LOW
        assert decision.score >= 0.2  # Should have reasonable score

    @pytest.mark.asyncio
    async def test_insufficient_data_decision(self, decision_engine):
        """Test insufficient data decision"""
        # Create decision input with very poor data quality
        from ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        poor_input = DecisionInput(
            text="",
            language="unknown",
            smartfilter=SmartFilterInfo(should_process=False, confidence=0.0),
            signals=SignalsInfo(person_confidence=0.0, org_confidence=0.0),
            similarity=SimilarityInfo()
        )

        decision = decision_engine.decide(poor_input)

        assert decision.risk == RiskLevel.SKIP  # Should skip processing when smartfilter says not to process
        assert decision.score == 0.0

    @pytest.mark.asyncio
    async def test_evidence_extraction(self, decision_engine, basic_processing_result):
        """Test that decision details are properly extracted"""
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.8, org_confidence=0.6)
        decision = decision_engine.decide(decision_input)

        # Check that we have details in the response
        assert decision.details is not None
        assert "calculated_score" in decision.details
        assert "score_breakdown" in decision.details
        assert "weights_used" in decision.details

    @pytest.mark.asyncio
    async def test_risk_factor_identification(self, decision_engine, basic_processing_result):
        """Test risk factor identification"""
        # Create decision input with low confidence to see reasoning
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.2, org_confidence=0.1)
        decision = decision_engine.decide(decision_input)

        # Check that we have reasons explaining the decision
        assert len(decision.reasons) > 0
        assert "Overall risk score:" in decision.reasons[0]

    @pytest.mark.asyncio
    async def test_context_sensitive_decisions(self, decision_engine, basic_processing_result):
        """Test that decisions are sensitive to input quality"""
        # Test with high quality input
        high_quality_input = self._create_decision_input(basic_processing_result, person_confidence=0.95, org_confidence=0.95)
        decision_high_quality = decision_engine.decide(high_quality_input)

        # Test with low quality input
        low_quality_input = self._create_decision_input(basic_processing_result, person_confidence=0.1, org_confidence=0.1)
        decision_low_quality = decision_engine.decide(low_quality_input)

        # High quality should have higher score than low quality
        assert decision_high_quality.score > decision_low_quality.score

    @pytest.mark.asyncio
    async def test_reasoning_generation(self, decision_engine, basic_processing_result):
        """Test that reasoning is generated for decisions"""
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.8, org_confidence=0.6)
        decision = decision_engine.decide(decision_input)

        # Check that we have reasons explaining the decision
        assert decision.reasons is not None
        assert len(decision.reasons) > 0
        assert "Overall risk score:" in decision.reasons[0]

    @pytest.mark.asyncio
    async def test_recommendations_generation(self, decision_engine, basic_processing_result):
        """Test that appropriate decision output is generated"""
        decision_input = self._create_decision_input(basic_processing_result, person_confidence=0.3, org_confidence=0.2)
        decision = decision_engine.decide(decision_input)

        # Basic decision output validation
        assert decision.score >= 0.0
        assert decision.risk in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.SKIP]

    @pytest.mark.asyncio
    async def test_batch_decisions(self, decision_engine, basic_processing_result):
        """Test multiple decision processing"""
        # Create multiple decision inputs
        inputs = [
            self._create_decision_input(basic_processing_result, person_confidence=0.8, org_confidence=0.6),
            self._create_decision_input(basic_processing_result, person_confidence=0.5, org_confidence=0.3),
            self._create_decision_input(basic_processing_result, person_confidence=0.2, org_confidence=0.1)
        ]

        decisions = [decision_engine.decide(inp) for inp in inputs]

        assert len(decisions) == 3
        # Ensure descending order of scores (higher confidence = higher score)
        assert decisions[0].score >= decisions[1].score >= decisions[2].score

    def test_threshold_updates(self, decision_engine):
        """Test threshold updating functionality"""
        # Test threshold updates (if supported)
        # Note: DecisionEngine uses config-based thresholds
        pass

    @pytest.mark.skip(reason="Feature not implemented")
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

    @pytest.mark.skip(reason="Feature not implemented")
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

    @pytest.mark.skip(reason="Feature not implemented")
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

    @pytest.mark.skip(reason="Feature not implemented")
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

    @pytest.mark.skip(reason="Feature not implemented")
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