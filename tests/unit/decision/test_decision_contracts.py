"""
Unit tests for decision contracts.

Tests the basic functionality of decision contracts including
enum values, dataclass serialization, and basic validation.
"""

import pytest
from dataclasses import asdict

from src.ai_service.contracts.decision_contracts import (
    DecisionInput,
    DecisionOutput,
    RiskLevel,
    SmartFilterInfo,
    SignalsInfo,
    SimilarityInfo,
)
from src.ai_service.core.decision_engine import DecisionConfig, DecisionEngine


class TestRiskLevel:
    """Test RiskLevel enum functionality"""
    
    def test_risk_level_values(self):
        """Test that RiskLevel enum has correct values"""
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.SKIP.value == "skip"
    
    def test_risk_level_enumeration(self):
        """Test that all risk levels can be enumerated"""
        levels = list(RiskLevel)
        assert len(levels) == 4
        assert RiskLevel.HIGH in levels
        assert RiskLevel.MEDIUM in levels
        assert RiskLevel.LOW in levels
        assert RiskLevel.SKIP in levels


class TestSmartFilterInfo:
    """Test SmartFilterInfo dataclass"""
    
    def test_smart_filter_info_creation(self):
        """Test creating SmartFilterInfo with required fields"""
        info = SmartFilterInfo(should_process=True, confidence=0.8)
        assert info.should_process is True
        assert info.confidence == 0.8
        assert info.estimated_complexity is None
    
    def test_smart_filter_info_with_optional(self):
        """Test creating SmartFilterInfo with optional fields"""
        info = SmartFilterInfo(
            should_process=False, 
            confidence=0.5, 
            estimated_complexity="high"
        )
        assert info.should_process is False
        assert info.confidence == 0.5
        assert info.estimated_complexity == "high"
    
    def test_smart_filter_info_serialization(self):
        """Test SmartFilterInfo serialization to dict"""
        info = SmartFilterInfo(should_process=True, confidence=0.7, estimated_complexity="medium")
        data = asdict(info)
        
        expected = {
            "should_process": True,
            "confidence": 0.7,
            "estimated_complexity": "medium"
        }
        assert data == expected


class TestSignalsInfo:
    """Test SignalsInfo dataclass"""
    
    def test_signals_info_creation(self):
        """Test creating SignalsInfo with required fields"""
        info = SignalsInfo(person_confidence=0.6, org_confidence=0.4)
        assert info.person_confidence == 0.6
        assert info.org_confidence == 0.4
        assert info.date_match is None
        assert info.id_match is None
        assert info.evidence == {}
    
    def test_signals_info_with_optional(self):
        """Test creating SignalsInfo with optional fields"""
        evidence = {"found_names": ["John", "Doe"], "found_orgs": ["ACME Corp"]}
        info = SignalsInfo(
            person_confidence=0.8,
            org_confidence=0.3,
            date_match=True,
            id_match=False,
            evidence=evidence
        )
        assert info.person_confidence == 0.8
        assert info.org_confidence == 0.3
        assert info.date_match is True
        assert info.id_match is False
        assert info.evidence == evidence
    
    def test_signals_info_serialization(self):
        """Test SignalsInfo serialization to dict"""
        evidence = {"test": "data"}
        info = SignalsInfo(
            person_confidence=0.7,
            org_confidence=0.5,
            date_match=True,
            id_match=None,
            evidence=evidence
        )
        data = asdict(info)
        
        expected = {
            "person_confidence": 0.7,
            "org_confidence": 0.5,
            "date_match": True,
            "id_match": None,
            "evidence": evidence
        }
        assert data == expected


class TestSimilarityInfo:
    """Test SimilarityInfo dataclass"""
    
    def test_similarity_info_creation(self):
        """Test creating SimilarityInfo with default values"""
        info = SimilarityInfo()
        assert info.cos_top is None
        assert info.cos_p95 is None
    
    def test_similarity_info_with_values(self):
        """Test creating SimilarityInfo with values"""
        info = SimilarityInfo(cos_top=0.9, cos_p95=0.7)
        assert info.cos_top == 0.9
        assert info.cos_p95 == 0.7
    
    def test_similarity_info_serialization(self):
        """Test SimilarityInfo serialization to dict"""
        info = SimilarityInfo(cos_top=0.8, cos_p95=0.6)
        data = asdict(info)
        
        expected = {
            "cos_top": 0.8,
            "cos_p95": 0.6
        }
        assert data == expected


class TestDecisionInput:
    """Test DecisionInput dataclass"""
    
    def test_decision_input_creation(self):
        """Test creating DecisionInput with required fields"""
        inp = DecisionInput(text="Test text", language="en")
        assert inp.text == "Test text"
        assert inp.language == "en"
        assert inp.smartfilter.should_process is True
        assert inp.smartfilter.confidence == 1.0
        assert inp.signals.person_confidence == 0.0
        assert inp.signals.org_confidence == 0.0
    
    def test_decision_input_with_all_fields(self):
        """Test creating DecisionInput with all fields"""
        smartfilter = SmartFilterInfo(should_process=True, confidence=0.8, estimated_complexity="high")
        signals = SignalsInfo(person_confidence=0.7, org_confidence=0.5, date_match=True, id_match=False)
        similarity = SimilarityInfo(cos_top=0.9, cos_p95=0.7)
        
        inp = DecisionInput(
            text="John Doe from ACME Corp",
            language="en",
            smartfilter=smartfilter,
            signals=signals,
            similarity=similarity
        )
        
        assert inp.text == "John Doe from ACME Corp"
        assert inp.language == "en"
        assert inp.smartfilter == smartfilter
        assert inp.signals == signals
        assert inp.similarity == similarity
    
    def test_decision_input_serialization(self):
        """Test DecisionInput serialization to dict"""
        inp = DecisionInput(text="Test", language="en")
        data = asdict(inp)
        
        assert "text" in data
        assert "language" in data
        assert "smartfilter" in data
        assert "signals" in data
        assert "similarity" in data
        assert data["text"] == "Test"
        assert data["language"] == "en"


