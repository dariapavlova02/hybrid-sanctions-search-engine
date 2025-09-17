#!/usr/bin/env python3
"""
spaCy Russian NER gateway for name normalization.

Provides Named Entity Recognition using spaCy's Russian model (ru_core_news_sm)
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


class SpacyRuNER:
    """
    Russian NER using spaCy ru_core_news_sm model.
    
    Provides entity extraction for person and organization detection
    to improve role tagging accuracy.
    """
    
    def __init__(self):
        """Initialize spaCy Russian NER."""
        self.logger = get_logger(__name__)
        self._model = None
        self._model_available = False
        
        try:
            import spacy
            self._model = spacy.load("ru_core_news_sm")
            self._model_available = True
            self.logger.info("Russian spaCy NER model loaded successfully")
        except OSError as e:
            self.logger.warning(f"Russian spaCy model not found: {e}")
            self.logger.warning("Install with: python -m spacy download ru_core_news_sm")
        except Exception as e:
            self.logger.error(f"Failed to load Russian spaCy model: {e}")
    
    @property
    def is_available(self) -> bool:
        """Check if the Russian NER model is available."""
        return self._model_available
    
    def extract_entities(self, text: str) -> NERHints:
        """
        Extract person and organization entities from text.
        
        Args:
            text: Input text to analyze
            
        Returns:
            NERHints with person and organization spans
        """
        if not self._model_available or not text:
            return NERHints(person_spans=[], org_spans=[], entities=[])
        
        try:
            doc = self._model(text)
            
            person_spans = []
            org_spans = []
            entities = []
            
            for ent in doc.ents:
                entity = NEREntity(
                    text=ent.text,
                    label=ent.label_,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0  # spaCy doesn't provide confidence scores by default
                )
                entities.append(entity)
                
                if ent.label_ == "PER":
                    person_spans.append((ent.start_char, ent.end_char))
                elif ent.label_ == "ORG":
                    org_spans.append((ent.start_char, ent.end_char))
            
            self.logger.debug(f"Russian NER extracted {len(person_spans)} person spans and {len(org_spans)} org spans")
            
            return NERHints(
                person_spans=person_spans,
                org_spans=org_spans,
                entities=entities
            )
            
        except Exception as e:
            self.logger.error(f"Russian NER extraction failed: {e}")
            return NERHints(person_spans=[], org_spans=[], entities=[])
    
    def get_entity_at_position(self, text: str, start: int, end: int) -> Optional[NEREntity]:
        """
        Get entity at specific text position.
        
        Args:
            text: Input text
            start: Start character position
            end: End character position
            
        Returns:
            NEREntity if found, None otherwise
        """
        if not self._model_available:
            return None
        
        try:
            doc = self._model(text)
            
            for ent in doc.ents:
                if ent.start_char <= start < ent.end_char or ent.start_char < end <= ent.end_char:
                    return NEREntity(
                        text=ent.text,
                        label=ent.label_,
                        start=ent.start_char,
                        end=ent.end_char,
                        confidence=1.0
                    )
            
            return None
            
        except Exception as e:
            self.logger.error(f"Russian NER position lookup failed: {e}")
            return None


# Singleton instance
_spacy_ru_ner: Optional[SpacyRuNER] = None


def get_spacy_ru_ner() -> Optional[SpacyRuNER]:
    """
    Get singleton instance of Russian spaCy NER.
    
    Returns:
        SpacyRuNER instance if available, None otherwise
    """
    global _spacy_ru_ner
    
    if _spacy_ru_ner is None:
        _spacy_ru_ner = SpacyRuNER()
    
    return _spacy_ru_ner if _spacy_ru_ner.is_available else None


def clear_spacy_ru_ner():
    """Clear the singleton instance (useful for testing)."""
    global _spacy_ru_ner
    _spacy_ru_ner = None
