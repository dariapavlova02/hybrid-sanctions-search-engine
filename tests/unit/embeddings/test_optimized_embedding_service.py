"""
Unit tests for OptimizedEmbeddingService
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from ai_service.layers.embeddings.optimized_embedding_service import OptimizedEmbeddingService


class TestOptimizedEmbeddingService:
    """Tests for OptimizedEmbeddingService"""

    @pytest.fixture
    def optimized_service(self):
        """Create OptimizedEmbeddingService instance"""
        return OptimizedEmbeddingService(
            max_cache_size=100,
            enable_batch_optimization=True,
            enable_gpu=False,  # Disable GPU for testing
            thread_pool_size=2,
            precompute_common_patterns=False,  # Disable for faster test setup
        )

    def test_service_initialization(self, optimized_service):
        """Test service initialization"""
        assert optimized_service.max_cache_size == 100
        assert optimized_service.enable_batch_optimization is True
        assert optimized_service.thread_pool_size == 2
        assert optimized_service.gpu_available is False  # Disabled for testing
        assert len(optimized_service.embedding_cache) == 0

    def test_cache_key_generation(self, optimized_service):
        """Test cache key generation"""
        key1 = optimized_service._get_cache_key("test text", "model1")
        key2 = optimized_service._get_cache_key("test text", "model2")
        key3 = optimized_service._get_cache_key("other text", "model1")

        # Same text, different model should have different keys
        assert key1 != key2

        # Different text, same model should have different keys
        assert key1 != key3

        # Same inputs should produce same key
        assert key1 == optimized_service._get_cache_key("test text", "model1")

    def test_embedding_caching(self, optimized_service):
        """Test embedding caching functionality"""
        text = "test text"
        model = "test_model"
        embedding = [0.1, 0.2, 0.3]

        # Initially no cache entry
        assert optimized_service._get_cached_embedding(text, model) is None

        # Cache the embedding
        optimized_service._cache_embedding(text, model, embedding)

        # Should now be cached
        cached = optimized_service._get_cached_embedding(text, model)
        assert cached == embedding

    def test_cache_lru_eviction(self):
        """Test LRU cache eviction when cache is full"""
        service = OptimizedEmbeddingService(max_cache_size=2, precompute_common_patterns=False)

        # Add first embedding
        service._cache_embedding("text1", "model", [0.1, 0.2])
        assert len(service.embedding_cache) == 1

        # Add second embedding
        service._cache_embedding("text2", "model", [0.3, 0.4])
        assert len(service.embedding_cache) == 2

        # Add third embedding - should evict oldest
        service._cache_embedding("text3", "model", [0.5, 0.6])
        assert len(service.embedding_cache) == 2

        # text1 should be evicted, text2 and text3 should remain
        assert service._get_cached_embedding("text1", "model") is None
        assert service._get_cached_embedding("text2", "model") is not None
        assert service._get_cached_embedding("text3", "model") is not None

    @patch('sentence_transformers.SentenceTransformer')
    def test_optimized_embeddings_with_cache(self, mock_transformer_class, optimized_service):
        """Test optimized embedding generation with caching"""
        # Mock the transformer
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_transformer_class.return_value = mock_model

        texts = ["text1", "text2"]

        # First call - should generate embeddings
        result1 = optimized_service.get_embeddings_optimized(texts, use_cache=True)

        assert result1["success"] is True
        assert len(result1["embeddings"]) == 2
        assert result1["cache_hits"] == 0
        assert result1["cache_misses"] == 2

        # Second call - should use cache
        result2 = optimized_service.get_embeddings_optimized(texts, use_cache=True)

        assert result2["success"] is True
        assert len(result2["embeddings"]) == 2
        assert result2["cache_hits"] == 2
        assert result2["cache_misses"] == 0

        # Model should only be called once
        assert mock_model.encode.call_count == 1

    @patch('sentence_transformers.SentenceTransformer')
    def test_optimized_embeddings_without_cache(self, mock_transformer_class, optimized_service):
        """Test optimized embedding generation without caching"""
        # Mock the transformer
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
        mock_transformer_class.return_value = mock_model

        text = "test text"

        # Call with cache disabled
        result = optimized_service.get_embeddings_optimized([text], use_cache=False)

        assert result["success"] is True
        assert len(result["embeddings"]) == 1
        assert result["cache_hits"] == 0
        assert result["cache_misses"] == 1

        # Cache should be empty
        assert len(optimized_service.embedding_cache) == 0

    def test_performance_metrics_tracking(self, optimized_service):
        """Test performance metrics are properly tracked"""
        initial_metrics = optimized_service.get_performance_metrics()

        assert initial_metrics["cache_hit_rate"] == 0.0
        assert initial_metrics["total_embeddings_generated"] == 0
        assert initial_metrics["gpu_available"] is False

    @patch('sentence_transformers.SentenceTransformer')
    def test_batch_optimization(self, mock_transformer_class):
        """Test batch size optimization"""
        service = OptimizedEmbeddingService(
            enable_batch_optimization=True,
            enable_gpu=False,  # Simulate no GPU
            precompute_common_patterns=False,
        )

        # Mock the transformer
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2]] * 100  # 100 embeddings
        mock_transformer_class.return_value = mock_model

        # Large batch should trigger optimization
        texts = [f"text_{i}" for i in range(100)]
        result = service.get_embeddings_optimized(texts)

        assert result["success"] is True
        # Batch size should remain standard since no GPU
        assert result["batch_size"] == 32

    def test_gpu_availability_check(self):
        """Test GPU availability checking"""
        # Test with GPU disabled
        service_no_gpu = OptimizedEmbeddingService(enable_gpu=False, precompute_common_patterns=False)
        assert service_no_gpu.gpu_available is False

        # Test with GPU enabled but not available (in test environment)
        service_gpu = OptimizedEmbeddingService(enable_gpu=True, precompute_common_patterns=False)
        # Should be False in test environment without CUDA
        assert service_gpu.gpu_available is False

    @patch('sentence_transformers.SentenceTransformer')
    def test_optimized_similarity_search(self, mock_transformer_class, optimized_service):
        """Test optimized similarity search"""
        # Mock the transformer
        mock_model = Mock()
        mock_model.encode.return_value = [
            [1.0, 0.0, 0.0],  # Query
            [0.9, 0.1, 0.0],  # Very similar
            [0.1, 0.9, 0.0],  # Less similar
            [0.0, 0.0, 1.0],  # Not similar
        ]
        mock_transformer_class.return_value = mock_model

        query = "test query"
        candidates = ["similar text", "different text", "unrelated text"]

        result = optimized_service.find_similar_texts_optimized(
            query, candidates, threshold=0.5, top_k=2
        )

        assert result["success"] is True
        assert result["optimized"] is True
        assert len(result["results"]) <= 2  # Respects top_k
        assert result["total_candidates"] == 3

    @patch('ai_service.layers.embeddings.optimized_embedding_service.faiss')
    @patch('sentence_transformers.SentenceTransformer')
    def test_faiss_acceleration(self, mock_transformer_class, mock_faiss, optimized_service):
        """Test FAISS acceleration for large candidate sets"""
        # Mock FAISS
        mock_index = Mock()
        mock_index.search.return_value = ([[0.9, 0.8]], [[0, 1]])
        mock_faiss.IndexFlatIP.return_value = mock_index
        mock_faiss.normalize_L2 = Mock()

        # Mock the transformer
        mock_model = Mock()
        # Query + many candidates
        embeddings = [[1.0, 0.0]] + [[0.1, 0.9]] * 150
        mock_model.encode.return_value = embeddings
        mock_transformer_class.return_value = mock_model

        query = "test query"
        candidates = [f"candidate_{i}" for i in range(150)]  # Large candidate set

        result = optimized_service.find_similar_texts_optimized(
            query, candidates, use_faiss=True, threshold=0.5
        )

        assert result["success"] is True
        assert result["faiss_accelerated"] is True

    def test_numpy_similarity_search(self, optimized_service):
        """Test numpy-based similarity search"""
        query_embedding = [1.0, 0.0, 0.0]
        candidate_embeddings = [
            [0.9, 0.1, 0.0],  # High similarity
            [0.5, 0.5, 0.0],  # Medium similarity
            [0.0, 1.0, 0.0],  # Low similarity
        ]
        candidates = ["high_sim", "med_sim", "low_sim"]

        results = optimized_service._numpy_similarity_search(
            query_embedding, candidate_embeddings, candidates, top_k=2, threshold=0.7, metric="cosine"
        )

        assert len(results) >= 1  # At least the high similarity result
        assert results[0]["text"] == "high_sim"  # Should be ranked first
        assert results[0]["similarity_score"] > 0.7

    def test_cache_clearing(self, optimized_service):
        """Test cache clearing functionality"""
        # Add some items to cache
        optimized_service._cache_embedding("text1", "model", [0.1, 0.2])
        optimized_service._cache_embedding("text2", "model", [0.3, 0.4])

        assert len(optimized_service.embedding_cache) == 2

        # Clear cache
        optimized_service.clear_cache()

        assert len(optimized_service.embedding_cache) == 0

    @patch('sentence_transformers.SentenceTransformer')
    def test_cache_warmup(self, mock_transformer_class, optimized_service):
        """Test cache warm-up functionality"""
        # Mock the transformer
        mock_model = Mock()
        mock_model.encode.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        mock_transformer_class.return_value = mock_model

        texts = ["warm up text 1", "warm up text 2"]

        # Initially cache is empty
        assert len(optimized_service.embedding_cache) == 0

        # Warm up cache
        optimized_service.warm_up_cache(texts)

        # Cache should now contain the texts
        assert len(optimized_service.embedding_cache) == 2

    def test_error_handling(self, optimized_service):
        """Test error handling in optimized service"""
        # Test with invalid model
        result = optimized_service.get_embeddings_optimized(
            ["test"], model_name="invalid_model_name"
        )

        # Should handle error gracefully
        assert "success" in result
        # Depending on implementation, might succeed with fallback or fail gracefully

    @pytest.mark.asyncio
    async def test_async_optimized_methods(self, optimized_service):
        """Test optimized async methods"""
        with patch.object(optimized_service, 'get_embeddings_optimized') as mock_get_embeddings:
            mock_get_embeddings.return_value = {
                "success": True,
                "embeddings": [[0.1, 0.2, 0.3]],
                "processing_time": 0.001,
            }

            # Test async embedding generation
            result = await optimized_service.get_embeddings_async_optimized(["test text"])

            assert result["success"] is True
            mock_get_embeddings.assert_called_once()

        with patch.object(optimized_service, 'find_similar_texts_optimized') as mock_find_similar:
            mock_find_similar.return_value = {
                "success": True,
                "results": [{"text": "similar", "similarity_score": 0.9, "rank": 1}],
            }

            # Test async similarity search
            result = await optimized_service.find_similar_texts_async_optimized(
                "query", ["candidate"]
            )

            assert result["success"] is True
            mock_find_similar.assert_called_once()

    def test_performance_under_load(self, optimized_service):
        """Test performance with multiple concurrent operations"""
        with patch.object(optimized_service, '_load_model_optimized') as mock_load:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]] * 50
            mock_load.return_value = mock_model

            # Simulate multiple operations
            texts_list = [["text1", "text2"], ["text3", "text4"], ["text5", "text6"]]

            start_time = time.time()
            results = []

            for texts in texts_list:
                result = optimized_service.get_embeddings_optimized(texts)
                results.append(result)

            total_time = time.time() - start_time

            # All operations should succeed
            assert all(r["success"] for r in results)

            # Should complete reasonably quickly (adjust threshold as needed)
            assert total_time < 5.0

    def test_metrics_accumulation(self, optimized_service):
        """Test that performance metrics accumulate correctly"""
        with patch.object(optimized_service, '_load_model_optimized') as mock_load:
            mock_model = Mock()
            mock_model.encode.return_value = [[0.1, 0.2, 0.3]]
            mock_load.return_value = mock_model

            # Perform multiple operations
            for i in range(5):
                optimized_service.get_embeddings_optimized([f"text_{i}"])

            metrics = optimized_service.get_performance_metrics()

            assert metrics["total_embeddings_generated"] == 5
            assert metrics["cache_hit_rate"] >= 0.0  # Should be valid rate
            assert metrics["average_processing_time"] > 0.0

    def test_thread_safety(self, optimized_service):
        """Test thread safety of cache operations"""
        import threading
        import time

        errors = []

        def cache_operation(thread_id):
            try:
                for i in range(10):
                    text = f"thread_{thread_id}_text_{i}"
                    embedding = [float(thread_id), float(i)]

                    optimized_service._cache_embedding(text, "model", embedding)
                    cached = optimized_service._get_cached_embedding(text, "model")

                    if cached != embedding:
                        errors.append(f"Cache mismatch in thread {thread_id}")

                    time.sleep(0.001)  # Small delay to increase chance of race conditions
            except Exception as e:
                errors.append(f"Exception in thread {thread_id}: {e}")

        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=cache_operation, args=(i,))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check that no errors occurred
        assert len(errors) == 0, f"Thread safety errors: {errors}"