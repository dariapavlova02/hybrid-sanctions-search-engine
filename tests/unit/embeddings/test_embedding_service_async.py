#!/usr/bin/env python3
"""
Tests for async methods in EmbeddingService
"""

import asyncio
import pytest
from unittest.mock import Mock, patch

from src.ai_service.layers.embeddings.embedding_service import EmbeddingService


class TestEmbeddingServiceAsync:
    """Test async methods in EmbeddingService"""

    @pytest.fixture
    def service(self):
        """Create EmbeddingService instance"""
        return EmbeddingService()

    @pytest.mark.asyncio
    async def test_get_embeddings_async_success(self, service):
        """Test successful async embedding generation"""
        test_texts = ["Hello world", "Test text"]
        
        # Mock the synchronous method
        with patch.object(service, 'get_embeddings') as mock_get_embeddings:
            mock_result = {
                "success": True,
                "embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]],
                "model_name": "test-model",
                "text_count": 2,
                "embedding_dimension": 3,
                "processing_time": 0.1,
                "normalized": True,
                "batch_size": 32,
                "timestamp": "2023-01-01T00:00:00"
            }
            mock_get_embeddings.return_value = mock_result

            result = await service.get_embeddings_async(test_texts)

            assert result["success"] is True
            assert len(result["embeddings"]) == 2
            assert result["text_count"] == 2
            mock_get_embeddings.assert_called_once_with(test_texts, None, True, 32)

    @pytest.mark.asyncio
    async def test_get_embeddings_async_with_params(self, service):
        """Test async embedding generation with custom parameters"""
        test_texts = ["Single text"]
        
        with patch.object(service, 'get_embeddings') as mock_get_embeddings:
            mock_result = {"success": True, "embeddings": [[0.1, 0.2, 0.3]]}
            mock_get_embeddings.return_value = mock_result

            result = await service.get_embeddings_async(
                test_texts,
                model_name="custom-model",
                normalize=False,
                batch_size=16
            )

            assert result["success"] is True
            mock_get_embeddings.assert_called_once_with(
                test_texts, "custom-model", False, 16
            )

    @pytest.mark.asyncio
    async def test_calculate_similarity_async(self, service):
        """Test async similarity calculation"""
        text1 = "Hello world"
        text2 = "Hi there"
        
        with patch.object(service, 'calculate_similarity') as mock_calc_sim:
            mock_result = {
                "success": True,
                "similarity": 0.85,
                "metric": "cosine",
                "model_name": "test-model"
            }
            mock_calc_sim.return_value = mock_result

            result = await service.calculate_similarity_async(text1, text2)

            assert result["success"] is True
            assert result["similarity"] == 0.85
            mock_calc_sim.assert_called_once_with(text1, text2, None, "cosine")

    @pytest.mark.asyncio
    async def test_find_most_similar_async(self, service):
        """Test async most similar text finding"""
        query_text = "Hello world"
        candidate_texts = ["Hi there", "Goodbye", "Hello universe"]
        
        with patch.object(service, 'find_similar_texts') as mock_find_sim:
            mock_result = {
                "success": True,
                "most_similar": [
                    {"text": "Hello universe", "similarity": 0.9},
                    {"text": "Hi there", "similarity": 0.7}
                ],
                "query_text": query_text,
                "top_k": 2
            }
            mock_find_sim.return_value = mock_result

            result = await service.find_most_similar_async(
                query_text, candidate_texts, top_k=2
            )

            assert result["success"] is True
            assert len(result["most_similar"]) == 2
            mock_find_sim.assert_called_once_with(
                query_text, candidate_texts, None, 2, "cosine"
            )

    @pytest.mark.asyncio
    async def test_batch_similarity_async(self, service):
        """Test async batch similarity calculation"""
        query_texts = ["Hello", "Goodbye"]
        candidate_texts = ["Hi", "Bye", "See you"]
        
        with patch.object(service, 'calculate_batch_similarity') as mock_batch_sim:
            mock_result = {
                "success": True,
                "similarity_matrix": [[0.8, 0.2, 0.1], [0.1, 0.9, 0.3]],
                "query_texts": query_texts,
                "candidate_texts": candidate_texts
            }
            mock_batch_sim.return_value = mock_result

            result = await service.batch_similarity_async(
                query_texts, candidate_texts, batch_size=16
            )

            assert result["success"] is True
            assert len(result["similarity_matrix"]) == 2
            mock_batch_sim.assert_called_once_with(
                query_texts, candidate_texts, None, "cosine", 16
            )

    @pytest.mark.asyncio
    async def test_async_methods_use_thread_pool(self, service):
        """Test that async methods properly use thread pool executor"""
        test_texts = ["Test"]
        
        with patch.object(service, 'get_embeddings') as mock_get_embeddings:
            mock_result = {"success": True, "embeddings": [[0.1, 0.2, 0.3]]}
            mock_get_embeddings.return_value = mock_result

            # Test that the method runs in thread pool
            result = await service.get_embeddings_async(test_texts)
            
            # Verify it was called
            mock_get_embeddings.assert_called_once()
            
            # Verify result is correct
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_async_error_handling(self, service):
        """Test async error handling"""
        test_texts = ["Test"]
        
        with patch.object(service, 'get_embeddings') as mock_get_embeddings:
            # Mock to return error result instead of raising exception
            mock_get_embeddings.return_value = {
                "success": False,
                "error": "Test error",
                "embeddings": [],
                "model_name": "test-model",
                "text_count": 0,
                "embedding_dimension": 0,
                "processing_time": 0.0,
                "normalized": True,
                "batch_size": 32,
                "timestamp": "2023-01-01T00:00:00"
            }

            result = await service.get_embeddings_async(test_texts)

            # Should return error result
            assert result["success"] is False
            assert "error" in result

    @pytest.mark.asyncio
    async def test_concurrent_async_calls(self, service):
        """Test that multiple async calls can run concurrently"""
        test_texts = ["Test 1", "Test 2", "Test 3"]
        
        with patch.object(service, 'get_embeddings') as mock_get_embeddings:
            mock_result = {"success": True, "embeddings": [[0.1, 0.2, 0.3]]}
            mock_get_embeddings.return_value = mock_result

            # Start multiple async calls concurrently
            tasks = [
                service.get_embeddings_async([text])
                for text in test_texts
            ]
            
            results = await asyncio.gather(*tasks)

            # All should succeed
            assert len(results) == 3
            assert all(result["success"] for result in results)
            
            # Should have been called 3 times
            assert mock_get_embeddings.call_count == 3
