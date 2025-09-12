"""
Unit tests for EnhancedTemplateBuilder
"""

import pytest
from unittest.mock import Mock, patch
from src.ai_service.services.enhanced_template_builder import EnhancedTemplateBuilder
from src.ai_service.services.template_builder import EntityTemplate


class TestEnhancedTemplateBuilder:
    """Test cases for EnhancedTemplateBuilder"""

    def setup_method(self):
        """Set up test fixtures"""
        self.builder = EnhancedTemplateBuilder()

    def test_initialization(self):
        """Test service initialization"""
        assert self.builder is not None
        assert hasattr(self.builder, 'logger')
        assert hasattr(self.builder, 'pattern_generator')
        assert hasattr(self.builder, 'entity_configs')
        assert 'person' in self.builder.entity_configs
        assert 'company' in self.builder.entity_configs
        assert 'document' in self.builder.entity_configs

    def test_entity_configs(self):
        """Test entity configuration settings"""
        person_config = self.builder.entity_configs['person']
        assert person_config['require_context_for_surnames'] is True
        assert person_config['min_confidence'] == 0.6
        assert person_config['max_patterns_per_entity'] == 15

        company_config = self.builder.entity_configs['company']
        assert company_config['require_legal_form'] is False
        assert company_config['min_confidence'] == 0.7
        assert company_config['max_patterns_per_entity'] == 20

        document_config = self.builder.entity_configs['document']
        assert document_config['require_context'] is False
        assert document_config['min_confidence'] == 0.95
        assert document_config['max_patterns_per_entity'] == 5

    @patch('src.ai_service.services.enhanced_template_builder.HighRecallACGenerator')
    def test_create_optimized_entity_template_person(self, mock_generator_class):
        """Test creating optimized template for person entity"""
        # Mock the pattern generator
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator

        # Mock pattern generation
        mock_pattern = Mock()
        mock_pattern.pattern = "John Smith"
        mock_pattern.variants = ["J. Smith", "JOHN SMITH"]
        mock_pattern.pattern_type = "full_name_aggressive"
        mock_pattern.precision_hint = 0.9
        mock_pattern.source_confidence = 0.8
        mock_pattern.recall_tier = 1

        mock_generator.generate_high_recall_patterns.return_value = [mock_pattern]

        # Test data
        entity = {
            'text': 'John Smith',
            'type': 'person',
            'source': 'test'
        }

        template = self.builder.create_optimized_entity_template(
            entity=entity,
            normalized_text="john smith",
            language="en",
            language_confidence=0.9,
            variants=["john smith", "j. smith"],
            token_variants={"john": ["j", "jon"]},
            embeddings=[0.1, 0.2, 0.3],
            entity_metadata={"age": 30}
        )

        assert isinstance(template, EntityTemplate)
        assert template.original_text == "John Smith"
        assert template.entity_type == "person"
        assert template.normalized_text == "john smith"
        assert template.language == "en"
        assert template.language_confidence == 0.9
        assert "John Smith" in template.search_patterns
        assert template.template_confidence > 0
        assert hasattr(template, 'metadata')
        assert template.metadata['optimization_applied'] is True

    def test_convert_to_ac_patterns(self):
        """Test converting optimized patterns to AC patterns"""
        # Mock pattern objects
        mock_pattern1 = Mock()
        mock_pattern1.pattern = "John Smith"
        mock_pattern1.variants = ["J. Smith"]
        mock_pattern1.pattern_type = "full_name_aggressive"
        mock_pattern1.precision_hint = 0.9

        mock_pattern2 = Mock()
        mock_pattern2.pattern = "Jane Doe"
        mock_pattern2.variants = ["J. Doe"]
        mock_pattern2.pattern_type = "structured_name_aggressive"
        mock_pattern2.precision_hint = 0.8

        patterns = [mock_pattern1, mock_pattern2]

        ac_patterns = self.builder._convert_to_ac_patterns(patterns, "person")

        assert "John Smith" in ac_patterns
        assert "J. Smith" in ac_patterns
        assert "Jane Doe" in ac_patterns
        assert "J. Doe" in ac_patterns
        # Should include case variations for high-confidence patterns
        assert "john smith" in ac_patterns
        assert "JOHN SMITH" in ac_patterns

    def test_filter_patterns_by_entity_config(self):
        """Test filtering patterns by entity configuration"""
        patterns = [
            "John Smith",
            "J. Smith",
            "John",
            "Smith",
            "Very Long Name With Many Words",
            "Short"
        ]

        # Test with high confidence
        filtered = self.builder._filter_patterns_by_entity_config(patterns, "person", 0.8)
        assert len(filtered) <= 15  # max_patterns_per_entity for person
        assert "John Smith" in filtered

        # Test with low confidence
        filtered_low = self.builder._filter_patterns_by_entity_config(patterns, "person", 0.3)
        assert len(filtered_low) <= 5  # Should be limited for low confidence
        assert all(len(p.split()) <= 2 for p in filtered_low)  # Only short patterns

    def test_create_enhanced_variants(self):
        """Test creating enhanced variants"""
        filtered_patterns = ["John Smith", "Jane Doe", "Acme Corp LLC"]
        original_variants = ["john smith", "jane doe"]

        enhanced = self.builder._create_enhanced_variants(filtered_patterns, original_variants, "en")

        assert "john smith" in enhanced
        assert "jane doe" in enhanced
        # Should include initials
        assert "J. Smith" in enhanced
        assert "J. Doe" in enhanced
        # Should include clean versions (note: the method may not preserve exact case)
        assert any("john smith" in variant.lower() for variant in enhanced)
        assert any("jane doe" in variant.lower() for variant in enhanced)

    def test_calculate_enhanced_confidence(self):
        """Test calculating enhanced confidence"""
        # Mock pattern objects
        mock_pattern = Mock()
        mock_pattern.precision_hint = 0.8
        mock_pattern.source_confidence = 0.9

        patterns = [mock_pattern]

        confidence = self.builder._calculate_enhanced_confidence(patterns, 0.8, 5)

        assert 0.1 <= confidence <= 1.0
        assert confidence > 0.5  # Should be reasonably high with good inputs