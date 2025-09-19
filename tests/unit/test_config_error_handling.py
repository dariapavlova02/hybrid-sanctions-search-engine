"""
Unit tests for configuration error handling
"""

import pytest
from unittest.mock import patch, MagicMock

from src.ai_service.config.settings import SearchConfig
from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
from src.ai_service.layers.search.config import HybridSearchConfig


class TestSearchConfigErrorHandling:
    """Test SearchConfig error handling"""
    
    def test_validation_error_handling(self):
        """Test validation error handling"""
        with pytest.raises(Exception) as exc_info:
            SearchConfig(
                es_hosts=[],  # Invalid: empty hosts
                es_timeout=-1,  # Invalid: negative timeout
                escalation_threshold=1.5,  # Invalid: > 1.0
                vector_dimension=0,  # Invalid: zero dimension
                max_concurrent_requests=-1,  # Invalid: negative requests
                request_timeout_ms=0,  # Invalid: zero timeout
                embedding_cache_size=-1,  # Invalid: negative size
                embedding_cache_ttl_seconds=0  # Invalid: zero TTL
            )
        
        # Should contain multiple validation errors
        error_str = str(exc_info.value)
        assert "At least one Elasticsearch host must be specified" in error_str
        assert "Timeout must be positive" in error_str
        assert "Thresholds must be between 0.0 and 1.0" in error_str
        assert "Vector dimension must be positive" in error_str
        assert "Max concurrent requests must be positive" in error_str
        assert "Request timeout must be positive" in error_str
        assert "Embedding cache size must be positive" in error_str
        assert "Embedding cache TTL must be positive" in error_str
    
    def test_consistency_validation_error_handling(self):
        """Test consistency validation error handling"""
        with pytest.raises(Exception) as exc_info:
            SearchConfig(
                enable_escalation=True,
                escalation_threshold=0.4,  # Too low for escalation
                enable_fallback=True,
                fallback_threshold=0.05,  # Too low for fallback
                vector_similarity_threshold=0.2,  # Too low for similarity
                enable_embedding_cache=True,
                embedding_cache_size=50  # Too small for cache
            )
        
        # Should contain multiple consistency validation errors
        error_str = str(exc_info.value)
        assert "Escalation threshold should be greater than 0.5" in error_str
        assert "Fallback threshold should be greater than 0.1" in error_str
        assert "Vector similarity threshold should be greater than 0.3" in error_str
        assert "Embedding cache size should be at least 100" in error_str
    
    def test_reload_configuration_error_handling(self):
        """Test reload configuration error handling"""
        config = SearchConfig()
        
        # Mock environment variables with invalid values
        with patch.dict('os.environ', {
            'ES_HOSTS': '',  # Empty hosts
            'ES_TIMEOUT': 'invalid',  # Invalid timeout
            'ESCALATION_THRESHOLD': 'invalid',  # Invalid threshold
            'VECTOR_DIMENSION': 'invalid',  # Invalid dimension
            'MAX_CONCURRENT_REQUESTS': 'invalid',  # Invalid requests
            'REQUEST_TIMEOUT_MS': 'invalid',  # Invalid timeout
            'EMBEDDING_CACHE_SIZE': 'invalid',  # Invalid size
            'EMBEDDING_CACHE_TTL_SECONDS': 'invalid'  # Invalid TTL
        }):
            # Should not raise exception, but log error
            config._reload_configuration()
        
        # Should fall back to defaults
        assert config.es_hosts == ["localhost:9200"]  # Default
        assert config.es_timeout == 30  # Default
        assert config.escalation_threshold == 0.8  # Default
        assert config.vector_dimension == 384  # Default
        assert config.max_concurrent_requests == 10  # Default
        assert config.request_timeout_ms == 5000  # Default
        assert config.embedding_cache_size == 1000  # Default
        assert config.embedding_cache_ttl_seconds == 3600  # Default


