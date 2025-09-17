#!/usr/bin/env python3
"""
spaCy Ukrainian NER gateway for name normalization.

Provides Named Entity Recognition using spaCy's Ukrainian model (uk_core_news_sm)
to extract person and organization entities from text.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

from ....utils.logging_config import get_logger

logger = logging.getLogger(__name__)


@dataclass
class NEREntity:
    """Named Entity Recognition result."""
    text: str
    label: str  # PER, ORG, etc.
    start: int
    end: int
    confidence: float = 1.0


@dataclass
class NERHints:
    """NER hints for role tagging."""
    person_spans: List[Tuple[int, int]]  # (start, end) tuples
    org_spans: List[Tuple[int, int]]    # (start, end) tuples
    entities: List[NEREntity]           # All entities


class SpacyUkNER:
    """
    Ukrainian NER using spaCy uk_core_news_sm model.
    
    Provides entity extraction for person and organization detection
    to improve role tagging accuracy.
    """
    
    def __init__(self):
        """Initialize spaCy Ukrainian NER."""
        self.logger = get_logger(__name__)
        self._model = None
        self._model_available = False
        
        try:
            self._initialize_model()
        except Exception as e:
            self.logger.warning(f"Failed to initialize spaCy Ukrainian model: {e}")
            self._model_available = False
    
    def _initialize_model(self):
        """Initialize the spaCy Ukrainian model."""
        try:
            import spacy
            
            # Try to load the Ukrainian model
            self._model = spacy.load("uk_core_news_sm")
            self._model_available = True
            self.logger.info("spaCy Ukrainian model (uk_core_news_sm) loaded successfully")
            
        except OSError as e:
            self.logger.warning(f"spaCy Ukrainian model not found: {e}")
            self.logger.info("To install: python -m spacy download uk_core_news_sm")
            self._model_available = False
        except ImportError:
            self.logger.warning("spaCy not available. Install with: pip install spacy")
            self._model_available = False
        except Exception as e:
            self.logger.error(f"Unexpected error loading spaCy Ukrainian model: {e}")
            self._model_available = False
    
    def is_available(self) -> bool:
        """Check if the NER model is available."""
        return self._model_available and self._model is not None
    
    def extract_entities(self, text: str) -> NERHints:
        """
        Extract named entities from Ukrainian text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            NERHints with person and organization spans
        """
        if not self.is_available():
            self.logger.debug("spaCy Ukrainian NER not available, returning empty hints")
            return NERHints(person_spans=[], org_spans=[], entities=[])
        
        if not text or not text.strip():
            return NERHints(person_spans=[], org_spans=[], entities=[])
        
        try:
            # Process text with spaCy
            doc = self._model(text)
            
            person_spans = []
            org_spans = []
            entities = []
            
            for ent in doc.ents:
                # Map spaCy labels to our labels
                if ent.label_ in ["PERSON", "PER"]:
                    person_spans.append((ent.start_char, ent.end_char))
                    entities.append(NEREntity(
                        text=ent.text,
                        label="PER",
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=getattr(ent, 'confidence', 1.0)
                    ))
                elif ent.label_ in ["ORG", "ORGANIZATION"]:
                    org_spans.append((ent.start_char, ent.end_char))
                    entities.append(NEREntity(
                        text=ent.text,
                        label="ORG",
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=getattr(ent, 'confidence', 1.0)
                    ))
            
            self.logger.debug(f"Extracted {len(person_spans)} person spans and {len(org_spans)} org spans")
            
            return NERHints(
                person_spans=person_spans,
                org_spans=org_spans,
                entities=entities
            )
            
        except Exception as e:
            self.logger.error(f"Error extracting entities: {e}")
            return NERHints(person_spans=[], org_spans=[], entities=[])
    
    def get_entity_at_position(self, text: str, position: int) -> Optional[NEREntity]:
        """
        Get entity at a specific character position.
        
        Args:
            text: Input text
            position: Character position
            
        Returns:
            NEREntity at position or None
        """
        hints = self.extract_entities(text)
        
        for entity in hints.entities:
            if entity.start <= position < entity.end:
                return entity
        
        return None
    
    def is_person_entity(self, text: str, start: int, end: int) -> bool:
        """
        Check if a text span is identified as a person entity.
        
        Args:
            text: Full text
            start: Start character position
            end: End character position
            
        Returns:
            True if the span is identified as a person
        """
        hints = self.extract_entities(text)
        
        for entity in hints.entities:
            if entity.label == "PER" and entity.start <= start and entity.end >= end:
                return True
        
        return False
    
    def is_org_entity(self, text: str, start: int, end: int) -> bool:
        """
        Check if a text span is identified as an organization entity.
        
        Args:
            text: Full text
            start: Start character position
            end: End character position
            
        Returns:
            True if the span is identified as an organization
        """
        hints = self.extract_entities(text)
        
        for entity in hints.entities:
            if entity.label == "ORG" and entity.start <= start and entity.end >= end:
                return True
        
        return False
    
    def get_statistics(self) -> Dict[str, any]:
        """Get NER statistics."""
        return {
            "model_available": self.is_available(),
            "model_name": "uk_core_news_sm" if self.is_available() else None,
            "spacy_available": self._model is not None
        }


# Global instance for caching
_spacy_uk_ner: Optional[SpacyUkNER] = None


def get_spacy_uk_ner() -> SpacyUkNER:
    """
    Get global spaCy Ukrainian NER instance.
    
    Returns:
        SpacyUkNER instance
    """
    global _spacy_uk_ner
    
    if _spacy_uk_ner is None:
        _spacy_uk_ner = SpacyUkNER()
    
    return _spacy_uk_ner


def clear_ner_cache():
    """Clear the NER cache. Useful for testing."""
    global _spacy_uk_ner
    _spacy_uk_ner = None
