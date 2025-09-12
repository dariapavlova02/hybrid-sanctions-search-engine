"""
Dictionaries for AI Service
"""

from .english_names import ENGLISH_NAMES
from .ukrainian_names import UKRAINIAN_NAMES
from .russian_names import RUSSIAN_NAMES
from .asian_names import NAMES as ASIAN_NAMES
from .arabic_names import NAMES as ARABIC_NAMES
from .indian_names import INDIAN_NAMES
from .european_names import NAMES as EUROPEAN_NAMES
from .scandinavian_names import SCANDINAVIAN_NAMES
from .lemmatization_blacklist import LEMMATIZATION_BLACKLIST
from .phonetic_patterns import PHONETIC_PATTERNS
from .regional_patterns import REGIONAL_PATTERNS

__all__ = [
    'ENGLISH_NAMES',
    'UKRAINIAN_NAMES', 
    'RUSSIAN_NAMES',
    'ASIAN_NAMES',
    'ARABIC_NAMES',
    'INDIAN_NAMES',
    'EUROPEAN_NAMES',
    'SCANDINAVIAN_NAMES',
    'LEMMATIZATION_BLACKLIST',
    'PHONETIC_PATTERNS',
    'REGIONAL_PATTERNS'
]
