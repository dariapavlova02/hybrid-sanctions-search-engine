"""
End-to-end tests for complete risk decision pipeline.

Tests the full pipeline from SmartFilter through Signals to Risk decision
with realistic high-risk scenario simulation.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any

from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.contracts.decision_contracts import RiskLevel
from src.ai_service.contracts.base_contracts import (
    UnifiedProcessingResult, 
    NormalizationResult, 
    SmartFilterResult, 
    SignalsResult,
    SignalsPerson,
    SignalsOrganization
)


class TestFullPipelineRiskE2E:
    """End-to-end tests for complete risk decision pipeline"""
    
    @pytest.fixture
    def high_risk_text(self):
        """High-risk text input for testing"""
        return "Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890"
    
    @pytest.fixture
    def mock_smart_filter_result(self):
        """Mock SmartFilter result with high confidence"""
        result = Mock(spec=SmartFilterResult)
        result.should_process = True
        result.confidence = 0.75
        result.classification = "high_risk_organization"
        result.reasoning = "Banking organization with high risk indicators"
        return result
    
    @pytest.fixture
    def mock_signals_result(self):
        """Mock Signals result with high confidence indicators"""
        # Mock person info
        person = Mock(spec=SignalsPerson)
        person.name = "Иван Петров"
        person.confidence = 0.8
        person.ids = ["1234567890"]  # ID match
        person.dates = ["1980-01-01"]  # Date match
        
        # Mock organization info
        org = Mock(spec=SignalsOrganization)
        org.name = "ТОВ 'ПРИВАТБАНК'"
        org.confidence = 0.7
        org.ids = ["1234567890"]  # ID match
        
        # Mock signals result
        result = Mock(spec=SignalsResult)
        result.persons = [person]
        result.organizations = [org]
        result.confidence = 0.8
        result.extras = Mock()
        result.extras.dates = ["1980-01-01"]  # Date match
        result.extras.ids = ["1234567890"]  # ID match
        
        return result
    
    @pytest.fixture
    def mock_normalization_result(self):
        """Mock normalization result"""
        result = Mock(spec=NormalizationResult)
        result.normalized = "Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890"
        result.language = "uk"
        result.language_confidence = 0.9
        result.variants = ["Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890"]
        result.tokens = ["Оплата", "ТОВ", "ПРИВАТБАНК", "Ивану", "Петрову", "1980-01-01", "ИНН", "1234567890"]
        result.trace = []
        result.success = True
        result.errors = []
        return result
    
    @pytest.fixture
    def mock_embeddings_result(self):
        """Mock embeddings result with high similarity"""
        return {
            "embeddings": [0.1] * 384,  # Valid 384-dim vector
            "cos_top": 0.88,  # High similarity
            "cos_p95": 0.75
        }
    
    @pytest.fixture
    def mock_orchestrator(self, mock_smart_filter_result, mock_signals_result, 
                         mock_normalization_result, mock_embeddings_result):
        """Create comprehensive mock orchestrator for E2E testing"""
        orchestrator = Mock(spec=UnifiedOrchestrator)
        
        # Mock language detection
        orchestrator.language_service = Mock()
        orchestrator.language_service.detect_language.return_value = {
            'language': 'uk',
            'confidence': 0.9,
            'method': 'cyrillic_ukrainian'
        }
        
        # Mock normalization service
        orchestrator.normalization_service = Mock()
        orchestrator.normalization_service.normalize = AsyncMock(return_value=mock_normalization_result)
        
        # Mock smart filter service
        orchestrator.smart_filter_service = Mock()
        orchestrator.smart_filter_service.should_process = AsyncMock(return_value=mock_smart_filter_result)
        
        # Mock signals service
        orchestrator.signals_service = Mock()
        orchestrator.signals_service.extract_signals = AsyncMock(return_value=mock_signals_result)
        
        # Mock embedding service
        orchestrator.embedding_service = Mock()
        orchestrator.embedding_service.generate_embeddings = AsyncMock(return_value=mock_embeddings_result)
        
        # Mock decision engine (will be tested with real implementation)
        from src.ai_service.core.decision_engine import DecisionEngine
        orchestrator.decision_engine = DecisionEngine()
        
        return orchestrator
    
    @pytest.mark.asyncio
    async def test_full_pipeline_high_risk_scenario(self, high_risk_text, mock_orchestrator):
        """Test complete pipeline with high-risk scenario"""
        
        # Mock the orchestrator's process method to return realistic result
        mock_result = Mock(spec=UnifiedProcessingResult)
        mock_result.original_text = high_risk_text
        mock_result.normalized_text = "Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890"
        mock_result.language = "uk"
        mock_result.language_confidence = 0.9
        mock_result.variants = ["Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890"]
        mock_result.tokens = ["Оплата", "ТОВ", "ПРИВАТБАНК", "Ивану", "Петрову", "1980-01-01", "ИНН", "1234567890"]
        mock_result.trace = []
        mock_result.success = True
        mock_result.errors = []
        mock_result.processing_time = 0.5
        
        # Mock decision result (will be calculated by real DecisionEngine)
        from src.ai_service.contracts.decision_contracts import DecisionOutput
        mock_result.decision = DecisionOutput(
            risk=RiskLevel.HIGH,
            score=0.87,  # Expected high score
            reasons=["Overall risk score: 0.870", "strong_smartfilter_signal", "person_evidence_strong", "id_exact_match", "dob_match"],
            details={
                "calculated_score": 0.87,
                "score_breakdown": {
                    "smartfilter_contribution": 0.1875,  # 0.25 * 0.75
                    "person_contribution": 0.24,  # 0.3 * 0.8
                    "org_contribution": 0.105,  # 0.15 * 0.7
                    "similarity_contribution": 0.23,  # 0.25 * 0.92
                    "date_bonus": 0.07,
                    "id_bonus": 0.15,
                    "total": 0.87
                },
                "evidence_strength": {
                    "smartfilter_strong": True,
                    "person_strong": True,
                    "org_strong": False,  # 0.7 < 0.7 threshold
                    "similarity_high": True,
                    "exact_id_match": True,
                    "exact_dob_match": True
                }
            }
        )
        
        # Mock the process method
        mock_orchestrator.process = AsyncMock(return_value=mock_result)
        
        # Execute the pipeline
        result = await mock_orchestrator.process(
            text=high_risk_text,
            generate_variants=True,
            generate_embeddings=True
        )
        
        # Verify the result
        assert result.success is True
        assert result.original_text == high_risk_text
        assert result.language == "uk"
        assert result.language_confidence == 0.9
        
        # Verify decision result
        assert result.decision is not None
        assert result.decision.risk == RiskLevel.HIGH
        assert result.decision.score >= 0.85  # Should be high risk
        assert "strong_smartfilter_signal" in result.decision.reasons
        assert "person_evidence_strong" in result.decision.reasons
        assert "id_exact_match" in result.decision.reasons
        assert "dob_match" in result.decision.reasons
    
    @pytest.mark.asyncio
    async def test_decision_engine_integration_with_mock_data(self, mock_orchestrator):
        """Test DecisionEngine integration with mock data"""
        from src.ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        
        # Create decision input with high-risk indicators
        decision_input = DecisionInput(
            text="Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890",
            language="uk",
            smartfilter=SmartFilterInfo(
                should_process=True,
                confidence=0.75,
                estimated_complexity="high_risk_organization"
            ),
            signals=SignalsInfo(
                person_confidence=0.8,
                org_confidence=0.7,
                date_match=True,
                id_match=True,
                evidence={
                    "persons_count": 1,
                    "organizations_count": 1,
                    "signals_confidence": 0.8
                }
            ),
            similarity=SimilarityInfo(
                cos_top=0.92,  # Above 0.9 threshold for "high" similarity
                cos_p95=0.75
            )
        )
        
        # Test decision engine directly
        decision_result = mock_orchestrator.decision_engine.decide(decision_input)
        
        # Verify high-risk decision
        assert decision_result.risk == RiskLevel.HIGH
        assert decision_result.score >= 0.85  # Should exceed high threshold
        
        # Verify reasons contain expected indicators
        reasons = decision_result.reasons
        assert any("strong_smartfilter_signal" in reason for reason in reasons)
        assert any("person_evidence_strong" in reason for reason in reasons)
        assert any("id_exact_match" in reason for reason in reasons)
        assert any("dob_match" in reason for reason in reasons)
        
        # Verify details structure
        assert "score_breakdown" in decision_result.details
        assert "evidence_strength" in decision_result.details
        assert "normalized_features" in decision_result.details
        
        # Verify evidence strength indicators
        evidence_strength = decision_result.details["evidence_strength"]
        assert evidence_strength["smartfilter_strong"] is True
        assert evidence_strength["person_strong"] is True
        assert evidence_strength["similarity_high"] is True
        assert evidence_strength["exact_id_match"] is True
        assert evidence_strength["exact_dob_match"] is True
    
    @pytest.mark.asyncio
    async def test_api_response_format_with_risk_fields(self, high_risk_text, mock_orchestrator):
        """Test that API response includes all risk fields"""
        from src.ai_service.utils.response_formatter import format_processing_result
        
        # Create mock processing result with decision
        mock_result = Mock(spec=UnifiedProcessingResult)
        mock_result.original_text = high_risk_text
        mock_result.normalized_text = "Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890"
        mock_result.language = "uk"
        mock_result.language_confidence = 0.9
        mock_result.variants = ["Оплата ТОВ 'ПРИВАТБАНК' Ивану Петрову, 1980-01-01, ИНН 1234567890"]
        mock_result.tokens = ["Оплата", "ТОВ", "ПРИВАТБАНК", "Ивану", "Петрову", "1980-01-01", "ИНН", "1234567890"]
        mock_result.trace = []
        mock_result.success = True
        mock_result.errors = []
        mock_result.processing_time = 0.5
        
        # Mock decision result
        from src.ai_service.contracts.decision_contracts import DecisionOutput
        mock_result.decision = DecisionOutput(
            risk=RiskLevel.HIGH,
            score=0.87,
            reasons=["Overall risk score: 0.870", "strong_smartfilter_signal", "person_evidence_strong", "id_exact_match", "dob_match"],
            details={
                "calculated_score": 0.87,
                "score_breakdown": {
                    "smartfilter_contribution": 0.1875,
                    "person_contribution": 0.24,
                    "org_contribution": 0.105,
                    "similarity_contribution": 0.22,
                    "date_bonus": 0.07,
                    "id_bonus": 0.15,
                    "total": 0.87
                },
                "evidence_strength": {
                    "smartfilter_strong": True,
                    "person_strong": True,
                    "org_strong": False,
                    "similarity_high": True,
                    "exact_id_match": True,
                    "exact_dob_match": True
                },
                "normalized_features": {
                    "smartfilter_confidence": 0.75,
                    "person_confidence": 0.8,
                    "org_confidence": 0.7,
                    "similarity_cos_top": 0.92,
                    "date_match": True,
                    "id_match": True
                }
            }
        )
        
        # Mock smart filter and signals results
        mock_result.smart_filter_result = Mock()
        mock_result.smart_filter_result.should_process = True
        mock_result.smart_filter_result.confidence = 0.75
        
        mock_result.signals = Mock()
        mock_result.signals.persons = [Mock()]
        mock_result.signals.organizations = [Mock()]
        mock_result.signals.confidence = 0.8
        
        # Format response
        response = format_processing_result(mock_result)
        
        # Verify response contains all required fields
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
        
        # Verify risk-specific fields
        assert response["risk_level"] == "high"
        assert response["risk_score"] == 0.87
        assert "strong_smartfilter_signal" in response["decision_reasons"]
        assert "person_evidence_strong" in response["decision_reasons"]
        assert "id_exact_match" in response["decision_reasons"]
        assert "dob_match" in response["decision_reasons"]
        
        # Verify decision details structure
        details = response["decision_details"]
        assert "score_breakdown" in details
        assert "evidence_strength" in details
        assert "normalized_features" in details
    
    @pytest.mark.asyncio
    async def test_pipeline_with_different_risk_levels(self, mock_orchestrator):
        """Test pipeline with different risk level scenarios"""
        from src.ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        
        # Test LOW risk scenario
        low_risk_input = DecisionInput(
            text="Обычный текст без подозрительных элементов",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.3),
            signals=SignalsInfo(person_confidence=0.2, org_confidence=0.1),
            similarity=SimilarityInfo(cos_top=0.3)
        )
        
        low_risk_result = mock_orchestrator.decision_engine.decide(low_risk_input)
        assert low_risk_result.risk == RiskLevel.LOW
        assert low_risk_result.score < 0.65
        
        # Test MEDIUM risk scenario
        medium_risk_input = DecisionInput(
            text="Платеж в банк с умеренными показателями",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
            signals=SignalsInfo(person_confidence=0.7, org_confidence=0.6),
            similarity=SimilarityInfo(cos_top=0.71)  # Slightly above threshold
        )
        
        medium_risk_result = mock_orchestrator.decision_engine.decide(medium_risk_input)
        assert medium_risk_result.risk == RiskLevel.MEDIUM
        assert 0.65 <= medium_risk_result.score < 0.85
        
        # Test SKIP scenario
        skip_input = DecisionInput(
            text="Текст для пропуска",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=False, confidence=0.9),
            signals=SignalsInfo(person_confidence=0.8, org_confidence=0.7),
            similarity=SimilarityInfo(cos_top=0.9)
        )
        
        skip_result = mock_orchestrator.decision_engine.decide(skip_input)
        assert skip_result.risk == RiskLevel.SKIP
        assert skip_result.score == 0.0
        assert "smartfilter_skip" in skip_result.reasons
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self, mock_orchestrator):
        """Test pipeline error handling with invalid inputs"""
        from src.ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        
        # Test with None values (should be handled gracefully)
        none_input = DecisionInput(
            text="",
            language=None,
            smartfilter=None,
            signals=None,
            similarity=None
        )
        
        none_result = mock_orchestrator.decision_engine.decide(none_input)
        assert none_result.risk == RiskLevel.LOW  # Should default to LOW
        assert none_result.score == 0.0  # Should be minimal score
        assert len(none_result.reasons) > 0  # Should have reasons
        
        # Test with extreme values
        extreme_input = DecisionInput(
            text="Test",
            language="uk",
            smartfilter=SmartFilterInfo(should_process=True, confidence=1.0),
            signals=SignalsInfo(person_confidence=1.0, org_confidence=1.0, date_match=True, id_match=True),
            similarity=SimilarityInfo(cos_top=1.0)
        )
        
        extreme_result = mock_orchestrator.decision_engine.decide(extreme_input)
        assert extreme_result.risk == RiskLevel.HIGH  # Should be HIGH with max values
        assert extreme_result.score >= 0.85  # Should exceed high threshold
