"""
Service for creating name and surname search patterns
Used for preparing data for Aho-Corasick algorithm in Module 3
"""

import re
import logging
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass
from datetime import datetime

from ..utils import get_logger


@dataclass
class NamePattern:
    """Name search pattern"""
    pattern: str
    pattern_type: str
    language: str
    confidence: float
    source: str
    created_at: str = None


class PatternService:
    """Service for creating name and surname search patterns"""
    
    def __init__(self):
        """Initialize pattern service"""
        self.logger = get_logger(__name__)
        
        # Basic regex patterns for different languages
        self.name_patterns = {
            'en': {
                'full_name': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
                'initials_surname': r'\b[A-Z]\. [A-Z]\. [A-Z][a-z]+\b',
                'surname_initials': r'\b[A-Z][a-z]+ [A-Z]\. [A-Z]\.\b',
                'surname_only': r'\b[A-Z][a-z]{2,}\b',
                'name_only': r'\b[A-Z][a-z]{2,}\b'
            },
            'ru': {
                'full_name': r'\b[А-ЯІЇЄ][а-яіїє]+ [А-ЯІЇЄ][а-яіїє]+\b',
                'initials_surname': r'\b[А-ЯІЇЄ]\. [А-ЯІЇЄ]\. [А-ЯІЇЄ][а-яіїє]+\b',
                'surname_initials': r'\b[А-ЯІЇЄ][а-яіїє]+ [А-ЯІЇЄ]\. [А-ЯІЇЄ]\.\b',
                'surname_only': r'\b[А-ЯІЇЄ][а-яіїє]{2,}\b',
                'name_only': r'\b[А-ЯІЇЄ][а-яіїє]{2,}\b'
            },
            'uk': {
                'full_name': r'\b[А-ЯІЇЄ][а-яіїє]+ [А-ЯІЇЄ][а-яіїє]+\b',
                'initials_surname': r'\b[А-ЯІЇЄ]\. [А-ЯІЇЄ]\. [А-ЯІЇЄ][а-яіїє]+\b',
                'surname_initials': r'\b[А-ЯІЇЄ][а-яіїє]+ [А-ЯІЇЄ]\. [А-ЯІЇЄ]\.\b',
                'surname_only': r'\b[А-ЯІЇЄ][а-яіїє]{2,}\b',
                'name_only': r'\b[А-ЯІЇЄ][а-яіїє]{2,}\b'
            },
            'fr': {
                'full_name': r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',
                'initials_surname': r'\b[A-Z]\. [A-Z]\. [A-Z][a-z]+\b',
                'surname_initials': r'\b[A-Z][a-z]+ [A-Z]\. [A-Z]\.\b',
                'surname_only': r'\b[A-Z][a-z]{2,}\b',
                'name_only': r'\b[A-Z][a-z]{2,}\b',
                'compound_name': r'\b[A-Z][a-z]+-[A-Z][a-z]+\b'  # For names like Jean-Baptiste
            },
            'es': {
                'full_name': r'\b[A-Z][a-záéíóúñÁÉÍÓÚÑ]+ [A-Z][a-záéíóúñÁÉÍÓÚÑ]+\b',
                'initials_surname': r'\b[A-Z]\. [A-Z]\. [A-Z][a-záéíóúñÁÉÍÓÚÑ]+\b',
                'surname_initials': r'\b[A-Z][a-záéíóúñÁÉÍÓÚÑ]+ [A-Z]\. [A-Z]\.\b',
                'surname_only': r'\b[A-Z][a-záéíóúñÁÉÍÓÚÑ]{2,}\b',
                'name_only': r'\b[A-Z][a-záéíóúñÁÉÍÓÚÑ]{2,}\b'
            }
        }
        
        # Dictionaries of known names and surnames for each language
        self.name_dictionaries = {
            'ru': {
                'names': {'Иван', 'Петр', 'Сергей', 'Володимир', 'Дарья', 'Анна', 'Мария', 'Олексій'},
                'surnames': {'Иванов', 'Петров', 'Сидоров', 'Порошенко', 'Акопджанів', 'Ковриков', 'Гаркушев'}
            },
            'uk': {
                'names': {'Іван', 'Петро', 'Сергій', 'Володимир', 'Дарʼя', 'Анна', 'Марія', 'Олексій'},
                'surnames': {'Іванов', 'Петренко', 'Сидоренко', 'Порошенко', 'Акопджанів', 'Ковриков', 'Гаркушев'}
            },
            'fr': {
                'names': {'Jean', 'Pierre', 'Marie', 'Sophie', 'Baptiste', 'Antoine', 'Claude'},
                'surnames': {'Martin', 'Bernard', 'Dubois', 'Thomas', 'Robert', 'Richard', 'Petit'}
            },
            'es': {
                'names': {'María', 'José', 'Carlos', 'Ana', 'Luis', 'Carmen', 'Miguel'},
                'surnames': {'García', 'Rodríguez', 'González', 'Fernández', 'López', 'Martínez', 'Sánchez'}
            }
        }
        
        # Payment context patterns
        self.payment_patterns = {
            'ru': [
                r'оплата\s+від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)',
                r'оплата\s+для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)',
                r'від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)',
                r'для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)'
            ],
            'uk': [
                r'оплата\s+від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)',
                r'оплата\s+для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)',
                r'від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)',
                r'для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)'
            ]
        }
        
        self.logger.info("PatternService initialized")
    
    def generate_patterns(
        self,
        text: str,
        language: str = 'auto'
    ) -> List[NamePattern]:
        """
        Generate patterns for searching names in text
        
        Args:
            text: Input text
            language: Text language ('auto', 'en', 'ru', 'uk')
            
        Returns:
            List of search patterns
        """
        if not text or not text.strip():
            return []
        
        # Auto-detect language if needed
        if language == 'auto':
            language = self._detect_language_simple(text)
        
        patterns = []
        
        # 1. Basic name patterns
        basic_patterns = self._extract_basic_name_patterns(text, language)
        patterns.extend(basic_patterns)
        
        # 2. Payment context patterns
        context_patterns = self._extract_payment_context_patterns(text, language)
        patterns.extend(context_patterns)
        
        # 3. Dictionary patterns
        dict_patterns = self._extract_dictionary_name_patterns(text, language)
        patterns.extend(dict_patterns)
        
        # 4. Position patterns (3-4 word)
        position_patterns = self._extract_position_patterns(text, language)
        patterns.extend(position_patterns)
        
        # 5. Deduplicate patterns
        unique_patterns = self._remove_duplicate_patterns(patterns)
        
        self.logger.info(f"Generated {len(unique_patterns)} unique patterns for language: {language}")
        return unique_patterns
    
    def _remove_duplicate_patterns(self, patterns: List[NamePattern]) -> List[NamePattern]:
        """Remove duplicate patterns"""
        seen = set()
        unique_patterns = []
        
        for pattern in patterns:
            # Create a key for uniqueness based on pattern text, type, and language
            # Preserve original case for uniqueness
            key = (pattern.pattern.lower(), pattern.pattern_type, pattern.language)
            
            if key not in seen:
                seen.add(key)
                unique_patterns.append(pattern)
        
        return unique_patterns
    
    def _extract_basic_name_patterns(self, text: str, language: str) -> List[NamePattern]:
        """Extract basic name patterns"""
        patterns = []
        
        if language not in self.name_patterns:
            return patterns
        
        for pattern_type, regex in self.name_patterns[language].items():
            matches = re.finditer(regex, text, re.IGNORECASE)
            
            for match in matches:
                matched_text = match.group()
                
                # Create pattern in original case
                pattern = NamePattern(
                    pattern=matched_text,
                    pattern_type=pattern_type,
                    language=language,
                    confidence=0.8,
                    source='regex',
                    created_at=datetime.now().isoformat()
                )
                patterns.append(pattern)
                
                # Additionally create pattern in lowercase for better coverage
                if matched_text != matched_text.lower():
                    pattern_lower = NamePattern(
                        pattern=matched_text.lower(),
                        pattern_type=pattern_type,
                        language=language,
                        confidence=0.7,
                        source='regex_lowercase',
                        created_at=datetime.now().isoformat()
                    )
                    patterns.append(pattern_lower)
                
                # And in title case
                if matched_text != matched_text.title():
                    pattern_title = NamePattern(
                        pattern=matched_text.title(),
                        pattern_type=pattern_type,
                        language=language,
                        confidence=0.7,
                        source='regex_titlecase',
                        created_at=datetime.now().isoformat()
                    )
                    patterns.append(pattern_title)
        
        return patterns
    
    def _extract_payment_context_patterns(self, text: str, language: str) -> List[NamePattern]:
        """Extract payment context patterns"""
        patterns = []
        
        if language not in self.payment_patterns:
            return patterns
        
        for regex in self.payment_patterns[language]:
            matches = re.finditer(regex, text, re.IGNORECASE)
            
            for match in matches:
                if match.group(1):  # Group with name
                    name_text = match.group(1).strip()
                    
                    # Check if extracted text looks like a name
                    if self._looks_like_name(name_text, language):
                        pattern = NamePattern(
                            pattern=name_text,
                            pattern_type='payment_context',
                            language=language,
                            confidence=0.9,
                            source='payment_context',
                            created_at=datetime.now().isoformat()
                        )
                        patterns.append(pattern)
        
        return patterns
    
    def _extract_dictionary_name_patterns(self, text: str, language: str) -> List[NamePattern]:
        """Extract patterns from name dictionaries"""
        patterns = []
        
        if language not in self.name_dictionaries:
            return patterns
        
        # Improved regex for handling apostrophes and hyphens in names
        words = re.findall(r'\b[A-ZА-ЯІЇЄ][a-zA-Zа-яіїє\'-]+\b', text)
        
        # Check names
        for word in words:
            if word in self.name_dictionaries[language]['names']:
                pattern = NamePattern(
                    pattern=word,  # Preserve original spelling
                    pattern_type='dictionary_name',
                    language=language,
                    confidence=0.95,
                    source='name_dictionary',
                    created_at=datetime.now().isoformat()
                )
                patterns.append(pattern)
            
            # Additionally check compound name parts (e.g., "O'Connor" -> "OConnor")
            if "'" in word or "-" in word:
                # Remove apostrophes and hyphens for checking
                clean_word = re.sub(r'[\'-]', '', word)
                if clean_word in self.name_dictionaries[language]['names']:
                    pattern = NamePattern(
                        pattern=clean_word,
                        pattern_type='dictionary_name_clean',
                        language=language,
                        confidence=0.9,
                        source='name_dictionary_clean',
                        created_at=datetime.now().isoformat()
                    )
                    patterns.append(pattern)
        
        # Check surnames
        for word in words:
            if word in self.name_dictionaries[language]['surnames']:
                pattern = NamePattern(
                    pattern=word,
                    pattern_type='dictionary_surname',
                    language=language,
                    confidence=0.95,
                    source='surname_dictionary',
                    created_at=datetime.now().isoformat()
                )
                patterns.append(pattern)
            
            # Clean compound surnames
            if "'" in word or "-" in word:
                clean_word = re.sub(r'[\'-]', '', word)
                if clean_word in self.name_dictionaries[language]['surnames']:
                    pattern = NamePattern(
                        pattern=clean_word,
                        pattern_type='dictionary_surname_clean',
                        language=language,
                        confidence=0.9,
                        source='surname_dictionary_clean',
                        created_at=datetime.now().isoformat()
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _extract_position_patterns(self, text: str, language: str) -> List[NamePattern]:
        """Extract patterns by position (3-4 word)"""
        patterns = []
        
        words = text.strip().split()
        
        # 3-4 word potentially could be name + surname
        for i in range(2, min(4, len(words))):
            if i < len(words):
                # Check if it looks like name + surname
                potential_name = words[i]
                if self._looks_like_name(potential_name, language):
                    pattern = NamePattern(
                        pattern=potential_name,
                        pattern_type='position_based',
                        language=language,
                        confidence=0.6,
                        source='position_analysis',
                        created_at=datetime.now().isoformat()
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _looks_like_name(self, word: str, language: str) -> bool:
        """Check if word looks like a name"""
        if not word or len(word) < 2:
            return False
        
        # Basic rules
        if language in ['ru', 'uk']:
            # Cyrillic: first letter uppercase, rest lowercase
            return bool(re.match(r'^[А-ЯІЇЄ][а-яіїє]+$', word))
        else:
            # Latin: first letter uppercase, rest lowercase
            return bool(re.match(r'^[A-Z][a-z]+$', word))
    
    def _looks_like_surname(self, word: str, language: str) -> bool:
        """Check if word looks like a surname"""
        if not word or len(word) < 3:
            return False
        
        # Surnames are usually longer than names
        if len(word) < 4:
            return False
        
        # Same rules as for names
        return self._looks_like_name(word, language)
    
    def _detect_language_simple(self, text: str) -> str:
        """Simple language detection by characters"""
        cyrillic_chars = len(re.findall(r'[а-яіїєА-ЯІЇЄ]', text))
        latin_chars = len(re.findall(r'[a-zA-Z]', text))
        
        if cyrillic_chars > 0:
            # Determine Ukrainian vs Russian by specific letters
            ukrainian_specific = len(re.findall(r'[іїєґІЇЄҐ]', text))
            if ukrainian_specific > 0:
                return 'uk'
            else:
                return 'ru'
        elif latin_chars > 0:
            return 'en'
        else:
            return 'en'  # Default to English
    
    def get_pattern_statistics(self, patterns: List[NamePattern]) -> Dict[str, Any]:
        """Get pattern statistics"""
        if not patterns:
            return {
                'total_patterns': 0,
                'by_type': {},
                'by_language': {},
                'by_source': {}
            }
        
        stats = {
            'total_patterns': len(patterns),
            'by_type': {},
            'by_language': {},
            'by_source': {}
        }
        
        # By type
        for pattern in patterns:
            pattern_type = pattern.pattern_type
            stats['by_type'][pattern_type] = stats['by_type'].get(pattern_type, 0) + 1
        
        # By language
        for pattern in patterns:
            language = pattern.language
            stats['by_language'][language] = stats['by_language'].get(language, 0) + 1
        
        # By source
        for pattern in patterns:
            source = pattern.source
            stats['by_source'][source] = stats['by_source'].get(source, 0) + 1
        
        return stats
