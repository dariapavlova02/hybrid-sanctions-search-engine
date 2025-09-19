"""
Unit tests for HybridSearchService.

Tests the core functionality of the hybrid search service including
AC search, vector search, hybrid search, and fallback mechanisms.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from typing import List, Dict, Any

from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
from src.ai_service.layers.search.config import HybridSearchConfig
from src.ai_service.layers.search.contracts import SearchOpts, SearchMode, Candidate
from src.ai_service.contracts.base_contracts import NormalizationResult
from src.ai_service.exceptions import ServiceInitializationError


class TestHybridSearchService:
    """Test cases for HybridSearchService"""

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
            vector_dimension=384,
            vector_similarity_threshold=0.7,
            enable_embedding_cache=True,
            embedding_cache_size=100,
            embedding_cache_ttl_seconds=3600
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
    def mock_candidates(self):
        """Create mock search candidates for testing"""
        return [
            Candidate(
                doc_id="1",
                score=0.95,
                text="Test Name",
                entity_type="person",
                metadata={"dob": "1990-01-01"},
                search_mode=SearchMode.AC,
                match_fields=["name"],
                confidence=0.9
            ),
            Candidate(
                doc_id="2",
                score=0.85,
                text="Test Name Variant",
                entity_type="person",
                metadata={"dob": "1990-01-01"},
                search_mode=SearchMode.VECTOR,
                match_fields=["name"],
                confidence=0.8
            )
        ]

    @pytest.fixture
    async def search_service(self, mock_config):
        """Create a HybridSearchService instance for testing"""
        service = HybridSearchService(mock_config)
        
        # Mock the adapters
        service._ac_adapter = AsyncMock()
        service._vector_adapter = AsyncMock()
        service._client_factory = AsyncMock()
        
        # Mock the fallback services
        service._fallback_watchlist_service = AsyncMock()
        service._fallback_vector_service = AsyncMock()
        
        # Mock the embedding service
        service._embedding_service = AsyncMock()
        service._embedding_service.generate_embedding.return_value = [0.1] * 384
        
        # Mock the metrics service
        service.metrics_service = AsyncMock()
        
        # Initialize the service
        service._initialized = True
        
        return service

    @pytest.mark.asyncio
    async def test_initialization_success(self, mock_config):
        """Test successful service initialization"""
        with patch('src.ai_service.layers.search.hybrid_search_service.ElasticsearchClientFactory') as mock_factory:
            with patch('src.ai_service.layers.search.hybrid_search_service.ElasticsearchACAdapter') as mock_ac:
                with patch('src.ai_service.layers.search.hybrid_search_service.ElasticsearchVectorAdapter') as mock_vector:
                    service = HybridSearchService(mock_config)
                    await service.initialize()
                    
                    assert service._initialized is True
                    assert service._ac_adapter is not None
                    assert service._vector_adapter is not None

    @pytest.mark.asyncio
    async def test_initialization_failure(self, mock_config):
        """Test service initialization failure"""
        with patch('src.ai_service.layers.search.hybrid_search_service.ElasticsearchClientFactory') as mock_factory:
            mock_factory.side_effect = Exception("Connection failed")
            
            service = HybridSearchService(mock_config)
            
            with pytest.raises(ServiceInitializationError):
                await service.initialize()

    @pytest.mark.asyncio
    async def test_find_candidates_ac_mode(self, search_service, mock_normalization_result, mock_candidates):
        """Test AC search mode"""
        # Mock AC adapter response
        search_service._ac_adapter.search.return_value = mock_candidates
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.7)
        result = await search_service.find_candidates(mock_normalization_result, "test name", opts)
        
        assert len(result) == 2
        assert result[0].search_mode == SearchMode.AC
        assert result[0].score == 0.95
        search_service._ac_adapter.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_candidates_vector_mode(self, search_service, mock_normalization_result, mock_candidates):
        """Test vector search mode"""
        # Mock vector adapter response
        search_service._vector_adapter.search.return_value = mock_candidates
        
        opts = SearchOpts(search_mode=SearchMode.VECTOR, top_k=10, threshold=0.7)
        result = await search_service.find_candidates(mock_normalization_result, "test name", opts)
        
        assert len(result) == 2
        assert result[1].search_mode == SearchMode.VECTOR
        assert result[1].score == 0.85
        search_service._vector_adapter.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_find_candidates_hybrid_mode(self, search_service, mock_normalization_result, mock_candidates):
        """Test hybrid search mode"""
        # Mock both adapters
        search_service._ac_adapter.search.return_value = mock_candidates[:1]
        search_service._vector_adapter.search.return_value = mock_candidates[1:]
        
        opts = SearchOpts(search_mode=SearchMode.HYBRID, top_k=10, threshold=0.7)
        result = await search_service.find_candidates(mock_normalization_result, "test name", opts)
        
        assert len(result) == 2
        # Should have both AC and vector results
        search_modes = [c.search_mode for c in result]
        assert SearchMode.AC in search_modes
        assert SearchMode.VECTOR in search_modes

    @pytest.mark.asyncio
    async def test_fallback_search(self, search_service, mock_normalization_result, mock_candidates):
        """Test fallback search when Elasticsearch is unavailable"""
        # Mock AC adapter failure
        search_service._ac_adapter.search.side_effect = Exception("Elasticsearch unavailable")
        search_service._ac_adapter._connected = False
        
        # Mock fallback service
        search_service._fallback_watchlist_service.search.return_value = mock_candidates
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.7)
        result = await search_service.find_candidates(mock_normalization_result, "test name", opts)
        
        assert len(result) == 2
        search_service._fallback_watchlist_service.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_embedding_cache(self, search_service, mock_normalization_result):
        """Test embedding caching functionality"""
        # First call should generate embedding
        query_vector1 = await search_service._build_query_vector(mock_normalization_result, "test name")
        
        # Second call should use cache
        query_vector2 = await search_service._build_query_vector(mock_normalization_result, "test name")
        
        assert query_vector1 == query_vector2
        # Should only call embedding service once
        search_service._embedding_service.generate_embedding.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check(self, search_service):
        """Test health check functionality"""
        # Mock health check responses
        search_service._ac_adapter.health_check.return_value = {"status": "healthy"}
        search_service._vector_adapter.health_check.return_value = {"status": "healthy"}
        search_service._client_factory.health_check.return_value = {"status": "green"}
        
        health = await search_service.health_check()
        
        assert health["status"] == "healthy"
        assert "elasticsearch" in health
        assert "adapters" in health
        assert "fallback_services" in health
        assert "embedding_cache" in health

    @pytest.mark.asyncio
    async def test_metrics_collection(self, search_service, mock_normalization_result, mock_candidates):
        """Test metrics collection"""
        # Mock AC adapter response
        search_service._ac_adapter.search.return_value = mock_candidates
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.7)
        await search_service.find_candidates(mock_normalization_result, "test name", opts)
        
        # Check that metrics were updated
        metrics = search_service.get_metrics()
        assert metrics.total_requests > 0
        assert metrics.ac_requests > 0
        assert metrics.avg_hybrid_latency_ms > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, search_service, mock_normalization_result):
        """Test error handling in search operations"""
        # Mock adapter failure
        search_service._ac_adapter.search.side_effect = Exception("Search failed")
        search_service._fallback_watchlist_service.search.side_effect = Exception("Fallback failed")
        
        opts = SearchOpts(search_mode=SearchMode.AC, top_k=10, threshold=0.7)
        result = await search_service.find_candidates(mock_normalization_result, "test name", opts)
        
        # Should return empty list on error
        assert result == []

    @pytest.mark.asyncio
    async def test_configuration_validation(self, mock_config):
        """Test configuration validation"""
        # Test valid configuration
        service = HybridSearchService(mock_config)
        assert service.config == mock_config
        
        # Test invalid configuration
        invalid_config = HybridSearchConfig(
            elasticsearch={
                "hosts": [],  # Invalid: empty hosts
                "timeout": 10,
                "max_retries": 3,
                "retry_on_timeout": True,
                "verify_certs": False,
                "ac_index": "test_ac",
                "vector_index": "test_vector",
                "smoke_test_timeout": 5
            }
        )
        
        with pytest.raises(ValueError):
            service = HybridSearchService(invalid_config)

    @pytest.mark.asyncio
    async def test_clear_embedding_cache(self, search_service):
        """Test embedding cache clearing"""
        # Add some items to cache
        await search_service._build_query_vector(
            NormalizationResult(
                normalized="test1", tokens=["test1"], trace=[], errors=[],
                language="en", confidence=0.9, original_length=5, normalized_length=5,
                token_count=1, processing_time=0.1, success=True
            ),
            "test1"
        )
        
        # Clear cache
        await search_service.clear_embedding_cache()
        
        # Cache should be empty
        stats = await search_service.get_embedding_cache_stats()
        assert stats["cache_size"] == 0

    def test_search_trace_creation(self, search_service):
        """Test search trace creation and management"""
        from src.ai_service.layers.search.hybrid_search_service import SearchTrace
        
        trace = SearchTrace(query="test", mode=SearchMode.AC)
        assert trace.query == "test"
        assert trace.mode == SearchMode.AC
        assert trace.enabled is True
        
        # Test trace finalization
        trace.finalize(100.0, 5)
        assert trace.total_time_ms == 100.0
        assert trace.total_hits == 5
