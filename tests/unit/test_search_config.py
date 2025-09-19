"""
Unit tests for search configuration.

Tests the SearchConfig validation and hot-reloading functionality.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from typing import List, Dict, Any

from src.ai_service.config.settings import SearchConfig
from src.ai_service.layers.search.config import HybridSearchConfig
from pydantic import ValidationError


class TestSearchConfig:
    """Test cases for SearchConfig"""

    @pytest.fixture(autouse=True)
    def clear_env_vars(self):
        """Clear environment variables before each test"""
        keys_to_clear = [
            "ES_HOSTS", "ES_USERNAME", "ES_PASSWORD", "ES_API_KEY", "ES_VERIFY_CERTS", "ES_TIMEOUT",
            "ENABLE_HYBRID_SEARCH", "ENABLE_ESCALATION", "ESCALATION_THRESHOLD",
            "ENABLE_FALLBACK", "FALLBACK_THRESHOLD",
            "VECTOR_DIMENSION", "VECTOR_SIMILARITY_THRESHOLD",
            "MAX_CONCURRENT_REQUESTS", "REQUEST_TIMEOUT_MS",
            "ENABLE_EMBEDDING_CACHE", "EMBEDDING_CACHE_SIZE", "EMBEDDING_CACHE_TTL_SECONDS"
        ]
        for key in keys_to_clear:
            if key in os.environ:
                del os.environ[key]
        yield
        # Clean up after test
        for key in keys_to_clear:
            if key in os.environ:
                del os.environ[key]

    def test_default_configuration(self):
        """Test default configuration values"""
        config = SearchConfig()
        
        assert config.es_hosts == ["localhost:9200"]
        assert config.es_username is None
        assert config.es_password is None
        assert config.es_api_key is None
        assert config.es_verify_certs is True
        assert config.es_timeout == 30
        assert config.enable_hybrid_search is True
        assert config.enable_escalation is True
        assert config.escalation_threshold == 0.8
        assert config.enable_fallback is True
        assert config.fallback_threshold == 0.3
        assert config.vector_dimension == 384
        assert config.vector_similarity_threshold == 0.7
        assert config.max_concurrent_requests == 10
        assert config.request_timeout_ms == 5000
        assert config.enable_embedding_cache is True
        assert config.embedding_cache_size == 1000
        assert config.embedding_cache_ttl_seconds == 3600

    def test_environment_variable_override(self):
        """Test configuration override with environment variables"""
        os.environ["ES_HOSTS"] = "es1:9200,es2:9200"
        os.environ["ES_USERNAME"] = "test_user"
        os.environ["ES_PASSWORD"] = "test_pass"
        os.environ["ES_TIMEOUT"] = "60"
        os.environ["ESCALATION_THRESHOLD"] = "0.9"
        os.environ["FALLBACK_THRESHOLD"] = "0.4"
        os.environ["VECTOR_DIMENSION"] = "512"
        os.environ["VECTOR_SIMILARITY_THRESHOLD"] = "0.8"
        os.environ["MAX_CONCURRENT_REQUESTS"] = "20"
        os.environ["REQUEST_TIMEOUT_MS"] = "10000"
        os.environ["EMBEDDING_CACHE_SIZE"] = "2000"
        os.environ["EMBEDDING_CACHE_TTL_SECONDS"] = "7200"
        
        config = SearchConfig()
        
        assert config.es_hosts == ["es1:9200", "es2:9200"]
        assert config.es_username == "test_user"
        assert config.es_password == "test_pass"
        assert config.es_timeout == 60
        assert config.escalation_threshold == 0.9
        assert config.fallback_threshold == 0.4
        assert config.vector_dimension == 512
        assert config.vector_similarity_threshold == 0.8
        assert config.max_concurrent_requests == 20
        assert config.request_timeout_ms == 10000
        assert config.embedding_cache_size == 2000
        assert config.embedding_cache_ttl_seconds == 7200

    def test_host_validation(self):
        """Test host format validation"""
        # Valid hosts
        os.environ["ES_HOSTS"] = "localhost:9200,es1:9200,es2:9300"
        config = SearchConfig()
        assert config.es_hosts == ["localhost:9200", "es1:9200", "es2:9300"]
        
        # Invalid host format (missing port)
        os.environ["ES_HOSTS"] = "localhost"
        with pytest.raises(ValidationError, match="Host must include port"):
            SearchConfig()
        
        # Invalid port number
        os.environ["ES_HOSTS"] = "localhost:99999"
        with pytest.raises(ValidationError, match="Port must be between 1 and 65535"):
            SearchConfig()
        
        # Invalid port format
        os.environ["ES_HOSTS"] = "localhost:abc"
        with pytest.raises(ValidationError, match="Invalid port number"):
            SearchConfig()

    def test_timeout_validation(self):
        """Test timeout validation"""
        # Valid timeout
        os.environ["ES_TIMEOUT"] = "60"
        config = SearchConfig()
        assert config.es_timeout == 60
        
        # Invalid timeout (negative)
        os.environ["ES_TIMEOUT"] = "-1"
        with pytest.raises(ValidationError, match="Timeout must be positive"):
            SearchConfig()
        
        # Invalid timeout (too large)
        os.environ["ES_TIMEOUT"] = "400"
        with pytest.raises(ValidationError, match="Timeout must not exceed 300 seconds"):
            SearchConfig()

    def test_threshold_validation(self):
        """Test threshold validation"""
        # Valid thresholds
        os.environ["ESCALATION_THRESHOLD"] = "0.9"
        os.environ["FALLBACK_THRESHOLD"] = "0.4"
        os.environ["VECTOR_SIMILARITY_THRESHOLD"] = "0.8"
        config = SearchConfig()
        assert config.escalation_threshold == 0.9
        assert config.fallback_threshold == 0.4
        assert config.vector_similarity_threshold == 0.8
        
        # Invalid thresholds (out of range)
        os.environ["ESCALATION_THRESHOLD"] = "1.5"
        with pytest.raises(ValidationError, match="Thresholds must be between 0.0 and 1.0"):
            SearchConfig()
        
        os.environ["FALLBACK_THRESHOLD"] = "-0.1"
        with pytest.raises(ValidationError, match="Thresholds must be between 0.0 and 1.0"):
            SearchConfig()

    def test_vector_dimension_validation(self):
        """Test vector dimension validation"""
        # Valid dimension
        os.environ["VECTOR_DIMENSION"] = "512"
        config = SearchConfig()
        assert config.vector_dimension == 512
        
        # Invalid dimension (negative)
        os.environ["VECTOR_DIMENSION"] = "-1"
        with pytest.raises(ValidationError, match="Vector dimension must be positive"):
            SearchConfig()
        
        # Invalid dimension (too large)
        os.environ["VECTOR_DIMENSION"] = "5000"
        with pytest.raises(ValidationError, match="Vector dimension must not exceed 4096"):
            SearchConfig()

    def test_concurrent_requests_validation(self):
        """Test max concurrent requests validation"""
        # Valid value
        os.environ["MAX_CONCURRENT_REQUESTS"] = "20"
        config = SearchConfig()
        assert config.max_concurrent_requests == 20
        
        # Invalid value (negative)
        os.environ["MAX_CONCURRENT_REQUESTS"] = "-1"
        with pytest.raises(ValidationError, match="Max concurrent requests must be positive"):
            SearchConfig()
        
        # Invalid value (too large)
        os.environ["MAX_CONCURRENT_REQUESTS"] = "200"
        with pytest.raises(ValidationError, match="Max concurrent requests must not exceed 100"):
            SearchConfig()

    def test_request_timeout_validation(self):
        """Test request timeout validation"""
        # Valid timeout
        os.environ["REQUEST_TIMEOUT_MS"] = "10000"
        config = SearchConfig()
        assert config.request_timeout_ms == 10000
        
        # Invalid timeout (negative)
        os.environ["REQUEST_TIMEOUT_MS"] = "-1"
        with pytest.raises(ValidationError, match="Request timeout must be positive"):
            SearchConfig()
        
        # Invalid timeout (too large)
        os.environ["REQUEST_TIMEOUT_MS"] = "40000"
        with pytest.raises(ValidationError, match="Request timeout must not exceed 30000 milliseconds"):
            SearchConfig()

    def test_cache_size_validation(self):
        """Test embedding cache size validation"""
        # Valid size
        os.environ["EMBEDDING_CACHE_SIZE"] = "2000"
        config = SearchConfig()
        assert config.embedding_cache_size == 2000
        
        # Invalid size (negative)
        os.environ["EMBEDDING_CACHE_SIZE"] = "-1"
        with pytest.raises(ValidationError, match="Embedding cache size must be positive"):
            SearchConfig()
        
        # Invalid size (too large)
        os.environ["EMBEDDING_CACHE_SIZE"] = "200000"
        with pytest.raises(ValidationError, match="Embedding cache size must not exceed 100000"):
            SearchConfig()

    def test_cache_ttl_validation(self):
        """Test embedding cache TTL validation"""
        # Valid TTL
        os.environ["EMBEDDING_CACHE_TTL_SECONDS"] = "7200"
        config = SearchConfig()
        assert config.embedding_cache_ttl_seconds == 7200
        
        # Invalid TTL (negative)
        os.environ["EMBEDDING_CACHE_TTL_SECONDS"] = "-1"
        with pytest.raises(ValidationError, match="Embedding cache TTL must be positive"):
            SearchConfig()
        
        # Invalid TTL (too large)
        os.environ["EMBEDDING_CACHE_TTL_SECONDS"] = "100000"
        with pytest.raises(ValidationError, match="Embedding cache TTL must not exceed 86400 seconds"):
            SearchConfig()

    def test_configuration_consistency_validation(self):
        """Test cross-field validation"""
        # Valid configuration
        os.environ["ESCALATION_THRESHOLD"] = "0.9"
        os.environ["FALLBACK_THRESHOLD"] = "0.4"
        os.environ["VECTOR_SIMILARITY_THRESHOLD"] = "0.8"
        os.environ["EMBEDDING_CACHE_SIZE"] = "2000"
        config = SearchConfig()
        assert config.escalation_threshold == 0.9
        
        # Invalid escalation threshold (too low)
        os.environ["ESCALATION_THRESHOLD"] = "0.3"
        with pytest.raises(ValidationError, match="Escalation threshold should be greater than 0.5"):
            SearchConfig()
        
        # Invalid fallback threshold (too low)
        os.environ["FALLBACK_THRESHOLD"] = "0.05"
        with pytest.raises(ValidationError, match="Fallback threshold should be greater than 0.1"):
            SearchConfig()
        
        # Invalid vector similarity threshold (too low)
        os.environ["VECTOR_SIMILARITY_THRESHOLD"] = "0.2"
        with pytest.raises(ValidationError, match="Vector similarity threshold should be greater than 0.3"):
            SearchConfig()
        
        # Invalid cache size (too small)
        os.environ["EMBEDDING_CACHE_SIZE"] = "50"
        with pytest.raises(ValidationError, match="Embedding cache size should be at least 100"):
            SearchConfig()

    def test_model_dump(self):
        """Test model serialization"""
        config = SearchConfig()
        data = config.model_dump()
        
        assert "es_hosts" in data
        assert "es_username" in data
        assert "es_password" in data
        assert "es_api_key" in data
        assert "es_verify_certs" in data
        assert "es_timeout" in data
        assert "enable_hybrid_search" in data
        assert "enable_escalation" in data
        assert "escalation_threshold" in data
        assert "enable_fallback" in data
        assert "fallback_threshold" in data
        assert "vector_dimension" in data
        assert "vector_similarity_threshold" in data
        assert "max_concurrent_requests" in data
        assert "request_timeout_ms" in data
        assert "enable_embedding_cache" in data
        assert "embedding_cache_size" in data
        assert "embedding_cache_ttl_seconds" in data
        
        # Check that sensitive data is masked
        assert data["es_password"] == "***"
        assert data["es_api_key"] == "***"

    def test_hot_reload_stats(self):
        """Test hot reload statistics"""
        config = SearchConfig()
        stats = config.get_reload_stats()
        
        assert "last_reloaded" in stats
        assert "reload_count" in stats
        assert "monitoring_active" in stats
        assert "watched_paths" in stats
        
        assert stats["reload_count"] == 0
        assert stats["monitoring_active"] is False

    @pytest.mark.asyncio
    async def test_hot_reload_functionality(self):
        """Test hot reload functionality"""
        config = SearchConfig()
        
        # Test starting hot reload
        await config.start_hot_reload()
        assert config._reload_task is not None
        assert not config._reload_task.done()
        
        # Test stopping hot reload
        config.stop_hot_reload()
        assert config._reload_task is None

    def test_reload_configuration(self):
        """Test configuration reload"""
        config = SearchConfig()
        original_hosts = config.es_hosts
        
        # Change environment variable
        os.environ["ES_HOSTS"] = "new_host:9200"
        
        # Reload configuration
        config._reload_configuration()
        
        # Check that configuration was updated
        assert config.es_hosts == ["new_host:9200"]
        assert config.es_hosts != original_hosts


class TestHybridSearchConfig:
    """Test cases for HybridSearchConfig"""

    def test_default_configuration(self):
        """Test default HybridSearchConfig values"""
        config = HybridSearchConfig()
        
        assert config.enable_fallback is True
        assert config.fallback_threshold == 0.3
        assert config.vector_dimension == 384
        assert config.vector_similarity_threshold == 0.7
        assert config.enable_embedding_cache is True
        assert config.embedding_cache_size == 1000
        assert config.embedding_cache_ttl_seconds == 3600

    def test_elasticsearch_config_validation(self):
        """Test Elasticsearch configuration validation"""
        # Valid configuration
        config = HybridSearchConfig(
            elasticsearch={
                "hosts": ["localhost:9200"],
                "timeout": 10,
                "max_retries": 3,
                "retry_on_timeout": True,
                "verify_certs": False,
                "ac_index": "test_ac",
                "vector_index": "test_vector",
                "smoke_test_timeout": 5
            }
        )
        assert config.elasticsearch.hosts == ["localhost:9200"]
        
        # Invalid configuration (empty hosts)
        with pytest.raises(ValidationError):
            HybridSearchConfig(
                elasticsearch={
                    "hosts": [],
                    "timeout": 10,
                    "max_retries": 3,
                    "retry_on_timeout": True,
                    "verify_certs": False,
                    "ac_index": "test_ac",
                    "vector_index": "test_vector",
                    "smoke_test_timeout": 5
                }
            )

    def test_fallback_config_validation(self):
        """Test fallback configuration validation"""
        # Valid configuration
        config = HybridSearchConfig(
            enable_fallback=True,
            fallback_threshold=0.5,
            fallback_timeout_ms=2000,
            fallback_max_results=100
        )
        assert config.enable_fallback is True
        assert config.fallback_threshold == 0.5
        
        # Invalid fallback threshold
        with pytest.raises(ValidationError):
            HybridSearchConfig(fallback_threshold=1.5)

    def test_vector_config_validation(self):
        """Test vector configuration validation"""
        # Valid configuration
        config = HybridSearchConfig(
            vector_dimension=512,
            vector_similarity_threshold=0.8,
            enable_vector_fallback=True,
            vector_fallback_threshold=0.4
        )
        assert config.vector_dimension == 512
        assert config.vector_similarity_threshold == 0.8
        
        # Invalid vector dimension
        with pytest.raises(ValidationError):
            HybridSearchConfig(vector_dimension=0)

    def test_embedding_cache_config_validation(self):
        """Test embedding cache configuration validation"""
        # Valid configuration
        config = HybridSearchConfig(
            enable_embedding_cache=True,
            embedding_cache_size=2000,
            embedding_cache_ttl_seconds=7200
        )
        assert config.enable_embedding_cache is True
        assert config.embedding_cache_size == 2000
        
        # Invalid cache size
        with pytest.raises(ValidationError):
            HybridSearchConfig(embedding_cache_size=0)
