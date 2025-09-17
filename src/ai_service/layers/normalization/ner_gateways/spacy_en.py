"""
spaCy English NER gateway for enhanced role tagging.

This module provides a gateway to spaCy's English NER model for
improving person and organization detection in English text.
"""

import logging
from typing import List, Tuple, Optional
from dataclasses import dataclass

from ....utils.logging_config import get_logger

logger = get_logger(__name__)

# Lazy loading of spaCy model to avoid import overhead
_nlp_en = None
SPACY_EN_AVAILABLE = None

def _load_spacy_en():
    """Lazy load spaCy English model."""
    global _nlp_en, SPACY_EN_AVAILABLE
    
    if SPACY_EN_AVAILABLE is not None:
        return _nlp_en, SPACY_EN_AVAILABLE
    
    try:
        import spacy
        # Load the English model
        # This model needs to be downloaded separately: python -m spacy download en_core_web_sm
        _nlp_en = spacy.load("en_core_web_sm")
        SPACY_EN_AVAILABLE = True
    except ImportError:
        logger.warning("spaCy not installed. English NER will be unavailable.")
        _nlp_en = None
        SPACY_EN_AVAILABLE = False
    except Exception as e:
        logger.warning(f"Could not load spaCy 'en_core_web_sm' model: {e}. English NER will be unavailable.")
        _nlp_en = None
        SPACY_EN_AVAILABLE = False
    
    return _nlp_en, SPACY_EN_AVAILABLE


@dataclass
class NERHints:
    """Container for NER extracted entities."""
    person_spans: List[Tuple[int, int]]  # List of (start_char, end_char) for persons
    org_spans: List[Tuple[int, int]]     # List of (start_char, end_char) for organizations


class SpacyEnNER:
    """
    NER gateway for spaCy's English model.
    Provides methods to extract person and organization entities.
    """

    def __init__(self):
        nlp, available = _load_spacy_en()
        if not available:
            raise RuntimeError("spaCy English NER model is not available.")
        self.nlp = nlp
        logger.info("SpacyEnNER initialized.")

    def extract_entities(self, text: str) -> NERHints:
        """
        Extracts person and organization entities from the given text.

        Args:
            text: The input text.

        Returns:
            NERHints object containing lists of (start_char, end_char) tuples for persons and organizations.
        """
        if not self.nlp:
            return NERHints(person_spans=[], org_spans=[])

        doc = self.nlp(text)
        person_spans = []
        org_spans = []

        for ent in doc.ents:
            if ent.label_ == "PERSON":  # Person
                person_spans.append((ent.start_char, ent.end_char))
            elif ent.label_ == "ORG":  # Organization
                org_spans.append((ent.start_char, ent.end_char))

        return NERHints(person_spans=person_spans, org_spans=org_spans)


_spacy_en_ner: Optional[SpacyEnNER] = None


def get_spacy_en_ner() -> Optional[SpacyEnNER]:
    """
    Returns a singleton instance of SpacyEnNER.
    """
    global _spacy_en_ner
    if _spacy_en_ner is None:
        _, available = _load_spacy_en()
        if available:
            try:
                _spacy_en_ner = SpacyEnNER()
            except RuntimeError as e:
                logger.error(f"Failed to initialize SpacyEnNER: {e}")
                _spacy_en_ner = None
    return _spacy_en_ner


def clear_spacy_en_ner() -> None:
    """Clear the singleton instance (useful for testing)."""
    global _spacy_en_ner
    _spacy_en_ner = None
