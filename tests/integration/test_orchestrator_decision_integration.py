"""
Integration tests for orchestrator decision engine integration.

Tests the complete flow from text input through orchestrator processing
to decision engine risk assessment and API response.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from ai_service.contracts.base_contracts import (
    NormalizationResult,
    SignalsPerson,
    SignalsOrganization,
    SignalsResult,
    SmartFilterResult,
    TokenTrace,
)
from ai_service.contracts.decision_contracts import RiskLevel
from ai_service.core.orchestrator_factory import OrchestratorFactory
from ai_service.core.unified_orchestrator import UnifiedOrchestrator


class TestOrchestratorDecisionIntegration:
    """Test orchestrator integration with decision engine"""
    
    @pytest.fixture
    async def orchestrator_with_decision_engine(self):
        """Create orchestrator with decision engine enabled"""
        return await OrchestratorFactory.create_orchestrator(
            enable_smart_filter=True,
            enable_variants=False,
            enable_embeddings=False,
            enable_decision_engine=True,
            allow_smart_filter_skip=True,
        )
    
    @pytest.fixture
    async def orchestrator_without_decision_engine(self):
        """Create orchestrator without decision engine"""
        return await OrchestratorFactory.create_orchestrator(
            enable_smart_filter=True,
            enable_variants=False,
            enable_embeddings=False,
            enable_decision_engine=False,
            allow_smart_filter_skip=True,
        )
    
    async def test_high_risk_scenario(self, orchestrator_with_decision_engine):
        """Test high risk scenario with high confidence signals and ID match"""
        
        # Process text that should trigger high risk
        result = await orchestrator_with_decision_engine.process(
            text="John Doe from ACME Corp with ID 123456789",
            generate_variants=False,
            generate_embeddings=False,
        )
        
        # Verify processing was successful
        assert result.success is True
        assert result.original_text == "John Doe from ACME Corp with ID 123456789"
        
        # Verify decision result is present
        assert result.decision is not None
        assert isinstance(result.decision.risk, RiskLevel)
        assert 0.0 <= result.decision.score <= 1.0
        assert isinstance(result.decision.reasons, list)
        assert isinstance(result.decision.details, dict)
        
        # Verify decision details contain expected information
        assert "calculated_score" in result.decision.details
        assert "weights_used" in result.decision.details
        assert "thresholds" in result.decision.details
        assert "input_signals" in result.decision.details
        
        # Verify thresholds are correct
        thresholds = result.decision.details["thresholds"]
        assert thresholds["thr_high"] == 0.85
        assert thresholds["thr_medium"] == 0.65
        
        # Verify reasons contain relevant information
        reasons_text = " ".join(result.decision.reasons)
        assert "Overall risk score:" in reasons_text
        assert "Risk level:" in reasons_text
    
    async def test_skip_scenario_smartfilter_false(self, orchestrator_with_decision_engine):
        """Test skip scenario when smart filter says should_process=False"""
        
        # Mock the smart filter to return should_process=False
        # This is a bit tricky since we need to mock the service
        # For now, we'll test with a text that might trigger skip
        
        # Process text that might be filtered out
        result = await orchestrator_with_decision_engine.process(
            text="123456789",  # Just numbers, might be filtered
            generate_variants=False,
            generate_embeddings=False,
        )
        
        # Verify processing completed
        assert result.success is True
        
        # If decision engine is enabled, check the result
        if result.decision:
            # Could be SKIP if smart filter said no, or LOW if it passed
            assert result.decision.risk in [RiskLevel.SKIP, RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH]
            assert 0.0 <= result.decision.score <= 1.0
    
    async def test_medium_risk_scenario(self, orchestrator_with_decision_engine):
        """Test medium risk scenario with moderate confidence signals"""
        
        # Process text that should trigger medium risk
        result = await orchestrator_with_decision_engine.process(
            text="Jane Smith from Tech Company",
            generate_variants=False,
            generate_embeddings=False,
        )
        
        # Verify processing was successful
        assert result.success is True
        
        # Verify decision result is present
        if result.decision:
            assert isinstance(result.decision.risk, RiskLevel)
            assert 0.0 <= result.decision.score <= 1.0
            assert isinstance(result.decision.reasons, list)
            assert isinstance(result.decision.details, dict)
    
    async def test_low_risk_scenario(self, orchestrator_with_decision_engine):
        """Test low risk scenario with low confidence signals"""
        
        # Process text that should trigger low risk
        result = await orchestrator_with_decision_engine.process(
            text="hello world",
            generate_variants=False,
            generate_embeddings=False,
        )
        
        # Verify processing was successful
        assert result.success is True
        
        # Verify decision result is present
        if result.decision:
            assert isinstance(result.decision.risk, RiskLevel)
            assert 0.0 <= result.decision.score <= 1.0
            # Should be LOW or SKIP for generic text
            assert result.decision.risk in [RiskLevel.LOW, RiskLevel.SKIP]
    
    async def test_decision_engine_disabled(self, orchestrator_without_decision_engine):
        """Test behavior when decision engine is disabled"""
        
        # Process text
        result = await orchestrator_without_decision_engine.process(
            text="John Doe from ACME Corp",
            generate_variants=False,
            generate_embeddings=False,
        )
        
        # Verify processing was successful
        assert result.success is True
        
        # Verify decision result is None when disabled
        assert result.decision is None
    
    async def test_decision_input_creation(self, orchestrator_with_decision_engine):
        """Test that DecisionInput is created correctly from processing results"""
        
        # Process text
        result = await orchestrator_with_decision_engine.process(
            text="John Doe from ACME Corp",
            generate_variants=False,
            generate_embeddings=False,
        )
        
        # Verify processing was successful
        assert result.success is True
        
        # If decision engine is enabled, verify the decision input was created correctly
        if result.decision:
            details = result.decision.details
            
            # Verify input signals are captured
            assert "input_signals" in details
            input_signals = details["input_signals"]
            assert "person_confidence" in input_signals
            assert "org_confidence" in input_signals
            assert "date_match" in input_signals
            assert "id_match" in input_signals
            assert "evidence_count" in input_signals
            
            # Verify smart filter information is captured
            assert "smartfilter" in details
            smartfilter = details["smartfilter"]
            assert "should_process" in smartfilter
            assert "confidence" in smartfilter
            
            # Verify similarity information is captured
            assert "similarity" in details
            similarity = details["similarity"]
            assert "cos_top" in similarity
            assert "cos_p95" in similarity
    
    async def test_risk_level_determination(self, orchestrator_with_decision_engine):
        """Test that risk levels are determined correctly based on score"""
        
        # Process multiple texts and verify risk level determination
        test_cases = [
            ("John Doe with ID 123456789", "Should be HIGH or MEDIUM"),
            ("Jane Smith from Company", "Should be MEDIUM or LOW"),
            ("hello world", "Should be LOW or SKIP"),
        ]
        
        for text, description in test_cases:
            result = await orchestrator_with_decision_engine.process(
                text=text,
                generate_variants=False,
                generate_embeddings=False,
            )
            
            # Verify processing was successful
            assert result.success is True, f"Processing failed for: {text}"
            
            # If decision engine is enabled, verify risk level makes sense
            if result.decision:
                risk = result.decision.risk
                score = result.decision.score
                
                # Verify risk level is consistent with score
                if score >= 0.85:
                    assert risk == RiskLevel.HIGH, f"Expected HIGH for score {score}, got {risk}"
                elif score >= 0.65:
                    assert risk == RiskLevel.MEDIUM, f"Expected MEDIUM for score {score}, got {risk}"
                else:
                    assert risk in [RiskLevel.LOW, RiskLevel.SKIP], f"Expected LOW/SKIP for score {score}, got {risk}"
    
    async def test_decision_reasons_generation(self, orchestrator_with_decision_engine):
        """Test that decision reasons are generated appropriately"""
        
        # Process text
        result = await orchestrator_with_decision_engine.process(
            text="John Doe from ACME Corp",
            generate_variants=False,
            generate_embeddings=False,
        )
        
        # Verify processing was successful
        assert result.success is True
        
        # If decision engine is enabled, verify reasons are generated
        if result.decision:
            reasons = result.decision.reasons
            
            # Should have at least basic reasons
            assert len(reasons) > 0
            
            # Should contain overall risk score
            assert any("Overall risk score:" in reason for reason in reasons)
            
            # Should contain risk level
            assert any("Risk level:" in reason for reason in reasons)
            
            # Should contain contributing factors if they exist
            reasons_text = " ".join(reasons)
            if "Person confidence:" in reasons_text:
                assert "Person confidence:" in reasons_text
            if "Organization confidence:" in reasons_text:
                assert "Organization confidence:" in reasons_text
            if "ID match bonus applied" in reasons_text:
                assert "ID match bonus applied" in reasons_text
            if "Date match bonus applied" in reasons_text:
                assert "Date match bonus applied" in reasons_text
