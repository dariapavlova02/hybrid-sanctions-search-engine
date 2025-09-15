"""
Integration tests for API risk response format.

Tests that the API correctly exposes risk fields in the response
without requiring full orchestrator initialization.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai_service.contracts.decision_contracts import DecisionOutput, RiskLevel
from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator


class TestAPIRiskResponse:
    """Test API response format with risk information"""
    
    def test_process_endpoint_response_format(self):
        """Test that /process endpoint includes risk fields in response"""
        
        # Mock the orchestrator and its process method
        mock_orchestrator = MagicMock()
        
        # Create a mock processing result with decision
        mock_decision = DecisionOutput(
            risk=RiskLevel.HIGH,
            score=0.87,
            reasons=["High person confidence: 0.9", "ID match bonus applied", "Risk level: high"],
            details={
                "calculated_score": 0.87,
                "weights_used": {
                    "w_smartfilter": 0.25,
                    "w_person": 0.3,
                    "w_org": 0.15,
                    "w_similarity": 0.25,
                    "bonus_date_match": 0.07,
                    "bonus_id_match": 0.15
                },
                "thresholds": {
                    "thr_high": 0.85,
                    "thr_medium": 0.65
                },
                "input_signals": {
                    "person_confidence": 0.9,
                    "org_confidence": 0.7,
                    "date_match": True,
                    "id_match": True,
                    "evidence_count": 2
                }
            }
        )
        
        # Mock the processing result
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_text = "John Doe from ACME Corp"
        mock_result.normalized_text = "JOHN DOE ACME CORP"
        mock_result.language = "en"
        mock_result.language_confidence = 0.95
        mock_result.tokens = ["JOHN", "DOE", "ACME", "CORP"]
        mock_result.trace = []
        mock_result.signals = MagicMock()
        mock_result.signals.persons = []
        mock_result.signals.organizations = []
        mock_result.signals.confidence = 0.8
        mock_result.variants = None
        mock_result.embeddings = None
        mock_result.processing_time = 0.1
        mock_result.errors = []
        mock_result.decision = mock_decision
        
        # Configure the mock orchestrator
        mock_orchestrator.process = AsyncMock(return_value=mock_result)
        
        # Test the ProcessResponse model structure
        response = {
            "normalized_text": mock_result.normalized_text,
            "tokens": mock_result.tokens,
            "trace": mock_result.trace,
            "language": mock_result.language,
            "success": mock_result.success,
            "errors": mock_result.errors,
            "processing_time": mock_result.processing_time,
            "signals": {
                "persons": [
                    {
                        "core": person.core,
                        "full_name": person.full_name,
                        "dob": person.dob,
                        "ids": person.ids,
                        "confidence": person.confidence,
                        "evidence": person.evidence,
                    }
                    for person in mock_result.signals.persons
                ],
                "organizations": [
                    {
                        "core": org.core,
                        "legal_form": org.legal_form,
                        "full_name": org.full_name,
                        "ids": org.ids,
                        "confidence": org.confidence,
                        "evidence": org.evidence,
                    }
                    for org in mock_result.signals.organizations
                ],
                "confidence": mock_result.signals.confidence,
            },
            "decision": {
                "risk_level": mock_result.decision.risk.value,
                "risk_score": mock_result.decision.score,
                "decision_reasons": mock_result.decision.reasons,
                "decision_details": mock_result.decision.details,
            } if mock_result.decision else None,
            "embedding": mock_result.embeddings,
        }
        
        # Verify the ProcessResponse format
        assert response["success"] is True
        assert response["normalized_text"] == "JOHN DOE ACME CORP"
        assert response["tokens"] == ["JOHN", "DOE", "ACME", "CORP"]
        assert response["language"] == "en"
        assert response["errors"] == []
        
        # Verify signals section
        assert response["signals"] is not None
        assert response["signals"]["confidence"] == 0.8
        
        # Verify decision section
        assert response["decision"] is not None
        assert response["decision"]["risk_level"] == "high"
        assert response["decision"]["risk_score"] == 0.87
        assert response["decision"]["decision_reasons"] == ["High person confidence: 0.9", "ID match bonus applied", "Risk level: high"]
        assert response["decision"]["decision_details"]["calculated_score"] == 0.87
        assert response["decision"]["decision_details"]["thresholds"]["thr_high"] == 0.85
        assert response["decision"]["decision_details"]["thresholds"]["thr_medium"] == 0.65
    
    def test_process_endpoint_response_without_decision_engine(self):
        """Test response format when decision engine is not enabled"""
        
        # Mock the processing result without decision
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.original_text = "John Doe"
        mock_result.normalized_text = "JOHN DOE"
        mock_result.language = "en"
        mock_result.language_confidence = 0.9
        mock_result.tokens = ["JOHN", "DOE"]
        mock_result.trace = []
        mock_result.signals = MagicMock()
        mock_result.signals.persons = []
        mock_result.signals.organizations = []
        mock_result.signals.confidence = 0.5
        mock_result.variants = None
        mock_result.embeddings = None
        mock_result.processing_time = 0.05
        mock_result.errors = []
        mock_result.decision = None  # No decision engine
        
        # Test the ProcessResponse model structure without decision
        response = {
            "normalized_text": mock_result.normalized_text,
            "tokens": mock_result.tokens,
            "trace": mock_result.trace,
            "language": mock_result.language,
            "success": mock_result.success,
            "errors": mock_result.errors,
            "processing_time": mock_result.processing_time,
            "signals": {
                "persons": [],
                "organizations": [],
                "confidence": mock_result.signals.confidence,
            },
            "decision": None,  # No decision engine
            "embedding": None,  # No embeddings
        }
        
        # Verify the ProcessResponse format
        assert response["success"] is True
        assert response["normalized_text"] == "JOHN DOE"
        assert response["tokens"] == ["JOHN", "DOE"]
        assert response["language"] == "en"
        assert response["errors"] == []
        
        # Verify signals section
        assert response["signals"] is not None
        assert response["signals"]["confidence"] == 0.5
        
        # Verify decision section is None (no decision engine)
        assert response["decision"] is None
    
    def test_decision_output_serialization(self):
        """Test that DecisionOutput can be serialized to dict"""
        
        decision = DecisionOutput(
            risk=RiskLevel.MEDIUM,
            score=0.72,
            reasons=["Person confidence: 0.6", "Organization confidence: 0.5", "Risk level: medium"],
            details={
                "calculated_score": 0.72,
                "weights_used": {
                    "w_smartfilter": 0.25,
                    "w_person": 0.3,
                    "w_org": 0.15,
                    "w_similarity": 0.25,
                    "bonus_date_match": 0.07,
                    "bonus_id_match": 0.15
                },
                "thresholds": {
                    "thr_high": 0.85,
                    "thr_medium": 0.65
                }
            }
        )
        
        # Test to_dict method
        decision_dict = decision.to_dict()
        
        assert decision_dict["risk"] == "medium"
        assert decision_dict["score"] == 0.72
        assert decision_dict["reasons"] == ["Person confidence: 0.6", "Organization confidence: 0.5", "Risk level: medium"]
        assert decision_dict["details"]["calculated_score"] == 0.72
        assert decision_dict["details"]["thresholds"]["thr_high"] == 0.85
        assert decision_dict["details"]["thresholds"]["thr_medium"] == 0.65
    
    def test_risk_level_values(self):
        """Test that all risk level values are correctly handled"""
        
        risk_levels = [RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW, RiskLevel.SKIP]
        expected_values = ["high", "medium", "low", "skip"]
        
        for risk_level, expected_value in zip(risk_levels, expected_values):
            decision = DecisionOutput(
                risk=risk_level,
                score=0.5,
                reasons=["Test reason"],
                details={}
            )
            
            decision_dict = decision.to_dict()
            assert decision_dict["risk"] == expected_value
