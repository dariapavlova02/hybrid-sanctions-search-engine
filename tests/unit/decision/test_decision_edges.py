"""
Unit tests for decision engine edge cases and robust handling.

Tests robust handling of None/empty evidence and missing fields
to ensure the decision engine works reliably even with incomplete data.
"""

import pytest
from unittest.mock import Mock

from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.contracts.decision_contracts import (
    DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo, RiskLevel
)


class TestDecisionEngineEdgeCases:
    """Test decision engine robust handling of edge cases"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = DecisionEngine()
    
    def test_none_smartfilter_defaults_to_process_true(self):
        """Test that None smartfilter defaults to should_process=True, confidence=0"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=None,
            signals=SignalsInfo(person_confidence=0.0, org_confidence=0.0),
            similarity=SimilarityInfo()
        )
        
        result = self.engine.decide(inp)
        
        # Should not skip (should_process=True by default)
        assert result.risk != RiskLevel.SKIP
        assert result.risk == RiskLevel.LOW  # Low confidence = low risk
        assert result.score == 0.0  # Only smartfilter contribution (0.25 * 0.0)
        assert "Overall risk score: 0.000" in result.reasons
    
    def test_none_signals_defaults_to_zero_confidence(self):
        """Test that None signals defaults to zero confidence values"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
            signals=None,
            similarity=SimilarityInfo()
        )
        
        result = self.engine.decide(inp)
        
        # Should have smartfilter contribution only
        expected_score = 0.25 * 0.5  # w_smartfilter * confidence
        assert abs(result.score - expected_score) < 0.001
        assert result.risk == RiskLevel.LOW
        assert "Overall risk score:" in result.reasons[0]
    
    def test_none_similarity_defaults_to_zero_contribution(self):
        """Test that None similarity defaults to zero contribution"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
            signals=SignalsInfo(person_confidence=0.3, org_confidence=0.2),
            similarity=None
        )
        
        result = self.engine.decide(inp)
        
        # Should have smartfilter + person + org contributions
        expected_score = (0.25 * 0.5) + (0.3 * 0.3) + (0.15 * 0.2)  # No similarity contribution
        assert abs(result.score - expected_score) < 0.001
        assert result.risk == RiskLevel.LOW
    
    def test_all_none_evidence_results_in_low_risk(self):
        """Test that all None evidence results in LOW risk with minimal score"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=None,
            signals=None,
            similarity=None
        )
        
        result = self.engine.decide(inp)
        
        # Should have only smartfilter contribution (0.25 * 0.0 = 0.0)
        assert result.score == 0.0
        assert result.risk == RiskLevel.LOW
        assert "Overall risk score: 0.000" in result.reasons
        assert len(result.reasons) >= 2  # At least score + risk level
    
    def test_none_confidence_values_default_to_zero(self):
        """Test that None confidence values default to zero"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=None),
            signals=SignalsInfo(person_confidence=None, org_confidence=None),
            similarity=SimilarityInfo(cos_top=None)
        )
        
        result = self.engine.decide(inp)
        
        # All contributions should be zero
        assert result.score == 0.0
        assert result.risk == RiskLevel.LOW
        assert "Overall risk score: 0.000" in result.reasons
    
    def test_none_boolean_flags_default_to_false(self):
        """Test that None boolean flags default to False"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
            signals=SignalsInfo(
                person_confidence=0.3,
                org_confidence=0.2,
                date_match=None,
                id_match=None
            ),
            similarity=SimilarityInfo()
        )
        
        result = self.engine.decide(inp)
        
        # Should not have date or ID bonuses
        expected_score = (0.25 * 0.5) + (0.3 * 0.3) + (0.15 * 0.2)  # No bonuses
        assert abs(result.score - expected_score) < 0.001
        assert result.risk == RiskLevel.LOW
        assert "dob_match" not in result.reasons
        assert "id_exact_match" not in result.reasons
    
    def test_none_evidence_dict_defaults_to_empty(self):
        """Test that None evidence dict defaults to empty dict"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
            signals=SignalsInfo(
                person_confidence=0.3,
                org_confidence=0.2,
                evidence=None
            ),
            similarity=SimilarityInfo()
        )
        
        result = self.engine.decide(inp)
        
        # Should work without errors
        assert result.risk == RiskLevel.LOW
        assert result.score > 0.0
        assert "input_signals" in result.details
        assert result.details["input_signals"]["evidence_count"] == 0
    
    def test_smartfilter_should_process_none_defaults_to_true(self):
        """Test that None should_process defaults to True"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=None, confidence=0.5),
            signals=SignalsInfo(person_confidence=0.0, org_confidence=0.0),
            similarity=SimilarityInfo()
        )
        
        result = self.engine.decide(inp)
        
        # Should not skip (should_process=True by default)
        assert result.risk != RiskLevel.SKIP
        assert result.risk == RiskLevel.LOW
        assert result.score == 0.25 * 0.5  # Only smartfilter contribution
    
    def test_mixed_none_values_handled_gracefully(self):
        """Test that mixed None values are handled gracefully"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.6),
            signals=SignalsInfo(
                person_confidence=0.4,
                org_confidence=None,  # None value
                date_match=True,
                id_match=None  # None value
            ),
            similarity=SimilarityInfo(cos_top=0.3, cos_p95=None)
        )
        
        result = self.engine.decide(inp)
        
        # Should work without errors
        assert result.risk == RiskLevel.LOW
        assert result.score > 0.0
        
        # Should have person contribution but not org
        expected_score = (0.25 * 0.6) + (0.3 * 0.4) + (0.15 * 0.0) + (0.25 * 0.3) + 0.07  # date bonus
        assert abs(result.score - expected_score) < 0.001
        
        # Should have date match but not ID match
        assert "dob_match" in result.reasons
        assert "id_exact_match" not in result.reasons
    
    def test_empty_text_handled_gracefully(self):
        """Test that empty text is handled gracefully"""
        inp = DecisionInput(
            text="",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
            signals=SignalsInfo(person_confidence=0.0, org_confidence=0.0),
            similarity=SimilarityInfo()
        )
        
        result = self.engine.decide(inp)
        
        # Should work without errors
        assert result.risk == RiskLevel.LOW
        assert result.score == 0.25 * 0.5  # Only smartfilter contribution
        assert "Overall risk score:" in result.reasons[0]
    
    def test_very_high_confidence_with_none_other_values(self):
        """Test that high confidence values work even with None other values"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.9),
            signals=SignalsInfo(person_confidence=0.8, org_confidence=None),
            similarity=None
        )
        
        result = self.engine.decide(inp)
        
        # Should have high score due to high confidence values
        expected_score = (0.25 * 0.9) + (0.3 * 0.8) + (0.15 * 0.0)  # No org, no similarity
        assert abs(result.score - expected_score) < 0.001
        # Score should be 0.465, which is below MEDIUM threshold (0.65), so LOW is correct
        assert result.risk == RiskLevel.LOW  # 0.465 < 0.65 threshold
        assert "strong_smartfilter_signal" in result.reasons
        assert "person_evidence_strong" in result.reasons
    
    def test_skip_decision_with_none_values(self):
        """Test that skip decision works even with None values"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=False, confidence=None),
            signals=None,
            similarity=None
        )
        
        result = self.engine.decide(inp)
        
        # Should skip regardless of other values
        assert result.risk == RiskLevel.SKIP
        assert result.score == 0.0
        assert "smartfilter_skip" in result.reasons
        assert len(result.details) > 0
    
    def test_details_contain_safe_values(self):
        """Test that details contain safe values even with None inputs"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=None,
            signals=None,
            similarity=None
        )
        
        result = self.engine.decide(inp)
        
        # Details should contain safe values
        assert "normalized_features" in result.details
        assert "evidence_strength" in result.details
        assert "score_breakdown" in result.details
        assert "input_signals" in result.details
        
        # All values should be safe (no None values)
        normalized = result.details["normalized_features"]
        assert normalized["smartfilter_confidence"] == 0.0
        assert normalized["person_confidence"] == 0.0
        assert normalized["org_confidence"] == 0.0
        assert normalized["similarity_cos_top"] == 0.0
        assert normalized["date_match"] is False
        assert normalized["id_match"] is False
        
        # Evidence count should be 0 for None evidence
        assert result.details["input_signals"]["evidence_count"] == 0
    
    def test_evidence_strength_indicators_with_none_values(self):
        """Test that evidence strength indicators work with None values"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=None),
            similarity=SimilarityInfo(cos_top=0.95)
        )
        
        result = self.engine.decide(inp)
        
        # Evidence strength should be calculated correctly
        evidence_strength = result.details["evidence_strength"]
        assert evidence_strength["smartfilter_strong"] is True  # 0.8 >= 0.7
        assert evidence_strength["person_strong"] is True  # 0.9 >= 0.7
        assert evidence_strength["org_strong"] is False  # None -> 0.0 < 0.7
        assert evidence_strength["similarity_high"] is True  # 0.95 >= 0.9
        assert evidence_strength["exact_id_match"] is False  # None -> False
        assert evidence_strength["exact_dob_match"] is False  # None -> False
    
    def test_score_breakdown_with_none_values(self):
        """Test that score breakdown is calculated correctly with None values"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.6),
            signals=SignalsInfo(person_confidence=0.4, org_confidence=None),
            similarity=SimilarityInfo(cos_top=None)
        )
        
        result = self.engine.decide(inp)
        
        # Score breakdown should be calculated correctly
        breakdown = result.details["score_breakdown"]
        assert breakdown["smartfilter_contribution"] == 0.25 * 0.6
        assert breakdown["person_contribution"] == 0.3 * 0.4
        assert breakdown["org_contribution"] == 0.15 * 0.0  # None -> 0.0
        assert breakdown["similarity_contribution"] == 0.25 * 0.0  # None -> 0.0
        assert breakdown["date_bonus"] == 0.0  # None -> False
        assert breakdown["id_bonus"] == 0.0  # None -> False
        
        # Total should match calculated score
        expected_total = breakdown["smartfilter_contribution"] + breakdown["person_contribution"]
        assert abs(breakdown["total"] - expected_total) < 0.001
    
    def test_reasons_generation_with_none_values(self):
        """Test that reasons are generated correctly with None values"""
        inp = DecisionInput(
            text="John Doe",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=None),
            similarity=SimilarityInfo(cos_top=0.95)
        )
        
        result = self.engine.decide(inp)
        
        # Should have appropriate reasons
        assert "Overall risk score:" in result.reasons[0]
        assert "strong_smartfilter_signal" in result.reasons
        assert "person_evidence_strong" in result.reasons
        assert "high_vector_similarity" in result.reasons
        assert "org_evidence_strong" not in result.reasons  # None -> 0.0
        assert "id_exact_match" not in result.reasons  # None -> False
        assert "dob_match" not in result.reasons  # None -> False
    
    def test_decision_engine_never_raises_exceptions(self):
        """Test that decision engine never raises exceptions with None values"""
        # Test various combinations of None values
        test_cases = [
            DecisionInput(text="", smartfilter=None, signals=None, similarity=None),
            DecisionInput(text="John", smartfilter=SmartFilterInfo(should_process=None, confidence=None), signals=None, similarity=None),
            DecisionInput(text="Jane", smartfilter=None, signals=SignalsInfo(person_confidence=None, org_confidence=None), similarity=None),
            DecisionInput(text="Bob", smartfilter=None, signals=None, similarity=SimilarityInfo(cos_top=None, cos_p95=None)),
        ]
        
        for inp in test_cases:
            # Should never raise an exception
            result = self.engine.decide(inp)
            
            # Should always return a valid result
            assert result.risk in [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.SKIP]
            assert 0.0 <= result.score <= 1.0
            assert isinstance(result.reasons, list)
            assert isinstance(result.details, dict)
            assert len(result.reasons) > 0
