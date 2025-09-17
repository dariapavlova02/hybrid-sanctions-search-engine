"""
Unit tests for SearchTrace integration in decision engine and orchestrator.
"""

import pytest
from unittest.mock import Mock, patch
from src.ai_service.core.decision_engine import DecisionEngine
from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
from src.ai_service.contracts.trace_models import SearchTrace, SearchTraceBuilder
from src.ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
from src.ai_service.config.feature_flags import FeatureFlags


class TestSearchTraceIntegration:
    """Test SearchTrace integration in decision engine and orchestrator."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.decision_engine = DecisionEngine()
        self.search_trace = SearchTrace(enabled=True)
    
    def test_decision_engine_with_search_trace(self):
        """Test decision engine with search trace."""
        # Create test input
        decision_input = DecisionInput(
            text="John Doe",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.8),
            signals=SignalsInfo(
                person_confidence=0.9,
                org_confidence=0.1,
                date_match=False,
                id_match=False,
                evidence={}
            ),
            similarity=SimilarityInfo(cos_top=0.85, cos_p95=0.75)
        )
        
        # Add some trace data
        self.search_trace.note("AC search completed with 3 results")
        self.search_trace.note("Vector fallback engaged")
        
        # Make decision with trace
        result = self.decision_engine.decide(decision_input, self.search_trace)
        
        # Check result
        assert result.risk is not None
        assert result.score > 0
        assert len(result.reasons) > 0
        
        # Check that search trace was added to details
        assert "search_trace" in result.details
        trace_data = result.details["search_trace"]
        assert trace_data["enabled"] is True
        assert len(trace_data["notes"]) == 2
        assert "AC search completed" in trace_data["notes"][0]
        assert "Vector fallback engaged" in trace_data["notes"][1]
    
    def test_decision_engine_without_search_trace(self):
        """Test decision engine without search trace."""
        decision_input = DecisionInput(
            text="Jane Smith",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.7),
            signals=SignalsInfo(
                person_confidence=0.8,
                org_confidence=0.2,
                date_match=True,
                id_match=False,
                evidence={}
            ),
            similarity=SimilarityInfo(cos_top=0.9, cos_p95=0.8)
        )
        
        # Make decision without trace
        result = self.decision_engine.decide(decision_input)
        
        # Check result
        assert result.risk is not None
        assert result.score > 0
        assert len(result.reasons) > 0
        
        # Check that no search trace was added
        assert "search_trace" not in result.details
    
    def test_decision_engine_with_disabled_trace(self):
        """Test decision engine with disabled search trace."""
        disabled_trace = SearchTrace(enabled=False)
        disabled_trace.note("This should not be added")
        
        decision_input = DecisionInput(
            text="Test User",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.6),
            signals=SignalsInfo(
                person_confidence=0.7,
                org_confidence=0.3,
                date_match=False,
                id_match=True,
                evidence={}
            ),
            similarity=SimilarityInfo(cos_top=0.7, cos_p95=0.6)
        )
        
        # Make decision with disabled trace
        result = self.decision_engine.decide(decision_input, disabled_trace)
        
        # Check result
        assert result.risk is not None
        assert result.score > 0
        
        # Check that no search trace was added (disabled)
        assert "search_trace" not in result.details
    
    async def test_orchestrator_search_trace_propagation(self):
        """Test orchestrator search trace propagation."""
        # Mock services
        mock_validation = Mock()
        mock_validation.validate_and_sanitize.return_value = {"should_process": True, "sanitized_text": "test"}
        
        mock_language = Mock()
        mock_language.detect_language_config_driven.return_value = {"language": "en", "confidence": 0.9}
        
        mock_unicode = Mock()
        mock_unicode.normalize_unicode.return_value = "test"
        
        mock_normalization = Mock()
        mock_normalization.normalize_async.return_value = Mock(
            normalized="test",
            tokens=["test"],
            trace=[],
            success=True,
            errors=[]
        )
        
        mock_signals = Mock()
        mock_signals.extract_signals.return_value = Mock(
            persons=[],
            organizations=[],
            confidence=0.8
        )
        
        mock_decision_engine = Mock()
        mock_decision_engine.decide.return_value = Mock(
            risk="LOW",
            score=0.5,
            reasons=["test"],
            details={}
        )
        
        # Create orchestrator
        orchestrator = UnifiedOrchestrator(
            validation_service=mock_validation,
            language_service=mock_language,
            unicode_service=mock_unicode,
            normalization_service=mock_normalization,
            signals_service=mock_signals,
            decision_engine=mock_decision_engine,
            enable_decision_engine=True
        )
        
        # Test with search trace enabled
        result = await orchestrator.process(
            "test text",
            search_trace_enabled=True
        )
        
        # Check that decision engine was called with search trace
        mock_decision_engine.decide.assert_called_once()
        call_args = mock_decision_engine.decide.call_args
        assert len(call_args[0]) == 2  # decision_input, search_trace
        assert call_args[0][1] is not None  # search_trace should be passed
        assert call_args[0][1].enabled is True
    
    async def test_orchestrator_without_search_trace(self):
        """Test orchestrator without search trace."""
        # Mock services
        mock_validation = Mock()
        mock_validation.validate_and_sanitize.return_value = {"should_process": True, "sanitized_text": "test"}
        
        mock_language = Mock()
        mock_language.detect_language_config_driven.return_value = {"language": "en", "confidence": 0.9}
        
        mock_unicode = Mock()
        mock_unicode.normalize_unicode.return_value = "test"
        
        mock_normalization = Mock()
        mock_normalization.normalize_async.return_value = Mock(
            normalized="test",
            tokens=["test"],
            trace=[],
            success=True,
            errors=[]
        )
        
        mock_signals = Mock()
        mock_signals.extract_signals.return_value = Mock(
            persons=[],
            organizations=[],
            confidence=0.8
        )
        
        mock_decision_engine = Mock()
        mock_decision_engine.decide.return_value = Mock(
            risk="LOW",
            score=0.5,
            reasons=["test"],
            details={}
        )
        
        # Create orchestrator
        orchestrator = UnifiedOrchestrator(
            validation_service=mock_validation,
            language_service=mock_language,
            unicode_service=mock_unicode,
            normalization_service=mock_normalization,
            signals_service=mock_signals,
            decision_engine=mock_decision_engine,
            enable_decision_engine=True
        )
        
        # Test without search trace
        result = await orchestrator.process(
            "test text",
            search_trace_enabled=False
        )
        
        # Check that decision engine was called without search trace
        mock_decision_engine.decide.assert_called_once()
        call_args = mock_decision_engine.decide.call_args
        assert len(call_args[0]) == 2  # decision_input, search_trace
        assert call_args[0][1] is None  # search_trace should be None
    
    async def test_search_trace_notes_in_orchestrator(self):
        """Test that orchestrator adds appropriate trace notes."""
        # Mock services
        mock_validation = Mock()
        mock_validation.validate_and_sanitize.return_value = {"should_process": True, "sanitized_text": "test"}
        
        mock_language = Mock()
        mock_language.detect_language_config_driven.return_value = {"language": "en", "confidence": 0.9}
        
        mock_unicode = Mock()
        mock_unicode.normalize_unicode.return_value = "test"
        
        mock_normalization = Mock()
        mock_normalization.normalize_async.return_value = Mock(
            normalized="test",
            tokens=["TEST", "USER"],  # Uppercase tokens for AC pattern detection
            trace=[],
            success=True,
            errors=[]
        )
        
        mock_signals = Mock()
        mock_signals.extract_signals.return_value = Mock(
            persons=[],
            organizations=[],
            confidence=0.8
        )
        
        mock_embeddings = Mock()
        mock_embeddings.generate_embeddings.return_value = [0.1, 0.2, 0.3]
        
        mock_decision_engine = Mock()
        mock_decision_engine.decide.return_value = Mock(
            risk="LOW",
            score=0.5,
            reasons=["test"],
            details={}
        )
        
        # Create orchestrator
        orchestrator = UnifiedOrchestrator(
            validation_service=mock_validation,
            language_service=mock_language,
            unicode_service=mock_unicode,
            normalization_service=mock_normalization,
            signals_service=mock_signals,
            embeddings_service=mock_embeddings,
            decision_engine=mock_decision_engine,
            enable_decision_engine=True
        )
        
        # Test with search trace enabled
        result = await orchestrator.process(
            "test text",
            search_trace_enabled=True,
            generate_embeddings=True
        )
        
        # Check that decision engine was called with search trace
        mock_decision_engine.decide.assert_called_once()
        call_args = mock_decision_engine.decide.call_args
        search_trace = call_args[0][1]
        
        # Check that trace has appropriate notes
        assert search_trace is not None
        assert search_trace.enabled is True
        assert len(search_trace.notes) >= 2  # At least smart filter and AC pattern notes
        
        # Check for specific notes
        notes_text = " ".join(search_trace.notes)
        assert "Smart filter passed" in notes_text
        assert "AC patterns detected" in notes_text
        assert "Vector fallback engaged" in notes_text
    
    def test_search_trace_serialization(self):
        """Test search trace serialization in decision details."""
        # Create a trace with some data
        trace = SearchTrace(enabled=True)
        trace.note("Test note 1")
        trace.note("Test note 2")
        
        # Create decision input
        decision_input = DecisionInput(
            text="Test",
            language="en",
            smartfilter=SmartFilterInfo(should_process=True, confidence=0.5),
            signals=SignalsInfo(
                person_confidence=0.6,
                org_confidence=0.4,
                date_match=False,
                id_match=False,
                evidence={}
            ),
            similarity=SimilarityInfo(cos_top=0.7, cos_p95=0.6)
        )
        
        # Make decision
        result = self.decision_engine.decide(decision_input, trace)
        
        # Check serialization
        assert "search_trace" in result.details
        trace_data = result.details["search_trace"]
        
        assert trace_data["enabled"] is True
        assert len(trace_data["notes"]) == 2
        assert trace_data["notes"][0] == "Test note 1"
        assert trace_data["notes"][1] == "Test note 2"
        assert "total_time_ms" in trace_data
        assert "total_hits" in trace_data
