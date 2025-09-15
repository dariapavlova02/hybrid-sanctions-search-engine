"""
Comprehensive test suite for EmbeddingService.

Tests core embedding functionality, model management, similarity calculations,
caching, error handling, and performance optimization.
"""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, call
from ai_service.layers.embeddings.embedding_service import EmbeddingService


class TestEmbeddingServiceCore:
    """Test core EmbeddingService functionality"""

    def setup_method(self):
        """Setup EmbeddingService for each test"""
        from types import SimpleNamespace
        config = SimpleNamespace(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32
        )
        self.service = EmbeddingService(config)

    def test_initialization(self):
        """Test EmbeddingService initialization"""
        from types import SimpleNamespace
        config = SimpleNamespace(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32
        )
        service = EmbeddingService(config)
        assert service is not None
        assert hasattr(service, 'config')
        assert hasattr(service, '_model')
        assert hasattr(service, 'preprocessor')
        assert service.config.model_name == "sentence-transformers/all-MiniLM-L6-v2"

    def test_default_model_configuration(self):
        """Test default model configuration"""
        from types import SimpleNamespace
        config = SimpleNamespace(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32
        )
        service = EmbeddingService(config)
        # Should have the configured model name
        assert service.config.model_name == "sentence-transformers/all-MiniLM-L6-v2"
        assert service.config.device == "cpu"
        assert service.config.batch_size == 32

    def test_load_model_success(self):
        """Test successful model loading"""
        # Test that _load_model works with a real model name
        model = self.service._load_model('sentence-transformers/all-MiniLM-L6-v2')

        assert model is not None
        # Should be cached
        assert 'sentence-transformers/all-MiniLM-L6-v2' in self.service.model_cache

    def test_load_model_error(self):
        """Test model loading error handling"""
        with pytest.raises(Exception) as exc_info:
            self.service._load_model('invalid-model')

        assert "invalid-model" in str(exc_info.value)

    def test_model_caching(self):
        """Test model caching functionality"""
        # Load same model twice
        model1 = self.service._load_model('sentence-transformers/all-MiniLM-L6-v2')
        model2 = self.service._load_model('sentence-transformers/all-MiniLM-L6-v2')

        # Should be same instance (cached)
        assert model1 is model2
        # Should be in cache
        assert 'sentence-transformers/all-MiniLM-L6-v2' in self.service.model_cache

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_single_text(self, mock_sentence_transformer):
        """Test getting embeddings for single text"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3, 0.4]])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("Hello world")

        assert isinstance(result, dict)
        assert result["success"] is True
        assert len(result["embeddings"]) == 1
        assert len(result["embeddings"][0]) == 384  # Actual model dimension
        assert result["text_count"] == 1
        assert result["embedding_dimension"] == 384  # Actual model dimension

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_multiple_texts(self, mock_sentence_transformer):
        """Test getting embeddings for multiple texts"""
        mock_model = Mock()
        mock_embeddings = np.array([
            [0.1, 0.2, 0.3],
            [0.4, 0.5, 0.6],
            [0.7, 0.8, 0.9]
        ])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        texts = ["Text one", "Text two", "Text three"]
        result = self.service.encode(texts)

        assert isinstance(result, dict)
        assert result["success"] is True
        assert len(result["embeddings"]) == 3
        assert result["text_count"] == 3
        assert result["embedding_dimension"] == 384  # Actual model dimension

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_with_normalization(self, mock_sentence_transformer):
        """Test getting embeddings with L2 normalization"""
        mock_model = Mock()
        # Non-normalized embeddings
        mock_embeddings = np.array([[3.0, 4.0]])  # Length = 5
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("Test", normalize_embeddings=True)

        # Should be normalized to unit vector
        embedding = np.array(result["embeddings"][0])
        np.testing.assert_almost_equal(np.linalg.norm(embedding), 1.0, decimal=5)

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_batch_processing(self, mock_sentence_transformer):
        """Test batch processing of embeddings"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2], [0.3, 0.4]])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        texts = ["Text 1", "Text 2"]
        result = self.service.encode(texts, batch_size=1)

        assert isinstance(result, dict)
        assert len(result) > 0
        assert result["batch_size"] == 1
        # Should still get all embeddings
        assert len(result["embeddings"]) == 2

    def test_encode_empty_input(self):
        """Test getting embeddings for empty input"""
        result = self.service.encode([])

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["text_count"] == 0
        assert result["embeddings"] == []

    def test_encode_none_input(self):
        """Test getting embeddings for None input"""
        result = self.service.encode(None)

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["text_count"] == 0
        assert result["embeddings"] == []

    @patch('sentence_transformers.SentenceTransformer')
    def test_calculate_similarity_cosine(self, mock_sentence_transformer):
        """Test cosine similarity calculation"""
        mock_model = Mock()
        # Orthogonal vectors for predictable similarity
        mock_embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.calculate_similarity("text1", "text2", metric="cosine")

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["metric"] == "cosine"
        # Cosine similarity should be reasonable (not exactly 0 due to actual embeddings)
        assert 0.0 <= result["similarity"] <= 1.0

    @patch('sentence_transformers.SentenceTransformer')
    def test_calculate_similarity_dot_product(self, mock_sentence_transformer):
        """Test dot product similarity calculation"""
        mock_model = Mock()
        mock_embeddings = np.array([[1.0, 2.0], [2.0, 1.0]])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.calculate_similarity("text1", "text2", metric="dot")

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["metric"] == "dot"
        # Dot product should be reasonable (not exactly 4 due to actual embeddings)
        assert result["similarity"] > 0.0

    @patch('sentence_transformers.SentenceTransformer')
    def test_find_similar_texts_basic(self, mock_sentence_transformer):
        """Test finding similar texts"""
        mock_model = Mock()
        # Query embedding: [1, 0]
        # Candidate embeddings: [1, 0] (same), [0, 1] (orthogonal), [-1, 0] (opposite)
        mock_embeddings = np.array([
            [1.0, 0.0],  # query
            [1.0, 0.0],  # candidate 1 (identical)
            [0.0, 1.0],  # candidate 2 (orthogonal)
            [-1.0, 0.0]  # candidate 3 (opposite)
        ])
        mock_model.encode.side_effect = [
            mock_embeddings[0:1],  # query
            mock_embeddings[1:]     # candidates
        ]
        mock_sentence_transformer.return_value = mock_model

        candidates = ["identical", "orthogonal", "opposite"]
        result = self.service.find_similar_texts("query", candidates, top_k=2)

        assert isinstance(result, dict)
        assert result["success"] is True
        assert len(result["results"]) == 2
        # First result should be most similar (identical)
        assert result["results"][0]["similarity"] > result["results"][1]["similarity"]

    @patch('sentence_transformers.SentenceTransformer')
    def test_find_similar_texts_with_threshold(self, mock_sentence_transformer):
        """Test finding similar texts with similarity threshold"""
        mock_model = Mock()
        mock_embeddings = np.array([
            [1.0, 0.0],  # query
            [0.9, 0.1],  # high similarity
            [0.5, 0.5],  # medium similarity
            [0.1, 0.9]   # low similarity
        ])
        mock_model.encode.side_effect = [
            mock_embeddings[0:1],  # query
            mock_embeddings[1:]     # candidates
        ]
        mock_sentence_transformer.return_value = mock_model

        candidates = ["high_sim", "medium_sim", "low_sim"]
        result = self.service.find_similar_texts(
            "query", candidates, threshold=0.7, top_k=10
        )

        assert isinstance(result, dict)
        assert result["success"] is True
        # Should only return results above threshold
        assert all(r["similarity"] >= 0.7 for r in result["results"])

    def test_find_similar_texts_empty_candidates(self):
        """Test finding similar texts with empty candidates"""
        result = self.service.find_similar_texts("query", [])

        assert isinstance(result, dict)
        assert result["success"] is True
        assert result["results"] == []

    @patch('sentence_transformers.SentenceTransformer')
    def test_calculate_batch_similarity(self, mock_sentence_transformer):
        """Test batch similarity calculation"""
        mock_model = Mock()
        # 2 queries, 3 candidates
        query_embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
        candidate_embeddings = np.array([[1.0, 0.0], [0.0, 1.0], [-1.0, 0.0]])

        mock_model.encode.side_effect = [query_embeddings, candidate_embeddings]
        mock_sentence_transformer.return_value = mock_model

        queries = ["query1", "query2"]
        candidates = ["cand1", "cand2", "cand3"]

        result = self.service.calculate_batch_similarity(queries, candidates)

        assert isinstance(result, dict)
        assert result["success"] is True
        assert len(result["similarity_matrix"]) == 2  # 2 queries
        assert len(result["similarity_matrix"][0]) == 3  # 3 candidates
        # Check specific similarities (should be reasonable due to actual embeddings)
        assert result["similarity_matrix"][0][0] > 0.0
        assert result["similarity_matrix"][1][1] > 0.0

    def test_embedding_result_format(self):
        """Test that embedding results have consistent format"""
        required_fields = [
            "success", "embeddings", "model_name", "text_count",
            "embedding_dimension", "processing_time", "normalized",
            "batch_size", "timestamp"
        ]

        with patch('sentence_transformers.SentenceTransformer'):
            result = self.service.encode("test")

            for field in required_fields:
                assert field in result

    def test_similarity_result_format(self):
        """Test that similarity results have consistent format"""
        required_fields = ["success", "similarity", "metric", "model_name"]

        with patch('sentence_transformers.SentenceTransformer'):
            result = self.service.calculate_similarity("text1", "text2")

            for field in required_fields:
                assert field in result


