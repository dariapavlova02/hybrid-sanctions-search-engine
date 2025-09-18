"""
Unit tests for decision explanation functionality.

Tests human-readable reasons generation and detailed audit trail
in DecisionEngine output.
"""

import pytest
from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.contracts.decision_contracts import (
    DecisionInput, DecisionOutput, RiskLevel, SmartFilterInfo, SignalsInfo, SimilarityInfo
)
from src.ai_service.config.settings import DecisionConfig


class TestDecisionExplanation:
    """Test decision explanation and audit trail functionality"""
    
    @pytest.fixture
    def default_config(self):
        """Default decision configuration"""
        return DecisionConfig()
    
    @pytest.fixture
    def decision_engine(self, default_config):
        """Decision engine with default configuration"""
        return DecisionEngine(config=default_config)
    
    def create_decision_input(
        self,
        should_process: bool = True,
        sf_confidence: float = 0.0,
        person_conf: float = 0.0,
        org_conf: float = 0.0,
        cos_top: float = None,
        date_match: bool = None,
        id_match: bool = None,
        text: str = "test text",
        lang: str = "en"
    ) -> DecisionInput:
        """Helper to create DecisionInput with specified parameters"""
        return DecisionInput(
            text=text,
            language=lang,
            smartfilter=SmartFilterInfo(should_process=should_process, confidence=sf_confidence),
            signals=SignalsInfo(
                person_confidence=person_conf,
                org_confidence=org_conf,
                date_match=date_match,
                id_match=id_match
            ),
            similarity=SimilarityInfo(cos_top=cos_top)
        )
    
    def test_strong_smartfilter_signal_reason(self, decision_engine):
        """Test that strong smart filter signal generates correct reason"""
        inp = self.create_decision_input(sf_confidence=0.8)
        output = decision_engine.decide(inp)
        
        assert "strong_smartfilter_signal" in output.reasons
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_person_evidence_strong_reason(self, decision_engine):
        """Test that strong person evidence generates correct reason"""
        inp = self.create_decision_input(person_conf=0.8)
        output = decision_engine.decide(inp)
        
        assert "person_evidence_strong" in output.reasons
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_org_evidence_strong_reason(self, decision_engine):
        """Test that strong organization evidence generates correct reason"""
        inp = self.create_decision_input(org_conf=0.8)
        output = decision_engine.decide(inp)
        
        assert "org_evidence_strong" in output.reasons
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_high_vector_similarity_reason(self, decision_engine):
        """Test that high vector similarity generates correct reason"""
        inp = self.create_decision_input(cos_top=0.95)
        output = decision_engine.decide(inp)
        
        assert "high_vector_similarity" in output.reasons
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_id_exact_match_reason(self, decision_engine):
        """Test that ID exact match generates correct reason"""
        inp = self.create_decision_input(id_match=True)
        output = decision_engine.decide(inp)
        
        assert "id_exact_match" in output.reasons
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_dob_match_reason(self, decision_engine):
        """Test that date of birth match generates correct reason"""
        inp = self.create_decision_input(date_match=True)
        output = decision_engine.decide(inp)
        
        assert "dob_match" in output.reasons
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_multiple_strong_evidence_reasons(self, decision_engine):
        """Test multiple strong evidence indicators generate all expected reasons"""
        inp = self.create_decision_input(
            sf_confidence=0.8,
            person_conf=0.8,
            org_conf=0.8,
            cos_top=0.95,
            id_match=True,
            date_match=True
        )
        output = decision_engine.decide(inp)
        
        expected_reasons = [
            "strong_smartfilter_signal",
            "person_evidence_strong",
            "org_evidence_strong",
            "high_vector_similarity",
            "id_exact_match",
            "dob_match"
        ]
        
        for reason in expected_reasons:
            assert reason in output.reasons, f"Expected reason '{reason}' not found in {output.reasons}"
        
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_moderate_evidence_fallback_reasons(self, decision_engine):
        """Test that moderate evidence generates fallback descriptive reasons"""
        inp = self.create_decision_input(
            sf_confidence=0.6,  # Between 0.5 and 0.7
            person_conf=0.5,    # Between 0.3 and 0.7
            org_conf=0.5,       # Between 0.3 and 0.7
            cos_top=0.7         # Between 0.5 and 0.9
        )
        output = decision_engine.decide(inp)
        
        # Should have descriptive reasons instead of strong evidence markers
        assert any("Smart filter confidence:" in reason for reason in output.reasons)
        assert any("Person confidence:" in reason for reason in output.reasons)
        assert any("Organization confidence:" in reason for reason in output.reasons)
        assert any("Similarity match:" in reason for reason in output.reasons)
        
        # Should not have strong evidence markers
        assert "strong_smartfilter_signal" not in output.reasons
        assert "person_evidence_strong" not in output.reasons
        assert "org_evidence_strong" not in output.reasons
        assert "high_vector_similarity" not in output.reasons
    
    def test_low_evidence_no_strong_reasons(self, decision_engine):
        """Test that low evidence does not generate strong evidence reasons"""
        inp = self.create_decision_input(
            sf_confidence=0.3,  # Below 0.5
            person_conf=0.2,    # Below 0.3
            org_conf=0.2,       # Below 0.3
            cos_top=0.3         # Below 0.5
        )
        output = decision_engine.decide(inp)
        
        # Should not have any strong evidence markers
        assert "strong_smartfilter_signal" not in output.reasons
        assert "person_evidence_strong" not in output.reasons
        assert "org_evidence_strong" not in output.reasons
        assert "high_vector_similarity" not in output.reasons
        
        # Should still have basic reasons
        assert any("Overall risk score:" in reason for reason in output.reasons)
        assert any("Risk level:" in reason for reason in output.reasons)
    
    def test_score_breakdown_in_details(self, decision_engine):
        """Test that score breakdown is included in details"""
        inp = self.create_decision_input(
            sf_confidence=0.5,
            person_conf=0.6,
            org_conf=0.4,
            cos_top=0.7,
            id_match=True,
            date_match=True
        )
        output = decision_engine.decide(inp)
        
        details = output.details
        assert "score_breakdown" in details
        
        breakdown = details["score_breakdown"]
        expected_keys = [
            "smartfilter_contribution",
            "person_contribution", 
            "org_contribution",
            "similarity_contribution",
            "date_bonus",
            "id_bonus",
            "total"
        ]
        
        for key in expected_keys:
            assert key in breakdown, f"Expected key '{key}' not found in score breakdown"
            assert isinstance(breakdown[key], (int, float)), f"Key '{key}' should be numeric"
        
        # Verify total matches calculated score
        assert breakdown["total"] == pytest.approx(output.score, abs=1e-10)
    
    def test_normalized_features_in_details(self, decision_engine):
        """Test that normalized features are included in details"""
        inp = self.create_decision_input(
            sf_confidence=0.6,
            person_conf=0.7,
            org_conf=0.5,
            cos_top=0.8,
            date_match=True,
            id_match=False
        )
        output = decision_engine.decide(inp)
        
        details = output.details
        assert "normalized_features" in details
        
        features = details["normalized_features"]
        expected_features = [
            "smartfilter_confidence",
            "person_confidence",
            "org_confidence", 
            "similarity_cos_top",
            "date_match",
            "id_match"
        ]
        
        for feature in expected_features:
            assert feature in features, f"Expected feature '{feature}' not found in normalized features"
        
        # Verify values match input
        assert features["smartfilter_confidence"] == 0.6
        assert features["person_confidence"] == 0.7
        assert features["org_confidence"] == 0.5
        assert features["similarity_cos_top"] == 0.8
        assert features["date_match"] is True
        assert features["id_match"] is False
    
    def test_evidence_strength_indicators(self, decision_engine):
        """Test that evidence strength indicators are correctly set"""
        inp = self.create_decision_input(
            sf_confidence=0.8,  # >= 0.7
            person_conf=0.8,    # >= 0.7
            org_conf=0.5,       # < 0.7
            cos_top=0.95,       # >= 0.9
            date_match=True,
            id_match=False
        )
        output = decision_engine.decide(inp)
        
        details = output.details
        assert "evidence_strength" in details
        
        strength = details["evidence_strength"]
        expected_indicators = [
            "smartfilter_strong",
            "person_strong",
            "org_strong",
            "similarity_high",
            "exact_id_match",
            "exact_dob_match"
        ]
        
        for indicator in expected_indicators:
            assert indicator in strength, f"Expected indicator '{indicator}' not found"
            assert isinstance(strength[indicator], bool), f"Indicator '{indicator}' should be boolean"
        
        # Verify specific values
        assert strength["smartfilter_strong"] is True   # 0.8 >= 0.7
        assert strength["person_strong"] is True        # 0.8 >= 0.7
        assert strength["org_strong"] is False          # 0.5 < 0.7
        assert strength["similarity_high"] is True      # 0.95 >= 0.9
        assert strength["exact_id_match"] is False      # id_match=False
        assert strength["exact_dob_match"] is True      # date_match=True
    
    def test_weights_and_thresholds_in_details(self, decision_engine):
        """Test that weights and thresholds are included in details"""
        inp = self.create_decision_input()
        output = decision_engine.decide(inp)
        
        details = output.details
        assert "weights_used" in details
        assert "thresholds" in details
        
        weights = details["weights_used"]
        expected_weights = [
            "w_smartfilter",
            "w_person",
            "w_org",
            "w_similarity",
            "bonus_date_match",
            "bonus_id_match"
        ]
        
        for weight in expected_weights:
            assert weight in weights, f"Expected weight '{weight}' not found"
            assert isinstance(weights[weight], (int, float)), f"Weight '{weight}' should be numeric"
        
        thresholds = details["thresholds"]
        assert "thr_high" in thresholds
        assert "thr_medium" in thresholds
        assert isinstance(thresholds["thr_high"], (int, float))
        assert isinstance(thresholds["thr_medium"], (int, float))
    
    def test_skip_scenario_reasons(self, decision_engine):
        """Test that skip scenario generates appropriate reasons"""
        inp = self.create_decision_input(should_process=False)
        output = decision_engine.decide(inp)
        
        assert output.risk == RiskLevel.SKIP
        assert output.score == 0.0
        assert "smartfilter_skip" in output.reasons
        assert len(output.reasons) == 1  # Only skip reason
    
    def test_reasons_consistency_with_evidence_strength(self, decision_engine):
        """Test that reasons are consistent with evidence strength indicators"""
        inp = self.create_decision_input(
            sf_confidence=0.8,
            person_conf=0.8,
            cos_top=0.95,
            id_match=True,
            date_match=True
        )
        output = decision_engine.decide(inp)
        
        details = output.details
        strength = details["evidence_strength"]
        
        # If evidence is strong, corresponding reason should be present
        if strength["smartfilter_strong"]:
            assert "strong_smartfilter_signal" in output.reasons
        
        if strength["person_strong"]:
            assert "person_evidence_strong" in output.reasons
        
        if strength["similarity_high"]:
            assert "high_vector_similarity" in output.reasons
        
        if strength["exact_id_match"]:
            assert "id_exact_match" in output.reasons
        
        if strength["exact_dob_match"]:
            assert "dob_match" in output.reasons
    
    def test_contribution_calculation_accuracy(self, decision_engine):
        """Test that contribution calculations are mathematically accurate"""
        inp = self.create_decision_input(
            sf_confidence=0.5,
            person_conf=0.6,
            org_conf=0.4,
            cos_top=0.7,
            id_match=True,
            date_match=True
        )
        output = decision_engine.decide(inp)
        
        details = output.details
        breakdown = details["score_breakdown"]
        config = decision_engine.config
        
        # Verify individual contributions
        expected_sf_contrib = config.w_smartfilter * 0.5
        expected_person_contrib = config.w_person * 0.6
        expected_org_contrib = config.w_org * 0.4
        expected_sim_contrib = config.w_similarity * 0.7
        expected_date_bonus = config.bonus_date_match
        expected_id_bonus = config.bonus_id_match
        
        assert breakdown["smartfilter_contribution"] == pytest.approx(expected_sf_contrib)
        assert breakdown["person_contribution"] == pytest.approx(expected_person_contrib)
        assert breakdown["org_contribution"] == pytest.approx(expected_org_contrib)
        assert breakdown["similarity_contribution"] == pytest.approx(expected_sim_contrib)
        assert breakdown["date_bonus"] == pytest.approx(expected_date_bonus)
        assert breakdown["id_bonus"] == pytest.approx(expected_id_bonus)
        
        # Verify total
        expected_total = (expected_sf_contrib + expected_person_contrib + 
                         expected_org_contrib + expected_sim_contrib + 
                         expected_date_bonus + expected_id_bonus)
        assert breakdown["total"] == pytest.approx(expected_total)
        assert output.score == pytest.approx(expected_total)
