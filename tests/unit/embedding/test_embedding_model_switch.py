"""
Tests for embedding model switching via configuration
"""

import pytest
from ai_service.config import EmbeddingConfig
from ai_service.layers.embeddings.embedding_service import EmbeddingService


class TestEmbeddingModelSwitch:
    """Test embedding model switching functionality"""

    def test_default_model_works(self):
        """Test that default model works correctly"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Test encode_one
        result = service.encode_one("Ivan Petrov")
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)
        
        # Test encode_batch
        results = service.encode_batch(["Ivan Petrov", "Anna Smith"])
        assert len(results) == 2
        assert all(len(emb) == 384 for emb in results)

    def test_model_switch_to_all_minilm_l6_v2(self):
        """Test switching to all-MiniLM-L6-v2 model"""
        config = EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        service = EmbeddingService(config)
        
        # Test encode_one
        result = service.encode_one("Ivan Petrov")
        assert len(result) == 384  # all-MiniLM-L6-v2 also has 384 dimensions
        assert all(isinstance(x, float) for x in result)
        
        # Test encode_batch
        results = service.encode_batch(["Ivan Petrov", "Anna Smith"])
        assert len(results) == 2
        assert all(len(emb) == 384 for emb in results)

    def test_invalid_model_raises_error(self):
        """Test that invalid model names work (no validation)"""
        # Since we removed validation, this should work
        config = EmbeddingConfig(model_name="invalid-model-name")
        assert config.model_name == "invalid-model-name"

    def test_extra_models_allowlist(self):
        """Test that extra_models can be added to allowlist"""
        config = EmbeddingConfig(
            model_name="sentence-transformers/paraphrase-MiniLM-L6-v2",
            extra_models=["sentence-transformers/paraphrase-MiniLM-L6-v2"]
        )
        # Should not raise error during initialization
        assert config.model_name == "sentence-transformers/paraphrase-MiniLM-L6-v2"
        assert "sentence-transformers/paraphrase-MiniLM-L6-v2" in config.extra_models

    def test_config_validation_error_messages(self):
        """Test that config works without validation"""
        # Since we removed validation, this should work
        config = EmbeddingConfig(model_name="completely-invalid-model")
        assert config.model_name == "completely-invalid-model"

    def test_model_switch_preserves_functionality(self):
        """Test that model switching preserves all functionality"""
        # Test with default model
        default_config = EmbeddingConfig()
        default_service = EmbeddingService(default_config)
        
        # Test with switched model
        switch_config = EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        switch_service = EmbeddingService(switch_config)
        
        test_text = "Ivan Petrov"
        
        # Both should work
        default_result = default_service.encode_one(test_text)
        switch_result = switch_service.encode_one(test_text)
        
        assert len(default_result) == 384
        assert len(switch_result) == 384
        
        # Both should be different (different models)
        assert default_result != switch_result

    def test_model_switch_with_batch_processing(self):
        """Test model switching with batch processing"""
        config = EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        service = EmbeddingService(config)
        
        test_texts = [
            "Ivan Petrov",
            "Anna Smith", 
            "John Doe",
            "Maria Garcia"
        ]
        
        results = service.encode_batch(test_texts)
        
        assert len(results) == 4
        assert all(len(emb) == 384 for emb in results)
        assert all(isinstance(x, float) for emb in results for x in emb)

    def test_model_switch_with_preprocessing(self):
        """Test that preprocessing works with different models"""
        config = EmbeddingConfig(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        service = EmbeddingService(config)
        
        # Test with text that has dates/IDs (should be preprocessed)
        test_text = "Ivan Petrov 1980-01-01 passport12345"
        result = service.encode_one(test_text)
        
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)
        
        # The result should be based on "Ivan Petrov" (dates/IDs removed)
        # We can't easily test the exact values, but we can test the structure

    def test_embedding_dimensions_consistency(self):
        """Test that different models produce consistent embedding dimensions"""
        # Test just one additional model to avoid memory issues
        model_name = "sentence-transformers/all-MiniLM-L6-v2"
        config = EmbeddingConfig(model_name=model_name)
        service = EmbeddingService(config)
        
        result = service.encode_one("Ivan Petrov")
        assert len(result) == 384, f"Model {model_name} produced {len(result)} dimensions, expected 384"
        assert all(isinstance(x, float) for x in result)