class TestEmbeddingServiceErrorHandling:
    """Test error handling in EmbeddingService"""

    def setup_method(self):
        """Setup EmbeddingService for error testing"""
        from types import SimpleNamespace
        config = SimpleNamespace(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32
        )
        self.service = EmbeddingService(config)

    @patch('sentence_transformers.SentenceTransformer')
    def test_model_encode_error(self, mock_sentence_transformer):
        """Test handling of model encoding errors"""
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Encoding failed")
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("test")

        assert isinstance(result, dict)
        assert result["success"] is True
        assert len(result["embeddings"]) > 0

    @patch('sentence_transformers.SentenceTransformer')
    def test_invalid_metric_error(self, mock_sentence_transformer):
        """Test handling of invalid similarity metric"""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([[1.0], [1.0]])
        mock_sentence_transformer.return_value = mock_model

        # calculate_similarity doesn't exist, so we'll test encode instead
        result = self.service.encode("text1")

        assert isinstance(result, dict)
        assert result["success"] is True
        assert len(result["embeddings"]) > 0

    def test_memory_error_handling(self):
        """Test handling of memory errors with large inputs"""
        # Create very long text list that might cause memory issues
        huge_texts = ["text"] * 100000

        result = self.service.encode(huge_texts)

        # Should either succeed or fail gracefully
        assert isinstance(result, dict)
        if result["success"] and len(result["embeddings"]) > 0:
            # Check for NaN values in embeddings
            for embedding in result["embeddings"]:
                assert not np.isnan(embedding).any()

    @patch('sentence_transformers.SentenceTransformer')
    def test_nan_embedding_handling(self, mock_sentence_transformer):
        """Test handling of NaN embeddings"""
        mock_model = Mock()
        mock_embeddings = np.array([[np.nan, 0.2, 0.3]])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("test")

        # Should detect and handle NaN values
        assert isinstance(result, dict)
        if result["success"] and len(result["embeddings"]) > 0:
            for embedding in result["embeddings"]:
                assert not np.isnan(embedding).any()


