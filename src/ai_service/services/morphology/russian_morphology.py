"""
Russian morphological analyzer
Inherits from BaseMorphologyAnalyzer
"""

import re
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass

from .base_morphology import BaseMorphologyAnalyzer, MorphologicalAnalysis
from ..utils import get_logger


@dataclass
class RussianMorphologyResult:
    """Result of Russian morphological analysis"""
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
    source: str = "russian"


class RussianMorphologyAnalyzer(BaseMorphologyAnalyzer):
    """Russian morphological analyzer"""
    
    def __init__(self):
        """Initialize Russian analyzer"""
        super().__init__('ru')
        self.logger = get_logger(__name__)
        
        # Initialize pymorphy3 analyzer
        self.morph_analyzer = self._initialize_pymorphy3()
        
        # Load dictionaries
        self.special_names = self._load_special_names()
        
        # Load lemmatization blacklist
        self.lemmatization_blacklist = self._load_lemmatization_blacklist()
        
        # Initialize additional resources
        self._initialize_additional_resources()
        
        self.logger.info("Russian Morphology Analyzer initialized")
    
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
            from ..data.dicts.russian_names import RUSSIAN_NAMES
            return RUSSIAN_NAMES
        except ImportError:
            self.logger.warning("Russian names dictionary not available")
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
        # Russian-specific initialization
        self.russian_specific_patterns = {
            'patronymic': r'\b[A-ZА-Я][a-zа-я]+ович\b|\b[A-ZА-Я][a-zа-я]+овна\b',
            'diminutive': r'\b[A-ZА-Я][a-zа-я]+енька\b|\b[A-ZА-Я][a-zа-я]+ечка\b',
            'formal': r'\b[A-ZА-Я][a-zа-я]+ич\b|\b[A-ZА-Я][a-zа-я]+ична\b'
        }
        
        # Regional transliterations for Russia
        self.regional_transliterations = {
            'ru_standard': {
                'ё': 'e', 'ъ': '', 'ь': '',
                'Ё': 'E', 'Ъ': '', 'Ь': ''
            },
            'ru_passport': {
                'ё': 'e', 'ъ': '', 'ь': '',
                'Ё': 'E', 'Ъ': '', 'Ь': ''
            }
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
                source='russian_short'
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
                    source='russian_pymorphy'
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
        words = re.findall(r'\b[A-ZА-Яa-zа-я]+\b', text)
        
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
            return word
        
        try:
            if self.morph_analyzer:
                parses = self.morph_analyzer.parse(word)
                if parses:
                    best_parse = max(parses, key=lambda p: p.score)
                    return best_parse.normal_form
            
            # Fallback: check special names
            if word in self.special_names:
                return self.special_names[word].get('lemma', word)
            
            return word
            
        except Exception as e:
            self.logger.warning(f"Error getting lemma for '{word}': {e}")
            return word
    
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
                    'lemma': word,  # Preserve original case
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
                lemma=name_info.get('lemma', word),
                part_of_speech=name_info.get('pos', 'NOUN'),
                gender=name_info.get('gender'),
                confidence=0.8,
                source='russian_special_names'
            )
        
        # Basic analysis based on endings
        pos = self._guess_pos_by_endings(word)
        gender = self._guess_gender_by_endings(word)
        
        return MorphologicalAnalysis(
            lemma=word,
            part_of_speech=pos,
            gender=gender,
            confidence=0.3,
            source='russian_fallback'
        )
    
    def _guess_pos_by_endings(self, word: str) -> str:
        """Guess part of speech by word endings"""
        if not word:
            return 'UNKN'
        
        word_lower = word.lower()
        
        # Noun endings
        noun_endings = ['ость', 'ство', 'ние', 'ание', 'ение', 'иние', 'ование']
        for ending in noun_endings:
            if word_lower.endswith(ending):
                return 'NOUN'
        
        # Adjective endings
        adj_endings = ['ый', 'ой', 'ая', 'ое', 'ые', 'ие']
        for ending in adj_endings:
            if word_lower.endswith(ending):
                return 'ADJF'
        
        # Verb endings
        verb_endings = ['ть', 'ться', 'л', 'ла', 'ло', 'ли']
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
        masc_endings = ['ий', 'ой', 'ый']
        for ending in masc_endings:
            if word_lower.endswith(ending):
                return 'masc'
        
        # Feminine endings (more specific ones)
        fem_endings = ['а', 'я', 'ова', 'ева', 'ина']
        for ending in fem_endings:
            if word_lower.endswith(ending):
                return 'femn'
        
        # Neuter endings
        neut_endings = ['е', 'ое', 'ее']
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
    
    def transliterate_russian(self, text: str) -> str:
        """
        Transliterate Russian text to Latin
        
        Args:
            text: Russian text to transliterate
            
        Returns:
            Transliterated text
        """
        if not text:
            return text
        
        # Russian transliteration mapping
        ru_to_latin = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'shch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
        }
        
        result = ''
        for char in text:
            if char.lower() in ru_to_latin:
                if char.isupper():
                    result += ru_to_latin[char.lower()].upper()
                else:
                    result += ru_to_latin[char.lower()]
            else:
                result += char
        
        return result
    
    def analyze_name(self, name: str) -> Dict[str, Any]:
        """
        Аналіз імені з детальною інформацією
        
        Args:
            name: Ім'я для аналізу
            
        Returns:
            Словник з результатами аналізу імені
        """
        if not name:
            return {
                'name': '',
                'language': 'ru',
                'gender': 'unknown',
                'total_forms': 0,
                'declensions': [],
                'diminutives': [],
                'variants': [],
                'transliterations': []
            }
        
        name = name.strip()
        if len(name) < 2:
            return {
                'name': name,
                'language': 'ru',
                'gender': 'unknown',
                'total_forms': 1,
                'declensions': [name],
                'diminutives': [name],
                'variants': [name],
                'transliterations': [name]
            }
        
        try:
            # Analysis through pymorphy3
            morph_analysis = self._analyze_with_pymorphy(name)
        except Exception as e:
            self.logger.warning(f"Pymorphy analysis failed for '{name}': {e}")
            morph_analysis = [{'gender': 'unknown'}]
        
        # Variant generation
        diminutives = self._generate_diminutives(name)
        variants = self._generate_variants(name)
        transliterations = self._generate_transliterations(name)
        
        # Add dictionary declensions if available
        dict_declensions = []
        if name in self.special_names:
            dict_declensions = self.special_names[name].get('declensions', [])
        
        # Get declensions from pymorphy3
        pymorphy_declensions = []
        if morph_analysis and len(morph_analysis) > 0:
            # Get all possible word forms
            pymorphy_declensions = self.get_word_forms(name)
        
        # Combine declensions from pymorphy3 and dictionary
        all_declensions = list(set(pymorphy_declensions + dict_declensions))
        
        # Determine gender
        gender = 'unknown'
        if morph_analysis and len(morph_analysis) > 0:
            gender = morph_analysis[0].get('gender', 'unknown')
        
        if gender == 'unknown':
            gender = self._analyze_gender_by_endings(name)
        
        # Count total number of forms
        total_forms = len(set(all_declensions + diminutives + variants + transliterations))
        
        return {
            'name': name,
            'language': 'ru',
            'gender': gender,
            'total_forms': total_forms,
            'declensions': all_declensions,
            'diminutives': diminutives,
            'variants': variants,
            'transliterations': transliterations
        }
    
    def _generate_diminutives(self, name: str) -> List[str]:
        """Generate diminutive forms"""
        if not name or len(name) < 2:
            return [name]
        
        # Check special names dictionary
        if name in self.special_names:
            return self.special_names[name].get('diminutives', [])
        
        # Basic logic for Russian names
        diminutives = []
        name_lower = name.lower()
        
        # Add common diminutive endings
        if name_lower.endswith('й'):
            diminutives.append(name[:-1] + 'енька')
            diminutives.append(name[:-1] + 'ик')
        elif name_lower.endswith('а'):
            diminutives.append(name[:-1] + 'енька')
            diminutives.append(name[:-1] + 'уся')
        
        return list(set(diminutives + [name]))
    
    def _generate_variants(self, name: str) -> List[str]:
        """Generate writing variants"""
        if not name:
            return []
        
        variants = [name]
        
        # Check special names dictionary
        if name in self.special_names:
            variants.extend(self.special_names[name].get('variants', []))
        
        # Add phonetic variants (placeholder)
        phonetic_variants = []
        variants.extend(phonetic_variants)
        
        return list(set(variants))
    
    def _generate_transliterations(self, name: str) -> List[str]:
        """Generate transliterations"""
        if not name:
            return []
        
        transliterations = []
        
        # Check special names dictionary
        if name in self.special_names:
            transliterations.extend(self.special_names[name].get('transliterations', []))
        
        # Add standard transliteration
        standard_translit = self.transliterate_russian(name)
        if standard_translit != name:
            transliterations.append(standard_translit)
        
        # Add regional variants
        for region, mapping in self.regional_transliterations.items():
            translit = name
            for ru_char, lat_char in mapping.items():
                translit = translit.replace(ru_char, lat_char)
            if translit != name:
                transliterations.append(translit)
        
        return list(set(transliterations + [name]))
    
    def is_russian_name(self, name: str) -> bool:
        """Check if name is Russian"""
        if not name:
            return False
        
        # Check special names dictionary
        if name in self.special_names:
            return True
        
        # Check endings
        name_lower = name.lower()
        russian_endings = ['ов', 'ев', 'ин', 'ын', 'ий', 'ой', 'ая', 'яя']
        
        for ending in russian_endings:
            if name_lower.endswith(ending):
                return True
        
        return False
    
    def get_name_complexity(self, name: str) -> Dict[str, Any]:
        """Analyze name complexity"""
        if not name:
            return {'name': '', 'complexity': 0, 'factors': []}
        
        factors = []
        complexity = 0
        
        # Name length
        if len(name) > 10:
            complexity += 2
            factors.append('long_name')
        elif len(name) > 6:
            complexity += 1
            factors.append('medium_name')
        
        # Presence of special characters
        if any(char in name for char in 'ёъь'):
            complexity += 1
            factors.append('special_chars')
        
        # Presence of rare letters
        rare_letters = ['ф', 'щ', 'э']
        if any(letter in name.lower() for letter in rare_letters):
            complexity += 1
            factors.append('rare_letters')
        
        return {
            'name': name,
            'complexity': complexity,
            'factors': factors
        }
    
    def get_all_forms(self, name: str) -> List[str]:
        """Get all name forms"""
        if not name:
            return []
        
        result = self.analyze_name(name)
        all_forms = []
        
        all_forms.extend(result.get('declensions', []))
        all_forms.extend(result.get('diminutives', []))
        all_forms.extend(result.get('variants', []))
        all_forms.extend(result.get('transliterations', []))
        
        return list(set(all_forms))
    
    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        stats = super().get_analysis_statistics()
        stats.update({
            'pymorphy_available': self.morph_analyzer is not None,
            'special_names_count': len(self.special_names),
            'blacklist_count': len(self.lemmatization_blacklist),
            'russian_patterns': list(self.russian_specific_patterns.keys()),
            'transliteration_support': True
        })
        return stats