class TestDecisionOutput:
    """Test DecisionOutput dataclass"""
    
    def test_decision_output_creation(self):
        """Test creating DecisionOutput with required fields"""
        output = DecisionOutput(risk=RiskLevel.HIGH, score=0.8)
        assert output.risk == RiskLevel.HIGH
        assert output.score == 0.8
        assert output.reasons == []
        assert output.details == {}
    
    def test_decision_output_with_all_fields(self):
        """Test creating DecisionOutput with all fields"""
        reasons = ["High person confidence", "ID match detected"]
        details = {"person_confidence": 0.9, "id_match": True}
        
        output = DecisionOutput(
            risk=RiskLevel.MEDIUM,
            score=0.6,
            reasons=reasons,
            details=details
        )
        
        assert output.risk == RiskLevel.MEDIUM
        assert output.score == 0.6
        assert output.reasons == reasons
        assert output.details == details
    
    def test_decision_output_to_dict(self):
        """Test DecisionOutput to_dict method"""
        output = DecisionOutput(
            risk=RiskLevel.LOW,
            score=0.3,
            reasons=["Low confidence"],
            details={"test": "data"}
        )
        
        data = output.to_dict()
        
        expected = {
            "risk": "low",
            "score": 0.3,
            "reasons": ["Low confidence"],
            "details": {"test": "data"}
        }
        assert data == expected


class TestDecisionConfig:
    """Test DecisionConfig dataclass"""
    
    def test_decision_config_defaults(self):
        """Test DecisionConfig default values"""
        config = DecisionConfig()
        assert config.thr_high == 0.85
        assert config.thr_medium == 0.65
        assert config.w_person == 0.3
        assert config.w_org == 0.15
        assert config.w_similarity == 0.25
        assert config.w_smartfilter == 0.25
        assert config.bonus_date_match == 0.07
        assert config.bonus_id_match == 0.15
    
    def test_decision_config_custom_values(self):
        """Test DecisionConfig with custom values"""
        config = DecisionConfig(
            thr_high=0.9,
            thr_medium=0.6,
            w_person=0.5
        )
        assert config.thr_high == 0.9
        assert config.thr_medium == 0.6
        assert config.w_person == 0.5
        assert config.w_org == 0.15  # default


class TestDecisionEngine:
    """Test DecisionEngine basic functionality"""
    
    def test_decision_engine_initialization(self):
        """Test DecisionEngine initialization with default config"""
        engine = DecisionEngine()
        assert isinstance(engine.config, DecisionConfig)
        assert engine.config.thr_high == 0.85
    
    def test_decision_engine_with_custom_config(self):
        """Test DecisionEngine initialization with custom config"""
        config = DecisionConfig(thr_high=0.9, w_person=0.6)
        engine = DecisionEngine(config)
        assert engine.config.thr_high == 0.9
        assert engine.config.w_person == 0.6
    
    def test_decision_engine_decide_stub(self):
        """Test DecisionEngine decide method (stub implementation)"""
        engine = DecisionEngine()
        
        # Create test input
        inp = DecisionInput(
            text="John Doe",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(person_confidence=0.7, org_confidence=0.3),
            similarity=SimilarityInfo(cos_top=0.9)
        )
        
        # Make decision
        output = engine.decide(inp)
        
        # Verify output structure
        assert isinstance(output, DecisionOutput)
        assert isinstance(output.risk, RiskLevel)
        assert 0.0 <= output.score <= 1.0
        assert isinstance(output.reasons, list)
        assert isinstance(output.details, dict)
        
        # Verify output contains expected information
        assert len(output.reasons) > 0
        assert "Overall risk score:" in output.reasons[0]
        assert "Risk level:" in output.reasons[-1]
    
    def test_decision_engine_high_risk_scenario(self):
        """Test DecisionEngine with high risk scenario"""
        engine = DecisionEngine()
        
        # High confidence signals
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
            similarity=SimilarityInfo(cos_top=0.95)
        )
        
        output = engine.decide(inp)
        
        # Should be high risk due to high confidence signals
        assert output.risk in [RiskLevel.HIGH, RiskLevel.MEDIUM]  # Depends on exact calculation
        assert output.score > 0.5  # Should be relatively high
    
    def test_decision_engine_low_risk_scenario(self):
        """Test DecisionEngine with low risk scenario"""
        engine = DecisionEngine()
        
        # Low confidence signals
        inp = DecisionInput(
            text="Low risk text",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.3),
            signals=SignalsInfo(person_confidence=0.2, org_confidence=0.1),
            similarity=SimilarityInfo(cos_top=0.2)
        )
        
        output = engine.decide(inp)
        
        # Should be low risk or skip
        assert output.risk in [RiskLevel.LOW, RiskLevel.SKIP]
        assert output.score < 0.5  # Should be relatively low
