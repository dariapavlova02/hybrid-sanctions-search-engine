"""
Unit tests for embedding configuration and service
"""

import pytest
from ai_service.config import EmbeddingConfig
from ai_service.layers.embeddings.embedding_service import EmbeddingService


class TestEmbeddingConfig:
    """Test embedding configuration"""

    def test_default_model_name(self):
        """Test that default model is paraphrase-multilingual-MiniLM-L12-v2"""
        config = EmbeddingConfig()
        assert config.model_name == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    def test_default_device(self):
        """Test that default device is cpu"""
        config = EmbeddingConfig()
        assert config.device == "cpu"

    def test_default_batch_size(self):
        """Test that default batch size is 64"""
        config = EmbeddingConfig()
        assert config.batch_size == 64

    def test_default_enable_index(self):
        """Test that default enable_index is False"""
        config = EmbeddingConfig()
        assert config.enable_index is False

    def test_custom_config(self):
        """Test custom configuration values"""
        config = EmbeddingConfig(
            model_name="custom-model",
            device="cuda",
            batch_size=32,
            enable_index=True
        )
        assert config.model_name == "custom-model"
        assert config.device == "cuda"
        assert config.batch_size == 32
        assert config.enable_index is True


class TestEmbeddingService:
    """Test embedding service functionality"""

    def test_single_text_encoding(self):
        """Test encoding single text returns 384-dimensional vector"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Test single text encoding
        result = service.encode("Ivan Ivanov")
        
        # Should return a single vector
        assert isinstance(result, list)
        assert len(result) == 384  # paraphrase-multilingual-MiniLM-L12-v2 produces 384-dim vectors
        assert all(isinstance(x, float) for x in result)

    def test_multiple_texts_encoding(self):
        """Test encoding multiple texts returns list of 384-dimensional vectors"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Test multiple texts encoding
        texts = ["Ivan Ivanov", "Petr Petrov", "Anna Ivanova"]
        result = service.encode(texts)
        
        # Should return list of vectors
        assert isinstance(result, list)
        assert len(result) == 3  # Three input texts
        assert all(len(vector) == 384 for vector in result)  # Each vector is 384-dimensional
        assert all(isinstance(x, float) for vector in result for x in vector)

    def test_empty_input(self):
        """Test handling of empty input"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Test empty list
        result = service.encode([])
        assert result == []
        
        # Test empty string
        result = service.encode("")
        assert result == []

    def test_device_from_config(self):
        """Test that device is read from configuration"""
        config = EmbeddingConfig(device="cpu")
        service = EmbeddingService(config)
        
        # Get model info to verify device
        model_info = service.get_model_info()
        assert model_info["device"] == "cpu"

    def test_embedding_dimension(self):
        """Test that embedding dimension is 384"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        dimension = service.get_embedding_dimension()
        assert dimension == 384

    def test_model_info(self):
        """Test model information retrieval"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        model_info = service.get_model_info()
        assert "model_name" in model_info
        assert "device" in model_info
        assert "embedding_dimension" in model_info
        assert "max_seq_length" in model_info
        
        assert model_info["model_name"] == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        assert model_info["embedding_dimension"] == 384

    def test_lazy_initialization(self):
        """Test that model is loaded lazily"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Model should not be loaded yet
        assert service._model is None
        
        # First encode call should load the model
        service.encode("test")
        assert service._model is not None