class TestHybridSearchServiceErrorHandling:
    """Test HybridSearchService configuration error handling"""
    
    def test_validate_configuration_error_handling(self):
        """Test configuration validation error handling"""
        service = HybridSearchService()
        
        # Create invalid configuration
        invalid_config = HybridSearchConfig(
            es_hosts=[],  # Invalid: empty hosts
            es_timeout=-1,  # Invalid: negative timeout
            escalation_threshold=1.5,  # Invalid: > 1.0
            vector_dimension=0,  # Invalid: zero dimension
            max_concurrent_requests=-1,  # Invalid: negative requests
            request_timeout_ms=0,  # Invalid: zero timeout
            embedding_cache_size=-1,  # Invalid: negative size
            embedding_cache_ttl_seconds=0  # Invalid: zero TTL
        )
        
        with pytest.raises(ValueError) as exc_info:
            service._validate_configuration(invalid_config)
        
        # Should contain validation error
        error_str = str(exc_info.value)
        assert "Invalid configuration" in error_str
    
    def test_validate_configuration_host_format_error(self):
        """Test host format validation error handling"""
        service = HybridSearchService()
        
        # Create configuration with invalid host format
        invalid_config = HybridSearchConfig(
            es_hosts=["localhost"],  # Invalid: missing port
            es_timeout=30,
            escalation_threshold=0.8,
            vector_dimension=384,
            max_concurrent_requests=10,
            request_timeout_ms=5000,
            embedding_cache_size=1000,
            embedding_cache_ttl_seconds=3600
        )
        
        with pytest.raises(ValueError) as exc_info:
            service._validate_configuration(invalid_config)
        
        # Should contain host format error
        error_str = str(exc_info.value)
        assert "Invalid host format" in error_str
    
    def test_validate_configuration_port_error(self):
        """Test port validation error handling"""
        service = HybridSearchService()
        
        # Create configuration with invalid port
        invalid_config = HybridSearchConfig(
            es_hosts=["localhost:invalid"],  # Invalid: non-numeric port
            es_timeout=30,
            escalation_threshold=0.8,
            vector_dimension=384,
            max_concurrent_requests=10,
            request_timeout_ms=5000,
            embedding_cache_size=1000,
            embedding_cache_ttl_seconds=3600
        )
        
        with pytest.raises(ValueError) as exc_info:
            service._validate_configuration(invalid_config)
        
        # Should contain port error
        error_str = str(exc_info.value)
        assert "Invalid port number" in error_str
    
    def test_validate_configuration_threshold_error(self):
        """Test threshold validation error handling"""
        service = HybridSearchService()
        
        # Create configuration with invalid thresholds
        invalid_config = HybridSearchConfig(
            es_hosts=["localhost:9200"],
            es_timeout=30,
            enable_escalation=True,
            escalation_threshold=0.4,  # Too low
            enable_fallback=True,
            fallback_threshold=0.05,  # Too low
            vector_similarity_threshold=0.2,  # Too low
            vector_dimension=384,
            max_concurrent_requests=10,
            request_timeout_ms=5000,
            embedding_cache_size=1000,
            embedding_cache_ttl_seconds=3600
        )
        
        with pytest.raises(ValueError) as exc_info:
            service._validate_configuration(invalid_config)
        
        # Should contain threshold errors
        error_str = str(exc_info.value)
        assert "Escalation threshold should be greater than 0.5" in error_str
        assert "Fallback threshold should be greater than 0.1" in error_str
        assert "Vector similarity threshold should be greater than 0.3" in error_str
    
    def test_validate_configuration_cache_error(self):
        """Test cache validation error handling"""
        service = HybridSearchService()
        
        # Create configuration with invalid cache settings
        invalid_config = HybridSearchConfig(
            es_hosts=["localhost:9200"],
            es_timeout=30,
            escalation_threshold=0.8,
            vector_dimension=384,
            max_concurrent_requests=10,
            request_timeout_ms=5000,
            enable_embedding_cache=True,
            embedding_cache_size=50,  # Too small
            embedding_cache_ttl_seconds=3600
        )
        
        with pytest.raises(ValueError) as exc_info:
            service._validate_configuration(invalid_config)
        
        # Should contain cache error
        error_str = str(exc_info.value)
        assert "Embedding cache size should be at least 100" in error_str
    
    def test_update_configuration_error_handling(self):
        """Test update configuration error handling"""
        service = HybridSearchService()
        
        # Create invalid configuration
        invalid_config = HybridSearchConfig(
            es_hosts=[],  # Invalid: empty hosts
            es_timeout=-1,  # Invalid: negative timeout
            escalation_threshold=1.5,  # Invalid: > 1.0
            vector_dimension=0,  # Invalid: zero dimension
            max_concurrent_requests=-1,  # Invalid: negative requests
            request_timeout_ms=0,  # Invalid: zero timeout
            embedding_cache_size=-1,  # Invalid: negative size
            embedding_cache_ttl_seconds=0  # Invalid: zero TTL
        )
        
        with pytest.raises(ValueError) as exc_info:
            service.update_configuration(invalid_config)
        
        # Should contain validation error
        error_str = str(exc_info.value)
        assert "Invalid configuration" in error_str
    
    def test_update_configuration_rollback(self):
        """Test update configuration rollback on error"""
        service = HybridSearchService()
        
        # Store original configuration
        original_config = service.config
        
        # Create invalid configuration
        invalid_config = HybridSearchConfig(
            es_hosts=[],  # Invalid: empty hosts
            es_timeout=-1,  # Invalid: negative timeout
            escalation_threshold=1.5,  # Invalid: > 1.0
            vector_dimension=0,  # Invalid: zero dimension
            max_concurrent_requests=-1,  # Invalid: negative requests
            request_timeout_ms=0,  # Invalid: zero timeout
            embedding_cache_size=-1,  # Invalid: negative size
            embedding_cache_ttl_seconds=0  # Invalid: zero TTL
        )
        
        with pytest.raises(ValueError):
            service.update_configuration(invalid_config)
        
        # Configuration should be rolled back to original
        assert service.config == original_config
    
    def test_update_configuration_partial_failure(self):
        """Test update configuration partial failure handling"""
        service = HybridSearchService()
        
        # Mock client factory to raise exception during reinitialization
        with patch.object(service, '_client_factory', MagicMock()) as mock_factory:
            mock_factory.side_effect = Exception("Client factory initialization failed")
            
            # Create valid configuration
            valid_config = HybridSearchConfig(
                es_hosts=["localhost:9200"],
                es_timeout=30,
                escalation_threshold=0.8,
                vector_dimension=384,
                max_concurrent_requests=10,
                request_timeout_ms=5000,
                embedding_cache_size=1000,
                embedding_cache_ttl_seconds=3600
            )
            
            with pytest.raises(Exception) as exc_info:
                service.update_configuration(valid_config)
            
            # Should contain initialization error
            error_str = str(exc_info.value)
            assert "Failed to update search service configuration" in error_str
