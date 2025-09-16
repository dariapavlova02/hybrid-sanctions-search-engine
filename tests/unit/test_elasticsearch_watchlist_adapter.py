"""
Unit tests for ElasticsearchWatchlistAdapter.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from src.ai_service.layers.embeddings.indexing.elasticsearch_watchlist_adapter import (
    ElasticsearchWatchlistAdapter,
    ElasticsearchWatchlistConfig,
    create_elasticsearch_watchlist_adapter,
    create_elasticsearch_enhanced_adapter
)
from src.ai_service.layers.embeddings.indexing.watchlist_index_service import WatchlistIndexService
from src.ai_service.layers.embeddings.indexing.vector_index_service import VectorIndexConfig


class TestElasticsearchWatchlistConfig:
    """Test ElasticsearchWatchlistConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = ElasticsearchWatchlistConfig()
        
        assert config.es_url == "http://localhost:9200"
        assert config.es_auth is None
        assert config.es_verify_ssl is False
        assert config.es_timeout == 30.0
        assert config.persons_index == "watchlist_persons_current"
        assert config.orgs_index == "watchlist_orgs_current"
        assert config.ac_threshold == 0.7
        assert config.ac_weak_threshold == 0.5
        assert config.max_ac_results == 50
        assert config.max_vector_results == 100
        assert config.enable_fallback is True
        assert config.fallback_timeout == 5.0
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = ElasticsearchWatchlistConfig(
            es_url="https://es.example.com:9200",
            es_auth="user:pass",
            es_verify_ssl=True,
            es_timeout=60.0,
            persons_index="custom_persons",
            orgs_index="custom_orgs",
            ac_threshold=0.8,
            ac_weak_threshold=0.6,
            max_ac_results=100,
            max_vector_results=200,
            enable_fallback=False,
            fallback_timeout=10.0
        )
        
        assert config.es_url == "https://es.example.com:9200"
        assert config.es_auth == "user:pass"
        assert config.es_verify_ssl is True
        assert config.es_timeout == 60.0
        assert config.persons_index == "custom_persons"
        assert config.orgs_index == "custom_orgs"
        assert config.ac_threshold == 0.8
        assert config.ac_weak_threshold == 0.6
        assert config.max_ac_results == 100
        assert config.max_vector_results == 200
        assert config.enable_fallback is False
        assert config.fallback_timeout == 10.0


