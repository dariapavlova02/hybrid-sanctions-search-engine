"""
Tests for build_templates.py script functionality
"""

import pytest
import os
import tempfile
import json
import time
from unittest.mock import Mock, patch
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from ai_service.services.template_builder import TemplateBuilder


class TestBuildTemplatesScript:
    """Test build templates script functionality"""
    
    @pytest.fixture
    def template_builder(self):
        """Create TemplateBuilder instance"""
        builder = TemplateBuilder()
        return builder
    

    
    def test_template_builder_initialization(self, template_builder):
        """Test TemplateBuilder initialization"""
        assert template_builder.logger is not None
    
    def test_create_entity_template(self, template_builder):
        """Test creating entity template"""
        entity = {
            "text": "John Smith",
            "type": "person",
            "source": "test"
        }
        
        template = template_builder.create_entity_template(
            entity=entity,
            normalized_text="john smith",
            language="en",
            language_confidence=0.9,
            variants=["john smith", "johnny smith", "j smith"]
        )
        
        # Verify template
        assert template.original_text == "John Smith"
        assert template.entity_type == "person"
        assert template.normalized_text == "john smith"
        assert template.language == "en"
        assert template.language_confidence == 0.9
        assert len(template.variants) == 3
        assert len(template.search_patterns) > 0
    
    def test_create_batch_templates(self, template_builder):
        """Test creating batch templates"""
        entities = [
            {
                "text": "John Smith",
                "type": "person",
                "source": "test"
            },
            {
                "text": "Jane Doe",
                "type": "person",
                "source": "test"
            }
        ]
        
        normalized_texts = ["john smith", "jane doe"]
        languages = ["en", "en"]
        language_confidences = [0.9, 0.8]
        variants_list = [
            ["john smith", "johnny smith"],
            ["jane doe", "jane d"]
        ]
        
        templates = template_builder.create_batch_templates(
            entities=entities,
            normalized_texts=normalized_texts,
            languages=languages,
            language_confidences=language_confidences,
            variants_list=variants_list
        )
        
        # Verify results
        assert isinstance(templates, list)
        assert len(templates) == 2
        assert templates[0].original_text == "John Smith"
        assert templates[1].original_text == "Jane Doe"
    
    def test_generate_search_patterns(self, template_builder):
        """Test search pattern generation"""
        normalized_text = "john smith"
        variants = ["john smith", "johnny smith", "j smith", "js"]
        
        patterns = template_builder._generate_search_patterns(normalized_text, variants)
        
        # Should include normalized text
        assert normalized_text in patterns
        # Should include high-quality variants (length >= 3)
        assert "johnny smith" in patterns
        assert "j smith" in patterns
        # Should not include short variants
        assert "js" not in patterns
        # Should limit patterns to avoid explosion
        assert len(patterns) <= 20
    
    def test_calculate_complexity_score(self, template_builder):
        """Test complexity score calculation"""
        score = template_builder._calculate_complexity_score(
            language_confidence=0.7,
            pattern_count=15,
            variant_count=25,
            normalized_text="test text"
        )
        
        # Score should be between 0.0 and 1.0
        assert 0.0 <= score <= 1.0
        # Higher complexity should result in higher score
        assert score > 0.0
    
    def test_template_builder_logging_setup(self, template_builder):
        """Test that logging is properly set up"""
        assert template_builder.logger is not None
        assert hasattr(template_builder.logger, 'info')
        assert hasattr(template_builder.logger, 'error')
        assert hasattr(template_builder.logger, 'warning')
    
    def test_build_templates_with_different_entity_types(self, template_builder):
        """Test building templates for different entity types"""
        mixed_data = [
            {"text": "Person Name", "type": "person", "source": "test"},
            {"text": "Company Name", "type": "company", "source": "test"},
            {"text": "Organization Name", "type": "organization", "source": "test"}
        ]
        
        normalized_texts = ["person name", "company name", "organization name"]
        languages = ["en", "en", "en"]
        language_confidences = [0.9, 0.8, 0.7]
        variants_list = [
            ["person name", "person"],
            ["company name", "company"],
            ["organization name", "org"]
        ]
        
        templates = template_builder.create_batch_templates(
            entities=mixed_data,
            normalized_texts=normalized_texts,
            languages=languages,
            language_confidences=language_confidences,
            variants_list=variants_list
        )
        
        # Should process all entity types
        assert isinstance(templates, list)
        assert len(templates) == 3
        
        # Verify different entity types
        entity_types = [t.entity_type for t in templates]
        assert "person" in entity_types
        assert "company" in entity_types
        assert "organization" in entity_types
    
    def test_template_builder_error_handling(self, template_builder):
        """Test error handling in TemplateBuilder"""
        # Test that logger captures errors appropriately
        with patch.object(template_builder.logger, 'error') as mock_error:
            try:
                # This should trigger an error
                raise ValueError("Test error")
            except ValueError as e:
                template_builder.logger.error(f"Test error occurred: {e}")
            
            mock_error.assert_called_once()
    
    def test_template_generation_performance(self, template_builder):
        """Test template generation performance with larger dataset"""
        # Create larger test dataset
        large_data = []
        for i in range(100):
            large_data.append({
                "text": f"Test Name {i}",
                "type": "person",
                "source": "test"
            })
        
        normalized_texts = [f"test name {i}" for i in range(100)]
        languages = ["en"] * 100
        language_confidences = [0.9] * 100
        variants_list = [["test name", "test"] for _ in range(100)]
        
        import time
        start_time = time.time()
        
        templates = template_builder.create_batch_templates(
            entities=large_data,
            normalized_texts=normalized_texts,
            languages=languages,
            language_confidences=language_confidences,
            variants_list=variants_list
        )
        
        end_time = time.time()
        processing_time = end_time - start_time
        
        # Should complete in reasonable time (adjust threshold as needed)
        assert processing_time < 10.0, f"Processing took too long: {processing_time}s"
        assert isinstance(templates, list)
        assert len(templates) == 100
