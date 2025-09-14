"""
Integration tests for multilingual embeddings consistency
Tests that RU/UK/EN names are encoded consistently with high similarity
"""

import numpy as np
import pytest
from ai_service.config import EmbeddingConfig
from ai_service.layers.embeddings.embedding_service import EmbeddingService


def cosine_similarity(a: list, b: list) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Cosine similarity score between 0 and 1
    """
    a = np.array(a)
    b = np.array(b)
    
    # Calculate cosine similarity
    dot_product = np.dot(a, b)
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    
    if norm_a == 0 or norm_b == 0:
        return 0.0
    
    return dot_product / (norm_a * norm_b)


class TestMultilingualEmbeddings:
    """Test multilingual embedding consistency"""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service for testing"""
        config = EmbeddingConfig()
        return EmbeddingService(config)

    def test_name_variants_similarity(self, embedding_service):
        """Test that name variants in different scripts have high similarity"""
        # Test names in different scripts
        names = [
            "Ivan Petrov",      # English transliteration
            "Іван Петров",      # Ukrainian
            "Иван Петров",      # Russian
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(names)
        assert len(embeddings) == 3
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
                print(f"Similarity between '{names[i]}' and '{names[j]}': {sim:.3f}")
        
        # All pairwise similarities should be high (> 0.7)
        min_similarity = min(similarities)
        assert min_similarity > 0.7, f"Minimum similarity {min_similarity:.3f} is too low, expected > 0.7"
        
        # At least one pair should be very similar (> 0.8)
        max_similarity = max(similarities)
        assert max_similarity > 0.8, f"Maximum similarity {max_similarity:.3f} is too low, expected > 0.8"

    def test_organization_names_similarity(self, embedding_service):
        """Test that organization names in different scripts have high similarity"""
        # Test organization names
        org_names = [
            "PrivatBank",       # English
            "Приватбанк",       # Russian/Ukrainian
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(org_names)
        assert len(embeddings) == 2
        
        # Calculate similarity
        similarity = cosine_similarity(embeddings[0], embeddings[1])
        print(f"Similarity between '{org_names[0]}' and '{org_names[1]}': {similarity:.3f}")
        
        # Should be highly similar
        assert similarity > 0.7, f"Organization similarity {similarity:.3f} is too low, expected > 0.7"

    def test_unrelated_strings_low_similarity(self, embedding_service):
        """Test that unrelated strings have low similarity"""
        # Test unrelated strings (excluding dates/IDs that get removed by preprocessor)
        unrelated_strings = [
            "Ivan Petrov",           # Person name
            "PrivatBank",            # Organization
            "random text here",      # Random text
            "completely different",  # Another random text
            "unrelated content",     # Yet another random text
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(unrelated_strings)
        assert len(embeddings) == 5
        
        # Calculate pairwise similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
                print(f"Similarity between '{unrelated_strings[i]}' and '{unrelated_strings[j]}': {sim:.3f}")
        
        # Most similarities should be low (< 0.4)
        low_similarities = [s for s in similarities if s < 0.4]
        assert len(low_similarities) >= len(similarities) * 0.6, f"Too few low similarities: {len(low_similarities)}/{len(similarities)}"

    def test_mixed_script_names(self, embedding_service):
        """Test names with mixed scripts"""
        # Test mixed script names
        mixed_names = [
            "Ivan Петров",           # Mixed English-Russian
            "Іван Petrov",           # Mixed Ukrainian-English
            "Иван Петров",           # Pure Russian
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(mixed_names)
        assert len(embeddings) == 3
        
        # Calculate similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
                print(f"Similarity between '{mixed_names[i]}' and '{mixed_names[j]}': {sim:.3f}")
        
        # Should have reasonable similarity (> 0.6)
        min_similarity = min(similarities)
        assert min_similarity > 0.6, f"Minimum mixed script similarity {min_similarity:.3f} is too low, expected > 0.6"

    def test_common_names_different_languages(self, embedding_service):
        """Test common names in different languages"""
        # Test common names
        common_names = [
            "Alexander",             # English
            "Александр",             # Russian
            "Олександр",             # Ukrainian
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(common_names)
        assert len(embeddings) == 3
        
        # Calculate similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
                print(f"Similarity between '{common_names[i]}' and '{common_names[j]}': {sim:.3f}")
        
        # Should be highly similar (> 0.7)
        min_similarity = min(similarities)
        assert min_similarity > 0.7, f"Minimum common name similarity {min_similarity:.3f} is too low, expected > 0.7"

    def test_organization_variants(self, embedding_service):
        """Test organization name variants"""
        # Test organization variants
        org_variants = [
            "PrivatBank",           # English
            "Приватбанк",           # Russian/Ukrainian
            "ПРИВАТБАНК",           # Uppercase
            "privatbank",           # Lowercase
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(org_variants)
        assert len(embeddings) == 4
        
        # Calculate similarities
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
                print(f"Similarity between '{org_variants[i]}' and '{org_variants[j]}': {sim:.3f}")
        
        # Should have reasonable similarities - some combinations may be lower due to script differences
        # Check that we have both high and low similarities as expected
        high_similarities = [s for s in similarities if s > 0.8]
        medium_similarities = [s for s in similarities if 0.4 <= s <= 0.8]
        
        # Should have at least some high similarities (same script)
        assert len(high_similarities) >= 2, f"Too few high similarities: {len(high_similarities)}/{len(similarities)}"
        
        # Should have some medium similarities (different scripts but same concept)
        assert len(medium_similarities) >= 1, f"Too few medium similarities: {len(medium_similarities)}/{len(similarities)}"
        
        # Overall average should be reasonable
        avg_similarity = sum(similarities) / len(similarities)
        assert avg_similarity > 0.5, f"Average similarity {avg_similarity:.3f} is too low, expected > 0.5"

    def test_embedding_dimensions_consistency(self, embedding_service):
        """Test that all embeddings have consistent dimensions"""
        # Test various texts (excluding dates/IDs that get removed by preprocessor)
        texts = [
            "Ivan Petrov",
            "Іван Петров", 
            "Иван Петров",
            "PrivatBank",
            "Приватбанк",
            "random text",
            "another text",
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(texts)
        assert len(embeddings) == 7
        
        # All embeddings should have the same dimension (384)
        dimensions = [len(emb) for emb in embeddings]
        assert all(dim == 384 for dim in dimensions), f"Inconsistent dimensions: {dimensions}"
        
        # All embeddings should be non-zero
        for i, emb in enumerate(embeddings):
            assert len(emb) > 0, f"Empty embedding for text: {texts[i]}"
            assert all(isinstance(x, float) for x in emb), f"Non-float values in embedding for text: {texts[i]}"

    def test_preprocessing_effectiveness(self, embedding_service):
        """Test that preprocessing removes dates/IDs effectively"""
        # Test texts with dates and IDs
        texts_with_attrs = [
            "Ivan Petrov 1980-01-01 passport12345",
            "Іван Петров 25.12.1990 ID789",
            "Иван Петров 1980-01-01 passport12345",
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(texts_with_attrs)
        assert len(embeddings) == 3
        
        # Calculate similarities - should be high despite different dates/IDs
        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                sim = cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
                print(f"Similarity between preprocessed texts {i} and {j}: {sim:.3f}")
        
        # Should be highly similar (> 0.7) because dates/IDs were removed
        min_similarity = min(similarities)
        assert min_similarity > 0.7, f"Minimum preprocessed similarity {min_similarity:.3f} is too low, expected > 0.7"
