"""
Ukrainian morphological analyzer
Inherits from BaseMorphologyAnalyzer
"""

import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

from .base_morphology import BaseMorphologyAnalyzer, MorphologicalAnalysis
from ..utils import get_logger


@dataclass
class UkrainianMorphologyResult:
    """Result of Ukrainian morphological analysis"""
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
    source: str = "ukrainian"


class UkrainianMorphologyAnalyzer(BaseMorphologyAnalyzer):
    """Ukrainian morphological analyzer"""
    
    def __init__(self):
        """Initialize Ukrainian analyzer"""
        super().__init__('uk')
        self.logger = get_logger(__name__)
        
        # Initialize pymorphy3 analyzer
        self.morph_analyzer = self._initialize_pymorphy3()
        
        # Load dictionaries
        self.special_names = self._load_special_names()
        
        # Load lemmatization blacklist
        self.lemmatization_blacklist = self._load_lemmatization_blacklist()
        
        # Initialize additional resources
        self._initialize_additional_resources()
        
        self.logger.info("Ukrainian Morphology Analyzer initialized")
    
    def _init_language_resources(self):
        """Initialize language-specific resources"""
        # This method is called by parent constructor
        pass
    
    def _initialize_pymorphy3(self):
        """Initialize pymorphy3 analyzer"""
        try:
            import pymorphy3
            return pymorphy3.MorphAnalyzer()
        except ImportError:
            self.logger.warning("pymorphy3 not available, using fallback methods")
            return None
        except Exception as e:
            self.logger.error(f"Error initializing pymorphy3: {e}")
            return None
    
    def _load_special_names(self) -> Dict[str, Any]:
        """Load special names dictionary"""
        try:
            from ..data.dicts.ukrainian_names import UKRAINIAN_NAMES
            return UKRAINIAN_NAMES
        except ImportError:
            self.logger.warning("Ukrainian names dictionary not available")
            return {}
    
    def _load_lemmatization_blacklist(self) -> Set[str]:
        """Load lemmatization blacklist"""
        try:
            from ..data.dicts.lemmatization_blacklist import LEMMATIZATION_BLACKLIST
            return set(LEMMATIZATION_BLACKLIST)
        except ImportError:
            self.logger.warning("Lemmatization blacklist not available")
            return set()
    
    def _initialize_additional_resources(self):
        """Initialize additional resources (can be overridden)"""
        # Ukrainian-specific initialization
        self.ukrainian_specific_patterns = {
            'patronymic': r'\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+ович\b|\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+івна\b',
            'diminutive': r'\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+енька\b|\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+ечка\b',
            'formal': r'\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+ич\b|\b[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ]+ична\b'
        }
        
        # Ukrainian-specific transliteration patterns
        self.ukrainian_transliteration = {
            'і': 'i', 'ї': 'yi', 'є': 'ye', 'ґ': 'g',
            'І': 'I', 'Ї': 'Yi', 'Є': 'Ye', 'Ґ': 'G'
        }
    
    def analyze_word(self, word: str) -> List[MorphologicalAnalysis]:
        """
        Analyze single word morphologically
        
        Args:
            word: Word to analyze
            
        Returns:
            List of morphological analysis results
        """
        if not word or not word.strip():
            return []
        
        word = word.strip()
        if len(word) < 2:
            return [MorphologicalAnalysis(
                lemma=word,
                part_of_speech='UNKN',
                confidence=0.1,
                source='ukrainian_short'
            )]
        
        try:
            # Analysis through pymorphy3
            morph_analysis = self._analyze_with_pymorphy(word)
            
            # Convert to MorphologicalAnalysis objects
            results = []
            for analysis in morph_analysis:
                results.append(MorphologicalAnalysis(
                    lemma=analysis.get('lemma', word),
                    part_of_speech=analysis.get('pos', 'UNKN'),
                    case=analysis.get('case'),
                    number=analysis.get('number'),
                    gender=analysis.get('gender'),
                    person=analysis.get('person'),
                    tense=analysis.get('tense'),
                    mood=analysis.get('mood'),
                    voice=analysis.get('voice'),
                    aspect=analysis.get('aspect'),
                    confidence=analysis.get('confidence', 1.0),
                    source='ukrainian_pymorphy'
                ))
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Error analyzing word '{word}': {e}")
            # Fallback analysis
            return [self._fallback_analysis(word)]
    
    def analyze_text(self, text: str) -> Dict[str, List[MorphologicalAnalysis]]:
        """
        Analyze text morphologically
        
        Args:
            text: Text to analyze
            
        Returns:
            Dict mapping words to their morphological analyses
        """
        if not text:
            return {}
        
        # Simple tokenization
        words = re.findall(r'\b[A-ZА-ЯІЇЄҐa-zа-яіїєґ]+\b', text)
        
        results = {}
        for word in words:
            if word not in results:
                results[word] = self.analyze_word(word)
        
        return results
    
    def get_lemma(self, word: str) -> str:
        """
        Get base form (lemma) of word
        
        Args:
            word: Word to lemmatize
            
        Returns:
            Base form of the word
        """
        if not word:
            return word
        
        # Check blacklist
        if word.lower() in self.lemmatization_blacklist:
            return word.lower()  # Return lowercase version
        
        try:
            if self.morph_analyzer:
                parses = self.morph_analyzer.parse(word)
                if parses:
                    best_parse = max(parses, key=lambda p: p.score)
                    return best_parse.normal_form.lower()  # Normalize to lowercase
        except Exception as e:
            self.logger.warning(f"Error getting lemma for '{word}': {e}")
        
        # Fallback: return word in lowercase
        return word.lower()
    
    def get_pos_tags(self, word: str) -> List[str]:
        """
        Get part-of-speech tags for word
        
        Args:
            word: Word to analyze
            
        Returns:
            List of part-of-speech tags
        """
        if not word:
            return []
        
        try:
            if self.morph_analyzer:
                parses = self.morph_analyzer.parse(word)
                if parses:
                    tags = []
                    for parse in parses:
                        if hasattr(parse, 'tag'):
                            tags.append(str(parse.tag))
                    return list(set(tags))
            
            # Fallback: check special names
            if word in self.special_names:
                return self.special_names[word].get('pos_tags', [])
            
            return []
            
        except Exception as e:
            self.logger.warning(f"Error getting POS tags for '{word}': {e}")
            return []
    
    def _analyze_with_pymorphy(self, word: str) -> List[Dict[str, Any]]:
        """Analyze word through pymorphy3"""
        if not self.morph_analyzer:
            return [self._fallback_analysis(word)]
        
        try:
            parses = self.morph_analyzer.parse(word)
            if not parses:
                return [self._fallback_analysis(word)]
            
            results = []
            for parse in parses:
                analysis = {
                    'lemma': parse.normal_form.lower(),  # Normalize to lowercase
                    'pos': str(parse.tag.POS) if hasattr(parse.tag, 'POS') else 'UNKN',
                    'case': str(parse.tag.case) if hasattr(parse.tag, 'case') else None,
                    'number': str(parse.tag.number) if hasattr(parse.tag, 'number') else None,
                    'gender': str(parse.tag.gender) if hasattr(parse.tag, 'gender') else None,
                    'person': str(parse.tag.person) if hasattr(parse.tag, 'person') else None,
                    'tense': str(parse.tag.tense) if hasattr(parse.tag, 'tense') else None,
                    'mood': str(parse.tag.mood) if hasattr(parse.tag, 'mood') else None,
                    'voice': str(parse.tag.voice) if hasattr(parse.tag, 'voice') else None,
                    'aspect': str(parse.tag.aspect) if hasattr(parse.tag, 'aspect') else None,
                    'confidence': parse.score if hasattr(parse, 'score') else 1.0
                }
                results.append(analysis)
            
            return results
            
        except Exception as e:
            self.logger.warning(f"Error in pymorphy analysis for '{word}': {e}")
            return [self._fallback_analysis(word)]
    
    def _fallback_analysis(self, word: str) -> MorphologicalAnalysis:
        """Fallback analysis when pymorphy3 fails"""
        # Check special names
        if word in self.special_names:
            name_info = self.special_names[word]
            return MorphologicalAnalysis(
                lemma=name_info.get('lemma', word.lower()),  # Normalize to lowercase
                part_of_speech=name_info.get('pos', 'NOUN'),
                gender=name_info.get('gender'),
                confidence=0.8,
                source='ukrainian_special_names'
            )
        
        # Basic analysis based on endings
        pos = self._guess_pos_by_endings(word)
        gender = self._guess_gender_by_endings(word)
        
        return MorphologicalAnalysis(
            lemma=word.lower(),  # Normalize to lowercase
            part_of_speech=pos,
            gender=gender,
            confidence=0.3,
            source='ukrainian_fallback'
        )
    
    def _guess_pos_by_endings(self, word: str) -> str:
        """Guess part of speech by word endings"""
        if not word:
            return 'UNKN'
        
        word_lower = word.lower()
        
        # Noun endings
        noun_endings = ['ість', 'ство', 'ння', 'ання', 'ення', 'іння', 'ування']
        for ending in noun_endings:
            if word_lower.endswith(ending):
                return 'NOUN'
        
        # Adjective endings
        adj_endings = ['ий', 'ий', 'а', 'е', 'і', 'і']
        for ending in adj_endings:
            if word_lower.endswith(ending):
                return 'ADJF'
        
        # Verb endings
        verb_endings = ['ти', 'ться', 'в', 'ла', 'ло', 'ли']
        for ending in verb_endings:
            if word_lower.endswith(ending):
                return 'VERB'
        
        return 'UNKN'
    
    def _guess_gender_by_endings(self, word: str) -> str:
        """Guess gender by word endings"""
        if not word:
            return None
        
        word_lower = word.lower()
        
        # Masculine endings (only specific ones)
        masc_endings = ['ий', 'ой', 'ій']
        for ending in masc_endings:
            if word_lower.endswith(ending):
                return 'masc'
        
        # Feminine endings (more specific ones)
        fem_endings = ['а', 'я', 'ова', 'ева', 'ина']
        for ending in fem_endings:
            if word_lower.endswith(ending):
                return 'femn'
        
        # Neuter endings
        neut_endings = ['е', 'е', 'е']
        for ending in neut_endings:
            if word_lower.endswith(ending):
                return 'neut'
        
        return None
    
    def get_word_forms(self, lemma: str, pos: str = None) -> List[str]:
        """
        Get all possible word forms for given lemma
        
        Args:
            lemma: Base form of word
            pos: Part of speech (optional)
            
        Returns:
            List of possible word forms
        """
        if not lemma or not self.morph_analyzer:
            return [lemma]
        
        try:
            parses = self.morph_analyzer.parse(lemma)
            if not parses:
                return [lemma]
            
            forms = [lemma]
            
            # Get inflected forms
            for parse in parses:
                if pos and hasattr(parse.tag, 'POS') and str(parse.tag.POS) != pos:
                    continue
                
                # Common cases
                cases = ['nomn', 'gent', 'datv', 'accs', 'ablt', 'loct']
                for case in cases:
                    try:
                        inflected = parse.inflect({case})
                        if inflected and str(inflected) not in forms:
                            forms.append(str(inflected))
                    except Exception:
                        continue
            
            return list(set(forms))
            
        except Exception as e:
            self.logger.warning(f"Error getting word forms for '{lemma}': {e}")
            return [lemma]
    
    def transliterate_ukrainian(self, text: str) -> str:
        """
        Transliterate Ukrainian text to Latin
        
        Args:
            text: Ukrainian text to transliterate
            
        Returns:
            Transliterated text
        """
        if not text:
            return text
        
        result = text
        for ukr_char, lat_char in self.ukrainian_transliteration.items():
            result = result.replace(ukr_char, lat_char)
        
        return result
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        stats = super().get_analysis_statistics()
        stats.update({
            'pymorphy_available': self.morph_analyzer is not None,
            'special_names_count': len(self.special_names),
            'blacklist_count': len(self.lemmatization_blacklist),
            'ukrainian_patterns': list(self.ukrainian_specific_patterns.keys()),
            'transliteration_support': True
        })
        return stats
