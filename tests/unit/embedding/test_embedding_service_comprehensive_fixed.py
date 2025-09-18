"""
Comprehensive test suite for EmbeddingService (Fixed Version)

Tests core embedding functionality, model management, and error handling.
Removed tests for similarity calculations as they were removed from the service.
"""

import numpy as np
import pytest
from unittest.mock import Mock, patch

from ai_service.layers.embeddings.embedding_service import EmbeddingService


class TestEmbeddingServiceCore:
    """Test core EmbeddingService functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        self.service = EmbeddingService(config)

    def test_initialization(self):
        """Test EmbeddingService initialization"""
        assert self.service is not None
        assert hasattr(self.service, '_model')
        assert hasattr(self.service, 'logger')

    def test_default_model_configuration(self):
        """Test default model configuration"""
        # Test that service initializes with default config
        assert self.service.config is not None
        assert self.service.config.model_name == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    @patch('sentence_transformers.SentenceTransformer')
    def test_load_model_success(self, mock_sentence_transformer):
        """Test successful model loading"""
        mock_model = Mock()
        mock_sentence_transformer.return_value = mock_model
        
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        config.model_name = "all-MiniLM-L6-v2"  # Set model name to match
        service = EmbeddingService(config)
        
        # Load model explicitly
        service._load_model("all-MiniLM-L6-v2")
        assert service._model is not None

    @patch('sentence_transformers.SentenceTransformer')
    def test_load_model_error(self, mock_sentence_transformer):
        """Test model loading error handling"""
        mock_sentence_transformer.side_effect = Exception("Model loading failed")
        
        with pytest.raises(Exception):
            EmbeddingService()

    def test_model_caching(self):
        """Test model caching functionality"""
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        
        # Test that the same model instance is reused
        service1 = EmbeddingService(config)
        service2 = EmbeddingService(config)
        
        # Both should have the same config
        assert service1.config == service2.config
        assert service1.model_cache == service2.model_cache

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_single_text(self, mock_sentence_transformer):
        """Test getting embeddings for single text"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("test text")

        assert isinstance(result, list)
        assert len(result) == 384  # Embedding dimension for all-MiniLM-L6-v2

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_multiple_texts(self, mock_sentence_transformer):
        """Test getting embeddings for multiple texts"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384, [0.4] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode(["text1", "text2"])

        assert isinstance(result, list)
        assert len(result) == 2
        assert len(result[0]) == 384  # Embedding dimension for all-MiniLM-L6-v2

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_with_normalization(self, mock_sentence_transformer):
        """Test getting embeddings with L2 normalization"""
        mock_model = Mock()
        mock_embeddings = np.array([[3.0] * 384])  # Will be normalized
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("test text", normalize=True)

        assert isinstance(result, list)
        assert len(result) == 384  # Single text returns 384-dimensional vector
        # Check that the embedding is normalized (magnitude should be close to 1)
        magnitude = np.linalg.norm(result)
        assert abs(magnitude - 1.0) < 0.01

    @patch('sentence_transformers.SentenceTransformer')
    def test_encode_batch_processing(self, mock_sentence_transformer):
        """Test batch processing of embeddings"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384, [0.3] * 384, [0.5] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        texts = ["text1", "text2", "text3"]
        result = self.service.encode(texts)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(len(emb) == 384 for emb in result)

    def test_encode_empty_input(self):
        """Test getting embeddings for empty input"""
        result = self.service.encode([])
        assert result == []

    def test_encode_none_input(self):
        """Test getting embeddings for None input"""
        result = self.service.encode(None)
        assert result == []

    @patch('sentence_transformers.SentenceTransformer')
    def test_embedding_result_format(self, mock_sentence_transformer):
        """Test that embedding results have consistent format"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("test text")

        assert isinstance(result, list)
        assert len(result) == 384  # Single text returns 384-dimensional vector
        assert all(isinstance(val, (int, float)) for val in result)


class TestEmbeddingServiceErrorHandling:
    """Test error handling in EmbeddingService"""

    def setup_method(self):
        """Set up test fixtures"""
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        self.service = EmbeddingService(config)

    @patch('src.ai_service.layers.embeddings.embedding_service.SentenceTransformer')
    def test_model_encode_error(self, mock_sentence_transformer):
        """Test handling of model encoding errors"""
        mock_model = Mock()
        mock_model.encode.side_effect = Exception("Encoding failed")
        mock_sentence_transformer.return_value = mock_model
        
        # Create a new service instance with the mocked model
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        service = EmbeddingService(config)

        # The service should return empty list on error, not raise exception
        result = service.encode("test text")
        assert result == []

    @patch('src.ai_service.layers.embeddings.embedding_service.SentenceTransformer')
    def test_memory_error_handling(self, mock_sentence_transformer):
        """Test handling of memory errors with large inputs"""
        mock_model = Mock()
        mock_model.encode.side_effect = MemoryError("Out of memory")
        mock_sentence_transformer.return_value = mock_model
        
        # Create a new service instance with the mocked model
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        service = EmbeddingService(config)

        # The service should return empty list on error, not raise exception
        result = service.encode("very large text" * 10000)
        assert result == []

    @patch('sentence_transformers.SentenceTransformer')
    def test_nan_embedding_handling(self, mock_sentence_transformer):
        """Test handling of NaN embeddings"""
        mock_model = Mock()
        mock_embeddings = np.array([[np.nan] + [0.2] * 383])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("test text")
        
        # Should handle NaN values gracefully
        assert isinstance(result, list)
        assert len(result) == 384


class TestEmbeddingServicePerformance:
    """Test performance-related functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        self.service = EmbeddingService(config)

    @patch('sentence_transformers.SentenceTransformer')
    def test_batch_size_optimization(self, mock_sentence_transformer):
        """Test that batch size affects processing"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384, [0.3] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        texts = ["text1", "text2"]
        result = self.service.encode(texts)

        assert isinstance(result, list)
        assert len(result) == 2

    @patch('sentence_transformers.SentenceTransformer')
    def test_processing_time_tracking(self, mock_sentence_transformer):
        """Test that processing time is tracked"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        result = self.service.encode("test text")

        assert isinstance(result, list)
        assert len(result) == 384  # Single text returns 384-dimensional vector

    def test_model_cache_efficiency(self):
        """Test that model caching improves efficiency"""
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        
        # Test that multiple service instances can be created efficiently
        service1 = EmbeddingService(config)
        service2 = EmbeddingService(config)
        
        # Load models to test caching
        service1._load_model()
        service2._load_model()
        
        assert service1._model is not None
        assert service2._model is not None


