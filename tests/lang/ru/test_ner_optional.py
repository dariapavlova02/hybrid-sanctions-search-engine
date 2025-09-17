#!/usr/bin/env python3
"""
Tests for optional Russian spaCy NER functionality.

Tests that the Russian NER adapter correctly extracts person and organization
entities and integrates with the normalization process.
"""

import pytest
from unittest.mock import Mock, patch
from src.ai_service.layers.normalization.ner_gateways.spacy_ru import SpacyRuNER, NERHints, NEREntity


class TestRussianNER:
    """Test Russian spaCy NER functionality."""
    
    @pytest.fixture
    def mock_spacy_ru_ner(self):
        """Create a mock Russian NER instance."""
        ner = SpacyRuNER()
        ner._model_available = True
        return ner
    
    def test_ner_initialization_without_model(self):
        """Test NER initialization when model is not available."""
        with patch('spacy.load') as mock_load:
            mock_load.side_effect = OSError("Model not found")
            ner = SpacyRuNER()
            
            assert not ner.is_available
            assert ner._model is None
    
    def test_ner_initialization_with_model(self):
        """Test NER initialization when model is available."""
        mock_model = Mock()
        with patch('spacy.load', return_value=mock_model):
            ner = SpacyRuNER()
            
            assert ner.is_available
            assert ner._model == mock_model
    
    def test_extract_entities_person(self, mock_spacy_ru_ner):
        """Test extraction of person entities."""
        # Mock spaCy document with person entity
        mock_doc = Mock()
        mock_ent = Mock()
        mock_ent.text = "Иван Петров"
        mock_ent.label_ = "PER"
        mock_ent.start_char = 0
        mock_ent.end_char = 11
        mock_doc.ents = [mock_ent]
        
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.return_value = mock_doc
        
        hints = mock_spacy_ru_ner.extract_entities("Иван Петров работает в компании")
        
        assert len(hints.person_spans) == 1
        assert hints.person_spans[0] == (0, 11)
        assert len(hints.org_spans) == 0
        assert len(hints.entities) == 1
        assert hints.entities[0].text == "Иван Петров"
        assert hints.entities[0].label == "PER"
    
    def test_extract_entities_organization(self, mock_spacy_ru_ner):
        """Test extraction of organization entities."""
        # Mock spaCy document with organization entity
        mock_doc = Mock()
        mock_ent = Mock()
        mock_ent.text = "ООО Рога и копыта"
        mock_ent.label_ = "ORG"
        mock_ent.start_char = 0
        mock_ent.end_char = 16
        mock_doc.ents = [mock_ent]
        
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.return_value = mock_doc
        
        hints = mock_spacy_ru_ner.extract_entities("ООО Рога и копыта - это компания")
        
        assert len(hints.person_spans) == 0
        assert len(hints.org_spans) == 1
        assert hints.org_spans[0] == (0, 16)
        assert len(hints.entities) == 1
        assert hints.entities[0].text == "ООО Рога и копыта"
        assert hints.entities[0].label == "ORG"
    
    def test_extract_entities_mixed(self, mock_spacy_ru_ner):
        """Test extraction of mixed person and organization entities."""
        # Mock spaCy document with both person and organization entities
        mock_doc = Mock()
        mock_person = Mock()
        mock_person.text = "Иван Петров"
        mock_person.label_ = "PER"
        mock_person.start_char = 0
        mock_person.end_char = 11
        
        mock_org = Mock()
        mock_org.text = "ООО Рога и копыта"
        mock_org.label_ = "ORG"
        mock_org.start_char = 20
        mock_org.end_char = 36
        
        mock_doc.ents = [mock_person, mock_org]
        
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.return_value = mock_doc
        
        hints = mock_spacy_ru_ner.extract_entities("Иван Петров работает в ООО Рога и копыта")
        
        assert len(hints.person_spans) == 1
        assert len(hints.org_spans) == 1
        assert len(hints.entities) == 2
        assert hints.person_spans[0] == (0, 11)
        assert hints.org_spans[0] == (20, 36)
    
    def test_extract_entities_no_entities(self, mock_spacy_ru_ner):
        """Test extraction when no entities are found."""
        # Mock spaCy document with no entities
        mock_doc = Mock()
        mock_doc.ents = []
        
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.return_value = mock_doc
        
        hints = mock_spacy_ru_ner.extract_entities("Обычный текст без именованных сущностей")
        
        assert len(hints.person_spans) == 0
        assert len(hints.org_spans) == 0
        assert len(hints.entities) == 0
    
    def test_extract_entities_empty_text(self, mock_spacy_ru_ner):
        """Test extraction with empty text."""
        hints = mock_spacy_ru_ner.extract_entities("")
        
        assert len(hints.person_spans) == 0
        assert len(hints.org_spans) == 0
        assert len(hints.entities) == 0
    
    def test_extract_entities_none_text(self, mock_spacy_ru_ner):
        """Test extraction with None text."""
        hints = mock_spacy_ru_ner.extract_entities(None)
        
        assert len(hints.person_spans) == 0
        assert len(hints.org_spans) == 0
        assert len(hints.entities) == 0
    
    def test_extract_entities_model_not_available(self):
        """Test extraction when model is not available."""
        ner = SpacyRuNER()
        ner._model_available = False
        
        hints = ner.extract_entities("Иван Петров")
        
        assert len(hints.person_spans) == 0
        assert len(hints.org_spans) == 0
        assert len(hints.entities) == 0
    
    def test_extract_entities_exception_handling(self, mock_spacy_ru_ner):
        """Test that exceptions during extraction are handled gracefully."""
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.side_effect = Exception("spaCy error")
        
        hints = mock_spacy_ru_ner.extract_entities("Иван Петров")
        
        assert len(hints.person_spans) == 0
        assert len(hints.org_spans) == 0
        assert len(hints.entities) == 0
    
    def test_get_entity_at_position(self, mock_spacy_ru_ner):
        """Test getting entity at specific position."""
        # Mock spaCy document with entity
        mock_doc = Mock()
        mock_ent = Mock()
        mock_ent.text = "Иван Петров"
        mock_ent.label_ = "PER"
        mock_ent.start_char = 0
        mock_ent.end_char = 11
        mock_doc.ents = [mock_ent]
        
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.return_value = mock_doc
        
        entity = mock_spacy_ru_ner.get_entity_at_position("Иван Петров работает", 0, 11)
        
        assert entity is not None
        assert entity.text == "Иван Петров"
        assert entity.label == "PER"
        assert entity.start == 0
        assert entity.end == 11
    
    def test_get_entity_at_position_no_entity(self, mock_spacy_ru_ner):
        """Test getting entity at position where no entity exists."""
        # Mock spaCy document with no entities
        mock_doc = Mock()
        mock_doc.ents = []
        
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.return_value = mock_doc
        
        entity = mock_spacy_ru_ner.get_entity_at_position("Обычный текст", 0, 5)
        
        assert entity is None
    
    def test_get_entity_at_position_model_not_available(self):
        """Test getting entity when model is not available."""
        ner = SpacyRuNER()
        ner._model_available = False
        
        entity = ner.get_entity_at_position("Иван Петров", 0, 5)
        
        assert entity is None
    
    def test_get_entity_at_position_exception_handling(self, mock_spacy_ru_ner):
        """Test that exceptions during position lookup are handled gracefully."""
        mock_spacy_ru_ner._model = Mock()
        mock_spacy_ru_ner._model.side_effect = Exception("spaCy error")
        
        entity = mock_spacy_ru_ner.get_entity_at_position("Иван Петров", 0, 5)
        
        assert entity is None
    
    def test_ner_entity_dataclass(self):
        """Test NEREntity dataclass."""
        entity = NEREntity(
            text="Иван Петров",
            label="PER",
            start=0,
            end=11,
            confidence=0.95
        )
        
        assert entity.text == "Иван Петров"
        assert entity.label == "PER"
        assert entity.start == 0
        assert entity.end == 11
        assert entity.confidence == 0.95
    
    def test_ner_hints_dataclass(self):
        """Test NERHints dataclass."""
        hints = NERHints(
            person_spans=[(0, 11)],
            org_spans=[(20, 36)],
            entities=[
                NEREntity("Иван Петров", "PER", 0, 11),
                NEREntity("ООО Рога и копыта", "ORG", 20, 36)
            ]
        )
        
        assert len(hints.person_spans) == 1
        assert len(hints.org_spans) == 1
        assert len(hints.entities) == 2
        assert hints.person_spans[0] == (0, 11)
        assert hints.org_spans[0] == (20, 36)
    
    def test_singleton_pattern(self):
        """Test that NER follows singleton pattern."""
        from src.ai_service.layers.normalization.ner_gateways.spacy_ru import get_spacy_ru_ner, clear_spacy_ru_ner
        
        # Clear any existing instance
        clear_spacy_ru_ner()
        
        # Get first instance
        ner1 = get_spacy_ru_ner()
        
        # Get second instance (should be the same)
        ner2 = get_spacy_ru_ner()
        
        # Should be the same instance
        assert ner1 is ner2
        
        # Clear and get new instance
        clear_spacy_ru_ner()
        ner3 = get_spacy_ru_ner()
        
        # Should be different from previous instances
        assert ner3 is not ner1
        assert ner3 is not ner2
