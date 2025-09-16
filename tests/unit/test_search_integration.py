"""
Unit tests for search integration functionality.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.ai_service.core.search_integration import SearchIntegration, create_search_integration
from src.ai_service.contracts.search_contracts import (
    SearchOpts, SearchMode, SearchType, Candidate, SearchInfo
)
from src.ai_service.contracts.base_contracts import NormalizationResult


class TestSearchIntegration:
    """Test SearchIntegration class."""
    
    def test_init_with_service(self):
        """Test initialization with hybrid search service."""
        mock_service = MagicMock()
        integration = SearchIntegration(mock_service)
        
        assert integration.hybrid_search_service == mock_service
        assert integration.logger is not None
    
    def test_init_without_service(self):
        """Test initialization without hybrid search service."""
        integration = SearchIntegration(None)
        
        assert integration.hybrid_search_service is None
        assert integration.logger is not None
    
    @pytest.mark.asyncio
    async def test_extract_and_search_with_service(self, mock_hybrid_search_service, mock_normalization_result, mock_signals_result):
        """Test extract_and_search with hybrid search service."""
        integration = SearchIntegration(mock_hybrid_search_service)
        
        search_opts = SearchOpts(
            top_k=50,
            threshold=0.7,
            search_mode=SearchMode.HYBRID
        )
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result,
            search_opts=search_opts
        )
        
        assert result is not None
        assert isinstance(result, SearchInfo)
        assert result.total_matches == 1
        assert result.search_time > 0
    
    @pytest.mark.asyncio
    async def test_extract_and_search_without_service(self, mock_normalization_result, mock_signals_result):
        """Test extract_and_search without hybrid search service."""
        integration = SearchIntegration(None)
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_extract_and_search_no_candidates(self, mock_hybrid_search_service, mock_normalization_result):
        """Test extract_and_search with no search candidates."""
        integration = SearchIntegration(mock_hybrid_search_service)
        
        # Empty signals result
        empty_signals_result = {"persons": [], "organizations": []}
        
        result = await integration.extract_and_search(
            text="test text",
            normalization_result=mock_normalization_result,
            signals_result=empty_signals_result
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_extract_and_search_service_error(self, mock_hybrid_search_service, mock_normalization_result, mock_signals_result):
        """Test extract_and_search with service error."""
        # Mock service to raise exception
        mock_hybrid_search_service.find_candidates.side_effect = Exception("Search service error")
        
        integration = SearchIntegration(mock_hybrid_search_service)
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result
        )
        
        assert result is None
    
    def test_create_decision_input_with_search(self, mock_signals_result):
        """Test create_decision_input_with_search."""
        from src.ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        
        integration = SearchIntegration(None)
        
        # Create original decision input
        original_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=1.0),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo()
        )
        
        # Create search info
        search_info = SearchInfo(
            has_exact_matches=True,
            has_phrase_matches=False,
            has_ngram_matches=True,
            has_vector_matches=True,
            exact_confidence=0.9,
            phrase_confidence=0.0,
            ngram_confidence=0.6,
            vector_confidence=0.8,
            total_matches=2,
            high_confidence_matches=1,
            search_time=0.1
        )
        
        # Create updated decision input
        updated_input = integration.create_decision_input_with_search(
            original_input, search_info
        )
        
        assert updated_input.text == original_input.text
        assert updated_input.language == original_input.language
        assert updated_input.smartfilter == original_input.smartfilter
        assert updated_input.signals == original_input.signals
        assert updated_input.similarity == original_input.similarity
        assert updated_input.search == search_info
    
    def test_create_decision_input_without_search(self, mock_signals_result):
        """Test create_decision_input_with_search without search info."""
        from src.ai_service.contracts.decision_contracts import DecisionInput, SmartFilterInfo, SignalsInfo, SimilarityInfo
        
        integration = SearchIntegration(None)
        
        # Create original decision input
        original_input = DecisionInput(
            text="иван петров",
            language="ru",
            smartfilter=SmartFilterInfo(should_process=True, confidence=1.0),
            signals=SignalsInfo(person_confidence=0.9, org_confidence=0.0),
            similarity=SimilarityInfo()
        )
        
        # Create updated decision input without search
        updated_input = integration.create_decision_input_with_search(
            original_input, None
        )
        
        assert updated_input.text == original_input.text
        assert updated_input.language == original_input.language
        assert updated_input.smartfilter == original_input.smartfilter
        assert updated_input.signals == original_input.signals
        assert updated_input.similarity == original_input.similarity
        assert updated_input.search is None
    
    def test_should_enable_search_with_persons(self, mock_signals_result):
        """Test should_enable_search with persons."""
        integration = SearchIntegration(None)
        
        result = integration.should_enable_search(mock_signals_result)
        assert result is True
    
    def test_should_enable_search_with_organizations(self):
        """Test should_enable_search with organizations."""
        integration = SearchIntegration(None)
        
        signals_result = {
            "persons": [],
            "organizations": [{"normalized_name": "ооо приватбанк"}]
        }
        
        result = integration.should_enable_search(signals_result)
        assert result is True
    
    def test_should_enable_search_empty(self):
        """Test should_enable_search with empty signals."""
        integration = SearchIntegration(None)
        
        signals_result = {"persons": [], "organizations": []}
        
        result = integration.should_enable_search(signals_result)
        assert result is False
    
    def test_should_enable_search_no_entities(self):
        """Test should_enable_search with no entities."""
        integration = SearchIntegration(None)
        
        signals_result = {}
        
        result = integration.should_enable_search(signals_result)
        assert result is False
    
    def test_get_search_metrics_with_service(self, mock_hybrid_search_service):
        """Test get_search_metrics with service."""
        integration = SearchIntegration(mock_hybrid_search_service)
        
        metrics = integration.get_search_metrics()
        
        assert "ac_attempts" in metrics
        assert "vector_attempts" in metrics
        assert "ac_success" in metrics
        assert "vector_success" in metrics
        assert "ac_latency_p95" in metrics
        assert "vector_latency_p95" in metrics
        assert "hit_rate" in metrics
        assert "escalation_rate" in metrics
    
    def test_get_search_metrics_without_service(self):
        """Test get_search_metrics without service."""
        integration = SearchIntegration(None)
        
        metrics = integration.get_search_metrics()
        
        assert metrics == {}
    
    def test_get_search_metrics_service_error(self, mock_hybrid_search_service):
        """Test get_search_metrics with service error."""
        # Mock service to raise exception
        mock_hybrid_search_service.get_metrics.side_effect = Exception("Metrics error")
        
        integration = SearchIntegration(mock_hybrid_search_service)
        
        metrics = integration.get_search_metrics()
        
        assert metrics == {}


class TestCreateSearchIntegration:
    """Test create_search_integration factory function."""
    
    def test_create_with_service(self):
        """Test creating SearchIntegration with service."""
        mock_service = MagicMock()
        integration = create_search_integration(mock_service)
        
        assert isinstance(integration, SearchIntegration)
        assert integration.hybrid_search_service == mock_service
    
    def test_create_without_service(self):
        """Test creating SearchIntegration without service."""
        integration = create_search_integration(None)
        
        assert isinstance(integration, SearchIntegration)
        assert integration.hybrid_search_service is None


class TestSearchIntegrationThresholds:
    """Test search integration threshold handling."""
    
    @pytest.mark.asyncio
    async def test_threshold_normalization(self, mock_hybrid_search_service, mock_normalization_result, mock_signals_result):
        """Test that thresholds are properly normalized."""
        integration = SearchIntegration(mock_hybrid_search_service)
        
        # Test with different threshold values
        search_opts = SearchOpts(
            top_k=25,
            threshold=0.5,  # Lower threshold
            search_mode=SearchMode.HYBRID
        )
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result,
            search_opts=search_opts
        )
        
        assert result is not None
        # Verify that the search options were passed correctly
        mock_hybrid_search_service.find_candidates.assert_called_once()
        call_args = mock_hybrid_search_service.find_candidates.call_args
        assert call_args[1]["opts"].threshold == 0.5
        assert call_args[1]["opts"].top_k == 25
    
    @pytest.mark.asyncio
    async def test_search_mode_handling(self, mock_hybrid_search_service, mock_normalization_result, mock_signals_result):
        """Test different search modes."""
        integration = SearchIntegration(mock_hybrid_search_service)
        
        # Test AC mode
        search_opts = SearchOpts(
            search_mode=SearchMode.AC,
            enable_escalation=False
        )
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result,
            search_opts=search_opts
        )
        
        assert result is not None
        call_args = mock_hybrid_search_service.find_candidates.call_args
        assert call_args[1]["opts"].search_mode == SearchMode.AC
        assert call_args[1]["opts"].enable_escalation is False


class TestSearchIntegrationErrorHandling:
    """Test search integration error handling."""
    
    @pytest.mark.asyncio
    async def test_elasticsearch_connection_error(self, mock_normalization_result, mock_signals_result):
        """Test handling of Elasticsearch connection errors."""
        from src.ai_service.exceptions import ElasticsearchConnectionError
        
        # Mock service to raise ElasticsearchConnectionError
        mock_service = MagicMock()
        mock_service.find_candidates.side_effect = ElasticsearchConnectionError("Connection failed")
        
        integration = SearchIntegration(mock_service)
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_timeout_error(self, mock_normalization_result, mock_signals_result):
        """Test handling of search timeout errors."""
        from src.ai_service.exceptions import SearchTimeoutError
        
        # Mock service to raise SearchTimeoutError
        mock_service = MagicMock()
        mock_service.find_candidates.side_effect = SearchTimeoutError("Search timeout")
        
        integration = SearchIntegration(mock_service)
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_search_service_error(self, mock_normalization_result, mock_signals_result):
        """Test handling of general search service errors."""
        from src.ai_service.exceptions import SearchServiceError
        
        # Mock service to raise SearchServiceError
        mock_service = MagicMock()
        mock_service.find_candidates.side_effect = SearchServiceError("Service error")
        
        integration = SearchIntegration(mock_service)
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result
        )
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_unexpected_error(self, mock_normalization_result, mock_signals_result):
        """Test handling of unexpected errors."""
        # Mock service to raise unexpected error
        mock_service = MagicMock()
        mock_service.find_candidates.side_effect = ValueError("Unexpected error")
        
        integration = SearchIntegration(mock_service)
        
        result = await integration.extract_and_search(
            text="иван петров",
            normalization_result=mock_normalization_result,
            signals_result=mock_signals_result
        )
        
        assert result is None