class TestElasticsearchWatchlistAdapter:
    """Test ElasticsearchWatchlistAdapter."""
    
    def test_init_with_default_config(self):
        """Test initialization with default config."""
        adapter = ElasticsearchWatchlistAdapter()
        
        assert adapter.config is not None
        assert adapter.fallback_service is None
        assert adapter._initialized is False
        assert adapter._client is None
        assert adapter._metrics["total_searches"] == 0
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = ElasticsearchWatchlistConfig(
            es_url="https://es.example.com:9200",
            ac_threshold=0.8
        )
        fallback_service = MagicMock(spec=WatchlistIndexService)
        
        adapter = ElasticsearchWatchlistAdapter(config, fallback_service)
        
        assert adapter.config == config
        assert adapter.fallback_service == fallback_service
        assert adapter._initialized is False
    
    def test_ready_before_initialization(self):
        """Test ready() before initialization."""
        adapter = ElasticsearchWatchlistAdapter()
        
        assert adapter.ready() is False
    
    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await adapter._health_check()
            
            assert result is True
            assert adapter._last_health_check is not None
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test failed health check."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_get_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Connection failed")
            
            result = await adapter._health_check()
            
            assert result is False
            assert adapter._last_health_check is None
    
    @pytest.mark.asyncio
    async def test_ensure_initialized_success(self):
        """Test successful initialization."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_health_check', return_value=True):
            result = await adapter._ensure_initialized()
            
            assert result is True
            assert adapter._initialized is True
    
    @pytest.mark.asyncio
    async def test_ensure_initialized_failure(self):
        """Test failed initialization."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_health_check', return_value=False):
            result = await adapter._ensure_initialized()
            
            assert result is False
            assert adapter._initialized is False
    
    @pytest.mark.asyncio
    async def test_build_from_corpus_success(self):
        """Test successful build_from_corpus."""
        adapter = ElasticsearchWatchlistAdapter()
        
        corpus = [
            ("person_001", "иван петров", "person", {"country": "RU"}),
            ("org_001", "ооо приватбанк", "org", {"country": "UA"})
        ]
        
        with patch.object(adapter, '_ensure_initialized', return_value=True), \
             patch.object(adapter, '_bulk_upsert_documents', return_value=True) as mock_bulk:
            
            await adapter.build_from_corpus(corpus, "test_index")
            
            assert mock_bulk.call_count == 2  # One call for persons, one for orgs
    
    @pytest.mark.asyncio
    async def test_build_from_corpus_fallback(self):
        """Test build_from_corpus with fallback."""
        fallback_service = MagicMock(spec=WatchlistIndexService)
        adapter = ElasticsearchWatchlistAdapter(fallback_service=fallback_service)
        
        corpus = [("person_001", "иван петров", "person", {})]
        
        with patch.object(adapter, '_ensure_initialized', return_value=False):
            await adapter.build_from_corpus(corpus, "test_index")
            
            fallback_service.build_from_corpus.assert_called_once_with(corpus, "test_index")
            assert adapter._metrics["fallbacks"] == 1
    
    @pytest.mark.asyncio
    async def test_set_overlay_from_corpus(self):
        """Test set_overlay_from_corpus."""
        adapter = ElasticsearchWatchlistAdapter()
        
        corpus = [("person_001", "иван петров", "person", {})]
        
        with patch.object(adapter, 'build_from_corpus') as mock_build:
            await adapter.set_overlay_from_corpus(corpus, "overlay_id")
            
            mock_build.assert_called_once_with(corpus, "overlay_id")
    
    def test_clear_overlay(self):
        """Test clear_overlay."""
        adapter = ElasticsearchWatchlistAdapter()
        
        # Should not raise any exceptions
        adapter.clear_overlay()
    
    @pytest.mark.asyncio
    async def test_search_ac_success(self):
        """Test search with successful AC results."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_ensure_initialized', return_value=True), \
             patch.object(adapter, '_ac_search', return_value=[("person_001", 0.8)]) as mock_ac:
            
            results = await adapter.search("иван петров", top_k=10)
            
            assert results == [("person_001", 0.8)]
            assert mock_ac.call_count == 2  # Called for both person and org
            assert adapter._metrics["ac_searches"] == 1
            assert adapter._metrics["total_searches"] == 1
    
    @pytest.mark.asyncio
    async def test_search_escalation_to_vector(self):
        """Test search escalation to vector when AC results are weak."""
        adapter = ElasticsearchWatchlistAdapter()
        adapter.config.ac_threshold = 0.8  # High threshold to force escalation
        
        with patch.object(adapter, '_ensure_initialized', return_value=True), \
             patch.object(adapter, '_ac_search', return_value=[("person_001", 0.5)]), \
             patch.object(adapter, '_vector_search', return_value=[("person_002", 0.9)]) as mock_vector:
            
            results = await adapter.search("иван петров", top_k=10)
            
            assert len(results) > 0
            assert mock_vector.call_count == 2  # Called for both person and org
            assert adapter._metrics["vector_searches"] == 1
            assert adapter._metrics["escalations"] == 1
    
    @pytest.mark.asyncio
    async def test_search_fallback(self):
        """Test search with fallback service."""
        fallback_service = MagicMock(spec=WatchlistIndexService)
        fallback_service.search.return_value = [("person_001", 0.7)]
        adapter = ElasticsearchWatchlistAdapter(fallback_service=fallback_service)
        
        with patch.object(adapter, '_ensure_initialized', return_value=False):
            results = await adapter.search("иван петров", top_k=10)
            
            assert results == [("person_001", 0.7)]
            fallback_service.search.assert_called_once_with("иван петров", 10)
            assert adapter._metrics["fallbacks"] == 1
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self):
        """Test search error handling."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_ensure_initialized', side_effect=Exception("ES error")):
            results = await adapter.search("иван петров", top_k=10)
            
            assert results == []
            assert adapter._metrics["errors"] == 1
    
    def test_get_doc(self):
        """Test get_doc method."""
        adapter = ElasticsearchWatchlistAdapter()
        
        # Should return None as this is not implemented
        result = adapter.get_doc("person_001")
        assert result is None
    
    @pytest.mark.asyncio
    async def test_save_snapshot_success(self):
        """Test successful save_snapshot."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_ensure_initialized', return_value=True), \
             patch.object(adapter, '_get_client') as mock_get_client:
            
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.put.return_value = mock_response
            mock_get_client.return_value = mock_client
            
            result = await adapter.save_snapshot("/tmp/snapshot")
            
            assert result["snapshot_created"] is True
            assert "repository" in result
            assert "snapshot" in result
    
    @pytest.mark.asyncio
    async def test_save_snapshot_fallback(self):
        """Test save_snapshot with fallback."""
        fallback_service = MagicMock(spec=WatchlistIndexService)
        fallback_service.save_snapshot.return_value = {"saved": True}
        adapter = ElasticsearchWatchlistAdapter(fallback_service=fallback_service)
        
        with patch.object(adapter, '_ensure_initialized', return_value=False):
            result = await adapter.save_snapshot("/tmp/snapshot")
            
            assert result == {"saved": True}
            fallback_service.save_snapshot.assert_called_once_with("/tmp/snapshot", False)
    
    @pytest.mark.asyncio
    async def test_reload_snapshot_success(self):
        """Test successful reload_snapshot."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_ensure_initialized', return_value=True), \
             patch.object(adapter, '_get_client') as mock_get_client:
            
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "repo1": {"settings": {"location": "/tmp/snapshot"}},
                "repo2": {"settings": {"location": "/other/path"}}
            }
            mock_client.get.return_value = mock_response
            
            # Mock snapshot list response
            mock_snapshot_response = MagicMock()
            mock_snapshot_response.json.return_value = {
                "snapshots": [{"snapshot": "snapshot_123"}]
            }
            mock_client.get.side_effect = [mock_response, mock_snapshot_response]
            
            result = await adapter.reload_snapshot("/tmp/snapshot")
            
            assert result["snapshot_restored"] is True
            assert "repository" in result
            assert "snapshot" in result
    
    @pytest.mark.asyncio
    async def test_reload_snapshot_fallback(self):
        """Test reload_snapshot with fallback."""
        fallback_service = MagicMock(spec=WatchlistIndexService)
        fallback_service.reload_snapshot.return_value = {"reloaded": True}
        adapter = ElasticsearchWatchlistAdapter(fallback_service=fallback_service)
        
        with patch.object(adapter, '_ensure_initialized', return_value=False):
            result = await adapter.reload_snapshot("/tmp/snapshot")
            
            assert result == {"reloaded": True}
            fallback_service.reload_snapshot.assert_called_once_with("/tmp/snapshot", False)
    
    def test_status(self):
        """Test status method."""
        adapter = ElasticsearchWatchlistAdapter()
        
        status = adapter.status()
        
        assert "elasticsearch_available" in status
        assert "last_health_check" in status
        assert "fallback_available" in status
        assert "metrics" in status
        assert status["elasticsearch_available"] is False
        assert status["fallback_available"] is False
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test close method."""
        adapter = ElasticsearchWatchlistAdapter()
        
        with patch.object(adapter, '_get_client') as mock_get_client:
            mock_client = AsyncMock()
            mock_get_client.return_value = mock_client
            
            await adapter.close()
            
            mock_client.aclose.assert_called_once()
            assert adapter._initialized is False


class TestFactoryFunctions:
    """Test factory functions."""
    
    def test_create_elasticsearch_watchlist_adapter(self):
        """Test create_elasticsearch_watchlist_adapter."""
        config = ElasticsearchWatchlistConfig(es_url="https://es.example.com:9200")
        fallback_config = VectorIndexConfig()
        
        adapter = create_elasticsearch_watchlist_adapter(config, fallback_config)
        
        assert isinstance(adapter, ElasticsearchWatchlistAdapter)
        assert adapter.config == config
        assert isinstance(adapter.fallback_service, WatchlistIndexService)
    
    def test_create_elasticsearch_enhanced_adapter(self):
        """Test create_elasticsearch_enhanced_adapter."""
        config = ElasticsearchWatchlistConfig(es_url="https://es.example.com:9200")
        fallback_config = VectorIndexConfig()
        
        adapter = create_elasticsearch_enhanced_adapter(config, fallback_config)
        
        assert isinstance(adapter, ElasticsearchWatchlistAdapter)
        assert adapter.config == config
        # Note: This would create an EnhancedVectorIndex in real implementation
        assert adapter.fallback_service is not None


class TestElasticsearchWatchlistAdapterIntegration:
    """Test integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_full_workflow(self):
        """Test full workflow: build -> search -> status."""
        adapter = ElasticsearchWatchlistAdapter()
        
        corpus = [
            ("person_001", "иван петров", "person", {"country": "RU"}),
            ("org_001", "ооо приватбанк", "org", {"country": "UA"})
        ]
        
        with patch.object(adapter, '_ensure_initialized', return_value=True), \
             patch.object(adapter, '_bulk_upsert_documents', return_value=True), \
             patch.object(adapter, '_ac_search', return_value=[("person_001", 0.8)]):
            
            # Build corpus
            await adapter.build_from_corpus(corpus, "test_index")
            
            # Search
            results = await adapter.search("иван петров", top_k=10)
            
            # Check status
            status = adapter.status()
            
            assert len(results) > 0
            assert status["elasticsearch_available"] is True
            assert adapter._metrics["total_searches"] == 1
    
    @pytest.mark.asyncio
    async def test_fallback_workflow(self):
        """Test fallback workflow when ES is unavailable."""
        fallback_service = MagicMock(spec=WatchlistIndexService)
        fallback_service.search.return_value = [("person_001", 0.7)]
        adapter = ElasticsearchWatchlistAdapter(fallback_service=fallback_service)
        
        with patch.object(adapter, '_ensure_initialized', return_value=False):
            # Search should use fallback
            results = await adapter.search("иван петров", top_k=10)
            
            assert results == [("person_001", 0.7)]
            assert adapter._metrics["fallbacks"] == 1
            assert adapter._metrics["total_searches"] == 1
