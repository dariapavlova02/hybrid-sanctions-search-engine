"""NER gateways for different languages and models."""

from .spacy_uk import SpacyUkNER, NEREntity, NERHints, get_spacy_uk_ner, clear_ner_cache
from .spacy_en import SpacyEnNER, NERHints as NERHintsEn, get_spacy_en_ner, clear_spacy_en_ner
from .spacy_ru import SpacyRuNER, NERHints as NERHintsRu, get_spacy_ru_ner, clear_spacy_ru_ner

__all__ = [
    "SpacyUkNER",
    "SpacyEnNER",
    "SpacyRuNER",
    "NEREntity", 
    "NERHints",
    "NERHintsEn",
    "NERHintsRu",
    "get_spacy_uk_ner",
    "get_spacy_en_ner",
    "get_spacy_ru_ner",
    "clear_ner_cache",
    "clear_spacy_en_ner",
    "clear_spacy_ru_ner"
]
