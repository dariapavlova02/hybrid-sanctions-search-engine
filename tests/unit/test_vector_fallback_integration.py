"""
Integration tests for vector fallback functionality
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
from src.ai_service.layers.search.config import HybridSearchConfig
from src.ai_service.layers.search.contracts import SearchOpts, Candidate, SearchMode
from src.ai_service.contracts.base_contracts import NormalizationResult


class TestVectorFallbackIntegration:
    """Integration tests for vector fallback functionality"""

    @pytest.fixture
    def config(self):
        """Create test configuration with vector fallback enabled"""
        return HybridSearchConfig(
            enable_vector_fallback=True,
            vector_cos_threshold=0.45,
            vector_fallback_max_results=50,
            enable_rapidfuzz_rerank=True,
            enable_dob_id_anchors=True,
            enable_ac_es=True
        )

    @pytest.fixture
    def search_opts(self):
        """Create test search options"""
        return SearchOpts(
            top_k=10,
            timeout_ms=5000,
            enable_escalation=True
        )

    @pytest.fixture
    def normalization_result(self):
        """Create test normalization result"""
        return NormalizationResult(
            normalized="John Doe",
            tokens=["John", "Doe"],
            trace=[],
            errors=[],
            language="en",
            confidence=0.9,
            original_length=8,
            normalized_length=8,
            token_count=2,
            processing_time=0.1,
            success=True
        )

    @pytest.fixture
    def mock_embedding_service(self):
        """Mock embedding service"""
        service = Mock()
        service.get_embeddings_optimized = AsyncMock(return_value={
            "success": True,
            "embeddings": [[0.1, 0.2, 0.3, 0.4] * 96]  # 384 dimensions
        })
        return service

    @pytest.fixture
    def mock_vector_adapter(self):
        """Mock vector adapter with fallback search"""
        adapter = Mock()
        adapter.search_vector_fallback = AsyncMock(return_value=[
            Candidate(
                doc_id="1",
                score=0.8,
                text="John Doe",
                entity_type="person",
                metadata={"dob": "1980-01-01", "doc_id": "PASS123456"},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector", "text"],
                confidence=0.8,
                trace={
                    "reason": "vector_fallback",
                    "cosine": 0.57,
                    "fuzz": 85,
                    "anchors": ["dob_anchor"]
                }
            )
        ])
        return adapter

    @pytest.fixture
    def mock_ac_adapter(self):
        """Mock AC adapter"""
        adapter = Mock()
        adapter.search = AsyncMock(return_value=[])  # No AC results to trigger fallback
        return adapter

    @pytest.fixture
    def hybrid_service(self, config, mock_embedding_service, mock_vector_adapter, mock_ac_adapter):
        """Create hybrid search service with mocked dependencies"""
        service = HybridSearchService(config)
        service._embedding_service = mock_embedding_service
        service._vector_adapter = mock_vector_adapter
        service._ac_adapter = mock_ac_adapter
        return service

    @pytest.mark.asyncio
    async def test_vector_fallback_triggered_when_no_ac_results(
        self, hybrid_service, normalization_result, search_opts
    ):
        """Test that vector fallback is triggered when no AC results"""
        # Mock AC search to return empty results
        hybrid_service._ac_adapter.search = AsyncMock(return_value=[])
        
        # Mock vector search to return empty results (to trigger fallback)
        hybrid_service._vector_adapter.search = AsyncMock(return_value=[])
        
        # Mock vector fallback to return results
        hybrid_service._vector_adapter.search_vector_fallback = AsyncMock(return_value=[
            Candidate(
                doc_id="1",
                score=0.8,
                text="John Doe",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector"],
                confidence=0.8,
                trace={"reason": "vector_fallback", "cosine": 0.57}
            )
        ])
        
        # Execute search
        results = await hybrid_service._hybrid_search(
            normalization_result, "John Doe", search_opts
        )
        
        # Verify fallback was used
        assert len(results) == 1
        assert results[0].trace["reason"] == "vector_fallback"
        assert results[0].trace["cosine"] == 0.57

    @pytest.mark.asyncio
    async def test_vector_fallback_triggered_when_weak_ac_results(
        self, hybrid_service, normalization_result, search_opts
    ):
        """Test that vector fallback is triggered when AC results are weak"""
        # Mock AC search to return weak results
        hybrid_service._ac_adapter.search = AsyncMock(return_value=[
            Candidate(
                doc_id="1",
                score=0.2,  # Weak score
                text="John Smith",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.AC,
                match_fields=["text"],
                confidence=0.2
            )
        ])
        
        # Mock vector search to return empty results
        hybrid_service._vector_adapter.search = AsyncMock(return_value=[])
        
        # Mock vector fallback to return results
        hybrid_service._vector_adapter.search_vector_fallback = AsyncMock(return_value=[
            Candidate(
                doc_id="2",
                score=0.8,
                text="John Doe",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector"],
                confidence=0.8,
                trace={"reason": "vector_fallback", "cosine": 0.57}
            )
        ])
        
        # Execute search
        results = await hybrid_service._hybrid_search(
            normalization_result, "John Doe", search_opts
        )
        
        # Verify fallback was used
        assert len(results) >= 1
        fallback_results = [r for r in results if r.trace and r.trace.get("reason") == "vector_fallback"]
        assert len(fallback_results) == 1

    @pytest.mark.asyncio
    async def test_vector_fallback_not_triggered_when_strong_ac_results(
        self, hybrid_service, normalization_result, search_opts
    ):
        """Test that vector fallback is not triggered when AC results are strong"""
        # Mock AC search to return strong results
        hybrid_service._ac_adapter.search = AsyncMock(return_value=[
            Candidate(
                doc_id="1",
                score=0.9,  # Strong score
                text="John Doe",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.AC,
                match_fields=["text"],
                confidence=0.9
            )
        ])
        
        # Mock vector search to return results
        hybrid_service._vector_adapter.search = AsyncMock(return_value=[
            Candidate(
                doc_id="2",
                score=0.8,
                text="John Smith",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector"],
                confidence=0.8
            )
        ])
        
        # Execute search
        results = await hybrid_service._hybrid_search(
            normalization_result, "John Doe", search_opts
        )
        
        # Verify fallback was not used
        fallback_results = [r for r in results if r.trace and r.trace.get("reason") == "vector_fallback"]
        assert len(fallback_results) == 0

    def test_rapidfuzz_reranking(self, hybrid_service):
        """Test RapidFuzz reranking functionality"""
        candidates = [
            Candidate(
                doc_id="1",
                score=0.8,
                text="John Doe",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector"],
                confidence=0.8,
                trace={"reason": "vector_fallback", "cosine": 0.7}
            ),
            Candidate(
                doc_id="2",
                score=0.9,
                text="Jane Smith",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector"],
                confidence=0.9,
                trace={"reason": "vector_fallback", "cosine": 0.6}
            )
        ]
        
        query_text = "John Doe"
        
        # Apply reranking
        reranked = hybrid_service._apply_rapidfuzz_reranking(candidates, query_text)
        
        # Check that fuzz scores were added
        for candidate in reranked:
            if candidate.trace.get("reason") == "vector_fallback":
                assert "fuzz" in candidate.trace
                assert candidate.trace["fuzz"] >= 0
                assert candidate.trace["fuzz"] <= 100

    def test_anchor_boost(self, hybrid_service):
        """Test DoB/ID anchor boost functionality"""
        candidates = [
            Candidate(
                doc_id="1",
                score=0.8,
                text="John Doe",
                entity_type="person",
                metadata={"dob": "1980-01-01", "doc_id": "PASS123456"},
                search_mode=SearchMode.VECTOR,
                match_fields=["dense_vector"],
                confidence=0.8,
                trace={"reason": "vector_fallback", "cosine": 0.7}
            )
        ]
        
        query_text = "John Doe 1980-01-01 passport 123456"
        original_score = candidates[0].score
        
        # Apply anchor boost
        boosted = hybrid_service._apply_anchor_boost(candidates, query_text)
        
        # Check that anchors were detected and scores boosted
        assert len(boosted) == 1
        candidate = boosted[0]
        anchors = candidate.trace.get("anchors", [])
        
        # Should detect DoB anchor
        assert "dob_anchor" in anchors or "id_anchor" in anchors
        
        # Score should be boosted
        assert candidate.score > original_score

    def test_trace_information_format(self, hybrid_service):
        """Test that trace information is properly formatted"""
        candidate = Candidate(
            doc_id="1",
            score=0.8,
            text="John Doe",
            entity_type="person",
            metadata={"dob": "1980-01-01"},
            search_mode=SearchMode.VECTOR,
            match_fields=["dense_vector"],
            confidence=0.8,
            trace={
                "reason": "vector_fallback",
                "cosine": 0.57,
                "fuzz": 85,
                "anchors": ["dob_anchor"]
            }
        )
        
        # Verify trace format
        assert candidate.trace["reason"] == "vector_fallback"
        assert isinstance(candidate.trace["cosine"], (int, float))
        assert isinstance(candidate.trace["fuzz"], (int, float))
        assert isinstance(candidate.trace["anchors"], list)
        assert 0 <= candidate.trace["cosine"] <= 1
        assert 0 <= candidate.trace["fuzz"] <= 100

    def test_configuration_flags(self, config):
        """Test that configuration flags are properly set"""
        assert config.enable_vector_fallback == True
        assert config.vector_cos_threshold == 0.45
        assert config.vector_fallback_max_results == 50
        assert config.enable_rapidfuzz_rerank == True
        assert config.enable_dob_id_anchors == True

    @pytest.mark.asyncio
    async def test_vector_fallback_disabled(self, normalization_result, search_opts):
        """Test that vector fallback is disabled when flag is False"""
        config = HybridSearchConfig(enable_vector_fallback=False)
        service = HybridSearchService(config)
        
        # Mock dependencies
        service._ac_adapter = Mock()
        service._ac_adapter.search = AsyncMock(return_value=[])
        service._vector_adapter = Mock()
        service._vector_adapter.search = AsyncMock(return_value=[])
        service._vector_adapter.search_vector_fallback = AsyncMock(return_value=[])
        
        # Execute search
        results = await service._hybrid_search(
            normalization_result, "John Doe", search_opts
        )
        
        # Verify fallback was not called
        service._vector_adapter.search_vector_fallback.assert_not_called()
        assert len(results) == 0
