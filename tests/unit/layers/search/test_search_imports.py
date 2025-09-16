"""
Test search layer imports and basic functionality.

This test ensures that the search layer can be imported without errors
and basic interfaces are properly defined.
"""

import pytest
from typing import List

from ai_service.layers.search import (
    HybridSearchService,
    SearchService,
    Candidate,
    SearchOpts,
    HybridSearchConfig,
    SearchMetrics,
    ElasticsearchACAdapter,
    ElasticsearchVectorAdapter,
)
from ai_service.layers.search.contracts import SearchMode
from ai_service.contracts.base_contracts import NormalizationResult


class TestSearchImports:
    """Test that search layer imports work correctly"""
    
    def test_imports_successful(self):
        """Test that all main classes can be imported"""
        # This test will fail if there are import errors
        assert HybridSearchService is not None
        assert SearchService is not None
        assert Candidate is not None
        assert SearchOpts is not None
        assert HybridSearchConfig is not None
        assert SearchMetrics is not None
        assert ElasticsearchACAdapter is not None
        assert ElasticsearchVectorAdapter is not None
    
    def test_search_mode_enum(self):
        """Test SearchMode enum values"""
        assert SearchMode.AC.value == "ac"
        assert SearchMode.VECTOR.value == "vector"
        assert SearchMode.HYBRID.value == "hybrid"
    
    def test_candidate_creation(self):
        """Test Candidate creation"""
        candidate = Candidate(
            doc_id="test_123",
            score=0.95,
            text="Test Person",
            entity_type="person",
            metadata={"source": "test"},
            search_mode=SearchMode.AC,
            match_fields=["normalized_text"],
            confidence=0.9
        )
        
        assert candidate.doc_id == "test_123"
        assert candidate.score == 0.95
        assert candidate.search_mode == SearchMode.AC
        assert candidate.confidence == 0.9
    
    def test_search_opts_creation(self):
        """Test SearchOpts creation with defaults"""
        opts = SearchOpts()
        
        assert opts.top_k == 50
        assert opts.threshold == 0.7
        assert opts.search_mode == SearchMode.HYBRID  # Default uses enum object
        assert opts.enable_escalation is True
    
    def test_search_opts_custom(self):
        """Test SearchOpts creation with custom values"""
        opts = SearchOpts(
            top_k=100,
            threshold=0.8,
            search_mode=SearchMode.AC,
            enable_escalation=False
        )
        
        assert opts.top_k == 100
        assert opts.threshold == 0.8
        assert opts.search_mode == "ac"  # Pydantic converts enum to string value
        assert opts.enable_escalation is False
    
    def test_hybrid_search_config_creation(self):
        """Test HybridSearchConfig creation"""
        config = HybridSearchConfig()
        
        assert config.service_name == "hybrid_search"
        assert config.enable_escalation is True
        assert config.escalation_threshold == 0.8
        assert config.elasticsearch is not None
        assert config.ac_search is not None
        assert config.vector_search is not None
    
    def test_search_metrics_creation(self):
        """Test SearchMetrics creation"""
        metrics = SearchMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.ac_requests == 0
        assert metrics.vector_requests == 0
        assert metrics.hybrid_requests == 0
        assert metrics.successful_requests == 0
        assert metrics.failed_requests == 0
    
    def test_candidate_serialization(self):
        """Test Candidate to_dict serialization"""
        candidate = Candidate(
            doc_id="test_456",
            score=0.85,
            text="Another Test Person",
            entity_type="person",
            metadata={"source": "test", "type": "individual"},
            search_mode=SearchMode.VECTOR,
            match_fields=["dense_vector"],
            confidence=0.8
        )
        
        data = candidate.to_dict()
        
        assert data["doc_id"] == "test_456"
        assert data["score"] == 0.85
        assert data["text"] == "Another Test Person"
        assert data["entity_type"] == "person"
        assert data["search_mode"] == "vector"
        assert data["match_fields"] == ["dense_vector"]
        assert data["confidence"] == 0.8
        assert data["metadata"]["source"] == "test"
        assert data["metadata"]["type"] == "individual"
    
    def test_search_metrics_serialization(self):
        """Test SearchMetrics serialization"""
        metrics = SearchMetrics(
            total_requests=100,
            ac_requests=60,
            vector_requests=40,
            successful_requests=95,
            failed_requests=5,
            avg_hybrid_latency_ms=150.5,
            p95_latency_ms=300.0,
            hybrid_hit_rate=0.85
        )
        
        data = metrics.to_dict()
        
        assert data["total_requests"] == 100
        assert data["ac_requests"] == 60
        assert data["vector_requests"] == 40
        assert data["successful_requests"] == 95
        assert data["failed_requests"] == 5
        assert data["avg_hybrid_latency_ms"] == 150.5
        assert data["p95_latency_ms"] == 300.0
        assert data["hybrid_hit_rate"] == 0.85


class TestSearchServiceInterface:
    """Test SearchService interface compliance"""
    
    def test_hybrid_search_service_implements_interface(self):
        """Test that HybridSearchService implements SearchService interface"""
        # This test ensures the service implements the required interface
        service = HybridSearchService()
        
        # Check that required methods exist
        assert hasattr(service, 'find_candidates')
        assert hasattr(service, 'health_check')
        assert hasattr(service, 'get_metrics')
        assert hasattr(service, 'reset_metrics')
        
        # Check method signatures (basic check)
        import inspect
        
        find_candidates_sig = inspect.signature(service.find_candidates)
        assert 'normalized' in find_candidates_sig.parameters
        assert 'text' in find_candidates_sig.parameters
        assert 'opts' in find_candidates_sig.parameters
        
        health_check_sig = inspect.signature(service.health_check)
        assert len(health_check_sig.parameters) == 0  # No parameters expected
    
    @pytest.mark.asyncio
    async def test_hybrid_search_service_health_check(self):
        """Test HybridSearchService health check"""
        service = HybridSearchService()
        
        # Health check should not raise an exception
        health = await service.health_check()
        
        assert isinstance(health, dict)
        assert "service" in health
        assert "status" in health
        assert "timestamp" in health
    
    def test_hybrid_search_service_metrics(self):
        """Test HybridSearchService metrics"""
        service = HybridSearchService()
        
        # Get metrics should not raise an exception
        metrics = service.get_metrics()
        
        assert isinstance(metrics, SearchMetrics)
        assert metrics.total_requests == 0  # Initial state
    
    def test_hybrid_search_service_reset_metrics(self):
        """Test HybridSearchService metrics reset"""
        service = HybridSearchService()
        
        # Reset metrics should not raise an exception
        service.reset_metrics()
        
        # Verify metrics are reset
        metrics = service.get_metrics()
        assert metrics.total_requests == 0
        assert metrics.ac_requests == 0
        assert metrics.vector_requests == 0
