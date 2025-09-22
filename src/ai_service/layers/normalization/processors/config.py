"""
Configuration classes for normalization processing.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class NormalizationConfig:
    """Configuration for normalization processing."""
    remove_stop_words: bool = True
    preserve_names: bool = True
    enable_advanced_features: bool = True
    enable_morphology: bool = True
    enable_ascii_fastpath: bool = False
    enable_gender_adjustment: bool = True
    language: str = 'ru'
    use_factory: bool = True  # Flag to use factory vs legacy implementation

    # Validation flags (default OFF, for validation only)
    enable_spacy_ner: bool = False
    enable_nameparser_en: bool = False
    enable_fsm_tuned_roles: bool = False
    enable_enhanced_diminutives: bool = True
    enable_enhanced_gender_rules: bool = False
    enable_ac_tier0: bool = False
    enable_vector_fallback: bool = False
    filter_titles_suffixes: bool = True  # Filter out titles and suffixes from EN names
    preserve_feminine_suffix_uk: bool = False  # Preserve Ukrainian feminine suffixes (-ська/-цька)
    enable_spacy_uk_ner: bool = False  # Enable spaCy Ukrainian NER

    # English-specific flags
    en_use_nameparser: bool = True  # Use nameparser for English names
    enable_en_nickname_expansion: bool = True  # Expand English nicknames
    enable_spacy_en_ner: bool = False  # Enable spaCy English NER
    enable_nameparser_en: bool = False  # Enable nameparser for English name parsing
    enable_en_nicknames: bool = False  # Enable English nickname resolution
    enable_en_rules: bool = False  # Enable English-specific normalization rules

    # Russian-specific flags
    ru_yo_strategy: str = "preserve"  # Russian 'ё' policy ('preserve' or 'fold')
    enable_ru_nickname_expansion: bool = True  # Expand Russian nicknames
    enable_spacy_ru_ner: bool = False  # Enable spaCy Russian NER

    # Unicode normalization flags
    normalize_homoglyphs: bool = False  # Normalize Cyrillic/Latin homoglyphs to dominant alphabet
    yo_strategy: Literal["fold", "preserve"] = "fold"  # Russian 'ё' strategy ('fold' or 'preserve')

    # Caching flags
    enable_cache: bool = True  # Enable caching
    debug_tracing: bool = False  # Enable debug tracing with cache info

    def validate(self) -> None:
        """Validate configuration settings."""
        if self.yo_strategy not in ("fold", "preserve"):
            raise ValueError(f"Invalid yo_strategy: {self.yo_strategy}")

        if self.language not in ("ru", "uk", "en", "auto"):
            raise ValueError(f"Invalid language: {self.language}")

    def copy(self, **overrides) -> "NormalizationConfig":
        """Create a copy with optional overrides."""
        import copy
        new_config = copy.deepcopy(self)
        for key, value in overrides.items():
            if hasattr(new_config, key):
                setattr(new_config, key, value)
            else:
                raise ValueError(f"Unknown configuration key: {key}")
        return new_config

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            key: getattr(self, key)
            for key in self.__dataclass_fields__.keys()
        }