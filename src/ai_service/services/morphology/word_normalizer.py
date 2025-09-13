"""
Word normalizer for names, surnames, and other words.
Implements a clear algorithm for word classification and normalization.
"""

import re
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from ..utils import get_logger


class WordType(Enum):
    """Types of words for normalization"""
    INITIAL = "initial"  # В., О.
    NAME = "name"  # Петрик, Петруся, Вовчика
    SURNAME = "surname"  # Іванова, Порошенка, Зеленського
    PATRONYMIC = "patronymic"  # Вікторович, Олександрович
    COMPANY = "company"  # O.Torvald, Apple Inc.
    COMMON_WORD = "common_word"  # оплата, за, ремонт


@dataclass
class WordClassification:
    """Result of word classification"""
    word_type: WordType
    confidence: float
    context: Optional[str] = None


class WordNormalizer:
    """Word normalizer with clear algorithm for different word types"""
    
    def __init__(self):
        """Initialize word normalizer"""
        self.logger = get_logger(__name__)
        
        # Load dictionaries
        self.diminutives = self._load_diminutives()
        self.surname_endings = self._load_surname_endings()
        self.case_endings = self._load_case_endings()
        self.patronymic_endings = self._load_patronymic_endings()
        
        self.logger.info("Word normalizer initialized")
    
    def _load_diminutives(self) -> Dict[str, str]:
        """Load diminutives dictionary (diminutive -> full name)"""
        try:
            from ..data.dicts.diminutives_extra import EXTRA_DIMINUTIVES_UK, EXTRA_DIMINUTIVES_RU
            
            diminutives = {}
            
            # Add Ukrainian diminutives
            for full_name, diminutives_list in EXTRA_DIMINUTIVES_UK.items():
                for diminutive in diminutives_list:
                    diminutives[diminutive.lower()] = full_name.lower()
                    diminutives[diminutive] = full_name  # Keep original case
            
            # Add Russian diminutives
            for full_name, diminutives_list in EXTRA_DIMINUTIVES_RU.items():
                for diminutive in diminutives_list:
                    diminutives[diminutive.lower()] = full_name.lower()
                    diminutives[diminutive] = full_name  # Keep original case
            
            return diminutives
        except ImportError:
            self.logger.warning("Diminutives dictionary not available")
            return {}
    
    def _load_surname_endings(self) -> Dict[str, List[str]]:
        """Load surname endings dictionary"""
        return {
            "feminine": ["ова", "ева", "ина", "ская", "цкая", "ої", "ою", "ської", "ською"],
            "masculine": ["ов", "ев", "ин", "ский", "цкий", "ко", "енко", "чук", "юк", "ак", "ик", "ук", "сько", "цько"],
            "ukrainian_masculine": ["ко", "енко", "чук", "юк", "ак", "ик", "ук", "сько", "цько", "ченко", "шенко"]
        }
    
    def _load_case_endings(self) -> Dict[str, str]:
        """Load case endings dictionary (inflected -> nominative)"""
        return {
            # Masculine surnames: genitive (-а) -> nominative (-о)
            "а": "о",  # Порошенка -> Порошенко
            # Feminine surnames: genitive (-ої) -> nominative (-а)
            "ої": "а",  # Квіткової -> Квіткова
            # Feminine surnames: instrumental (-ою) -> nominative (-а)
            "ою": "а",  # Квітковою -> Квіткова
            # Feminine surnames: genitive (-ської) -> nominative (-ська)
            "ської": "ська",  # Зеленської -> Зеленська
            # Feminine surnames: instrumental (-ською) -> nominative (-ська)
            "ською": "ська",  # Зеленською -> Зеленська
            # Masculine surnames: genitive (-ого) -> nominative (-ий)
            "ого": "ий",  # Зеленського -> Зеленський
            # Masculine surnames: genitive (-ого) -> nominative (-ий)
            "ого": "ий",  # Положинського -> Положинський
            # Feminine surnames: genitive (-ої) -> nominative (-а)
            "ої": "а",  # Квіткової -> Квіткова
            # Feminine surnames: genitive (-ої) -> nominative (-а)
            "ої": "а",  # Квіткової -> Квіткова
        }
    
    def _load_patronymic_endings(self) -> Dict[str, str]:
        """Load patronymic endings dictionary"""
        return {
            "ович": "ович",  # Вікторович -> Вікторович
            "івна": "івна",  # Вікторівна -> Вікторівна
            "ович": "ович",  # Олександрович -> Олександрович
            "івна": "івна",  # Олександрівна -> Олександрівна
        }
    
    def classify_word(self, word: str) -> WordClassification:
        """Classify word by type"""
        if not word or len(word) <= 2:
            return WordClassification(WordType.COMMON_WORD, 0.0)
        
        # Check for initials (В., О.)
        if re.match(r'^[А-ЯІЇЄҐ]\.$', word):
            return WordClassification(WordType.INITIAL, 1.0)
        
        # Check for company names (O.Torvald, Apple Inc.)
        if re.match(r'^[A-Za-z]+\.[A-Za-z]+$', word) or re.match(r'^[A-Za-z]+\s+Inc\.?$', word):
            return WordClassification(WordType.COMPANY, 0.9)
        
        # Check for diminutive names
        if word.lower() in self.diminutives:
            return WordClassification(WordType.NAME, 0.9)
        
        # Check for surnames (various endings)
        if self._is_surname(word):
            return WordClassification(WordType.SURNAME, 0.8)
        
        # Check for patronymics
        if self._is_patronymic(word):
            return WordClassification(WordType.PATRONYMIC, 0.8)
        
        # Default to common word
        return WordClassification(WordType.COMMON_WORD, 0.5)
    
    def _is_surname(self, word: str) -> bool:
        """Check if word is a surname"""
        if len(word) < 3:
            return False
        
        word_lower = word.lower()
        
        # Check for feminine surname endings
        for ending in self.surname_endings["feminine"]:
            if word_lower.endswith(ending):
                return True
        
        # Check for masculine surname endings
        for ending in self.surname_endings["masculine"]:
            if word_lower.endswith(ending):
                return True
        
        # Check for Ukrainian masculine surname endings
        for ending in self.surname_endings["ukrainian_masculine"]:
            if word_lower.endswith(ending):
                return True
        
        return False
    
    def _is_patronymic(self, word: str) -> bool:
        """Check if word is a patronymic"""
        if len(word) < 5:
            return False
        
        word_lower = word.lower()
        
        # Check for patronymic endings
        for ending in self.patronymic_endings:
            if word_lower.endswith(ending):
                return True
        
        return False
    
    def normalize_name(self, word: str) -> str:
        """Normalize name (diminutive -> full form)"""
        if word.lower() in self.diminutives:
            normalized = self.diminutives[word.lower()]
            self.logger.debug(f"Normalizing name '{word}' to '{normalized}'")
            return normalized
        
        return word
    
    def normalize_surname(self, word: str, context: Optional[List[str]] = None) -> str:
        """Normalize surname (inflected form -> nominative)"""
        if len(word) < 3:
            return word
        
        word_lower = word.lower()
        
        # Check for feminine surname endings and convert to masculine
        for ending in self.surname_endings["feminine"]:
            if word_lower.endswith(ending):
                if ending in ["ова", "ева", "ина", "ская", "цкая"]:
                    # Convert feminine to masculine
                    masculine_ending = ending[:-1] + "ов" if ending.endswith("ова") else ending[:-1] + "ев"
                    normalized = word[:-len(ending)] + masculine_ending
                    self.logger.debug(f"Normalizing feminine surname '{word}' to '{normalized}'")
                    return normalized
                elif ending in ["ої", "ою", "ської", "ською"]:
                    # Convert genitive/instrumental to nominative
                    if ending == "ої":
                        normalized = word[:-2] + "а"
                    elif ending == "ою":
                        normalized = word[:-2] + "а"
                    elif ending == "ської":
                        normalized = word[:-4] + "ська"
                    elif ending == "ською":
                        normalized = word[:-4] + "ська"
                    self.logger.debug(f"Normalizing feminine surname '{word}' to '{normalized}'")
                    return normalized
        
        # Check for masculine surname endings and convert to nominative
        for ending in self.surname_endings["masculine"]:
            if word_lower.endswith(ending):
                if ending == "а" and len(word) > 4:
                    # Convert genitive to nominative for masculine surnames
                    normalized = word[:-1] + "о"
                    self.logger.debug(f"Normalizing masculine surname '{word}' to '{normalized}'")
                    return normalized
                elif ending == "ого":
                    # Convert genitive to nominative for masculine surnames
                    normalized = word[:-4] + "ий"
                    self.logger.debug(f"Normalizing masculine surname '{word}' to '{normalized}'")
                    return normalized
        
        # Check for Ukrainian masculine surname endings
        for ending in self.surname_endings["ukrainian_masculine"]:
            if word_lower.endswith(ending):
                if ending == "а" and len(word) > 4:
                    # Convert genitive to nominative for Ukrainian masculine surnames
                    normalized = word[:-1] + "о"
                    self.logger.debug(f"Normalizing Ukrainian masculine surname '{word}' to '{normalized}'")
                    return normalized
                elif ending == "ого":
                    # Convert genitive to nominative for Ukrainian masculine surnames
                    normalized = word[:-4] + "ий"
                    self.logger.debug(f"Normalizing Ukrainian masculine surname '{word}' to '{normalized}'")
                    return normalized
        
        return word
    
    def normalize_patronymic(self, word: str) -> str:
        """Normalize patronymic (inflected form -> nominative)"""
        if len(word) < 5:
            return word
        
        word_lower = word.lower()
        
        # Check for patronymic endings and convert to nominative
        for ending in self.patronymic_endings:
            if word_lower.endswith(ending):
                # Patronymics are usually already in nominative form
                return word
        
        return word
    
    def normalize_word(self, word: str, context: Optional[List[str]] = None) -> str:
        """Main normalization method"""
        if not word or len(word) <= 2:
            return word
        
        # Classify the word
        classification = self.classify_word(word)
        
        # Normalize based on classification
        if classification.word_type == WordType.INITIAL:
            return word  # Keep initials as is
        
        elif classification.word_type == WordType.NAME:
            return self.normalize_name(word)
        
        elif classification.word_type == WordType.SURNAME:
            return self.normalize_surname(word, context)
        
        elif classification.word_type == WordType.PATRONYMIC:
            return self.normalize_patronymic(word)
        
        elif classification.word_type == WordType.COMPANY:
            return word  # Keep company names as is
        
        else:  # COMMON_WORD
            return word  # Keep common words as is
    
    def normalize_text(self, text: str) -> List[str]:
        """Normalize entire text"""
        if not text:
            return []
        
        # Split text into words
        words = re.findall(r'\b\w+\b', text)
        
        # Normalize each word
        normalized_words = []
        for word in words:
            normalized = self.normalize_word(word, context=normalized_words)
            normalized_words.append(normalized)
        
        return normalized_words
