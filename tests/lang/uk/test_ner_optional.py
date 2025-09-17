#!/usr/bin/env python3
"""
Tests for optional Ukrainian NER functionality.

Tests the enable_spacy_uk_ner flag functionality to ensure that
spaCy Ukrainian NER is properly integrated and improves role tagging.
"""

import pytest
from src.ai_service.layers.normalization.ner_gateways import get_spacy_uk_ner, SpacyUkNER, NERHints


class TestUkrainianNER:
    """Test Ukrainian NER functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.ner = get_spacy_uk_ner()

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_ner_model_availability(self):
        """Test that NER model is available when expected."""
        assert self.ner.is_available(), "spaCy Ukrainian NER should be available"
        assert self.ner._model is not None, "spaCy model should be loaded"

    def test_ner_model_unavailable_graceful_handling(self):
        """Test graceful handling when NER model is unavailable."""
        # This test should pass regardless of model availability
        hints = self.ner.extract_entities("Тестовий текст")
        assert isinstance(hints, NERHints), "Should return NERHints even when model unavailable"
        assert hints.person_spans == [], "Should return empty person spans when model unavailable"
        assert hints.org_spans == [], "Should return empty org spans when model unavailable"
        assert hints.entities == [], "Should return empty entities when model unavailable"

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_person_entity_extraction(self):
        """Test extraction of person entities from Ukrainian text."""
        test_cases = [
            ("Анна Ковальська", [(0, 4), (5, 15)]),  # "Анна" and "Ковальська"
            ("Олексій Петренко", [(0, 8), (9, 18)]),  # "Олексій" and "Петренко"
            ("Марія Іванівна Сидоренко", [(0, 6), (7, 15), (16, 25)]),  # Full name
        ]

        for text, expected_spans in test_cases:
            hints = self.ner.extract_entities(text)
            assert isinstance(hints, NERHints), f"Should return NERHints for: {text}"
            
            # Check that we have person spans
            assert len(hints.person_spans) > 0, f"Should extract person spans from: {text}"
            
            # Check that person entities are properly tagged
            person_entities = [e for e in hints.entities if e.label == "PER"]
            assert len(person_entities) > 0, f"Should have person entities for: {text}"

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_organization_entity_extraction(self):
        """Test extraction of organization entities from Ukrainian text."""
        test_cases = [
            "ТОВ ПРИВАТБАНК",
            "АТ КБ ПРИВАТБАНК", 
            "ПАТ Укртелеком",
            "ТОВ Альфа-Банк",
        ]

        for text in test_cases:
            hints = self.ner.extract_entities(text)
            assert isinstance(hints, NERHints), f"Should return NERHints for: {text}"
            
            # Check that we have org spans
            assert len(hints.org_spans) > 0, f"Should extract org spans from: {text}"
            
            # Check that org entities are properly tagged
            org_entities = [e for e in hints.entities if e.label == "ORG"]
            assert len(org_entities) > 0, f"Should have org entities for: {text}"

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_mixed_person_org_extraction(self):
        """Test extraction of both person and organization entities."""
        text = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"
        hints = self.ner.extract_entities(text)
        
        assert isinstance(hints, NERHints), "Should return NERHints"
        assert len(hints.person_spans) > 0, "Should extract person spans"
        assert len(hints.org_spans) > 0, "Should extract org spans"
        
        # Check entity types
        person_entities = [e for e in hints.entities if e.label == "PER"]
        org_entities = [e for e in hints.entities if e.label == "ORG"]
        
        assert len(person_entities) > 0, "Should have person entities"
        assert len(org_entities) > 0, "Should have org entities"

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_entity_at_position(self):
        """Test getting entity at specific character position."""
        text = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"
        hints = self.ner.extract_entities(text)
        
        # Test position within person entity
        person_entity = self.ner.get_entity_at_position(text, 0)  # Start of "Анна"
        if person_entity:
            assert person_entity.label == "PER", "Should be person entity"
            assert "Анна" in person_entity.text, "Should contain 'Анна'"
        
        # Test position within org entity
        org_entity = self.ner.get_entity_at_position(text, 30)  # Within "ПРИВАТБАНК"
        if org_entity:
            assert org_entity.label == "ORG", "Should be org entity"
            assert "ПРИВАТБАНК" in org_entity.text, "Should contain 'ПРИВАТБАНК'"

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_is_person_entity(self):
        """Test checking if text span is person entity."""
        text = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"
        
        # Test person span
        is_person = self.ner.is_person_entity(text, 0, 4)  # "Анна"
        assert is_person, "Should identify 'Анна' as person entity"
        
        # Test org span
        is_person_org = self.ner.is_person_entity(text, 25, 35)  # "ПРИВАТБАНК"
        assert not is_person_org, "Should not identify 'ПРИВАТБАНК' as person entity"

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_is_org_entity(self):
        """Test checking if text span is organization entity."""
        text = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"
        
        # Test org span
        is_org = self.ner.is_org_entity(text, 25, 35)  # "ПРИВАТБАНК"
        assert is_org, "Should identify 'ПРИВАТБАНК' as org entity"
        
        # Test person span
        is_org_person = self.ner.is_org_entity(text, 0, 4)  # "Анна"
        assert not is_org_person, "Should not identify 'Анна' as org entity"

    def test_empty_text_handling(self):
        """Test handling of empty text."""
        hints = self.ner.extract_entities("")
        assert isinstance(hints, NERHints), "Should return NERHints for empty text"
        assert hints.person_spans == [], "Should have empty person spans"
        assert hints.org_spans == [], "Should have empty org spans"
        assert hints.entities == [], "Should have empty entities"

    def test_whitespace_text_handling(self):
        """Test handling of whitespace-only text."""
        hints = self.ner.extract_entities("   \n\t   ")
        assert isinstance(hints, NERHints), "Should return NERHints for whitespace text"
        assert hints.person_spans == [], "Should have empty person spans"
        assert hints.org_spans == [], "Should have empty org spans"
        assert hints.entities == [], "Should have empty entities"

    def test_statistics(self):
        """Test NER statistics."""
        stats = self.ner.get_statistics()
        assert isinstance(stats, dict), "Should return statistics dict"
        assert "model_available" in stats, "Should have model_available in stats"
        assert "model_name" in stats, "Should have model_name in stats"
        assert "spacy_available" in stats, "Should have spacy_available in stats"
        
        if self.ner.is_available():
            assert stats["model_available"] is True, "Should report model as available"
            assert stats["model_name"] == "uk_core_news_sm", "Should report correct model name"
        else:
            assert stats["model_available"] is False, "Should report model as unavailable"

    @pytest.mark.skipif(not get_spacy_uk_ner().is_available(), reason="spaCy Ukrainian model not available")
    def test_confidence_scores(self):
        """Test that entities have confidence scores."""
        text = "Анна Ковальська працює в ТОВ ПРИВАТБАНК"
        hints = self.ner.extract_entities(text)
        
        for entity in hints.entities:
            assert hasattr(entity, 'confidence'), "Entity should have confidence attribute"
            assert isinstance(entity.confidence, (int, float)), "Confidence should be numeric"
            assert 0 <= entity.confidence <= 1, "Confidence should be between 0 and 1"

    def test_ner_hints_structure(self):
        """Test NERHints data structure."""
        hints = NERHints(
            person_spans=[(0, 4), (5, 15)],
            org_spans=[(20, 30)],
            entities=[]
        )
        
        assert isinstance(hints.person_spans, list), "person_spans should be list"
        assert isinstance(hints.org_spans, list), "org_spans should be list"
        assert isinstance(hints.entities, list), "entities should be list"
        
        # Check span format
        for span in hints.person_spans + hints.org_spans:
            assert isinstance(span, tuple), "Spans should be tuples"
            assert len(span) == 2, "Spans should have 2 elements (start, end)"
            assert isinstance(span[0], int), "Start should be int"
            assert isinstance(span[1], int), "End should be int"
            assert span[0] <= span[1], "Start should be <= end"
