"""
Canary tests for embedding quality - early regression detection

These tests verify that basic embedding properties remain stable:
1. Multilingual name variants should have high similarity
2. Random words with numbers should have low similarity to names
3. These serve as early warning system for quality regressions
"""

import numpy as np
import pytest
from ai_service.config import EmbeddingConfig
from ai_service.layers.embeddings.embedding_service import EmbeddingService


class TestEmbeddingsCanaryNames:
    """Canary tests for embedding quality and consistency"""

    @pytest.fixture
    def embedding_service(self):
        """Create embedding service for testing"""
        config = EmbeddingConfig()
        return EmbeddingService(config)

    def cosine_similarity(self, vec1: list, vec2: list) -> float:
        """Calculate cosine similarity between two vectors"""
        v1 = np.array(vec1)
        v2 = np.array(vec2)
        
        # Normalize vectors
        v1_norm = v1 / np.linalg.norm(v1)
        v2_norm = v2 / np.linalg.norm(v2)
        
        return float(np.dot(v1_norm, v2_norm))

    def test_multilingual_name_triangle_similarity(self, embedding_service):
        """
        Test that multilingual name variants form a similarity triangle
        
        Oleksandr (EN) ~ Олександр (UK) ~ Александр (RU)
        All pairs should have reasonable similarity (>=0.6-0.7)
        """
        # Multilingual variants of the same name
        names = [
            "Oleksandr",      # English transliteration
            "Олександр",      # Ukrainian
            "Александр",      # Russian
        ]
        
        # Generate embeddings
        embeddings = embedding_service.encode_batch(names)
        assert len(embeddings) == 3
        assert all(len(emb) == 384 for emb in embeddings)
        
        # Calculate similarity matrix
        similarities = []
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                sim = self.cosine_similarity(embeddings[i], embeddings[j])
                similarities.append(sim)
                print(f"Similarity '{names[i]}' ~ '{names[j]}': {sim:.3f}")
        
        # All pairs should have reasonable similarity
        min_similarity = min(similarities)
        avg_similarity = sum(similarities) / len(similarities)
        
        print(f"Min similarity: {min_similarity:.3f}")
        print(f"Avg similarity: {avg_similarity:.3f}")
        
        # Assertions for quality thresholds
        assert min_similarity >= 0.6, f"Minimum similarity {min_similarity:.3f} too low, expected >=0.6"
        assert avg_similarity >= 0.7, f"Average similarity {avg_similarity:.3f} too low, expected >=0.7"
        
        # Triangle property: most similarities should be in reasonable range
        # Allow for some very high similarities (same script variants)
        reasonable_similarities = [sim for sim in similarities if 0.5 <= sim <= 0.99]
        assert len(reasonable_similarities) >= len(similarities) * 0.8, f"Too few reasonable similarities: {len(reasonable_similarities)}/{len(similarities)}"

    def test_name_vs_noise_low_similarity(self, embedding_service):
        """
        Test that random words with numbers have low similarity to names
        
        Names should be semantically distinct from random alphanumeric strings
        """
        # Real names
        names = [
            "Ivan Petrov",
            "Anna Smith", 
            "Олександр Коваленко",
            "Владимир Путин"
        ]
        
        # Random words with numbers (noise)
        noise_texts = [
            "invoice 12345",
            "document 67890",
            "report 2023",
            "file 98765",
            "data 54321",
            "system 11111",
            "error 404",
            "status 200"
        ]
        
        # Generate embeddings
        name_embeddings = embedding_service.encode_batch(names)
        noise_embeddings = embedding_service.encode_batch(noise_texts)
        
        assert len(name_embeddings) == len(names)
        assert len(noise_embeddings) == len(noise_texts)
        
        # Calculate similarities between names and noise
        similarities = []
        for i, name in enumerate(names):
            for j, noise in enumerate(noise_texts):
                sim = self.cosine_similarity(name_embeddings[i], noise_embeddings[j])
                similarities.append(sim)
                print(f"Similarity '{name}' ~ '{noise}': {sim:.3f}")
        
        # All name-noise pairs should have low similarity
        max_similarity = max(similarities)
        avg_similarity = sum(similarities) / len(similarities)
        
        print(f"Max name-noise similarity: {max_similarity:.3f}")
        print(f"Avg name-noise similarity: {avg_similarity:.3f}")
        
        # Assertions for quality thresholds
        assert max_similarity <= 0.35, f"Maximum name-noise similarity {max_similarity:.3f} too high, expected <=0.35"
        assert avg_similarity <= 0.25, f"Average name-noise similarity {avg_similarity:.3f} too high, expected <=0.25"
        
        # Most similarities should be low (allow for some moderate similarities)
        low_similarities = [sim for sim in similarities if sim <= 0.25]
        assert len(low_similarities) >= len(similarities) * 0.6, f"Too few low similarities: {len(low_similarities)}/{len(similarities)}"

    def test_organization_vs_personal_names_distinction(self, embedding_service):
        """
        Test that organization names and personal names are distinguishable
        
        Organizations and personal names should have moderate similarity
        (not too high, not too low)
        """
        # Personal names
        personal_names = [
            "Ivan Petrov",
            "Anna Smith",
            "Олександр Коваленко"
        ]
        
        # Organization names (without dates/IDs due to preprocessing)
        org_names = [
            "Apple Inc",
            "Microsoft Corporation", 
            "Приватбанк",
            "ООО Рога и Копыта"
        ]
        
        # Generate embeddings
        personal_embeddings = embedding_service.encode_batch(personal_names)
        org_embeddings = embedding_service.encode_batch(org_names)
        
        # Calculate similarities between personal and org names
        similarities = []
        for i, personal in enumerate(personal_names):
            for j, org in enumerate(org_names):
                sim = self.cosine_similarity(personal_embeddings[i], org_embeddings[j])
                similarities.append(sim)
                print(f"Similarity '{personal}' ~ '{org}': {sim:.3f}")
        
        avg_similarity = sum(similarities) / len(similarities)
        print(f"Avg personal-org similarity: {avg_similarity:.3f}")
        
        # Personal-org similarity should be moderate (not too high, not too low)
        assert 0.2 <= avg_similarity <= 0.6, f"Personal-org similarity {avg_similarity:.3f} out of expected range [0.2, 0.6]"

    def test_empty_and_whitespace_handling(self, embedding_service):
        """
        Test that empty and whitespace-only inputs are handled gracefully
        
        This prevents regressions in input validation
        """
        # Test empty string
        empty_result = embedding_service.encode_one("")
        assert empty_result == []
        
        # Test whitespace-only string
        whitespace_result = embedding_service.encode_one("   \t\n  ")
        assert whitespace_result == []
        
        # Test batch with mixed empty and valid inputs
        mixed_inputs = ["Ivan Petrov", "", "   ", "Anna Smith"]
        mixed_results = embedding_service.encode_batch(mixed_inputs)
        
        # Should only return embeddings for non-empty inputs
        assert len(mixed_results) == 2  # Only "Ivan Petrov" and "Anna Smith"
        assert all(len(emb) == 384 for emb in mixed_results)

    def test_consistency_across_calls(self, embedding_service):
        """
        Test that embeddings are consistent across multiple calls
        
        Same input should produce same output (deterministic)
        """
        test_text = "Ivan Petrov"
        
        # Generate embeddings multiple times
        emb1 = embedding_service.encode_one(test_text)
        emb2 = embedding_service.encode_one(test_text)
        emb3 = embedding_service.encode_one(test_text)
        
        # All should be identical
        assert emb1 == emb2 == emb3, "Embeddings should be deterministic"
        
        # Test batch consistency
        batch_texts = ["Ivan Petrov", "Anna Smith"]
        batch1 = embedding_service.encode_batch(batch_texts)
        batch2 = embedding_service.encode_batch(batch_texts)
        
        assert batch1 == batch2, "Batch embeddings should be deterministic"

    def test_embedding_dimensions_consistency(self, embedding_service):
        """
        Test that all embeddings have consistent dimensions
        
        All vectors should be 384-dimensional
        """
        test_texts = [
            "Ivan Petrov",
            "Anna Smith",
            "Олександр Коваленко",
            "Приватбанк",
            "Apple Inc"
        ]
        
        # Single text
        single_emb = embedding_service.encode_one(test_texts[0])
        assert len(single_emb) == 384, f"Single embedding dimension {len(single_emb)}, expected 384"
        
        # Batch texts
        batch_embs = embedding_service.encode_batch(test_texts)
        assert len(batch_embs) == len(test_texts), f"Batch size mismatch: {len(batch_embs)} vs {len(test_texts)}"
        
        for i, emb in enumerate(batch_embs):
            assert len(emb) == 384, f"Embedding {i} dimension {len(emb)}, expected 384"
            assert all(isinstance(x, float) for x in emb), f"Embedding {i} contains non-float values"

    def test_preprocessing_removes_dates_ids(self, embedding_service):
        """
        Test that preprocessing correctly removes dates and IDs
        
        This verifies the preprocessing pipeline works as expected
        """
        # Texts with dates and IDs
        texts_with_attrs = [
            "Ivan Petrov 1980-01-01 passport12345",
            "Anna Smith 2023-12-25 ID67890",
            "Олександр Коваленко 1995-06-15 ИНН1234567890"
        ]
        
        # Clean names (what should remain after preprocessing)
        clean_names = [
            "Ivan Petrov",
            "Anna Smith", 
            "Олександр Коваленко"
        ]
        
        # Generate embeddings
        attrs_embeddings = embedding_service.encode_batch(texts_with_attrs)
        clean_embeddings = embedding_service.encode_batch(clean_names)
        
        # Should have same number of embeddings
        assert len(attrs_embeddings) == len(clean_embeddings)
        
        # Embeddings should be very similar (preprocessing should work)
        for i in range(len(attrs_embeddings)):
            sim = self.cosine_similarity(attrs_embeddings[i], clean_embeddings[i])
            assert sim >= 0.95, f"Preprocessing similarity {sim:.3f} too low for text {i}, expected >=0.95"
            print(f"Preprocessing similarity {i}: {sim:.3f}")
