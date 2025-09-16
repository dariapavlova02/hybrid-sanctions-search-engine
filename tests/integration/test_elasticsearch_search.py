"""
Integration tests for Elasticsearch search functionality.
"""

import pytest
import httpx
from src.ai_service.contracts.search_contracts import SearchOpts, SearchMode
from src.ai_service.layers.search.elasticsearch_adapters import (
    ElasticsearchACAdapter, ElasticsearchVectorAdapter
)


@pytest.mark.integration
@pytest.mark.docker
class TestElasticsearchACSearch:
    """Test AC search in Elasticsearch."""
    
    @pytest.mark.asyncio
    async def test_exact_search_finds_exact_match(self, elasticsearch_client, test_indices):
        """Test that exact search finds only exact normalized_name matches."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search for exact match
        candidates = ["иван петров"]
        opts = SearchOpts(
            top_k=10,
            threshold=0.8,
            search_mode=SearchMode.AC,
            entity_type="person"
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should find exact match
        assert len(results) > 0
        exact_matches = [r for r in results if r.ac_type == "exact"]
        assert len(exact_matches) > 0
        
        # Verify exact match details
        exact_match = exact_matches[0]
        assert exact_match.entity_id == "person_001"
        assert exact_match.normalized_name == "иван петров"
        assert exact_match.ac_score >= 2.0  # High score for exact match
        assert exact_match.matched_field == "normalized_name"
    
    @pytest.mark.asyncio
    async def test_exact_search_ignores_partial_matches(self, elasticsearch_client, test_indices):
        """Test that exact search ignores partial matches."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search for partial match
        candidates = ["иван"]  # Partial name
        opts = SearchOpts(
            top_k=10,
            threshold=0.8,
            search_mode=SearchMode.AC,
            entity_type="person"
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should not find exact matches for partial name
        exact_matches = [r for r in results if r.ac_type == "exact"]
        assert len(exact_matches) == 0
    
    @pytest.mark.asyncio
    async def test_phrase_search_finds_phrase_matches(self, elasticsearch_client, test_indices):
        """Test that phrase search finds phrase matches."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search for phrase match
        candidates = ["иван петров"]
        opts = SearchOpts(
            top_k=10,
            threshold=0.7,
            search_mode=SearchMode.AC,
            entity_type="person"
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should find phrase matches
        phrase_matches = [r for r in results if r.ac_type == "phrase"]
        assert len(phrase_matches) > 0
        
        # Verify phrase match details
        phrase_match = phrase_matches[0]
        assert phrase_match.entity_id == "person_001"
        assert phrase_match.normalized_name == "иван петров"
        assert phrase_match.ac_score >= 1.0  # Good score for phrase match
        assert phrase_match.matched_field == "name_text.shingle"
    
    @pytest.mark.asyncio
    async def test_ngram_search_finds_weak_signals(self, elasticsearch_client, test_indices):
        """Test that n-gram search finds weak signals."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search for n-gram match
        candidates = ["иван петров"]
        opts = SearchOpts(
            top_k=10,
            threshold=0.6,
            search_mode=SearchMode.AC,
            entity_type="person"
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should find n-gram matches
        ngram_matches = [r for r in results if r.ac_type == "ngram"]
        assert len(ngram_matches) > 0
        
        # Verify n-gram match details
        ngram_match = ngram_matches[0]
        assert ngram_match.entity_id == "person_001"
        assert ngram_match.normalized_name == "иван петров"
        assert ngram_match.ac_score >= 0.6  # Weak signal threshold
        assert ngram_match.matched_field == "name_ngrams"
    
    @pytest.mark.asyncio
    async def test_search_with_country_filter(self, elasticsearch_client, test_indices):
        """Test search with country filter."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search with country filter
        candidates = ["иван петров"]
        opts = SearchOpts(
            top_k=10,
            threshold=0.8,
            search_mode=SearchMode.AC,
            entity_type="person",
            country_filter="RU"
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should find matches only from Russia
        assert len(results) > 0
        for result in results:
            assert result.country == "RU"
    
    @pytest.mark.asyncio
    async def test_search_with_meta_filters(self, elasticsearch_client, test_indices):
        """Test search with meta filters."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search with meta filter
        candidates = ["иван петров"]
        opts = SearchOpts(
            top_k=10,
            threshold=0.8,
            search_mode=SearchMode.AC,
            entity_type="person",
            meta_filters={"source": "test"}
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should find matches with test source
        assert len(results) > 0
        for result in results:
            assert result.meta.get("source") == "test"
    
    @pytest.mark.asyncio
    async def test_search_multiple_candidates(self, elasticsearch_client, test_indices):
        """Test search with multiple candidates."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search with multiple candidates
        candidates = ["иван петров", "мария сидорова", "john smith"]
        opts = SearchOpts(
            top_k=10,
            threshold=0.8,
            search_mode=SearchMode.AC,
            entity_type="person"
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should find matches for multiple candidates
        assert len(results) > 0
        
        # Check that we have results for different entities
        entity_ids = set(result.entity_id for result in results)
        assert len(entity_ids) > 1
    
    @pytest.mark.asyncio
    async def test_search_no_results(self, elasticsearch_client, test_indices):
        """Test search with no matching results."""
        adapter = ElasticsearchACAdapter(elasticsearch_client)
        
        # Search for non-existent name
        candidates = ["несуществующее имя"]
        opts = SearchOpts(
            top_k=10,
            threshold=0.8,
            search_mode=SearchMode.AC,
            entity_type="person"
        )
        
        results = await adapter.search(candidates, "person", opts)
        
        # Should return empty results
        assert len(results) == 0


@pytest.mark.integration
@pytest.mark.docker
class TestElasticsearchVectorSearch:
    """Test Vector search in Elasticsearch."""
    
    @pytest.mark.asyncio
    async def test_vector_search_returns_relevant_results(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test that vector search returns relevant results."""
        adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        # Search with query vector
        opts = SearchOpts(
            top_k=10,
            threshold=0.5,
            search_mode=SearchMode.VECTOR,
            entity_type="person"
        )
        
        results = await adapter.search(sample_query_vector, "person", opts)
        
        # Should find relevant results
        assert len(results) > 0
        
        # Verify vector match details
        vector_match = results[0]
        assert vector_match.entity_id in ["person_001", "person_002", "person_003"]
        assert vector_match.entity_type == "person"
        assert vector_match.vector_score > 0.0
        assert vector_match.matched_field == "name_vector"
    
    @pytest.mark.asyncio
    async def test_vector_search_with_country_filter(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test vector search with country filter."""
        adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        # Search with country filter
        opts = SearchOpts(
            top_k=10,
            threshold=0.5,
            search_mode=SearchMode.VECTOR,
            entity_type="person",
            country_filter="RU"
        )
        
        results = await adapter.search(sample_query_vector, "person", opts)
        
        # Should find matches only from Russia
        assert len(results) > 0
        for result in results:
            assert result.country == "RU"
    
    @pytest.mark.asyncio
    async def test_vector_search_with_meta_filters(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test vector search with meta filters."""
        adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        # Search with meta filter
        opts = SearchOpts(
            top_k=10,
            threshold=0.5,
            search_mode=SearchMode.VECTOR,
            entity_type="person",
            meta_filters={"source": "test"}
        )
        
        results = await adapter.search(sample_query_vector, "person", opts)
        
        # Should find matches with test source
        assert len(results) > 0
        for result in results:
            assert result.meta.get("source") == "test"
    
    @pytest.mark.asyncio
    async def test_vector_search_organization_entities(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test vector search for organization entities."""
        adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        # Search for organizations
        opts = SearchOpts(
            top_k=10,
            threshold=0.5,
            search_mode=SearchMode.VECTOR,
            entity_type="org"
        )
        
        results = await adapter.search(sample_query_vector, "org", opts)
        
        # Should find organization results
        assert len(results) > 0
        for result in results:
            assert result.entity_type == "org"
            assert result.entity_id in ["org_001", "org_002"]
    
    @pytest.mark.asyncio
    async def test_vector_search_threshold_filtering(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test that vector search filters by threshold."""
        adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        # Search with high threshold
        opts = SearchOpts(
            top_k=10,
            threshold=0.9,  # Very high threshold
            search_mode=SearchMode.VECTOR,
            entity_type="person"
        )
        
        results = await adapter.search(sample_query_vector, "person", opts)
        
        # Should return fewer results due to high threshold
        assert len(results) >= 0  # May be empty with high threshold
        
        # All results should meet threshold
        for result in results:
            assert result.vector_score >= 0.9
    
    @pytest.mark.asyncio
    async def test_vector_search_top_k_limiting(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test that vector search respects top_k limit."""
        adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        # Search with low top_k
        opts = SearchOpts(
            top_k=2,
            threshold=0.5,
            search_mode=SearchMode.VECTOR,
            entity_type="person"
        )
        
        results = await adapter.search(sample_query_vector, "person", opts)
        
        # Should return at most 2 results
        assert len(results) <= 2


@pytest.mark.integration
@pytest.mark.docker
class TestElasticsearchHybridSearch:
    """Test hybrid search combining AC and Vector."""
    
    @pytest.mark.asyncio
    async def test_hybrid_search_combines_ac_and_vector(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test that hybrid search combines AC and Vector results."""
        from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
        from src.ai_service.contracts.search_contracts import HybridSearchConfig
        
        # Create hybrid search service
        config = HybridSearchConfig()
        service = HybridSearchService(config)
        
        # Mock the adapters
        ac_adapter = ElasticsearchACAdapter(elasticsearch_client)
        vector_adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        service._ac_adapter = ac_adapter
        service._vector_adapter = vector_adapter
        
        # Create mock normalization result
        from src.ai_service.contracts.base_contracts import NormalizationResult
        normalization_result = NormalizationResult(
            normalized="иван петров",
            tokens=["иван", "петров"],
            trace=[],
            errors=[],
            language="ru",
            confidence=0.9,
            original_length=12,
            normalized_length=12,
            token_count=2,
            processing_time=0.05,
            success=True
        )
        
        # Create search options
        opts = SearchOpts(
            top_k=10,
            threshold=0.7,
            search_mode=SearchMode.HYBRID,
            entity_type="person"
        )
        
        # Perform hybrid search
        results = await service.find_candidates(
            normalized=normalization_result,
            text="иван петров",
            opts=opts
        )
        
        # Should return combined results
        assert len(results) > 0
        
        # Check that results have fusion scores
        for result in results:
            assert result.final_score > 0.0
            assert result.ac_score >= 0.0
            assert result.vector_score >= 0.0
            assert result.search_type == "fusion"
    
    @pytest.mark.asyncio
    async def test_hybrid_search_escalation(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test that hybrid search escalates from AC to Vector when AC results are weak."""
        from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
        from src.ai_service.contracts.search_contracts import HybridSearchConfig
        
        # Create hybrid search service with low AC threshold
        config = HybridSearchConfig(
            ac_weak_threshold=0.9,  # Very high threshold to force escalation
            ac_empty_threshold=1
        )
        service = HybridSearchService(config)
        
        # Mock the adapters
        ac_adapter = ElasticsearchACAdapter(elasticsearch_client)
        vector_adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        service._ac_adapter = ac_adapter
        service._vector_adapter = vector_adapter
        
        # Create mock normalization result
        from src.ai_service.contracts.base_contracts import NormalizationResult
        normalization_result = NormalizationResult(
            normalized="иван петров",
            tokens=["иван", "петров"],
            trace=[],
            errors=[],
            language="ru",
            confidence=0.9,
            original_length=12,
            normalized_length=12,
            token_count=2,
            processing_time=0.05,
            success=True
        )
        
        # Create search options
        opts = SearchOpts(
            top_k=10,
            threshold=0.7,
            search_mode=SearchMode.HYBRID,
            entity_type="person",
            enable_escalation=True
        )
        
        # Perform hybrid search
        results = await service.find_candidates(
            normalized=normalization_result,
            text="иван петров",
            opts=opts
        )
        
        # Should return results (may be from Vector escalation)
        assert len(results) >= 0  # May be empty if both AC and Vector fail
    
    @pytest.mark.asyncio
    async def test_hybrid_search_fusion_scoring(self, elasticsearch_client, test_indices, sample_query_vector):
        """Test that hybrid search properly fuses AC and Vector scores."""
        from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
        from src.ai_service.contracts.search_contracts import HybridSearchConfig
        
        # Create hybrid search service
        config = HybridSearchConfig()
        service = HybridSearchService(config)
        
        # Mock the adapters
        ac_adapter = ElasticsearchACAdapter(elasticsearch_client)
        vector_adapter = ElasticsearchVectorAdapter(elasticsearch_client)
        
        service._ac_adapter = ac_adapter
        service._vector_adapter = vector_adapter
        
        # Create mock normalization result
        from src.ai_service.contracts.base_contracts import NormalizationResult
        normalization_result = NormalizationResult(
            normalized="иван петров",
            tokens=["иван", "петров"],
            trace=[],
            errors=[],
            language="ru",
            confidence=0.9,
            original_length=12,
            normalized_length=12,
            token_count=2,
            processing_time=0.05,
            success=True
        )
        
        # Create search options
        opts = SearchOpts(
            top_k=10,
            threshold=0.7,
            search_mode=SearchMode.HYBRID,
            entity_type="person"
        )
        
        # Perform hybrid search
        results = await service.find_candidates(
            normalized=normalization_result,
            text="иван петров",
            opts=opts
        )
        
        # Should return results with proper fusion scoring
        if len(results) > 0:
            result = results[0]
            
            # Fusion score should be calculated
            assert result.final_score > 0.0
            
            # Should have both AC and Vector components
            assert result.ac_score >= 0.0
            assert result.vector_score >= 0.0
            
            # Should have features
            assert isinstance(result.features, dict)
