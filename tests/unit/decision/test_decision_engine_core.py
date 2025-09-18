"""
Unit tests for decision engine core functionality.

Tests deterministic scoring, thresholds, and decision logic
with 4 specific scenarios: skip, high, medium, and low risk.
"""

import pytest

from src.ai_service.contracts.decision_contracts import (
    DecisionInput,
    RiskLevel,
    SmartFilterInfo,
    SignalsInfo,
    SimilarityInfo,
)
from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.config.settings import DecisionConfig


class TestDecisionEngineCore:
    """Test core decision engine functionality with deterministic scoring"""
    
    def test_skip_scenario_smartfilter_false(self):
        """Test skip scenario when smartfilter.should_process is False"""
        engine = DecisionEngine()
        
        # Create input with should_process=False
        inp = DecisionInput(
            text="Test text",
            language="en",
            smartfilter=SmartFilterInfo(should_process=False, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.8),
            similarity=SimilarityInfo(cos_top=0.95)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Verify skip decision
        assert output.risk == RiskLevel.SKIP
        assert output.score == 0.0
        assert "smartfilter_skip" in output.reasons
        assert output.details["smartfilter_should_process"] is False
    
    def test_high_risk_scenario(self):
        """Test high risk scenario with high confidence signals and matches"""
        engine = DecisionEngine()
        
        # Create input with high confidence signals
        inp = DecisionInput(
            text="High risk person",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.9),
            signals=SignalsInfo(
                person_confidence=0.9,
                org_confidence=0.8,
                date_match=True,
                id_match=True
            ),
            similarity=SimilarityInfo(cos_top=0.92)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Verify high risk decision
        assert output.risk == RiskLevel.HIGH
        assert output.score >= 0.85  # Should be above high threshold
        
        # Verify contributing factors are mentioned in reasons
        assert any("person_evidence_strong" in reason for reason in output.reasons)
        assert any("org_evidence_strong" in reason for reason in output.reasons)
        assert any("high_vector_similarity" in reason for reason in output.reasons)
        assert any("id_exact_match" in reason for reason in output.reasons)
        assert any("dob_match" in reason for reason in output.reasons)
        
        # Verify details contain weights and thresholds
        assert "calculated_score" in output.details
        assert "weights_used" in output.details
        assert "thresholds" in output.details
        assert output.details["thresholds"]["thr_high"] == 0.85
        assert output.details["thresholds"]["thr_medium"] == 0.65
    
    def test_medium_risk_scenario(self):
        """Test medium risk scenario with moderate confidence signals"""
        engine = DecisionEngine()
        
        # Create input with moderate confidence signals
        inp = DecisionInput(
            text="Medium risk person",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
            signals=SignalsInfo(
                person_confidence=0.6,
                org_confidence=0.5,
                date_match=True,
                id_match=False
            ),
            similarity=SimilarityInfo(cos_top=0.7)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Verify medium risk decision
        assert output.risk == RiskLevel.MEDIUM
        assert 0.65 <= output.score < 0.85  # Should be between medium and high thresholds
        
        # Verify contributing factors are mentioned
        assert any("Person confidence" in reason for reason in output.reasons)
        assert any("Organization confidence" in reason for reason in output.reasons)
        assert any("Similarity match" in reason for reason in output.reasons)
        assert any("dob_match" in reason for reason in output.reasons)
        # ID match should not be mentioned since it's False
        assert not any("id_exact_match" in reason for reason in output.reasons)
    
    def test_low_risk_scenario(self):
        """Test low risk scenario with low confidence signals and no matches"""
        engine = DecisionEngine()
        
        # Create input with low confidence signals
        inp = DecisionInput(
            text="Low risk text",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.4),
            signals=SignalsInfo(
                person_confidence=0.2,
                org_confidence=0.1,
                date_match=False,
                id_match=False
            ),
            similarity=SimilarityInfo(cos_top=0.3)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Verify low risk decision
        assert output.risk == RiskLevel.LOW
        assert output.score < 0.65  # Should be below medium threshold
        
        # Verify no bonus factors are mentioned
        assert not any("ID match bonus applied" in reason for reason in output.reasons)
        assert not any("Date match bonus applied" in reason for reason in output.reasons)
        
        # Verify score calculation is deterministic
        expected_score = (
            0.25 * 0.4 +  # w_smartfilter * smartfilter.confidence
            0.3 * 0.2 +   # w_person * person_confidence
            0.15 * 0.1 +  # w_org * org_confidence
            0.25 * 0.3 +  # w_similarity * cos_top
            0.0 +         # no date match bonus
            0.0           # no id match bonus
        )
        assert abs(output.score - expected_score) < 0.001  # Allow for floating point precision
    
    def test_score_calculation_deterministic(self):
        """Test that score calculation is deterministic and matches expected formula"""
        engine = DecisionEngine()
        
        # Create input with known values
        inp = DecisionInput(
            text="Test",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(
                person_confidence=0.6,
                org_confidence=0.4,
                date_match=True,
                id_match=True
            ),
            similarity=SimilarityInfo(cos_top=0.7)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Calculate expected score manually
        expected_score = (
            0.25 * 0.8 +  # w_smartfilter * smartfilter.confidence
            0.3 * 0.6 +   # w_person * person_confidence
            0.15 * 0.4 +  # w_org * org_confidence
            0.25 * 0.7 +  # w_similarity * cos_top
            0.07 +        # bonus_date_match
            0.15          # bonus_id_match
        )
        
        # Verify calculated score matches expected
        assert abs(output.score - expected_score) < 0.001
        
        # Verify details contain the correct weights
        weights = output.details["weights_used"]
        assert weights["w_smartfilter"] == 0.25
        assert weights["w_person"] == 0.3
        assert weights["w_org"] == 0.15
        assert weights["w_similarity"] == 0.25
        assert weights["bonus_date_match"] == 0.07
        assert weights["bonus_id_match"] == 0.15
    
    def test_custom_config_weights(self):
        """Test decision engine with custom configuration weights"""
        # Create custom config with different weights
        custom_config = DecisionConfig(
            w_smartfilter=0.4,
            w_person=0.4,
            w_org=0.1,
            w_similarity=0.1,
            bonus_date_match=0.05,
            bonus_id_match=0.1,
            thr_high=0.9,
            thr_medium=0.7
        )
        
        engine = DecisionEngine(custom_config)
        
        # Create input
        inp = DecisionInput(
            text="Test",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.6, org_confidence=0.4),
            similarity=SimilarityInfo(cos_top=0.5)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Verify custom weights are used
        weights = output.details["weights_used"]
        assert weights["w_smartfilter"] == 0.4
        assert weights["w_person"] == 0.4
        assert weights["w_org"] == 0.1
        assert weights["w_similarity"] == 0.1
        assert weights["bonus_date_match"] == 0.05
        assert weights["bonus_id_match"] == 0.1
        
        # Verify custom thresholds are used
        thresholds = output.details["thresholds"]
        assert thresholds["thr_high"] == 0.9
        assert thresholds["thr_medium"] == 0.7
    
    def test_similarity_none_handling(self):
        """Test that None similarity values are handled correctly"""
        engine = DecisionEngine()
        
        # Create input with None similarity
        inp = DecisionInput(
            text="Test",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.6, org_confidence=0.4),
            similarity=SimilarityInfo(cos_top=None, cos_p95=None)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Verify score calculation handles None similarity correctly
        # Should use 0.0 for similarity contribution
        expected_score = (
            0.25 * 0.8 +  # w_smartfilter * smartfilter.confidence
            0.3 * 0.6 +   # w_person * person_confidence
            0.15 * 0.4 +  # w_org * org_confidence
            0.25 * 0.0 +  # w_similarity * 0 (None treated as 0)
            0.0 +         # no date match bonus
            0.0           # no id match bonus
        )
        
        assert abs(output.score - expected_score) < 0.001
