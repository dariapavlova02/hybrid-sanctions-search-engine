#!/usr/bin/env python3
"""
Unit tests for business gates (TIN/DOB requirement logic).

Tests the business rule:
- If strong name match but missing TIN/DOB → mark REVIEW and set required_additional_fields=['TIN','DOB']
- Exception: if sanction record has neither TIN nor DOB → allow reject by full name
"""

import pytest
from unittest.mock import Mock
from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.contracts.decision_contracts import (
    DecisionInput, DecisionOutput, RiskLevel, SmartFilterInfo, 
    SignalsInfo, SimilarityInfo
)
from src.ai_service.config.settings import DecisionConfig


class TestBusinessGates:
    """Test business gates for TIN/DOB requirement logic."""

    @pytest.fixture
    def decision_engine(self):
        """Create decision engine instance for testing."""
        config = DecisionConfig()
        config.require_tin_dob_gate = True
        return DecisionEngine(config=config)

    @pytest.fixture
    def base_input(self):
        """Create base decision input for testing."""
        return DecisionInput(
            text="John Smith",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=1.0),
            signals=SignalsInfo(
                person_confidence=0.0,
                org_confidence=0.0,
                evidence={}
            ),
            similarity=SimilarityInfo(cos_top=None)
        )

    @pytest.mark.parametrize("test_case", [
        # Test case: (name_match, has_tin, has_dob, sanction_has_identifiers, expected_review, expected_fields)
        {
            "name": "strong_match_with_tin_dob",
            "person_confidence": 0.9,
            "has_tin": True,
            "has_dob": True,
            "expected_review": False,
            "expected_fields": []
        },
        {
            "name": "strong_match_missing_tin",
            "person_confidence": 0.9,
            "has_tin": False,
            "has_dob": True,
            "expected_review": True,
            "expected_fields": ["TIN"]
        },
        {
            "name": "strong_match_missing_dob",
            "person_confidence": 0.9,
            "has_tin": True,
            "has_dob": False,
            "expected_review": True,
            "expected_fields": ["DOB"]
        },
        {
            "name": "strong_match_missing_both",
            "person_confidence": 0.9,
            "has_tin": False,
            "has_dob": False,
            "expected_review": True,
            "expected_fields": ["TIN", "DOB"]
        },
        {
            "name": "weak_match_no_review",
            "person_confidence": 0.5,
            "has_tin": False,
            "has_dob": False,
            "expected_review": False,
            "expected_fields": []
        },
        {
            "name": "sanction_no_identifiers_allow_reject",
            "person_confidence": 0.9,
            "has_tin": False,
            "has_dob": False,
            "sanction_has_identifiers": False,
            "expected_review": False,
            "expected_fields": []
        },
        {
            "name": "sanction_has_identifiers_require_fields",
            "person_confidence": 0.9,
            "has_tin": False,
            "has_dob": False,
            "sanction_has_identifiers": True,
            "expected_review": True,
            "expected_fields": ["TIN", "DOB"]
        }
    ])
    def test_tin_dob_business_gate(self, decision_engine, base_input, test_case):
        """Test TIN/DOB business gate logic with various scenarios."""
        # Setup input based on test case
        base_input.signals.person_confidence = test_case["person_confidence"]
        
        # Setup TIN/DOB evidence
        evidence = {}
        if test_case["has_tin"]:
            evidence["extracted_ids"] = ["inn"]
        if test_case["has_dob"]:
            evidence["extracted_dates"] = ["dob"]
        
        # Setup sanction record if specified
        if "sanction_has_identifiers" in test_case:
            evidence["sanction_record"] = {
                "has_tin": test_case["sanction_has_identifiers"],
                "has_dob": test_case["sanction_has_identifiers"]
            }
        
        base_input.signals.evidence = evidence
        
        # Create mock decision output with HIGH risk (required for business gate)
        mock_decision = DecisionOutput(
            risk=RiskLevel.HIGH,
            score=0.9,
            reasons=["strong_match"],
            details={}
        )
        
        # Test the business gate logic
        review_required, required_fields = decision_engine._should_request_additional_fields(
            base_input, RiskLevel.HIGH, 0.9
        )
        
        # Assertions
        assert review_required == test_case["expected_review"], (
            f"Test case '{test_case['name']}': expected review_required={test_case['expected_review']}, "
            f"got {review_required}"
        )
        assert required_fields == test_case["expected_fields"], (
            f"Test case '{test_case['name']}': expected fields={test_case['expected_fields']}, "
            f"got {required_fields}"
        )

    def test_gate_disabled(self, base_input):
        """Test that business gate is disabled when flag is False."""
        config = DecisionConfig()
        config.require_tin_dob_gate = False
        decision_engine = DecisionEngine(config=config)
        
        # Setup strong match without TIN/DOB
        base_input.signals.person_confidence = 0.9
        base_input.signals.evidence = {}
        
        review_required, required_fields = decision_engine._should_request_additional_fields(
            base_input, RiskLevel.HIGH, 0.9
        )
        
        assert review_required == False
        assert required_fields == []

    def test_low_risk_no_gate(self, decision_engine, base_input):
        """Test that business gate doesn't apply to low-risk decisions."""
        # Setup strong match without TIN/DOB
        base_input.signals.person_confidence = 0.9
        base_input.signals.evidence = {}
        
        review_required, required_fields = decision_engine._should_request_additional_fields(
            base_input, RiskLevel.LOW, 0.5
        )
        
        assert review_required == False
        assert required_fields == []

    def test_org_confidence_trigger(self, decision_engine, base_input):
        """Test that high org confidence triggers business gate."""
        # Setup high org confidence without TIN/DOB
        base_input.signals.org_confidence = 0.9
        base_input.signals.evidence = {}
        
        review_required, required_fields = decision_engine._should_request_additional_fields(
            base_input, RiskLevel.HIGH, 0.9
        )
        
        assert review_required == True
        assert required_fields == ["TIN", "DOB"]

    def test_similarity_trigger(self, decision_engine, base_input):
        """Test that high similarity triggers business gate."""
        # Setup high similarity without TIN/DOB
        base_input.similarity.cos_top = 0.9
        base_input.signals.evidence = {}
        
        review_required, required_fields = decision_engine._should_request_additional_fields(
            base_input, RiskLevel.HIGH, 0.9
        )
        
        assert review_required == True
        assert required_fields == ["TIN", "DOB"]

    def test_id_match_evidence(self, decision_engine, base_input):
        """Test that id_match signal counts as TIN evidence."""
        # Setup strong match with id_match but no extracted_ids
        base_input.signals.person_confidence = 0.9
        base_input.signals.id_match = True
        base_input.signals.evidence = {"extracted_dates": ["dob"]}
        
        review_required, required_fields = decision_engine._should_request_additional_fields(
            base_input, RiskLevel.HIGH, 0.9
        )
        
        assert review_required == False
        assert required_fields == []

    def test_date_match_evidence(self, decision_engine, base_input):
        """Test that date_match signal counts as DOB evidence."""
        # Setup strong match with date_match but no extracted_dates
        base_input.signals.person_confidence = 0.9
        base_input.signals.date_match = True
        base_input.signals.evidence = {"extracted_ids": ["inn"]}
        
        review_required, required_fields = decision_engine._should_request_additional_fields(
            base_input, RiskLevel.HIGH, 0.9
        )
        
        assert review_required == False
        assert required_fields == []

    def test_full_decision_flow(self, decision_engine, base_input):
        """Test the full decision flow with business gates."""
        # Setup strong match without TIN/DOB - need multiple high signals to trigger HIGH risk
        base_input.signals.person_confidence = 0.9
        base_input.signals.org_confidence = 0.9  # Add org confidence
        base_input.similarity.cos_top = 0.9  # High similarity
        base_input.signals.evidence = {}
        
        # Make decision
        result = decision_engine.decide(base_input)
        
        # Should be HIGH risk with review required
        assert result.risk == RiskLevel.HIGH
        assert result.review_required == True
        assert result.required_additional_fields == ["TIN", "DOB"]
        # The business gate is working - we have review_required and required_additional_fields

    def test_response_formatter_integration(self):
        """Test that response formatter includes business gate fields."""
        from src.ai_service.utils.response_formatter import _get_review_required, _get_required_additional_fields
        
        # Test with review required
        decision_with_review = DecisionOutput(
            risk=RiskLevel.HIGH,
            score=0.9,
            reasons=["strong_match"],
            details={},
            review_required=True,
            required_additional_fields=["TIN", "DOB"]
        )
        
        assert _get_review_required(decision_with_review) == True
        assert _get_required_additional_fields(decision_with_review) == ["TIN", "DOB"]
        
        # Test with no review required
        decision_no_review = DecisionOutput(
            risk=RiskLevel.LOW,
            score=0.3,
            reasons=["weak_match"],
            details={},
            review_required=False,
            required_additional_fields=[]
        )
        
        assert _get_review_required(decision_no_review) == False
        assert _get_required_additional_fields(decision_no_review) == []
        
        # Test with None decision
        assert _get_review_required(None) == False
        assert _get_required_additional_fields(None) == []


# Test runner
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
