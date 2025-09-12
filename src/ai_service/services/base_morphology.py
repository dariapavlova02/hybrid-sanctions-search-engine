"""
Base class for morphological analyzers
Eliminates code duplication between UkrainianMorphologyAnalyzer and RussianMorphologyAnalyzer
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass

from ..utils import get_logger


@dataclass
class MorphologicalAnalysis:
    """Result of morphological analysis"""
    lemma: str
    part_of_speech: str
    case: Optional[str] = None
    number: Optional[str] = None
    gender: Optional[str] = None
    person: Optional[str] = None
    tense: Optional[str] = None
    mood: Optional[str] = None
    voice: Optional[str] = None
    aspect: Optional[str] = None
    confidence: float = 1.0
    source: str = "base"


class BaseMorphologyAnalyzer(ABC):
    """Base class for morphological analyzers"""
    
    def __init__(self, language: str):
        """
        Initialize base analyzer
        
        Args:
            language: Language code (e.g., 'uk', 'ru')
        """
        self.language = language
        self.logger = get_logger(__name__)
        
        # Initialize language-specific resources
        self._init_language_resources()
        
        self.logger.info(f"Base morphology analyzer initialized for {language}")
    
    @abstractmethod
    def _init_language_resources(self):
        """Initialize language-specific resources (must be implemented by subclasses)"""
        pass
    
    @abstractmethod
    def analyze_word(self, word: str) -> List[MorphologicalAnalysis]:
        """
        Analyze single word morphologically
        
        Args:
            word: Word to analyze
            
        Returns:
            List of morphological analysis results
        """
        pass
    
    @abstractmethod
    def analyze_text(self, text: str) -> Dict[str, List[MorphologicalAnalysis]]:
        """
        Analyze text morphologically
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict mapping words to their morphological analyses
        """
        pass
    
    @abstractmethod
    def get_lemma(self, word: str) -> str:
        """
        Get base form (lemma) of word
        
        Args:
            word: Word to lemmatize
            
        Returns:
            Base form of the word
        """
        pass
    
    @abstractmethod
    def get_pos_tags(self, word: str) -> List[str]:
        """
        Get part-of-speech tags for word
        
        Args:
            word: Word to analyze
            
        Returns:
            List of part-of-speech tags
        """
        pass
    
    def get_word_forms(self, lemma: str, pos: str = None) -> List[str]:
        """
        Get all possible word forms for given lemma
        
        Args:
            lemma: Base form of word
            pos: Part of speech (optional)
            
        Returns:
            List of possible word forms
        """
        # Default implementation - can be overridden by subclasses
        return [lemma]
    
    def is_known_word(self, word: str) -> bool:
        """
        Check if word is known to analyzer
        
        Args:
            word: Word to check
            
        Returns:
            True if word is known, False otherwise
        """
        try:
            analyses = self.analyze_word(word)
            if not analyses:
                return False
            
            # Check if any analysis has high confidence (indicating it's a known word)
            for analysis in analyses:
                if analysis.confidence > 0.5:  # High confidence indicates known word
                    return True
            
            # If all analyses have low confidence, word is not well known
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking word '{word}': {e}")
            return False
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """
        Get analyzer statistics
        
        Returns:
            Dict with analyzer statistics
        """
        return {
            'language': self.language,
            'analyzer_type': self.__class__.__name__,
            'initialized': True
        }
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info(f"Cleaning up {self.__class__.__name__}")
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.cleanup()
