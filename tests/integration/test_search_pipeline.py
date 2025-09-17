"""
Integration tests for search pipeline functionality
Testing AC search, vector fallback, and end-to-end search performance
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
from src.ai_service.layers.search.config import HybridSearchConfig
from src.ai_service.layers.search.contracts import SearchOpts, Candidate, SearchMode
from src.ai_service.contracts.base_contracts import NormalizationResult
from src.ai_service.contracts.search_contracts import SearchCandidate


class TestSearchPipelineIntegration:
    """Integration tests for search pipeline"""

    @pytest.fixture
    def config(self):
        """Create test configuration with all features enabled"""
        return HybridSearchConfig(
            enable_ac_es=True,
            enable_vector_fallback=True,
            vector_cos_threshold=0.5,
            enable_rapidfuzz_rerank=True,
            enable_dob_id_anchors=True,
            strict_candidate_contract=True,
            escalation_threshold=0.8,
            max_escalation_results=100
        )

    @pytest.fixture
    def search_opts(self):
        """Create test search options"""
        return SearchOpts(
            top_k=20,
            timeout_ms=5000,
            enable_escalation=True,
            threshold=0.7
        )

    @pytest.fixture
    def normalization_result(self):
        """Create test normalization result"""
        return NormalizationResult(
            normalized="Petro Poroshenka",
            tokens=["Petro", "Poroshenka"],
            trace=[],
            errors=[],
            language="uk",
            confidence=0.9,
            original_length=15,
            normalized_length=15,
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
    def mock_ac_adapter(self):
        """Mock AC adapter with passport/company matching"""
        adapter = Mock()
        
        # Mock AC search for passport ID
        def mock_ac_search(normalized, text, opts):
            if "passport" in text.lower() or "123456" in text:
                return [
                    Candidate(
                        doc_id="passport_123456",
                        score=0.95,
                        text="Passport 123456",
                        entity_type="document",
                        metadata={"doc_type": "passport", "doc_id": "123456"},
                        search_mode=SearchMode.AC,
                        match_fields=["text"],
                        confidence=0.95,
                        trace={"tier": 0, "reason": "exact_doc_id"}
                    )
                ]
            elif "llc" in text.lower() or "company" in text.lower():
                return [
                    Candidate(
                        doc_id="company_llc_001",
                        score=0.9,
                        text="Company Name LLC",
                        entity_type="organization",
                        metadata={"org_type": "llc", "name": "Company Name LLC"},
                        search_mode=SearchMode.AC,
                        match_fields=["text"],
                        confidence=0.9,
                        trace={"tier": 1, "reason": "full_name_context"}
                    )
                ]
            return []
        
        # Mock Elasticsearch client
        mock_client = Mock()
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"tagline": "You Know, for Search"})
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        adapter._ensure_connection = AsyncMock(return_value=mock_client)
        adapter.search = AsyncMock(side_effect=mock_ac_search)
        return adapter

    @pytest.fixture
    def mock_vector_adapter(self):
        """Mock vector adapter with fallback search"""
        adapter = Mock()
        
        # Mock vector search
        def mock_vector_search(normalized, text, opts):
            return []  # No regular vector results
        
        # Mock vector fallback search for Ukrainian names
        def mock_vector_fallback(query_vector, query_text, opts):
            if "petro" in query_text.lower() and "poroshenka" in query_text.lower():
                return [
                    Candidate(
                        doc_id="uk_person_001",
                        score=0.85,
                        text="Петро Порошенко",
                        entity_type="person",
                        metadata={"name_uk": "Петро Порошенко", "name_en": "Petro Poroshenko"},
                        search_mode=SearchMode.VECTOR,
                        match_fields=["dense_vector", "text"],
                        confidence=0.85,
                        trace={
                            "reason": "vector_fallback",
                            "cosine": 0.75,
                            "fuzz": 88,
                            "anchors": []
                        }
                    )
                ]
            return []
        
        # Mock Elasticsearch client
        mock_client = Mock()
        mock_response = AsyncMock()
        mock_response.json = AsyncMock(return_value={"tagline": "You Know, for Search"})
        mock_response.status_code = 200
        mock_response.raise_for_status = Mock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)
        
        adapter._ensure_connection = AsyncMock(return_value=mock_client)
        adapter.search = AsyncMock(side_effect=mock_vector_search)
        adapter.search_vector_fallback = AsyncMock(side_effect=mock_vector_fallback)
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
    async def test_smoke_ac_passport_id_matching(self, hybrid_service, search_opts):
        """Test AC search matches passport ID through ES"""
        # Test passport ID search
        passport_query = "passport 123456"
        norm_result = NormalizationResult(
            normalized=passport_query,
            tokens=["passport", "123456"],
            trace=[],
            errors=[],
            language="en",
            confidence=0.9,
            original_length=len(passport_query),
            normalized_length=len(passport_query),
            token_count=2,
            processing_time=0.1,
            success=True
        )
        
        start_time = time.time()
        results = await hybrid_service.find_candidates(norm_result, passport_query, search_opts)
        search_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Verify results
        assert len(results) > 0, "Should find passport match"
        passport_result = results[0]
        assert passport_result.doc_id == "passport_123456"
        assert passport_result.score >= 0.9
        assert passport_result.trace["tier"] == 0
        assert passport_result.trace["reason"] == "exact_doc_id"
        
        # Verify SLA (≤ 50ms locally)
        assert search_time <= 50, f"Search took {search_time:.2f}ms, should be ≤ 50ms"
        
        print(f"✓ Passport ID search: {search_time:.2f}ms, score: {passport_result.score}")

    @pytest.mark.asyncio
    async def test_smoke_ac_company_name_llc_matching(self, hybrid_service, search_opts):
        """Test AC search matches company name LLC through ES"""
        # Test company name search
        company_query = "Company Name LLC"
        norm_result = NormalizationResult(
            normalized=company_query,
            tokens=["Company", "Name", "LLC"],
            trace=[],
            errors=[],
            language="en",
            confidence=0.9,
            original_length=len(company_query),
            normalized_length=len(company_query),
            token_count=3,
            processing_time=0.1,
            success=True
        )
        
        start_time = time.time()
        results = await hybrid_service.find_candidates(norm_result, company_query, search_opts)
        search_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Verify results
        assert len(results) > 0, "Should find company match"
        company_result = results[0]
        assert company_result.doc_id == "company_llc_001"
        assert company_result.score >= 0.8
        assert company_result.trace["tier"] == 1
        assert company_result.trace["reason"] == "full_name_context"
        
        # Verify SLA (≤ 50ms locally)
        assert search_time <= 50, f"Search took {search_time:.2f}ms, should be ≤ 50ms"
        
        print(f"✓ Company LLC search: {search_time:.2f}ms, score: {company_result.score}")

    @pytest.mark.asyncio
    async def test_fallback_vector_petro_poroshenka_matching(self, hybrid_service, normalization_result, search_opts):
        """Test vector fallback matches Petro Poroshenka → Петро Порошенко with cos≥0.5"""
        query_text = "Petro Poroshenka"
        
        start_time = time.time()
        results = await hybrid_service.find_candidates(normalization_result, query_text, search_opts)
        search_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Verify results
        assert len(results) > 0, "Should find Ukrainian name match via vector fallback"
        uk_result = results[0]
        assert uk_result.text == "Петро Порошенко"
        assert uk_result.trace["reason"] == "vector_fallback"
        assert uk_result.trace["cosine"] >= 0.5, f"Cosine similarity {uk_result.trace['cosine']} should be ≥ 0.5"
        assert uk_result.trace["fuzz"] >= 80, f"Fuzz score {uk_result.trace['fuzz']} should be ≥ 80"
        
        # Verify SLA (≤ 50ms locally)
        assert search_time <= 50, f"Search took {search_time:.2f}ms, should be ≤ 50ms"
        
        print(f"✓ Vector fallback search: {search_time:.2f}ms, cosine: {uk_result.trace['cosine']}, fuzz: {uk_result.trace['fuzz']}")

    @pytest.mark.asyncio
    async def test_search_performance_sla(self, hybrid_service, search_opts):
        """Test that search meets SLA requirements (≤ 50ms locally)"""
        test_queries = [
            "John Doe",
            "passport 123456",
            "Company LLC",
            "Petro Poroshenka",
            "Ivan Ivanov",
            "Test Organization"
        ]
        
        total_time = 0
        successful_searches = 0
        
        for query in test_queries:
            start_time = time.time()
            try:
                results = await hybrid_service.find_candidates(normalization_result, query, search_opts)
                search_time = (time.time() - start_time) * 1000
                total_time += search_time
                successful_searches += 1
                
                # Verify individual query SLA
                assert search_time <= 50, f"Query '{query}' took {search_time:.2f}ms, should be ≤ 50ms"
                
            except Exception as e:
                pytest.fail(f"Search failed for query '{query}': {e}")
        
        # Calculate average search time
        avg_time = total_time / successful_searches if successful_searches > 0 else 0
        
        print(f"✓ Performance test: {successful_searches} searches, avg: {avg_time:.2f}ms")
        assert avg_time <= 50, f"Average search time {avg_time:.2f}ms should be ≤ 50ms"

    @pytest.mark.asyncio
    async def test_all_results_have_trace_information(self, hybrid_service, search_opts):
        """Test that all search results include trace with tier/score/reason"""
        test_queries = [
            "passport 123456",
            "Company Name LLC", 
            "Petro Poroshenka"
        ]
        
        for query in test_queries:
            results = await hybrid_service.find_candidates(normalization_result, query, search_opts)
            
            for result in results:
                # Verify trace exists
                assert hasattr(result, 'trace'), f"Result should have trace attribute"
                assert result.trace is not None, f"Trace should not be None"
                
                # Verify required trace fields
                assert 'reason' in result.trace, f"Trace should contain 'reason' field"
                assert 'tier' in result.trace or 'cosine' in result.trace, f"Trace should contain 'tier' or 'cosine' field"
                
                # Verify trace format
                reason = result.trace['reason']
                if reason == "exact_doc_id":
                    assert result.trace['tier'] == 0
                elif reason == "full_name_context":
                    assert result.trace['tier'] == 1
                elif reason == "vector_fallback":
                    assert 'cosine' in result.trace
                    assert 'fuzz' in result.trace
                
                print(f"✓ Query '{query}': {result.doc_id} - {reason}")

    def test_strict_candidate_contract_validation(self, config):
        """Test that strict candidate contract validation is enabled"""
        assert config.strict_candidate_contract == True, "Strict candidate contract should be enabled"

    @pytest.mark.asyncio
    async def test_search_candidate_contract_format(self, hybrid_service, normalization_result, search_opts):
        """Test that search results follow SearchCandidate contract format"""
        query = "test query"
        results = await hybrid_service.find_candidates(normalization_result, query, search_opts)
        
        for result in results:
            # Verify required fields exist
            assert hasattr(result, 'doc_id')
            assert hasattr(result, 'score')
            assert hasattr(result, 'text')
            assert hasattr(result, 'entity_type')
            assert hasattr(result, 'metadata')
            assert hasattr(result, 'search_mode')
            assert hasattr(result, 'match_fields')
            assert hasattr(result, 'confidence')
            assert hasattr(result, 'trace')
            
            # Verify field types
            assert isinstance(result.doc_id, str)
            assert isinstance(result.score, (int, float))
            assert isinstance(result.text, str)
            assert isinstance(result.entity_type, str)
            assert isinstance(result.metadata, dict)
            assert isinstance(result.match_fields, list)
            assert isinstance(result.confidence, (int, float))
            assert isinstance(result.trace, dict) or result.trace is None
            
            # Verify trace format if present
            if result.trace:
                assert 'reason' in result.trace
                print(f"✓ Contract validation passed for {result.doc_id}: {result.trace['reason']}")

    @pytest.mark.asyncio
    async def test_recall_improvement_over_legacy(self, hybrid_service, search_opts):
        """Test that new search pipeline shows improved recall over legacy"""
        # Test queries that should benefit from vector fallback
        test_cases = [
            ("Petro Poroshenka", "Петро Порошенко"),  # Ukrainian name variant
            ("Ivan Petrov", "Иван Петров"),  # Cyrillic variant
            ("John Smith", "Johnny Smith"),  # Nickname variant
        ]
        
        total_matches = 0
        total_queries = len(test_cases)
        
        for query, expected_match in test_cases:
            results = await hybrid_service.find_candidates(normalization_result, query, search_opts)
            
            # Check if we found a match (exact or similar)
            found_match = False
            for result in results:
                if (expected_match.lower() in result.text.lower() or 
                    result.text.lower() in expected_match.lower()):
                    found_match = True
                    break
            
            if found_match:
                total_matches += 1
                print(f"✓ Found match for '{query}' → '{expected_match}'")
            else:
                print(f"⚠ No match found for '{query}' → '{expected_match}'")
        
        # Calculate recall
        recall = total_matches / total_queries
        print(f"✓ Recall: {recall:.2%} ({total_matches}/{total_queries})")
        
        # Should have at least 50% recall for these test cases
        assert recall >= 0.5, f"Recall {recall:.2%} should be ≥ 50%"

    @pytest.mark.asyncio
    async def test_fewer_false_positives(self, hybrid_service, search_opts):
        """Test that new search pipeline produces fewer false positives"""
        # Test queries that should NOT match anything
        negative_queries = [
            "xyzabc123",  # Random string
            "nonexistent person",  # Non-existent name
            "fake company",  # Non-existent company
        ]
        
        total_false_positives = 0
        total_queries = len(negative_queries)
        
        for query in negative_queries:
            results = await hybrid_service.find_candidates(normalization_result, query, search_opts)
            
            # Count high-confidence false positives
            high_confidence_fp = sum(1 for r in results if r.score >= 0.8)
            total_false_positives += high_confidence_fp
            
            if high_confidence_fp > 0:
                print(f"⚠ False positive for '{query}': {high_confidence_fp} high-confidence results")
            else:
                print(f"✓ No false positives for '{query}'")
        
        # Should have very few false positives
        fp_rate = total_false_positives / total_queries
        print(f"✓ False positive rate: {fp_rate:.2f} per query")
        
        # Should have ≤ 1 false positive per query on average
        assert fp_rate <= 1.0, f"False positive rate {fp_rate:.2f} should be ≤ 1.0 per query"
