"""NER gateways for different languages and models."""

from .unified_spacy_gateway import (
    UnifiedSpacyGateway,
    SupportedLanguage,
    NEREntity,
    NERHints,
    get_global_gateway,
    create_russian_gateway,
    create_ukrainian_gateway,
    create_english_gateway
)

# Backward compatibility wrappers
def get_spacy_ru_ner():
    """Get Russian NER function for backward compatibility."""
    gateway = get_global_gateway()
    def ner_function(text):
        return gateway.get_ner_hints(text, SupportedLanguage.RUSSIAN)
    return ner_function

def get_spacy_uk_ner():
    """Get Ukrainian NER function for backward compatibility."""
    gateway = get_global_gateway()
    def ner_function(text):
        return gateway.get_ner_hints(text, SupportedLanguage.UKRAINIAN)
    return ner_function

def get_spacy_en_ner():
    """Get English NER function for backward compatibility."""
    gateway = get_global_gateway()
    def ner_function(text):
        return gateway.get_ner_hints(text, SupportedLanguage.ENGLISH)
    return ner_function

# Legacy class aliases for backward compatibility
SpacyRuNER = UnifiedSpacyGateway
SpacyUkNER = UnifiedSpacyGateway
SpacyEnNER = UnifiedSpacyGateway
NERHintsRu = NERHints
NERHintsEn = NERHints

# Legacy cache clearing functions
def clear_ner_cache():
    """Clear NER cache (unified gateway manages its own cache)."""
    pass

def clear_spacy_ru_ner():
    """Clear Russian spaCy NER cache."""
    pass

def clear_spacy_en_ner():
    """Clear English spaCy NER cache."""
    pass

__all__ = [
    "UnifiedSpacyGateway",
    "SupportedLanguage",
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
    "get_global_gateway",
    "clear_ner_cache",
    "clear_spacy_en_ner",
    "clear_spacy_ru_ner"
]