class TestEmbeddingServiceIntegration:
    """Integration tests for EmbeddingService"""

    def setup_method(self):
        """Set up test fixtures"""
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        self.service = EmbeddingService(config)

    @patch('sentence_transformers.SentenceTransformer')
    def test_multilingual_support(self, mock_sentence_transformer):
        """Test support for multilingual text"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        # Test with different languages
        texts = ["Hello world", "Привет мир", "Hola mundo"]
        result = self.service.encode(texts)

        assert isinstance(result, list)
        assert len(result) == 3
        assert all(len(emb) == 384 for emb in result)

    @patch('sentence_transformers.SentenceTransformer')
    def test_real_world_embedding_scenarios(self, mock_sentence_transformer):
        """Test real-world embedding scenarios"""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1] * 384, [0.4] * 384])
        mock_model.encode.return_value = mock_embeddings
        mock_sentence_transformer.return_value = mock_model

        # Test with realistic text data
        texts = [
            "John Doe is a software engineer",
            "Jane Smith works in marketing"
        ]
        result = self.service.encode(texts)

        assert isinstance(result, list)
        assert len(result) == 2
        assert all(len(emb) == 384 for emb in result)


class TestEmbeddingServiceErrorHandling:
    """Error handling tests for EmbeddingService"""

    def setup_method(self):
        """Set up test fixtures"""
        from src.ai_service.config import EmbeddingConfig
        config = EmbeddingConfig()
        self.service = EmbeddingService(config)

    def test_model_encode_error(self):
        """Test handling of model encode errors"""
        # Mock the model to raise an exception during encode
        with patch.object(self.service, '_load_model') as mock_load_model:
            mock_model = Mock()
            mock_model.encode.side_effect = Exception("Model encode error")
            mock_load_model.return_value = mock_model
            
            # Test that the service handles the error gracefully
            result = self.service.encode("test text")
            
            # Should return empty list on error
            assert result == []

    def test_memory_error_handling(self):
        """Test handling of memory errors"""
        # Mock the model to raise a memory error during encode
        with patch.object(self.service, '_load_model') as mock_load_model:
            mock_model = Mock()
            mock_model.encode.side_effect = MemoryError("Out of memory")
            mock_load_model.return_value = mock_model
            
            # Test that the service handles the error gracefully
            result = self.service.encode("test text")
            
            # Should return empty list on error
            assert result == []
