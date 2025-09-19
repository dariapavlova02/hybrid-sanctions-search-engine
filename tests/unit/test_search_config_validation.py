"""
Unit tests for SearchConfig validation
"""

import pytest
from pydantic import ValidationError

from src.ai_service.config.settings import SearchConfig


class TestSearchConfigValidation:
    """Test SearchConfig validation rules"""
    
    def test_valid_configuration(self):
        """Test valid configuration passes validation"""
        config = SearchConfig(
            es_hosts=["localhost:9200", "localhost:9201"],
            es_username="test_user",
            es_password="test_pass",
            es_timeout=30,
            enable_hybrid_search=True,
            enable_escalation=True,
            escalation_threshold=0.8,
            enable_fallback=True,
            fallback_threshold=0.3,
            vector_dimension=384,
            vector_similarity_threshold=0.7,
            max_concurrent_requests=10,
            request_timeout_ms=5000,
            enable_embedding_cache=True,
            embedding_cache_size=1000,
            embedding_cache_ttl_seconds=3600
        )
        
        assert config.es_hosts == ["localhost:9200", "localhost:9201"]
        assert config.es_username == "test_user"
        assert config.es_password == "test_pass"
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
    
    def test_empty_hosts_validation(self):
        """Test empty hosts list fails validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(es_hosts=[])
        
        assert "At least one Elasticsearch host must be specified" in str(exc_info.value)
    
    def test_invalid_host_format_validation(self):
        """Test invalid host format fails validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(es_hosts=["localhost"])
        
        assert "Host must include port" in str(exc_info.value)
    
    def test_invalid_port_validation(self):
        """Test invalid port fails validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(es_hosts=["localhost:invalid"])
        
        assert "Invalid port number" in str(exc_info.value)
    
    def test_port_range_validation(self):
        """Test port range validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(es_hosts=["localhost:0"])
        
        assert "Port must be between 1 and 65535" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(es_hosts=["localhost:65536"])
        
        assert "Port must be between 1 and 65535" in str(exc_info.value)
    
    def test_timeout_validation(self):
        """Test timeout validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(es_timeout=0)
        
        assert "Timeout must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(es_timeout=301)
        
        assert "Timeout must not exceed 300 seconds" in str(exc_info.value)
    
    def test_threshold_validation(self):
        """Test threshold validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(escalation_threshold=-0.1)
        
        assert "Thresholds must be between 0.0 and 1.0" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(escalation_threshold=1.1)
        
        assert "Thresholds must be between 0.0 and 1.0" in str(exc_info.value)
    
    def test_vector_dimension_validation(self):
        """Test vector dimension validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(vector_dimension=0)
        
        assert "Vector dimension must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(vector_dimension=4097)
        
        assert "Vector dimension must not exceed 4096" in str(exc_info.value)
    
    def test_max_concurrent_requests_validation(self):
        """Test max concurrent requests validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(max_concurrent_requests=0)
        
        assert "Max concurrent requests must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(max_concurrent_requests=101)
        
        assert "Max concurrent requests must not exceed 100" in str(exc_info.value)
    
    def test_request_timeout_ms_validation(self):
        """Test request timeout validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(request_timeout_ms=0)
        
        assert "Request timeout must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(request_timeout_ms=30001)
        
        assert "Request timeout must not exceed 30000 milliseconds" in str(exc_info.value)
    
    def test_embedding_cache_size_validation(self):
        """Test embedding cache size validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(embedding_cache_size=0)
        
        assert "Embedding cache size must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(embedding_cache_size=100001)
        
        assert "Embedding cache size must not exceed 100000" in str(exc_info.value)
    
    def test_embedding_cache_ttl_validation(self):
        """Test embedding cache TTL validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(embedding_cache_ttl_seconds=0)
        
        assert "Embedding cache TTL must be positive" in str(exc_info.value)
        
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(embedding_cache_ttl_seconds=86401)
        
        assert "Embedding cache TTL must not exceed 86400 seconds" in str(exc_info.value)
    
    def test_escalation_threshold_consistency_validation(self):
        """Test escalation threshold consistency validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(
                enable_escalation=True,
                escalation_threshold=0.4  # Too low
            )
        
        assert "Escalation threshold should be greater than 0.5" in str(exc_info.value)
    
    def test_fallback_threshold_consistency_validation(self):
        """Test fallback threshold consistency validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(
                enable_fallback=True,
                fallback_threshold=0.05  # Too low
            )
        
        assert "Fallback threshold should be greater than 0.1" in str(exc_info.value)
    
    def test_vector_similarity_threshold_consistency_validation(self):
        """Test vector similarity threshold consistency validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(vector_similarity_threshold=0.2)  # Too low
        
        assert "Vector similarity threshold should be greater than 0.3" in str(exc_info.value)
    
    def test_embedding_cache_size_consistency_validation(self):
        """Test embedding cache size consistency validation"""
        with pytest.raises(ValidationError) as exc_info:
            SearchConfig(
                enable_embedding_cache=True,
                embedding_cache_size=50  # Too small
            )
        
        assert "Embedding cache size should be at least 100" in str(exc_info.value)
    
    def test_model_dump_hides_sensitive_data(self):
        """Test model_dump hides sensitive data"""
        config = SearchConfig(
            es_username="test_user",
            es_password="test_pass",
            es_api_key="test_key"
        )
        
        dumped = config.model_dump()
        
        assert dumped["es_username"] == "test_user"
        assert dumped["es_password"] == "***"
        assert dumped["es_api_key"] == "***"
    
    def test_model_dump_handles_none_values(self):
        """Test model_dump handles None values correctly"""
        config = SearchConfig()
        
        dumped = config.model_dump()
        
        assert dumped["es_username"] is None
        assert dumped["es_password"] is None
        assert dumped["es_api_key"] is None
