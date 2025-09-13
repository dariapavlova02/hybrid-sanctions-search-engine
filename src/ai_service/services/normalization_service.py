"""
Text normalization service using SpaCy and NLTK
for text preparation for search
"""

import re
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Union, Any
from dataclasses import dataclass

import spacy
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer, SnowballStemmer
from nltk.tokenize import word_tokenize

from ..config import SERVICE_CONFIG
from ..exceptions import NormalizationError, LanguageDetectionError
from ..utils import get_logger
from .language_detection_service import LanguageDetectionService
from .unicode_service import UnicodeService

# Configure logging
logger = get_logger(__name__)

# Load SpaCy models
try:
    nlp_en = spacy.load("en_core_web_sm")
    nlp_ru = spacy.load("ru_core_news_sm")
    nlp_uk = spacy.load("uk_core_news_sm")
    SPACY_AVAILABLE = True
except OSError:
    logger.warning("SpaCy models not available, falling back to NLTK")
    SPACY_AVAILABLE = False

# Load NLTK data
try:
    import nltk
    import os
    
    # Set NLTK data path if not already set
    if 'NLTK_DATA' not in os.environ:
        # Check if we're running in Docker or locally
        if os.path.exists('/app'):
            os.environ['NLTK_DATA'] = '/app/nltk_data'
        else:
            # Local development - use current directory
            os.environ['NLTK_DATA'] = str(Path.cwd() / 'nltk_data')
    
    NLTK_AVAILABLE = True
except Exception as e:
    logger.warning(f"NLTK not available: {e}")
    NLTK_AVAILABLE = False

# Initialize stemmers
if NLTK_AVAILABLE:
    porter_stemmer = PorterStemmer()
    snowball_ru = SnowballStemmer('russian')
    # Ukrainian is not supported by NLTK SnowballStemmer, use Russian as fallback
    try:
        snowball_uk = SnowballStemmer('ukrainian')
    except ValueError:
        logger.warning("Ukrainian stemmer not available, using Russian as fallback")
        snowball_uk = snowball_ru  # Fallback to Russian stemmer
else:
    porter_stemmer = None
    snowball_ru = None
    snowball_uk = None

@dataclass
class NormalizationResult:
    """Normalization result"""
    normalized: str
    tokens: List[str]
    language: str
    confidence: float
    original_length: int
    normalized_length: int
    token_count: int
    processing_time: float
    success: bool
    errors: List[str] = None