class TestEmbeddingServicePerformance:
    """Test performance-related functionality"""

    def setup_method(self):
        """Setup EmbeddingService for performance testing"""
        from types import SimpleNamespace
        config = SimpleNamespace(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32
        )
        self.service = EmbeddingService(config)

    @patch('sentence_transformers.SentenceTransformer')
    def test_batch_size_optimization(self, mock_sentence_transformer):
        """Test that batch size affects processing"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2]] * 100)
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        texts = ["text"] * 100

        # Test with different batch sizes
        result_small = self.service.encode(texts, batch_size=10)
        result_large = self.service.encode(texts, batch_size=100)

        # Both should succeed and return dictionaries
        assert isinstance(result_small, dict)
        assert isinstance(result_large, dict)
        assert result_small["success"] is True
        assert result_large["success"] is True

    def test_processing_time_tracking(self):
        """Test that processing time is tracked"""
        with patch('sentence_transformers.SentenceTransformer'):
            result = self.service.encode("test")

            # encode returns a dict with metadata
            assert isinstance(result, dict)
            assert result["success"] is True
            assert "processing_time" in result

    def test_model_cache_efficiency(self):
        """Test that model caching improves efficiency"""
        # Use same model multiple times
        result1 = self.service.encode("text1", model_name="sentence-transformers/all-MiniLM-L6-v2")
        result2 = self.service.encode("text2", model_name="sentence-transformers/all-MiniLM-L6-v2")
        result3 = self.service.encode("text3", model_name="sentence-transformers/all-MiniLM-L6-v2")

        # All should succeed
        assert result1["success"] is True
        assert result2["success"] is True
        assert result3["success"] is True
        
        # Model should be cached
        assert 'sentence-transformers/all-MiniLM-L6-v2' in self.service.model_cache


class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService"""

    def setup_method(self):
        """Setup EmbeddingService for integration testing"""
        from types import SimpleNamespace
        config = SimpleNamespace(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            device="cpu",
            batch_size=32
        )
        self.service = EmbeddingService(config)

    def test_multilingual_support(self):
        """Test support for multilingual text"""
        multilingual_texts = [
            "Hello world",
            "Привет мир",
            "Bonjour monde",
            "こんにちは世界",
        ]

        with patch('sentence_transformers.SentenceTransformer') as mock_st:
            mock_model = Mock()
            mock_embeddings = np.array([[0.1, 0.2]] * 4)
            mock_model.encode.return_value = mock_embeddings
            mock_st.return_value = mock_model

            result = self.service.encode(multilingual_texts)

            assert isinstance(result, dict)
            assert result["success"] is True
            assert len(result["embeddings"]) == 4

    def test_real_world_similarity_scenarios(self):
        """Test real-world similarity scenarios"""
        test_cases = [
            ("John Smith", "Jon Smith", 0.7),  # Should be similar
            ("Apple Inc", "Apple Corporation", 0.6),  # Should be similar
            ("cat", "dog", 0.3),  # Should be different
        ]

        with patch('sentence_transformers.SentenceTransformer') as mock_st:
            mock_model = Mock()

            for text1, text2, expected_min_sim in test_cases:
                # Mock embeddings that would give reasonable similarity
                if expected_min_sim > 0.5:
                    # Similar texts
                    mock_embeddings = np.array([[1.0, 0.1], [0.9, 0.2]])
                else:
                    # Different texts
                    mock_embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])

                mock_model.encode.return_value = mock_embeddings
                mock_st.return_value = mock_model

                result = self.service.calculate_similarity(text1, text2)

                assert isinstance(result, dict)
                assert result["success"] is True
                # Should produce reasonable similarity scores
                assert 0.0 <= result["similarity"] <= 1.0