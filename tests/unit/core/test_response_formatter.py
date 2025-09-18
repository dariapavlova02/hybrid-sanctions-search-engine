"""
Unit tests for response formatter.

Tests the response formatter utility for standardized JSON response structure
with risk fields and raw evidence.
"""

import pytest
from unittest.mock import MagicMock

from src.ai_service.contracts.base_contracts import (
    UnifiedProcessingResult,
    SignalsPerson,
    SignalsOrganization,
    SignalsResult,
    TokenTrace,
)
from src.ai_service.contracts.decision_contracts import DecisionOutput, RiskLevel
from src.ai_service.utils.response_formatter import (
    format_processing_result,
    format_error_response,
    _extract_token_variants,
    _get_risk_level,
    _get_risk_score,
    _get_decision_reasons,
    _get_decision_details,
    _extract_smart_filter_info,
    _extract_signals_summary,
)


class TestResponseFormatter:
    """Test response formatter functionality"""
    
    @pytest.fixture
    def mock_processing_result(self):
        """Create mock processing result with decision"""
        # Create mock signals
        mock_person = MagicMock()
        mock_person.name = "John Doe"
        mock_person.confidence = 0.9
        mock_person.role = "person"
        mock_person.ids = ["123456789"]
        
        mock_org = MagicMock()
        mock_org.name = "ACME Corp"
        mock_org.confidence = 0.8
        mock_org.type = "organization"
        mock_org.ids = ["987654321"]
        
        mock_signals = MagicMock()
        mock_signals.persons = [mock_person]
        mock_signals.organizations = [mock_org]
        mock_signals.confidence = 0.85
        
        # Create mock decision
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
                "smartfilter": {
                    "should_process": True,
                    "confidence": 0.9,
                    "estimated_complexity": "medium"
                },
                "input_signals": {
                    "person_confidence": 0.9,
                    "org_confidence": 0.8,
                    "date_match": True,
                    "id_match": True,
                    "evidence_count": 2
                }
            }
        )
        
        # Create mock trace
        mock_trace = MagicMock()
        mock_trace.token = "JOHN"
        mock_trace.role = "given"
        mock_trace.normal_form = "JOHN"
        mock_trace.confidence = 0.95
        
        # Create mock processing result
        mock_result = MagicMock()
        mock_result.original_text = "John Doe from ACME Corp"
        mock_result.normalized_text = "JOHN DOE ACME CORP"
        mock_result.language = "en"
        mock_result.language_confidence = 0.95
        mock_result.tokens = ["JOHN", "DOE", "ACME", "CORP"]
        mock_result.trace = [mock_trace]
        mock_result.signals = mock_signals
        mock_result.variants = ["john doe acme corp", "j. doe acme corp"]
        mock_result.embeddings = None
        mock_result.decision = mock_decision
        mock_result.processing_time = 0.15
        mock_result.success = True
        mock_result.errors = []
        
        return mock_result
    
    @pytest.fixture
    def mock_processing_result_no_decision(self):
        """Create mock processing result without decision"""
        mock_signals = MagicMock()
        mock_signals.persons = []
        mock_signals.organizations = []
        mock_signals.confidence = 0.5
        
        mock_result = MagicMock()
        mock_result.original_text = "hello world"
        mock_result.normalized_text = "HELLO WORLD"
        mock_result.language = "en"
        mock_result.language_confidence = 0.9
        mock_result.tokens = ["HELLO", "WORLD"]
        mock_result.trace = []
        mock_result.signals = mock_signals
        mock_result.variants = None
        mock_result.embeddings = None
        mock_result.decision = None
        mock_result.processing_time = 0.05
        mock_result.success = True
        mock_result.errors = []
        
        return mock_result
    
    def test_format_processing_result_with_decision(self, mock_processing_result):
        """Test formatting processing result with decision engine enabled"""
        response = format_processing_result(mock_processing_result)
        
        # Verify basic structure
        assert isinstance(response, dict)
        assert "original_text" in response
        assert "normalized_text" in response
        assert "language" in response
        assert "language_confidence" in response
        assert "variants" in response
        assert "token_variants" in response
        assert "risk_level" in response
        assert "risk_score" in response
        assert "decision_reasons" in response
        assert "decision_details" in response
        assert "smart_filter" in response
        assert "signals" in response
        assert "processing_time" in response
        assert "success" in response
        assert "errors" in response
        
        # Verify basic values
        assert response["original_text"] == "John Doe from ACME Corp"
        assert response["normalized_text"] == "JOHN DOE ACME CORP"
        assert response["language"] == "en"
        assert response["language_confidence"] == 0.95
        assert response["variants"] == ["john doe acme corp", "j. doe acme corp"]
        assert response["processing_time"] == 0.15
        assert response["success"] is True
        assert response["errors"] == []
        
        # Verify risk fields
        assert response["risk_level"] == "high"
        assert response["risk_score"] == 0.87
        assert response["decision_reasons"] == ["High person confidence: 0.9", "ID match bonus applied", "Risk level: high"]
        assert response["decision_details"]["calculated_score"] == 0.87
        assert response["decision_details"]["thresholds"]["thr_high"] == 0.85
        
        # Verify token variants
        assert len(response["token_variants"]) == 1
        token_variant = response["token_variants"][0]
        assert token_variant["token"] == "JOHN"
        assert token_variant["role"] == "given"
        assert token_variant["normal_form"] == "JOHN"
        assert token_variant["confidence"] == 0.95
        
        # Verify smart filter info
        smart_filter = response["smart_filter"]
        assert smart_filter["enabled"] is True
        assert smart_filter["should_process"] is True
        assert smart_filter["confidence"] == 0.9
        assert smart_filter["classification"] == "medium"
        
        # Verify signals summary
        signals = response["signals"]
        assert len(signals["persons"]) == 1
        assert signals["persons"][0]["name"] == "John Doe"
        assert signals["persons"][0]["confidence"] == 0.9
        assert signals["persons"][0]["ids"] == ["123456789"]
        
        assert len(signals["organizations"]) == 1
        assert signals["organizations"][0]["name"] == "ACME Corp"
        assert signals["organizations"][0]["confidence"] == 0.8
        assert signals["organizations"][0]["ids"] == ["987654321"]
        
        assert signals["summary"]["persons_count"] == 1
        assert signals["summary"]["organizations_count"] == 1
        assert signals["summary"]["total_confidence"] == 0.85
    
    def test_format_processing_result_without_decision(self, mock_processing_result_no_decision):
        """Test formatting processing result without decision engine"""
        response = format_processing_result(mock_processing_result_no_decision)
        
        # Verify basic structure
        assert response["original_text"] == "hello world"
        assert response["normalized_text"] == "HELLO WORLD"
        assert response["language"] == "en"
        assert response["success"] is True
        
        # Verify risk fields with default values
        assert response["risk_level"] == "unknown"
        assert response["risk_score"] is None
        assert response["decision_reasons"] == ["decision_engine_not_enabled"]
        assert response["decision_details"] == {}
        
        # Verify smart filter with default values
        smart_filter = response["smart_filter"]
        assert smart_filter["enabled"] is False
        assert smart_filter["should_process"] is True
        assert smart_filter["confidence"] == 1.0
        assert smart_filter["classification"] is None
        
        # Verify signals with empty data
        signals = response["signals"]
        assert signals["persons"] == []
        assert signals["organizations"] == []
        assert signals["confidence"] == 0.5
        assert signals["summary"]["persons_count"] == 0
        assert signals["summary"]["organizations_count"] == 0
    
    def test_format_error_response(self):
        """Test formatting error response"""
        error_response = format_error_response("Test error message", "test_error")
        
        # Verify error structure
        assert error_response["success"] is False
        assert error_response["error"]["code"] == "test_error"
        assert error_response["error"]["message"] == "Test error message"
        
        # Verify all required fields are present
        assert "original_text" in error_response
        assert "normalized_text" in error_response
        assert "language" in error_response
        assert "variants" in error_response
        assert "token_variants" in error_response
        assert "risk_level" in error_response
        assert "risk_score" in error_response
        assert "decision_reasons" in error_response
        assert "decision_details" in error_response
        assert "smart_filter" in error_response
        assert "signals" in error_response
        assert "processing_time" in error_response
        assert "errors" in error_response
        
        # Verify default values
        assert error_response["risk_level"] == "unknown"
        assert error_response["risk_score"] is None
        assert error_response["decision_reasons"] == ["processing_failed"]
        assert error_response["errors"] == ["Test error message"]
    
    def test_extract_token_variants(self, mock_processing_result):
        """Test token variants extraction"""
        token_variants = _extract_token_variants(mock_processing_result)
        
        assert len(token_variants) == 1
        token_variant = token_variants[0]
        assert token_variant["token"] == "JOHN"
        assert token_variant["role"] == "given"
        assert token_variant["normal_form"] == "JOHN"
        assert token_variant["confidence"] == 0.95
    
    def test_extract_token_variants_empty_trace(self, mock_processing_result_no_decision):
        """Test token variants extraction with empty trace"""
        token_variants = _extract_token_variants(mock_processing_result_no_decision)
        assert token_variants == []
    
    def test_get_risk_level_with_decision(self, mock_processing_result):
        """Test risk level extraction with decision"""
        risk_level = _get_risk_level(mock_processing_result.decision)
        assert risk_level == "high"
    
    def test_get_risk_level_without_decision(self, mock_processing_result_no_decision):
        """Test risk level extraction without decision"""
        risk_level = _get_risk_level(mock_processing_result_no_decision.decision)
        assert risk_level == "unknown"
    
    def test_get_risk_score_with_decision(self, mock_processing_result):
        """Test risk score extraction with decision"""
        risk_score = _get_risk_score(mock_processing_result.decision)
        assert risk_score == 0.87
    
    def test_get_risk_score_without_decision(self, mock_processing_result_no_decision):
        """Test risk score extraction without decision"""
        risk_score = _get_risk_score(mock_processing_result_no_decision.decision)
        assert risk_score is None
    
    def test_get_decision_reasons_with_decision(self, mock_processing_result):
        """Test decision reasons extraction with decision"""
        reasons = _get_decision_reasons(mock_processing_result.decision)
        assert reasons == ["High person confidence: 0.9", "ID match bonus applied", "Risk level: high"]
    
    def test_get_decision_reasons_without_decision(self, mock_processing_result_no_decision):
        """Test decision reasons extraction without decision"""
        reasons = _get_decision_reasons(mock_processing_result_no_decision.decision)
        assert reasons == ["decision_engine_not_enabled"]
    
    def test_get_decision_details_with_decision(self, mock_processing_result):
        """Test decision details extraction with decision"""
        details = _get_decision_details(mock_processing_result.decision)
        assert details["calculated_score"] == 0.87
        assert details["thresholds"]["thr_high"] == 0.85
    
    def test_get_decision_details_without_decision(self, mock_processing_result_no_decision):
        """Test decision details extraction without decision"""
        details = _get_decision_details(mock_processing_result_no_decision.decision)
        assert details == {}
    
    def test_extract_smart_filter_info_with_decision(self, mock_processing_result):
        """Test smart filter info extraction with decision"""
        smart_filter = _extract_smart_filter_info(mock_processing_result)
        assert smart_filter["enabled"] is True
        assert smart_filter["should_process"] is True
        assert smart_filter["confidence"] == 0.9
        assert smart_filter["classification"] == "medium"
    
    def test_extract_smart_filter_info_without_decision(self, mock_processing_result_no_decision):
        """Test smart filter info extraction without decision"""
        smart_filter = _extract_smart_filter_info(mock_processing_result_no_decision)
        assert smart_filter["enabled"] is False
        assert smart_filter["should_process"] is True
        assert smart_filter["confidence"] == 1.0
        assert smart_filter["classification"] is None
    
    def test_extract_signals_summary_with_data(self, mock_processing_result):
        """Test signals summary extraction with data"""
        signals = _extract_signals_summary(mock_processing_result)
        
        assert len(signals["persons"]) == 1
        assert signals["persons"][0]["name"] == "John Doe"
        assert signals["persons"][0]["confidence"] == 0.9
        assert signals["persons"][0]["ids"] == ["123456789"]
        
        assert len(signals["organizations"]) == 1
        assert signals["organizations"][0]["name"] == "ACME Corp"
        assert signals["organizations"][0]["confidence"] == 0.8
        
        assert signals["summary"]["persons_count"] == 1
        assert signals["summary"]["organizations_count"] == 1
        assert signals["summary"]["total_confidence"] == 0.85
    
    def test_extract_signals_summary_without_data(self, mock_processing_result_no_decision):
        """Test signals summary extraction without data"""
        signals = _extract_signals_summary(mock_processing_result_no_decision)
        
        assert signals["persons"] == []
        assert signals["organizations"] == []
        assert signals["confidence"] == 0.5
        assert signals["summary"]["persons_count"] == 0
        assert signals["summary"]["organizations_count"] == 0
    
    def test_response_structure_completeness(self, mock_processing_result):
        """Test that response structure contains all required fields"""
        response = format_processing_result(mock_processing_result)
        
        # Required fields from the task specification
        required_fields = [
            "original_text", "normalized_text", "language", "language_confidence",
            "variants", "token_variants", "risk_level", "risk_score", 
            "decision_reasons", "decision_details", "smart_filter", "signals",
            "processing_time", "success", "errors"
        ]
        
        for field in required_fields:
            assert field in response, f"Required field '{field}' missing from response"
        
        # Verify field types
        assert isinstance(response["original_text"], str)
        assert isinstance(response["normalized_text"], str)
        assert isinstance(response["language"], str)
        assert isinstance(response["language_confidence"], float)
        assert isinstance(response["variants"], list)
        assert isinstance(response["token_variants"], list)
        assert isinstance(response["risk_level"], str)
        assert isinstance(response["risk_score"], (float, type(None)))
        assert isinstance(response["decision_reasons"], list)
        assert isinstance(response["decision_details"], dict)
        assert isinstance(response["smart_filter"], dict)
        assert isinstance(response["signals"], dict)
        assert isinstance(response["processing_time"], float)
        assert isinstance(response["success"], bool)
        assert isinstance(response["errors"], list)
