"""
Language detection service with fallback mechanisms
"""

import re
import logging
from typing import Dict, List, Optional, Union, Any
from datetime import datetime
import time

from ..config import SERVICE_CONFIG
from ..exceptions import LanguageDetectionError
from ..utils import get_logger

# Import name dictionaries for verification
try:
    from ...data.dicts import english_names, russian_names, ukrainian_names, asian_names, arabic_names, indian_names, european_names, scandinavian_names
    DICTIONARIES_AVAILABLE = True
except ImportError:
    DICTIONARIES_AVAILABLE = False


class LanguageDetectionService:
    """Service for language detection with focus on speed and accuracy"""
    
    def __init__(self):
        """Initialize language detection service"""
        self.logger = get_logger(__name__)
        
        # Import name dictionaries for verification
        if DICTIONARIES_AVAILABLE:
            self.english_names = set(english_names.NAMES)
            self.russian_names = set(russian_names.NAMES)
            self.ukrainian_names = set(ukrainian_names.NAMES)
            self.asian_names = set(asian_names.ASIAN_NAMES)
            self.arabic_names = set(arabic_names.ARABIC_NAMES)
            self.indian_names = set(indian_names.INDIAN_NAMES)
            self.european_names = set(european_names.EUROPEAN_NAMES)
            self.scandinavian_names = set(scandinavian_names.SCANDINAVIAN_NAMES)
        else:
            self.english_names = set()
            self.russian_names = set()
            self.ukrainian_names = set()
            self.asian_names = set()
            self.arabic_names = set()
            self.indian_names = set()
            self.european_names = set()
            self.scandinavian_names = set()
        
        # Supported languages
        self.supported_languages = {
            'en': 'English',
            'ru': 'Russian',
            'uk': 'Ukrainian'
        }
        
        # Language mapping (extended)
        self.language_mapping = {
            # English and similar
            'en': 'en',
            'en-US': 'en',
            'en-GB': 'en',
            
            # Russian and similar
            'ru': 'ru',
            'be': 'ru',  # Belarusian -> Russian
            'kk': 'ru',  # Kazakh -> Russian
            'ky': 'ru',  # Kyrgyz -> Russian
            
            # Ukrainian
            'uk': 'uk',
            
            # Other Slavic languages -> Russian
            'bg': 'ru',  # Bulgarian
            'sr': 'ru',  # Serbian
            'hr': 'ru',  # Croatian
            'sl': 'ru',  # Slovenian
            'pl': 'ru'   # Polish
        }
        
        # Patterns for fast detection
        self.language_patterns = {
            'en': [
                r'\b[aeiou]{2,}',  # Long vowels
                r'\b(the|and|or|but|in|on|at|to|for|of|with|by)\b',
                r'\b(is|are|was|were|be|been|being|have|has|had|do|does|did)\b'
            ],
            'ru': [
                r'\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто)\b',
                r'\b(был|была|были|быть|есть|нет|это|тот|эта|эти)\b',
                r'[аеёиоуыэюя]{2,}',  # Long vowels
                r'[йцкнгшщзхфвпрлджчсмтб]{3,}'  # Long consonants
            ],
            'uk': [
                r'\b(і|в|на|з|по|за|від|до|з|у|о|а|але|або|якщо|коли|де|як|що|хто)\b',
                r'\b(був|була|були|бути|є|немає|це|той|ця|ці)\b',
                r'[аеєиіїоущюя]{2,}',  # Long vowels
                r'[йцкнгшщзхфвпрлджчсмтб]{3,}'  # Long consonants
            ]
        }
        
        # Detection statistics
        self.detection_stats = {
            'total_detections': 0,
            'successful_detections': 0,
            'fallback_detections': 0,
            'average_confidence': 0.0,
            'method_usage': {
                'dictionary': 0,
                'cyrillic_priority': 0,
                'pattern': 0,
                'langdetect': 0,
                'fallback': 0
            },
            'recent_scores': []  # Last 1000 confidence scores
        }
        
        self.logger.info("LanguageDetectionService initialized")
    
    def detect_language(
        self,
        text: str,
        use_fallback: bool = True
    ) -> Dict[str, Any]:
        """
        Language detection with fallback mechanisms
        
        Args:
            text: Input text
            use_fallback: Use fallback methods
            
        Returns:
            Dict with detection result
        """
        if not text or not text.strip():
            return self._create_detection_result('en', 0.0, 'empty_text')
        
        # 0. PRIORITY check names in dictionaries
        dictionary_result = self._detect_language_by_dictionaries(text)
        if dictionary_result['confidence'] >= 0.9:
            self._update_stats(dictionary_result['confidence'], 'dictionary')
            return dictionary_result
        
        # 1. SECONDARY check for Cyrillic characters with ABSOLUTE PRIORITY
        cyrillic_result = self._detect_cyrillic_priority(text)
        if cyrillic_result['confidence'] >= 0.8:  # High priority for Cyrillic
            self._update_stats(cyrillic_result['confidence'], 'cyrillic_priority')
            return cyrillic_result
        
        # 2. Fast detection by patterns
        pattern_result = self._fast_pattern_detection(text)
        if pattern_result['confidence'] >= 0.6:
            self._update_stats(pattern_result['confidence'], 'pattern')
            return pattern_result
        
        # 3. Main detection (langdetect)
        try:
            from langdetect import detect, LangDetectException
            detected_lang = detect(text)
            
            if detected_lang in self.language_mapping:
                mapped_lang = self.language_mapping[detected_lang]
                confidence = 0.7  # Medium confidence for langdetect
                
                result = self._create_detection_result(mapped_lang, confidence, 'langdetect')
                self._update_stats(confidence, 'langdetect')
                return result
                
        except (ImportError, LangDetectException) as e:
            self.logger.debug(f"LangDetect failed: {e}")
            # Don't return result with method 'langdetect' on error
        
        # 4. Fallback detection
        if use_fallback:
            fallback_result = self._fallback_detection(text)
            self._update_stats(fallback_result['confidence'], 'fallback')
            return fallback_result
        
        # 5. Default
        default_result = self._create_detection_result('en', 0.5, 'default')
        self._update_stats(0.5, 'default')
        return default_result
    
    def _fast_pattern_detection(self, text: str) -> Dict[str, Any]:
        """Fast detection by patterns"""
        scores = {}
        
        for lang, patterns in self.language_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                score += matches
            
            # Normalize score
            scores[lang] = score / len(patterns) if patterns else 0
        
        # Find language with highest score
        if scores:
            best_lang = max(scores.keys(), key=lambda k: scores[k])
            best_score = scores[best_lang]
            
            if best_score > 0.3:  # Threshold for fast detection
                confidence = min(0.8, 0.5 + best_score * 0.3)
                return self._create_detection_result(best_lang, confidence, 'pattern')
        
        return self._create_detection_result('en', 0.3, 'pattern_low_confidence')
    
    def _detect_language_by_dictionaries(self, text: str) -> Dict[str, Any]:
        """Language detection based on name dictionaries"""
        # Clean text from punctuation and split into words
        words = re.findall(r'\b[А-Яа-яІіЇїЄєҐґA-Za-z]+\b', text)
        
        if not words:
            return self._create_detection_result('en', 0.0, 'dictionary_no_words')
        
        # Count matches in each dictionary
        english_matches = sum(1 for word in words if word.lower() in self.english_names)
        russian_matches = sum(1 for word in words if word.lower() in self.russian_names)
        ukrainian_matches = sum(1 for word in words if word.lower() in self.ukrainian_names)
        
        # If matches found in Ukrainian dictionary
        if ukrainian_matches > 0:
            confidence = 0.95  # High confidence for Ukrainian names
            if ukrainian_matches > russian_matches and ukrainian_matches > english_matches:
                return self._create_detection_result('uk', confidence, 'dictionary_ukrainian')
        
        # If matches found in Russian dictionary
        if russian_matches > 0:
            confidence = 0.9  # High confidence for Russian names
            if russian_matches > english_matches:
                return self._create_detection_result('ru', confidence, 'dictionary_russian')
        
        # If matches found in English dictionary
        if english_matches > 0:
            confidence = 0.85  # High confidence for English names
            return self._create_detection_result('en', confidence, 'dictionary_english')
        
        return self._create_detection_result('en', 0.0, 'dictionary_no_matches')
    
    def _detect_cyrillic_priority(self, text: str) -> Dict[str, Any]:
        """ABSOLUTE PRIORITY of Cyrillic characters"""
        # Count Ukrainian unique characters
        ukrainian_chars = len(re.findall(r'[іїєґІЇЄҐ]', text))
        
        # Count Russian specific characters
        russian_chars = len(re.findall(r'[ёъыэЁЪЫЭ]', text))
        
        # Count total Cyrillic characters
        cyrillic_chars = len(re.findall(r'[а-яёА-ЯЁ]', text))
        
        # ABSOLUTE PRIORITY: even ONE Ukrainian character = Ukrainian language
        if ukrainian_chars > 0:
            confidence = min(0.98, 0.8 + ukrainian_chars * 0.1)  # Very high confidence
            return self._create_detection_result('uk', confidence, 'cyrillic_ukrainian')
        
        # If there are Russian specific characters
        if russian_chars > 0:
            confidence = min(0.95, 0.8 + russian_chars * 0.1)
            return self._create_detection_result('ru', confidence, 'cyrillic_russian')
        
        # If there is Cyrillic in general (without specific characters)
        if cyrillic_chars > 0:
            # Additional check for Ukrainian words
            uk_patterns = len(re.findall(r'\b(і|в|на|з|по|за|від|до|у|о|а|але|або|якщо|коли|де|як|що|хто|це|той|ця|ці|був|була|були|бути|є|немає)\b', text, re.IGNORECASE))
            ru_patterns = len(re.findall(r'\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто|это|тот|эта|эти|был|была|были|быть|есть|нет)\b', text, re.IGNORECASE))
            
            if uk_patterns > ru_patterns:
                confidence = min(0.9, 0.7 + uk_patterns * 0.05)
                return self._create_detection_result('uk', confidence, 'cyrillic_patterns_ukrainian')
            else:
                confidence = min(0.9, 0.7 + ru_patterns * 0.05)
                return self._create_detection_result('ru', confidence, 'cyrillic_patterns_russian')
        
        # No Cyrillic characters - low confidence
        return self._create_detection_result('en', 0.2, 'cyrillic_none')
    
    def _fallback_detection(self, text: str) -> Dict[str, Any]:
        """Fallback detection based on character statistics with improved logic"""
        # Count Cyrillic characters
        cyrillic_count = len(re.findall(r'[а-яёіїє]', text, re.IGNORECASE))
        latin_count = len(re.findall(r'[a-z]', text, re.IGNORECASE))
        total_chars = len(re.findall(r'[а-яёіїєa-z]', text, re.IGNORECASE))
        
        if total_chars == 0:
            return self._create_detection_result('en', 0.1, 'fallback_no_letters')
        
        # Improved logic: even a small number of Cyrillic characters outweighs Latin
        if cyrillic_count > 0:
            # Additional check for Ukrainian
            if cyrillic_count > latin_count:
                uk_specific = len(re.findall(r'[іїєґІЇЄҐ]', text))
                ru_specific = len(re.findall(r'[ёъыэЁЪЫЭ]', text))
                
                if uk_specific > 0:
                    # Check for typical Ukrainian/Russian patterns
                    uk_patterns = len(re.findall(r'\b(і|в|на|з|по|за|від|до|у|о|а|але|або|якщо|коли|де|як|що|хто)\b', text, re.IGNORECASE))
                    ru_patterns = len(re.findall(r'\b(и|в|на|с|по|за|от|до|из|у|о|а|но|или|если|когда|где|как|что|кто)\b', text, re.IGNORECASE))
                    
                    if uk_patterns >= ru_patterns:
                        confidence = min(0.8, 0.6 + cyrillic_count / total_chars)
                        return self._create_detection_result('uk', confidence, 'fallback_cyrillic_ukrainian')
                    else:
                        confidence = min(0.8, 0.6 + cyrillic_count / total_chars)
                        return self._create_detection_result('ru', confidence, 'fallback_cyrillic_russian')
            
            # If there are Cyrillic characters, determine as Russian (default Cyrillic)
            if cyrillic_count > 0:
                confidence = min(0.8, 0.6 + cyrillic_count / total_chars)
                return self._create_detection_result('ru', confidence, 'fallback_cyrillic_default')
            
            # Only if there are no Cyrillic characters at all, determine as English
            confidence = min(0.7, 0.5 + latin_count / total_chars)
            return self._create_detection_result('en', confidence, 'fallback_latin')
        
        return self._create_detection_result('en', 0.5, 'fallback_default')
    
    def _create_detection_result(
        self,
        language: str,
        confidence: float,
        method: str
    ) -> Dict[str, Any]:
        """Create detection result"""
        result = {
            'language': language,
            'confidence': confidence,
            'method': method,
            'timestamp': None  # Can add timestamp
        }
        
        # Add additional fields
        result['supported'] = language in self.supported_languages
        result['language_name'] = self.supported_languages.get(language, language)
        
        # Update statistics
        self.detection_stats['total_detections'] += 1
        self.detection_stats['recent_scores'].append(confidence)
        
        # Keep only last 1000 scores
        if len(self.detection_stats['recent_scores']) > 1000:
            self.detection_stats['recent_scores'] = self.detection_stats['recent_scores'][-1000:]
        
        return result
    
    def _update_stats(self, confidence: float, method: str):
        """Update detection statistics"""
        self.detection_stats['successful_detections'] += 1
        self.detection_stats['average_confidence'] = (
            (self.detection_stats['average_confidence'] * (self.detection_stats['successful_detections'] - 1) + confidence) /
            self.detection_stats['successful_detections']
        )
        
        if method in self.detection_stats['method_usage']:
            self.detection_stats['method_usage'][method] += 1
    
    def detect_languages_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Batch language detection"""
        results = []
        for text in texts:
            result = self.detect_language(text)
            results.append(result)
        return results
    
    def detect_batch(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Alias for detect_languages_batch"""
        return self.detect_languages_batch(texts)
    
    def get_detection_stats(self) -> Dict[str, Any]:
        """Get detection statistics"""
        stats = self.detection_stats.copy()
        
        # Calculate additional metrics
        if stats['recent_scores']:
            stats['recent_average_confidence'] = sum(stats['recent_scores']) / len(stats['recent_scores'])
            stats['recent_min_confidence'] = min(stats['recent_scores'])
            stats['recent_max_confidence'] = max(stats['recent_scores'])
        else:
            stats['recent_average_confidence'] = 0.0
            stats['recent_min_confidence'] = 0.0
            stats['recent_max_confidence'] = 0.0
        
        stats['success_rate'] = (
            stats['successful_detections'] / stats['total_detections']
            if stats['total_detections'] > 0 else 0.0
        )
        
        stats['method_distribution'] = {
            method: count / max(stats['total_detections'], 1)
            for method, count in stats['method_usage'].items()
        }
        
        # Add aliases for backward compatibility
        stats['avg_confidence'] = stats['average_confidence']
        stats['confidence_scores'] = stats['recent_scores']
        stats['fallback_usage'] = stats['fallback_detections']
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset detection statistics"""
        self.detection_stats = {
            'total_detections': 0,
            'successful_detections': 0,
            'fallback_detections': 0,
            'average_confidence': 0.0,
            'method_usage': {
                'dictionary': 0,
                'cyrillic_priority': 0,
                'pattern': 0,
                'langdetect': 0,
                'fallback': 0
            },
            'recent_scores': []
        }
        self.logger.info("Detection statistics reset")
    
    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported"""
        return language in self.supported_languages
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.supported_languages.keys())
    
    def add_language_mapping(self, source_lang: str, target_lang: str) -> None:
        """Add new language mapping"""
        # Only add mapping if target language is supported
        if target_lang in self.supported_languages:
            self.language_mapping[source_lang] = target_lang
