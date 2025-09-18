#!/usr/bin/env python3
"""
Unified spaCy NER gateway for all languages.

Provides Named Entity Recognition using spaCy models for Russian, Ukrainian, and English
to extract person and organization entities from text. This replaces the separate
language-specific gateways with a single parametrized implementation.
"""

import logging
from typing import Dict, List, Optional, Set, Tuple, Any
from dataclasses import dataclass
from enum import Enum

from ....utils.logging_config import get_logger

logger = get_logger(__name__)


class SupportedLanguage(Enum):
    """Supported languages for NER processing."""
    RUSSIAN = "ru"
    UKRAINIAN = "uk"
    ENGLISH = "en"


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
    persons: Set[str]
    organizations: Set[str]
    locations: Set[str]
    confidence: float


class UnifiedSpacyGateway:
    """
    Unified spaCy NER gateway supporting multiple languages.

    This class provides a single interface for NER processing across
    Russian, Ukrainian, and English using appropriate spaCy models.
    """

    # Model configurations for each language
    MODEL_CONFIG = {
        SupportedLanguage.RUSSIAN: {
            "model_name": "ru_core_news_sm",
            "download_cmd": "python -m spacy download ru_core_news_sm"
        },
        SupportedLanguage.UKRAINIAN: {
            "model_name": "uk_core_news_sm",
            "download_cmd": "python -m spacy download uk_core_news_sm"
        },
        SupportedLanguage.ENGLISH: {
            "model_name": "en_core_web_sm",
            "download_cmd": "python -m spacy download en_core_web_sm"
        }
    }

    def __init__(self):
        """Initialize the unified spaCy gateway."""
        self.logger = get_logger(__name__)
        self._models: Dict[SupportedLanguage, Any] = {}  # Loaded models cache
        self._availability: Dict[SupportedLanguage, bool] = {}  # Model availability cache

    def _load_spacy_model(self, language: SupportedLanguage) -> Tuple[Any, bool]:
        """
        Lazy load spaCy model for the specified language.

        Args:
            language: Target language for NER processing

        Returns:
            Tuple of (model, is_available)
        """
        # Check cache first
        if language in self._availability:
            return self._models.get(language), self._availability[language]

        try:
            import spacy
            model_name = self.MODEL_CONFIG[language]["model_name"]

            # Try to load the model
            nlp = spacy.load(model_name)

            # Cache successful load
            self._models[language] = nlp
            self._availability[language] = True

            self.logger.info(f"spaCy model {model_name} loaded successfully")
            return nlp, True

        except (ImportError, OSError) as e:
            # Cache failure
            self._models[language] = None
            self._availability[language] = False

            download_cmd = self.MODEL_CONFIG[language]["download_cmd"]
            self.logger.warning(
                f"spaCy {language.value} model not available. "
                f"Install with: {download_cmd}. Error: {e}"
            )
            return None, False

    def is_available(self, language: SupportedLanguage) -> bool:
        """
        Check if spaCy model is available for the specified language.

        Args:
            language: Language to check

        Returns:
            True if model is available, False otherwise
        """
        _, available = self._load_spacy_model(language)
        return available

    def extract_entities(self, text: str, language: SupportedLanguage) -> List[NEREntity]:
        """
        Extract named entities from text using spaCy NER.

        Args:
            text: Text to process
            language: Language of the text

        Returns:
            List of extracted entities
        """
        nlp, available = self._load_spacy_model(language)

        if not available:
            self.logger.warning(f"spaCy model not available for {language.value}")
            return []

        if not text or not text.strip():
            return []

        try:
            doc = nlp(text)
            entities = []

            for ent in doc.ents:
                # Map spaCy labels to our standard labels
                label = self._normalize_label(ent.label_)

                entity = NEREntity(
                    text=ent.text,
                    label=label,
                    start=ent.start_char,
                    end=ent.end_char,
                    confidence=1.0  # spaCy doesn't provide confidence scores by default
                )
                entities.append(entity)

            return entities

        except Exception as e:
            self.logger.error(f"NER processing failed for {language.value}: {e}")
            return []

    def get_ner_hints(self, text: str, language: SupportedLanguage) -> NERHints:
        """
        Get NER hints for role tagging.

        Args:
            text: Text to analyze
            language: Language of the text

        Returns:
            NER hints with persons, organizations, and locations
        """
        entities = self.extract_entities(text, language)

        persons = set()
        organizations = set()
        locations = set()

        for entity in entities:
            if entity.label == "PERSON":
                persons.add(entity.text.lower())
            elif entity.label == "ORG":
                organizations.add(entity.text.lower())
            elif entity.label == "LOC":
                locations.add(entity.text.lower())

        # Calculate overall confidence based on entity count
        confidence = min(len(entities) / 10.0, 1.0) if entities else 0.0

        return NERHints(
            persons=persons,
            organizations=organizations,
            locations=locations,
            confidence=confidence
        )

    @staticmethod
    def _normalize_label(spacy_label: str) -> str:
        """
        Normalize spaCy entity labels to standard format.

        Args:
            spacy_label: Original spaCy label

        Returns:
            Normalized label
        """
        # Map various spaCy labels to our standard labels
        label_mapping = {
            # Person labels
            "PER": "PERSON", "PERSON": "PERSON",

            # Organization labels
            "ORG": "ORG", "ORGANIZATION": "ORG",

            # Location labels
            "LOC": "LOC", "LOCATION": "LOC", "GPE": "LOC",

            # Other common labels
            "MISC": "MISC", "DATE": "DATE", "TIME": "TIME"
        }

        return label_mapping.get(spacy_label.upper(), spacy_label.upper())

    def get_supported_languages(self) -> List[SupportedLanguage]:
        """Get list of supported languages."""
        return list(SupportedLanguage)

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about loaded models.

        Returns:
            Dictionary with model information
        """
        info = {}
        for language in SupportedLanguage:
            model, available = self._load_spacy_model(language)
            info[language.value] = {
                "available": available,
                "model_name": self.MODEL_CONFIG[language]["model_name"],
                "loaded": language in self._models
            }
        return info


# Convenience functions for backward compatibility
def create_russian_gateway() -> UnifiedSpacyGateway:
    """Create gateway configured for Russian processing."""
    return UnifiedSpacyGateway()

def create_ukrainian_gateway() -> UnifiedSpacyGateway:
    """Create gateway configured for Ukrainian processing."""
    return UnifiedSpacyGateway()

def create_english_gateway() -> UnifiedSpacyGateway:
    """Create gateway configured for English processing."""
    return UnifiedSpacyGateway()


# Global instance for shared use
_global_gateway = None

def get_global_gateway() -> UnifiedSpacyGateway:
    """Get shared global spaCy gateway instance."""
    global _global_gateway
    if _global_gateway is None:
        _global_gateway = UnifiedSpacyGateway()
    return _global_gateway