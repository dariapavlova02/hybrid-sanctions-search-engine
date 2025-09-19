"""
Unit tests for search fallback logic.

Tests the fallback mechanisms when Elasticsearch is unavailable.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import List, Dict, Any

from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
from src.ai_service.layers.search.config import HybridSearchConfig
from src.ai_service.layers.search.contracts import SearchOpts, SearchMode, Candidate
from src.ai_service.contracts.base_contracts import NormalizationResult


class TestSearchFallbackLogic:
    """Test cases for search fallback logic"""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing"""
        return HybridSearchConfig(
            elasticsearch={
                "hosts": ["localhost:9200"],
                "timeout": 10,
                "max_retries": 3,
                "retry_on_timeout": True,
                "verify_certs": False,
                "ac_index": "test_ac",
                "vector_index": "test_vector",
                "smoke_test_timeout": 5
            },
            enable_fallback=True,
            fallback_threshold=0.5,
            fallback_timeout_ms=2000,
            fallback_max_results=100,
            enable_vector_fallback=True,
            vector_fallback_threshold=0.4,
            vector_fallback_timeout_ms=3000,
            vector_fallback_max_results=50
        )

    @pytest.fixture
    def mock_normalization_result(self):
        """Create a mock normalization result for testing"""
        return NormalizationResult(
            normalized="test name",
            tokens=["test", "name"],
            trace=[],
            errors=[],
            language="en",
            confidence=0.9,
            original_length=9,
            normalized_length=9,
            token_count=2,
            processing_time=0.1,
            success=True
        )

    @pytest.fixture
    def mock_fallback_candidates(self):
        """Create mock fallback search candidates"""
        return [
            Candidate(
                doc_id="fallback_1",
                score=0.85,
                text="Fallback Test Name",
                entity_type="person",
                metadata={"dob": "1990-01-01"},
                search_mode=SearchMode.FALLBACK_AC,
                match_fields=["name"],
                confidence=0.8
            ),
            Candidate(
                doc_id="fallback_2",
                score=0.75,
                text="Fallback Test Name Variant",
                entity_type="person",
                metadata={"dob": "1990-01-01"},
                search_mode=SearchMode.FALLBACK_VECTOR,
                match_fields=["name"],
                confidence=0.7
            )
        ]

    @pytest.fixture
    async def search_service_with_fallback(self, mock_config, mock_fallback_candidates):
        """Create a HybridSearchService with fallback services"""
        service = HybridSearchService(mock_config)
        
        # Mock the adapters (will fail)
        service._ac_adapter = AsyncMock()
        service._ac_adapter.search.side_effect = Exception("Elasticsearch unavailable")
        service._ac_adapter._connected = False
        
        service._vector_adapter = AsyncMock()
        service._vector_adapter.search.side_effect = Exception("Elasticsearch unavailable")
        service._vector_adapter._connected = False
        
        # Mock the fallback services
        service._fallback_watchlist_service = AsyncMock()
        service._fallback_watchlist_service.search.return_value = mock_fallback_candidates[:1]
        
        service._fallback_vector_service = AsyncMock()
        service._fallback_vector_service.search.return_value = mock_fallback_candidates[1:]
        
        # Mock the embedding service
        service._embedding_service = AsyncMock()
        service._embedding_service.generate_embedding.return_value = [0.1] * 384
        
        # Mock the client factory
        service._client_factory = AsyncMock()
        service._client_factory.health_check.return_value = {"status": "red"}
        
        # Initialize the service
        service._initialized = True
        
        return service

    @pytest.mark.asyncio
    async def test_fallback_when_elasticsearch_unavailable(self, search_service_with_fallback, mock_normalization_result, mock_fallback_candidates):
        """Test fallback when Elasticsearch is unavailable"""
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.7)
        result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        assert len(result) == 1
        assert result[0].search_mode == SearchMode.FALLBACK_AC
        assert result[0].doc_id == "fallback_1"
        assert result[0].score == 0.85
        search_service_with_fallback._fallback_watchlist_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_vector_fallback_when_elasticsearch_unavailable(self, search_service_with_fallback, mock_normalization_result, mock_fallback_candidates):
        """Test vector fallback when Elasticsearch is unavailable"""
        opts = SearchOpts(search_mode=SearchMode.VECTOR, top_k=10, threshold=0.7)
        result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        assert len(result) == 1
        assert result[0].search_mode == SearchMode.FALLBACK_VECTOR
        assert result[0].doc_id == "fallback_2"
        assert result[0].score == 0.75
        search_service_with_fallback._fallback_vector_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_hybrid_fallback_when_elasticsearch_unavailable(self, search_service_with_fallback, mock_normalization_result, mock_fallback_candidates):
        """Test hybrid fallback when Elasticsearch is unavailable"""
        opts = SearchOpts(search_mode=SearchMode.HYBRID, top_k=10, threshold=0.7)
        result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        # Should have both AC and vector fallback results
        assert len(result) == 2
        search_modes = [c.search_mode for c in result]
        assert SearchMode.FALLBACK_AC in search_modes
        assert SearchMode.FALLBACK_VECTOR in search_modes

    @pytest.mark.asyncio
    async def test_fallback_threshold_filtering(self, search_service_with_fallback, mock_normalization_result):
        """Test fallback results are filtered by threshold"""
        # Create candidates with different scores
        low_score_candidates = [
            Candidate(
                doc_id="low_1",
                score=0.3,  # Below threshold
                text="Low Score Name",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.FALLBACK_AC,
                match_fields=["name"],
                confidence=0.3
            ),
            Candidate(
                doc_id="high_1",
                score=0.8,  # Above threshold
                text="High Score Name",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.FALLBACK_AC,
                match_fields=["name"],
                confidence=0.8
            )
        ]
        
        search_service_with_fallback._fallback_watchlist_service.search.return_value = low_score_candidates
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.5)
        result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        # Should only return high score candidate
        assert len(result) == 1
        assert result[0].score == 0.8

    @pytest.mark.asyncio
    async def test_fallback_max_results_limit(self, search_service_with_fallback, mock_normalization_result):
        """Test fallback respects max results limit"""
        # Create many candidates
        many_candidates = [
            Candidate(
                doc_id=f"candidate_{i}",
                score=0.8,
                text=f"Name {i}",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.FALLBACK_AC,
                match_fields=["name"],
                confidence=0.8
            )
            for i in range(150)  # More than max_results (100)
        ]
        
        search_service_with_fallback._fallback_watchlist_service.search.return_value = many_candidates
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.5)
        result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        # Should be limited to max_results
        assert len(result) <= 100

    @pytest.mark.asyncio
    async def test_fallback_timeout_handling(self, search_service_with_fallback, mock_normalization_result):
        """Test fallback timeout handling"""
        # Mock slow fallback service
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate slow response
            return []
        
        search_service_with_fallback._fallback_watchlist_service.search.side_effect = slow_search
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.5)
        result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        # Should handle timeout gracefully
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_service_unavailable(self, search_service_with_fallback, mock_normalization_result):
        """Test when fallback services are unavailable"""
        # Mock fallback service failure
        search_service_with_fallback._fallback_watchlist_service.search.side_effect = Exception("Fallback service unavailable")
        search_service_with_fallback._fallback_vector_service.search.side_effect = Exception("Fallback service unavailable")
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.5)
        result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        # Should return empty list when all services fail
        assert result == []

    @pytest.mark.asyncio
    async def test_fallback_health_check(self, search_service_with_fallback):
        """Test fallback service health check"""
        # Mock health check responses
        search_service_with_fallback._fallback_watchlist_service.health_check.return_value = {"status": "healthy"}
        search_service_with_fallback._fallback_vector_service.health_check.return_value = {"status": "healthy"}
        
        health = await search_service_with_fallback.health_check()
        
        assert "fallback_services" in health
        assert health["fallback_services"]["watchlist"]["status"] == "healthy"
        assert health["fallback_services"]["vector"]["status"] == "healthy"

    @pytest.mark.asyncio
    async def test_fallback_health_check_failure(self, search_service_with_fallback):
        """Test fallback service health check failure"""
        # Mock health check failure
        search_service_with_fallback._fallback_watchlist_service.health_check.side_effect = Exception("Health check failed")
        search_service_with_fallback._fallback_vector_service.health_check.side_effect = Exception("Health check failed")
        
        health = await search_service_with_fallback.health_check()
        
        assert "fallback_services" in health
        assert health["fallback_services"]["watchlist"]["status"] == "error"
        assert health["fallback_services"]["vector"]["status"] == "error"

    @pytest.mark.asyncio
    async def test_fallback_with_embedding_cache(self, search_service_with_fallback, mock_normalization_result):
        """Test fallback with embedding cache"""
        # First call should generate embedding
        query_vector1 = await search_service_with_fallback._build_query_vector(mock_normalization_result, "test name")
        
        # Second call should use cache
        query_vector2 = await search_service_with_fallback._build_query_vector(mock_normalization_result, "test name")
        
        assert query_vector1 == query_vector2
        # Should only call embedding service once
        search_service_with_fallback._embedding_service.generate_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_fallback_metrics_collection(self, search_service_with_fallback, mock_normalization_result, mock_fallback_candidates):
        """Test fallback metrics collection"""
        search_service_with_fallback._fallback_watchlist_service.search.return_value = mock_fallback_candidates[:1]
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.5)
        await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
        
        # Check that fallback metrics were updated
        metrics = search_service_with_fallback.get_metrics()
        assert metrics.fallback_requests > 0
        assert metrics.avg_fallback_latency_ms > 0

    @pytest.mark.asyncio
    async def test_fallback_disabled(self, mock_config, mock_normalization_result):
        """Test fallback when disabled"""
        # Disable fallback
        mock_config.enable_fallback = False
        
        service = HybridSearchService(mock_config)
        
        # Mock the adapters (will fail)
        service._ac_adapter = AsyncMock()
        service._ac_adapter.search.side_effect = Exception("Elasticsearch unavailable")
        service._ac_adapter._connected = False
        
        # Mock the fallback services (should not be called)
        service._fallback_watchlist_service = AsyncMock()
        service._fallback_vector_service = AsyncMock()
        
        service._initialized = True
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.5)
        result = await service.find_candidates(mock_normalization_result, "test name", opts)
        
        # Should return empty list when fallback is disabled
        assert result == []
        
        # Fallback services should not be called
        service._fallback_watchlist_service.search.assert_not_called()
        service._fallback_vector_service.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_fallback_error_logging(self, search_service_with_fallback, mock_normalization_result):
        """Test fallback error logging"""
        # Mock fallback service failure
        search_service_with_fallback._fallback_watchlist_service.search.side_effect = Exception("Fallback service error")
        
        with patch('src.ai_service.layers.search.hybrid_search_service.get_logger') as mock_logger:
            opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.5)
            result = await search_service_with_fallback.find_candidates(mock_normalization_result, "test name", opts)
            
            # Should log the error
            mock_logger.return_value.error.assert_called()
            assert result == []