class NormalizationService:
    """Service for text normalization before search"""
    
    def __init__(self):
        """
        Initialize normalization service
        
        Raises:
            NormalizationError: If service initialization fails
        """
        self.logger = get_logger(__name__)
        
        try:
            self.language_service = LanguageDetectionService()
            self.unicode_service = UnicodeService()
            
            # Language-specific settings
            self.language_configs = {
                'en': {
                    'stop_words': set(stopwords.words('english')) if NLTK_AVAILABLE else set(),
                    'stemmer': porter_stemmer if NLTK_AVAILABLE else None,
                    'spacy_model': nlp_en if SPACY_AVAILABLE else None
                },
                'ru': {
                    'stop_words': set(stopwords.words('russian')) if NLTK_AVAILABLE else set(),
                    'stemmer': snowball_ru if NLTK_AVAILABLE else None,
                    'spacy_model': nlp_ru if SPACY_AVAILABLE else None
                },
                'uk': {
                    'stop_words': set(stopwords.words('russian')) if NLTK_AVAILABLE else set(),  # Use Russian as fallback
                    'stemmer': snowball_uk if NLTK_AVAILABLE else None,
                    'spacy_model': nlp_uk if SPACY_AVAILABLE else None
                }
                # TODO: add ukrainian stop words
            }
            
            self.logger.info("NormalizationService initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize NormalizationService: {e}")
            raise NormalizationError(f"Service initialization failed: {str(e)}")
    
    def detect_language(self, text: str) -> str:
        """
        Automatic language detection for text
        
        Args:
            text: Text to detect language for
            
        Returns:
            Detected language code
            
        Raises:
            LanguageDetectionError: If language detection fails
        """
        try:
            language_result = self.language_service.detect_language(text)
            return language_result.get('language', SERVICE_CONFIG.default_language)
        except Exception as e:
            self.logger.warning(f"Language detection failed: {e}, using default language")
            raise LanguageDetectionError(f"Language detection failed: {str(e)}")
    
    def basic_cleanup(self, text: str, preserve_names: bool = True) -> str:
        """Basic text cleanup with name preservation"""
        if not text:
            return ""
        
        # Convert to string if needed
        text = str(text)
        
        # For names, preserve dots, hyphens, and apostrophes
        # Dots for initials (I.I. Ivanov)
        # Hyphens for compound names (Jean-Pierre)
        # Apostrophes for names (O'Connor, D'Artagnan)
        if preserve_names:
            # Preserve dots, hyphens, apostrophes
            text = re.sub(r'[^\w\s\.\-\']', ' ', text)
        else:
            # Remove all punctuation
            text = re.sub(r'[^\w\s]', ' ', text)
        
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def normalize_unicode(self, text: str) -> str:
        """Unicode character normalization"""
        if not text:
            return ""
        
        # Basic Unicode normalization
        text = text.replace('ё', 'е')  # Russian yo -> e
        text = text.replace('і', 'и')  # Ukrainian i -> i
        text = text.replace('ї', 'и')  # Ukrainian yi -> i
        text = text.replace('є', 'е')  # Ukrainian ye -> e
        text = text.replace('ґ', 'г')  # Ukrainian g -> g
        
        return text
    
    def tokenize_text(self, text: str, language: str = 'en') -> List[str]:
        """Tokenization using SpaCy"""
        if not text:
            return []
        
        try:
            if SPACY_AVAILABLE and language in self.language_configs:
                nlp = self.language_configs[language]['spacy_model']
                if nlp:
                    doc = nlp(text)
                    tokens = [token.text for token in doc if not token.is_space]
                    return tokens
        except Exception as e:
            self.logger.warning(f"SpaCy tokenization failed: {e}")
        
        # Fallback to NLTK
        if NLTK_AVAILABLE:
            try:
                tokens = word_tokenize(text)
                return [token for token in tokens if token.strip()]
            except Exception as e:
                self.logger.warning(f"NLTK tokenization failed: {e}")
        
        # Simple fallback
        return text.split()
    
    def remove_stop_words(self, tokens: List[str], language: str = 'en') -> List[str]:
        """Remove stop words"""
        if not tokens or language not in self.language_configs:
            return tokens
        
        stop_words = self.language_configs[language]['stop_words']
        if not stop_words:
            return tokens
        
        return [token for token in tokens if token.lower() not in stop_words]
    
    def apply_stemming(self, tokens: List[str], language: str = 'en') -> List[str]:
        """Apply stemming"""
        if not tokens or language not in self.language_configs:
            return tokens
        
        stemmer = self.language_configs[language]['stemmer']
        if not stemmer:
            return tokens
        
        try:
            return [stemmer.stem(token) for token in tokens]
        except Exception as e:
            self.logger.warning(f"Stemming failed: {e}")
            return tokens
    
    def apply_lemmatization(self, tokens: List[str], language: str = 'en') -> List[str]:
        """Lemmatization using SpaCy"""
        if not tokens or not SPACY_AVAILABLE:
            return tokens
        
        try:
            if language in self.language_configs:
                nlp = self.language_configs[language]['spacy_model']
                if nlp:
                    text = ' '.join(tokens)
                    doc = nlp(text)
                    lemmas = [token.lemma_ for token in doc if not token.is_space]
                    return lemmas
        except Exception as e:
            self.logger.warning(f"Lemmatization failed: {e}")
        
        return tokens
    
    async def normalize(
        self,
        text: str,
        language: str = 'auto',
        remove_stop_words: bool = False,  # For names, don't remove stop words
        apply_stemming: bool = False,     # For names, don't apply stemming
        apply_lemmatization: bool = True, # For names, apply lemmatization
        clean_unicode: bool = True,
        preserve_names: bool = True,      # Preserve names and surnames
        enable_advanced_features: bool = False  # Enable advanced features
    ) -> NormalizationResult:
        """
        Text normalization for name and surname search
        
        Args:
            text: Input text
            language: Text language ('en', 'ru', 'uk', 'auto')
            remove_stop_words: Remove stop words (False for names)
            apply_stemming: Apply stemming (False for names)
            apply_lemmatization: Apply lemmatization (True for names)
            clean_unicode: Clean Unicode characters
            preserve_names: Preserve names and surnames
            enable_advanced_features: Enable advanced features
            
        Returns:
            Dict with normalized text and tokens
        """
        import time
        start_time = time.time()
        
        try:
            # Automatic language detection
            if language == 'auto':
                language = self.detect_language(text)
            
            # Basic cleanup with name preservation
            if preserve_names:
                cleaned_text = self.basic_cleanup(text, preserve_names=True)
            else:
                cleaned_text = self.basic_cleanup(text, preserve_names=False)
            
            # Unicode normalization
            if clean_unicode:
                cleaned_text = self.normalize_unicode(cleaned_text)
            
            # Tokenization
            tokens = self.tokenize_text(cleaned_text, language)
            
            # For names, DON'T remove stop words and DON'T apply stemming
            # This can lead to loss of important information
            
            # Lemmatization (useful for names)
            if apply_lemmatization:
                tokens = self.apply_lemmatization(tokens, language)
            
            # Advanced features (if enabled)
            if enable_advanced_features:
                if language == 'uk':
                    tokens = self._get_ukrainian_forms(tokens)
            
            # Final normalization
            normalized_text = ' '.join(tokens)
            
            processing_time = time.time() - start_time
            
            result = NormalizationResult(
                normalized=normalized_text,
                tokens=tokens,
                language=language,
                confidence=1.0,
                original_length=len(text),
                normalized_length=len(normalized_text),
                token_count=len(tokens),
                processing_time=processing_time,
                success=True
            )
            
            self.logger.info(f"Text normalized successfully: {len(text)} -> {len(normalized_text)} chars, {len(tokens)} tokens")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            self.logger.error(f"Text normalization failed: {e}")
            
            result = NormalizationResult(
                normalized=text,
                tokens=[text],
                language=language,
                confidence=0.0,
                original_length=len(text),
                normalized_length=len(text),
                token_count=1,
                processing_time=processing_time,
                success=False,
                errors=[str(e)]
            )
            return result
    
    async def normalize_batch(
        self,
        texts: List[str],
        language: str = 'auto',
        **kwargs
    ) -> List[NormalizationResult]:
        """Normalize a list of texts"""
        results = []
        
        for text in texts:
            try:
                result = await self.normalize(text, language, **kwargs)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to normalize text: {e}")
                # Create error result
                error_result = NormalizationResult(
                    normalized=text,
                    tokens=[text],
                    language=language,
                    confidence=0.0,
                    original_length=len(text),
                    normalized_length=len(text),
                    token_count=1,
                    processing_time=0.0,
                    success=False,
                    errors=[str(e)]
                )
                results.append(error_result)
        
        return results
    
    def _get_ukrainian_forms(self, tokens: List[str]) -> List[str]:
        """Get extended forms through Ukrainian analyzer"""
        try:
            # Import Ukrainian analyzer only if needed
            from .ukrainian_morphology import UkrainianMorphology
            
            analyzer = UkrainianMorphology()
            extended_tokens = []
            
            # Analyze each word as a potential name
            for token in tokens:
                if len(token) > 2 and token[0].isupper():
                    # This might be a name
                    try:
                        forms = analyzer.get_word_forms(token)
                        if forms:
                            extended_tokens.extend(forms)
                        else:
                            extended_tokens.append(token)
                    except Exception as e:
                        self.logger.debug(f"Failed to analyze Ukrainian word {token}: {e}")
                        extended_tokens.append(token)
                else:
                    extended_tokens.append(token)
            
            return list(set(extended_tokens))  # Remove duplicates
            
        except ImportError:
            self.logger.debug("Ukrainian morphology not available")
            return tokens
        except Exception as e:
            self.logger.warning(f"Ukrainian form generation failed: {e}")
            return tokens
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages"""
        return list(self.language_configs.keys())
    
    def is_language_supported(self, language: str) -> bool:
        """Check if language is supported"""
        return language in self.language_configs