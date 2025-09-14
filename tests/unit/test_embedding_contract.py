"""
Unit tests for embedding service contract - pure vector generation only
"""

import pytest
from ai_service.config import EmbeddingConfig
from ai_service.layers.embeddings.embedding_service import EmbeddingService


class TestEmbeddingContract:
    """Test embedding service contract - only vector generation, no indexing"""

    def test_encode_one_returns_384_floats(self):
        """Test that encode_one returns exactly 384 float values"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        result = service.encode_one("Ivan Ivanov")
        
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(x, float) for x in result)

    def test_encode_batch_returns_2x384(self):
        """Test that encode_batch returns 2 vectors of 384 floats each"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        result = service.encode_batch(["A", "B"])
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(len(vector) == 384 for vector in result)
        assert all(isinstance(x, float) for vector in result for x in vector)

    def test_encode_one_empty_text(self):
        """Test that encode_one handles empty text correctly"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        result = service.encode_one("")
        assert result == []
        
        result = service.encode_one("   ")
        assert result == []

    def test_encode_batch_empty_list(self):
        """Test that encode_batch handles empty list correctly"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        result = service.encode_batch([])
        assert result == []

    def test_encode_batch_mixed_valid_empty(self):
        """Test that encode_batch filters out empty texts"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        result = service.encode_batch(["Valid text", "", "   ", "Another valid"])
        
        assert isinstance(result, list)
        assert len(result) == 2  # Only valid texts
        assert all(len(vector) == 384 for vector in result)

    def test_legacy_encode_method_still_works(self):
        """Test that legacy encode method still works for backward compatibility"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Test single text
        result_single = service.encode("Single text")
        assert isinstance(result_single, list)
        assert len(result_single) == 384
        
        # Test multiple texts
        result_batch = service.encode(["Text 1", "Text 2"])
        assert isinstance(result_batch, list)
        assert len(result_batch) == 2
        assert all(len(vector) == 384 for vector in result_batch)

    def test_no_similarity_methods_exist(self):
        """Test that similarity/search methods are not available"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Check that similarity methods don't exist
        assert not hasattr(service, 'calculate_similarity')
        assert not hasattr(service, 'find_similar_texts')
        assert not hasattr(service, 'calculate_batch_similarity')
        assert not hasattr(service, 'find_most_similar_async')

    def test_no_indexing_imports(self):
        """Test that EmbeddingService doesn't import VectorIndex"""
        import inspect
        from ai_service.layers.embeddings.embedding_service import EmbeddingService
        
        # Get the source file
        source_file = inspect.getfile(EmbeddingService)
        
        # Read the source file and check it doesn't import vector index
        with open(source_file, 'r') as f:
            source_content = f.read()
        
        # Should not import vector index services
        assert 'vector_index_service' not in source_content
        assert 'VectorIndexService' not in source_content
        assert 'from ..indexing' not in source_content

    def test_enable_index_ignored(self):
        """Test that enable_index=False is ignored by EmbeddingService"""
        config = EmbeddingConfig(enable_index=True)  # Set to True
        service = EmbeddingService(config)
        
        # Service should still work normally regardless of enable_index
        result = service.encode_one("Test text")
        assert len(result) == 384
        
        # Service should not have any indexing-related methods
        assert not hasattr(service, 'add_to_index')
        assert not hasattr(service, 'search_index')
        assert not hasattr(service, 'build_index')

    def test_pure_vector_generation_contract(self):
        """Test that service only generates vectors, nothing else"""
        config = EmbeddingConfig()
        service = EmbeddingService(config)
        
        # Should only have vector generation methods
        expected_methods = {
            'encode_one', 'encode_batch', 'encode',  # Vector generation
            'get_embedding_dimension', 'get_model_info',  # Info methods
            '_load_model'  # Internal method
        }
        
        # Get only callable methods (not attributes)
        actual_methods = {method for method in dir(service) 
                         if callable(getattr(service, method)) and 
                         (not method.startswith('_') or method == '_load_model')}
        
        # Should not have more methods than expected
        extra_methods = actual_methods - expected_methods
        assert not extra_methods, f"Unexpected methods found: {extra_methods}"

    def test_batch_size_from_config(self):
        """Test that batch_size is read from configuration"""
        config = EmbeddingConfig(batch_size=32)
        service = EmbeddingService(config)
        
        # Test that the service uses the configured batch size
        # We can't directly test this, but we can verify the config is stored
        assert service.config.batch_size == 32

    def test_device_from_config(self):
        """Test that device is read from configuration"""
        config = EmbeddingConfig(device="cpu")
        service = EmbeddingService(config)
        
        model_info = service.get_model_info()
        assert model_info["device"] == "cpu"
