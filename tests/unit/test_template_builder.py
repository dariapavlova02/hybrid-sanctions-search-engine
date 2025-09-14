"""
Unit tests for TemplateBuilder
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from src.ai_service.layers.variants.template_builder import TemplateBuilder, EntityTemplate
from src.ai_service.layers.patterns.unified_pattern_service import UnifiedPatternService


class TestTemplateBuilder:
    """Tests for TemplateBuilder"""
    
    def test_template_creation(self, template_builder):
        """Critically important test: template creation"""
        # Arrange
        entity = {"id": 1, "name": "Test Entity"}
        normalized_text = "test entity"
        language = "en"
        language_confidence = 0.9
        variants = ["test entity", "entity test", "test"]
        
        # Mock PatternService
        mock_patterns = [
            NamePattern("test", "exact", "en", 0.95, {}),
            NamePattern("entity", "exact", "en", 0.90, {}),
            NamePattern("test entity", "full", "en", 1.0, {})
        ]
        
        with patch.object(template_builder, '_generate_search_patterns') as mock_generate:
            mock_generate.return_value = ["test", "entity", "test entity"]
            
            # Act
            template = template_builder.create_entity_template(
                entity=entity,
                normalized_text=normalized_text,
                language=language,
                language_confidence=language_confidence,
                variants=variants
            )
            
            # Assert
            assert isinstance(template, EntityTemplate)
            assert template.original_text == entity.get('text', '')
            assert template.normalized_text == normalized_text
            assert template.language == language
            assert template.language_confidence == language_confidence
            assert template.variants == variants
            
            # Check that templates are created correctly
            assert len(template.search_patterns) >= 1
            
            # Check that complexity_score is calculated
            assert isinstance(template.complexity_score, float)
            assert 0.0 <= template.complexity_score <= 1.0
            
            # Check that timestamp is set
            assert template.creation_date is not None
            
            # Check that _generate_search_patterns was called
            mock_generate.assert_called_once_with(normalized_text, variants)
    
    def test_entity_template_initialization(self, template_builder):
        """Test EntityTemplate initialization"""
        # Arrange
        entity = {"name": "Test"}
        patterns = [NamePattern("test", "exact", "en", 0.9, {})]
        variants = ["test", "tset"]
        
        # Act
        template = EntityTemplate(
            original_text="test",
            entity_type="person",
            source="test",
            normalized_text="test",
            language="en",
            language_confidence=0.8,
            search_patterns=["test"],
            variants=variants,
            token_variants={}
        )
        
        # Assert
        assert template.original_text == "test"
        assert template.creation_date is not None
        assert isinstance(template.complexity_score, float)
    
    def test_entity_template_to_dict(self, template_builder):
        """Test template conversion to dictionary"""
        # Arrange
        entity = {"name": "Test"}
        patterns = [NamePattern("test", "exact", "en", 0.9, {})]
        variants = ["test"]
        embeddings = [0.1, 0.2, 0.3]
        
        template = EntityTemplate(
            original_text="test",
            entity_type="person",
            source="test",
            normalized_text="test",
            language="en",
            language_confidence=0.8,
            search_patterns=["test"],
            variants=variants,
            token_variants={},
            embeddings=embeddings
        )
        
        # Act
        template_dict = template.to_dict()
        
        # Assert
        assert isinstance(template_dict, dict)
        assert template_dict['original_text'] == "test"
        assert template_dict['normalized_text'] == "test"
        assert template_dict['language'] == "en"
        assert template_dict['embeddings'] == embeddings
    
    def test_entity_template_to_dict_with_numpy_embeddings(self, template_builder):
        """Test conversion with numpy embeddings"""
        # Arrange
        import numpy as np
        entity = {"name": "Test"}
        patterns = [NamePattern("test", "exact", "en", 0.9, {})]
        variants = ["test"]
        numpy_embeddings = np.array([0.1, 0.2, 0.3])
        
        template = EntityTemplate(
            original_text="test",
            entity_type="person",
            source="test",
            normalized_text="test",
            language="en",
            language_confidence=0.8,
            search_patterns=["test"],
            variants=variants,
            token_variants={},
            embeddings=numpy_embeddings
        )
        
        # Act
        template_dict = template.to_dict()
        
        # Assert
        assert isinstance(template_dict['embeddings'], list)
        assert template_dict['embeddings'] == [0.1, 0.2, 0.3]
    
    def test_get_search_keywords(self, template_builder):
        """Test search keywords retrieval"""
        # Arrange
        patterns = [
            NamePattern("john", "exact", "en", 0.9, {}),
            NamePattern("doe", "exact", "en", 0.8, {}),
            NamePattern("john doe", "full", "en", 1.0, {})
        ]
        variants = ["john doe", "j doe", "john d"]
        
        template = EntityTemplate(
            original_text="john doe",
            entity_type="person",
            source="test",
            normalized_text="john doe",
            language="en",
            language_confidence=0.9,
            search_patterns=["john", "doe", "john doe"],
            variants=variants,
            token_variants={}
        )
        
        # Act
        keywords = template.get_search_keywords()
        
        # Assert
        assert isinstance(keywords, list)
        expected_keywords = {"john", "doe", "john doe", "j doe", "john d"}
        assert set(keywords) == expected_keywords
    
    def test_get_high_confidence_patterns(self, template_builder):
        """Test high confidence patterns retrieval"""
        # Arrange
        template = EntityTemplate(
            original_text="test",
            entity_type="person",
            source="test",
            normalized_text="test",
            language="en",
            language_confidence=0.9,
            search_patterns=["high", "medium", "low"],
            variants=[],
            token_variants={},
            template_confidence=0.9
        )
        
        # Act
        high_confidence = template.get_high_confidence_patterns(threshold=0.8)
        
        # Assert
        assert len(high_confidence) == 3  # All patterns since template_confidence >= threshold
        assert "high" in high_confidence
    
    def test_build_templates_batch(self, template_builder):
        """Test batch template creation"""
        # Arrange
        entities = [{"id": 1, "name": "Entity 1"}, {"id": 2, "name": "Entity 2"}]
        normalized_texts = ["entity 1", "entity 2"]
        languages = ["en", "en"]
        language_confidences = [0.9, 0.8]
        variants_list = [["entity 1", "ent 1"], ["entity 2", "ent 2"]]
        
        mock_patterns = [NamePattern("test", "exact", "en", 0.9, {})]
        
        with patch.object(template_builder, '_generate_search_patterns') as mock_generate:
            mock_generate.return_value = ["test"]
            
            # Act
            templates = template_builder.create_batch_templates(
                entities=entities,
                normalized_texts=normalized_texts,
                languages=languages,
                language_confidences=language_confidences,
                variants_list=variants_list
            )
            
            # Assert
            assert len(templates) == 2
            for i, template in enumerate(templates):
                assert isinstance(template, EntityTemplate)
                assert template.original_text == entities[i].get('text', '')
                assert template.normalized_text == normalized_texts[i]
                assert template.language == languages[i]
    
    def test_build_templates_batch_with_embeddings(self, template_builder):
        """Test batch creation with embeddings"""
        # Arrange
        entities = [{"id": 1}]
        normalized_texts = ["test"]
        languages = ["en"]
        language_confidences = [0.9]
        variants_list = [["test"]]
        embeddings_list = [[0.1, 0.2, 0.3]]
        
        mock_patterns = [NamePattern("test", "exact", "en", 0.9, {})]
        
        with patch.object(template_builder, '_generate_search_patterns') as mock_generate:
            mock_generate.return_value = ["test"]
            
            # Act
            templates = template_builder.create_batch_templates(
                entities=entities,
                normalized_texts=normalized_texts,
                languages=languages,
                language_confidences=language_confidences,
                variants_list=variants_list,
                embeddings_list=embeddings_list
            )
            
            # Assert
            assert len(templates) == 1
            assert templates[0].embeddings == [0.1, 0.2, 0.3]
    
    def test_build_templates_batch_error_handling(self, template_builder):
        """Test error handling in batch creation"""
        # Arrange
        entities = [{"id": 1}, {"id": 2}]
        normalized_texts = ["test1", "test2"]  # Same number as entities
        languages = ["en", "en"]
        language_confidences = [0.9, 0.9]
        variants_list = [["test1"], ["test2"]]
        
        with patch.object(template_builder, 'create_entity_template') as mock_create:
            mock_create.side_effect = [Exception("Error"), Mock()]
            
            # Act
            templates = template_builder.create_batch_templates(
                entities=entities,
                normalized_texts=normalized_texts,
                languages=languages,
                language_confidences=language_confidences,
                variants_list=variants_list
            )
            
            # Assert
            # Should handle error and continue with others
            assert len(templates) == 1  # Only second successful
    
    def test_calculate_complexity_score(self, template_builder):
        """Test complexity score calculation"""
        # Act
        score1 = template_builder._calculate_complexity_score(
            language_confidence=0.9,  # High confidence
            pattern_count=5,  # Few patterns
            variant_count=10,  # Few variants
            normalized_text="short"  # Short text
        )
        
        score2 = template_builder._calculate_complexity_score(
            language_confidence=0.3,  # Low confidence
            pattern_count=25,  # Many patterns
            variant_count=40,  # Many variants
            normalized_text="very long normalized text with many words and characters"  # Long text
        )
        
        # Assert
        assert 0.0 <= score1 <= 1.0
        assert 0.0 <= score2 <= 1.0
        assert score2 > score1  # Second should be more complex
    
    def test_get_templates_statistics(self, template_builder):
        """Test template statistics retrieval"""
        # Arrange
        patterns1 = [NamePattern("test", "exact", "en", 0.9, {})]
        patterns2 = [
            NamePattern("complex", "exact", "en", 0.8, {}),
            NamePattern("pattern", "partial", "en", 0.7, {})
        ]
        
        templates = [
            EntityTemplate(
                original_text="test",
                entity_type="person",
                source="test",
                normalized_text="test",
                language="en",
                language_confidence=0.9,
                search_patterns=["test"],
                variants=["test"],
                token_variants={},
                complexity_score=0.2
            ),
            EntityTemplate(
                original_text="complex",
                entity_type="person",
                source="test",
                normalized_text="complex",
                language="ru",
                language_confidence=0.8,
                search_patterns=["complex", "pattern"],
                variants=["complex", "comp"],
                token_variants={},
                complexity_score=0.5
            )
        ]
        
        # Act
        stats = template_builder.get_template_statistics(templates)
        
        # Assert
        assert stats['total_templates'] == 2
        assert stats['total_patterns'] == 3
        assert stats['total_variants'] == 3
        assert stats['average_complexity'] == 0.35  # (0.2 + 0.5) / 2
        
        # Check language distribution
        assert stats['language_distribution']['en'] == 1
        assert stats['language_distribution']['ru'] == 1
        
        # Check that stats contain expected keys
        assert 'total_templates' in stats
        assert 'total_patterns' in stats
    
    def test_get_templates_statistics_empty(self, template_builder):
        """Test statistics for empty list"""
        # Act
        stats = template_builder.get_template_statistics([])
        
        # Assert
        assert isinstance(stats, dict)
    
    def test_export_templates_for_aho_corasick(self, template_builder):
        """Test template export for Aho-Corasick"""
        # Arrange
        high_confidence_pattern = NamePattern("high", "exact", "en", 0.9, {})
        low_confidence_pattern = NamePattern("low", "exact", "en", 0.5, {})
        
        templates = [
            EntityTemplate(
                original_text="test",
                entity_type="person",
                source="test",
                normalized_text="test",
                language="en",
                language_confidence=0.9,
                search_patterns=["high", "low"],
                variants=["variant1", "variant2"],
                token_variants={}
            )
        ]
        
        # Act
        patterns = template_builder.export_for_aho_corasick(templates)
        
        # Assert
        assert isinstance(patterns, list)
        assert "variant1" in patterns  # Variants should be included
        assert "variant2" in patterns
        
        # Check uniqueness
        assert len(patterns) == len(set(patterns))
    
    def test_template_builder_error_handling(self, template_builder):
        """Test error handling in TemplateBuilder"""
        # Arrange
        with patch.object(template_builder, '_generate_search_patterns') as mock_generate:
            mock_generate.side_effect = Exception("Pattern generation failed")
            
            # Act
            template = template_builder.create_entity_template(
                entity={},
                normalized_text="test",
                language="en",
                language_confidence=0.9,
                variants=[]
            )
            
            # Assert
            # Should return minimal template on error
            assert template is not None
            assert template.template_confidence == 0.0  # Low confidence on error
    
    def test_complexity_score_edge_cases(self, template_builder):
        """Test edge cases in complexity calculation"""
        # Act
        # Maximum complexity
        max_score = template_builder._calculate_complexity_score(
            language_confidence=0.0,  # Minimum confidence
            pattern_count=100,  # Very many patterns
            variant_count=100,  # Very many variants
            normalized_text="x" * 1000  # Very long text
        )
        
        # Minimum complexity
        min_score = template_builder._calculate_complexity_score(
            language_confidence=1.0,  # Maximum confidence
            pattern_count=1,  # Minimum patterns
            variant_count=1,  # Minimum variants
            normalized_text="x"  # Short text
        )
        
        # Assert
        assert max_score <= 1.0  # Should not exceed 1.0
        assert min_score >= 0.0  # Should not be less than 0.0
        assert max_score > min_score
    
    def test_template_post_init(self, template_builder):
        """Test automatic field initialization in EntityTemplate"""
        # Arrange & Act
        template = EntityTemplate(
            original_text="test",
            entity_type="person",
            source="test",
            normalized_text="test",
            language="en",
            language_confidence=0.9,
            search_patterns=["test"],
            variants=["test", "tset"],
            token_variants={}
        )
        
        # Assert
        assert template.creation_date is not None
        assert len(template.search_patterns) == 1
        assert len(template.variants) == 2
        
        # Check that timestamp is in correct format
        datetime.fromisoformat(template.creation_date)  # Should not fail
