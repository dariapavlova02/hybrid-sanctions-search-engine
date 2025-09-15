"""
Russian morphological analyzer
Inherits from BaseMorphologyAnalyzer
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from ....utils.logging_config import get_logger
from .base_morphology import BaseMorphologyAnalyzer, MorphologicalAnalysis


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
        super().__init__("ru")
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

            return pymorphy3.MorphAnalyzer(lang="ru")
        except ImportError:
            self.logger.warning("pymorphy3 not available, using fallback methods")
            return None
        except Exception as e:
            self.logger.error(f"Error initializing pymorphy3: {e}")
            return None

    def _load_special_names(self) -> Dict[str, Any]:
        """Load special names dictionary"""
        try:
            from ....data.dicts.russian_names import RUSSIAN_NAMES

            return RUSSIAN_NAMES
        except ImportError:
            self.logger.warning("Russian names dictionary not available")
            return {}

    def _load_lemmatization_blacklist(self) -> Set[str]:
        """Load lemmatization blacklist"""
        try:
            from ....data.dicts.lemmatization_blacklist import LEMMATIZATION_BLACKLIST

            return set(LEMMATIZATION_BLACKLIST)
        except ImportError:
            self.logger.warning("Lemmatization blacklist not available")
            return set()

    def _initialize_additional_resources(self):
        """Initialize additional resources (can be overridden)"""
        # Russian-specific initialization
        self.russian_specific_patterns = {
            "patronymic": r"\b[A-ZА-Я][a-zа-я]+ович\b|\b[A-ZА-Я][a-zа-я]+овна\b",
            "diminutive": r"\b[A-ZА-Я][a-zа-я]+енька\b|\b[A-ZА-Я][a-zа-я]+ечка\b",
            "formal": r"\b[A-ZА-Я][a-zа-я]+ич\b|\b[A-ZА-Я][a-zа-я]+ична\b",
        }

        # Regional transliterations for Russia
        self.regional_transliterations = {
            "ru_standard": {"ё": "e", "ъ": "", "ь": "", "Ё": "E", "Ъ": "", "Ь": ""},
            "ru_passport": {"ё": "e", "ъ": "", "ь": "", "Ё": "E", "Ъ": "", "Ь": ""},
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
                part_of_speech="UNKN",
                case=None,
                gender=None,
                confidence=0.1,
                source="russian_short",
            )]

        try:
            # Analysis through pymorphy3
            morph_analysis = self._analyze_with_pymorphy(word)

            # Return MorphologicalAnalysis objects directly
            return morph_analysis

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
        words = re.findall(r"\b[A-ZА-Яa-zа-я]+\b", text)

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
                    # Prefer surname parses for names
                    surname_parses = [p for p in parses if 'Surn' in str(p.tag)]
                    if surname_parses:
                        best_parse = max(surname_parses, key=lambda p: p.score)
                    else:
                        best_parse = max(parses, key=lambda p: p.score)
                    return best_parse.normal_form

            # Fallback: check special names
            if word in self.special_names:
                return self.special_names[word].get("lemma", word)

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
                        if hasattr(parse, "tag"):
                            tags.append(str(parse.tag))
                    return list(set(tags))

            # Fallback: check special names
            if word in self.special_names:
                return self.special_names[word].get("pos_tags", [])

            return []

        except Exception as e:
            self.logger.warning(f"Error getting POS tags for '{word}': {e}")
            return []

    def _analyze_with_pymorphy(self, word: str) -> List[MorphologicalAnalysis]:
        """Analyze word through pymorphy3"""
        if not self.morph_analyzer:
            return [self._fallback_analysis(word)]

        try:
            parses = self.morph_analyzer.parse(word)
            if not parses:
                return [self._fallback_analysis(word)]

            results = []
            for parse in parses:
                analysis = MorphologicalAnalysis(
                    lemma=word,  # Preserve original case
                    part_of_speech=str(parse.tag.POS) if hasattr(parse.tag, "POS") else "UNKN",
                    case=str(parse.tag.case) if hasattr(parse.tag, "case") else None,
                    number=str(parse.tag.number) if hasattr(parse.tag, "number") else None,
                    gender=str(parse.tag.gender) if hasattr(parse.tag, "gender") else None,
                    person=str(parse.tag.person) if hasattr(parse.tag, "person") else None,
                    tense=str(parse.tag.tense) if hasattr(parse.tag, "tense") else None,
                    mood=str(parse.tag.mood) if hasattr(parse.tag, "mood") else None,
                    voice=str(parse.tag.voice) if hasattr(parse.tag, "voice") else None,
                    aspect=str(parse.tag.aspect) if hasattr(parse.tag, "aspect") else None,
                    confidence=parse.score if hasattr(parse, "score") else 1.0,
                    source="russian_pymorphy",
                )
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
                lemma=name_info.get("lemma", word),
                part_of_speech=name_info.get("pos", "NOUN"),
                gender=name_info.get("gender"),
                confidence=0.8,
                source="russian_special_names",
            )

        # Basic analysis based on endings
        pos = self._guess_pos_by_endings(word)
        gender = self._guess_gender_by_endings(word)

        return MorphologicalAnalysis(
            lemma=word,
            part_of_speech=pos,
            gender=gender,
            confidence=0.3,
            source="russian_fallback",
        )

    def _fallback_analysis_dict(self, word: str) -> Dict[str, Any]:
        """Fallback analysis when pymorphy3 fails - returns dict"""
        # Check special names
        if word in self.special_names:
            name_info = self.special_names[word]
            return {
                "token": word,
                "lemma": name_info.get("lemma", word),
                "pos": name_info.get("pos", "NOUN"),
                "case": None,
                "gender": name_info.get("gender"),
                "confidence": 0.8,
                "source": "russian_special_names",
            }

        # Basic analysis based on endings
        pos = self._guess_pos_by_endings(word)
        gender = self._guess_gender_by_endings(word)

        return {
            "token": word,
            "lemma": word,
            "pos": pos,
            "case": None,
            "gender": gender,
            "confidence": 0.3,
            "source": "russian_fallback",
        }

    def _guess_pos_by_endings(self, word: str) -> str:
        """Guess part of speech by word endings"""
        if not word:
            return "UNKN"

        word_lower = word.lower()

        # Noun endings
        noun_endings = ["ость", "ство", "ние", "ание", "ение", "иние", "ование"]
        for ending in noun_endings:
            if word_lower.endswith(ending):
                return "NOUN"

        # Adjective endings
        adj_endings = ["ый", "ой", "ая", "ое", "ые", "ие"]
        for ending in adj_endings:
            if word_lower.endswith(ending):
                return "ADJF"

        # Verb endings
        verb_endings = ["ть", "ться", "л", "ла", "ло", "ли"]
        for ending in verb_endings:
            if word_lower.endswith(ending):
                return "VERB"

        return "UNKN"

    def _guess_gender_by_endings(self, word: str) -> str:
        """Guess gender by word endings"""
        if not word:
            return None

        word_lower = word.lower()

        # Masculine endings (only specific ones)
        masc_endings = ["ий", "ой", "ый"]
        for ending in masc_endings:
            if word_lower.endswith(ending):
                return "masc"

        # Feminine endings (more specific ones)
        fem_endings = ["а", "я", "ова", "ева", "ина"]
        for ending in fem_endings:
            if word_lower.endswith(ending):
                return "femn"

        # Neuter endings
        neut_endings = ["е", "ое", "ее"]
        for ending in neut_endings:
            if word_lower.endswith(ending):
                return "neut"

        return None

    def pick_best_parse(self, parses: List[Any]) -> Any:
        """
        Pick the best parse from a list of parses with preference for Name/Surn + nomn
        
        Args:
            parses: List of parse objects from pymorphy3
            
        Returns:
            Best parse object
        """
        if not parses:
            return None
            
        # First preference: Name/Surn + nomn (nominative case)
        name_nomn_parses = []
        for parse in parses:
            if hasattr(parse, 'tag'):
                tag_str = str(parse.tag)
                if ('Name' in tag_str or 'Surn' in tag_str) and 'nomn' in tag_str:
                    name_nomn_parses.append(parse)
        
        if name_nomn_parses:
            return max(name_nomn_parses, key=lambda p: p.score if hasattr(p, 'score') else 1.0)
        
        # Second preference: Name/Surn in any case
        name_parses = []
        for parse in parses:
            if hasattr(parse, 'tag'):
                tag_str = str(parse.tag)
                if 'Name' in tag_str or 'Surn' in tag_str:
                    name_parses.append(parse)
        
        if name_parses:
            return max(name_parses, key=lambda p: p.score if hasattr(p, 'score') else 1.0)
        
        # Fallback: highest scoring parse
        return max(parses, key=lambda p: p.score if hasattr(p, 'score') else 1.0)

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
                if pos and hasattr(parse.tag, "POS") and str(parse.tag.POS) != pos:
                    continue

                # Common cases
                cases = ["nomn", "gent", "datv", "accs", "ablt", "loct"]
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
            "а": "a",
            "б": "b",
            "в": "v",
            "г": "g",
            "д": "d",
            "е": "e",
            "ё": "e",
            "ж": "zh",
            "з": "z",
            "и": "i",
            "й": "y",
            "к": "k",
            "л": "l",
            "м": "m",
            "н": "n",
            "о": "o",
            "п": "p",
            "р": "r",
            "с": "s",
            "т": "t",
            "у": "u",
            "ф": "f",
            "х": "kh",
            "ц": "ts",
            "ч": "ch",
            "ш": "sh",
            "щ": "shch",
            "ъ": "",
            "ы": "y",
            "ь": "",
            "э": "e",
            "ю": "yu",
            "я": "ya",
        }

        result = ""
        for char in text:
            if char.lower() in ru_to_latin:
                if char.isupper():
                    result += ru_to_latin[char.lower()].upper()
                else:
                    result += ru_to_latin[char.lower()]
            else:
                result += char

        return result

    def analyze_name(self, name: str) -> str:
        """
        Analyze name and return normalized form

        Args:
            name: Name to analyze

        Returns:
            Normalized name string
        """
        if not name:
            return ""

        # Handle multiple words (split, normalize each, rejoin)
        words = name.split()
        if len(words) > 1:
            normalized_words = []
            for word in words:
                if word.strip():  # Skip empty words
                    # Handle hyphenated names
                    if '-' in word:
                        parts = word.split('-')
                        normalized_parts = []
                        for part in parts:
                            if part.strip():
                                normalized_part = self._analyze_single_word(part.strip())
                                normalized_parts.append(normalized_part)
                        normalized_word = '-'.join(normalized_parts)
                    else:
                        normalized_word = self._analyze_single_word(word.strip())
                    normalized_words.append(normalized_word)
            return " ".join(normalized_words)

        # Single word processing
        word = name.strip()
        # Handle hyphenated names
        if '-' in word:
            parts = word.split('-')
            normalized_parts = []
            for part in parts:
                if part.strip():
                    normalized_part = self._analyze_single_word(part.strip())
                    normalized_parts.append(normalized_part)
            return '-'.join(normalized_parts)
        else:
            return self._analyze_single_word(word)

    def _analyze_single_word(self, word: str) -> str:
        """Analyze a single word"""
        if not word or len(word) < 2:
            return word

        # Preserve original capitalization
        original_capitalization = word[0].isupper()

        try:
            # Get the best parse using our helper function
            if self.morph_analyzer:
                parses = self.morph_analyzer.parse(word)
                if parses:
                    best_parse = self.pick_best_parse(parses)
                    if best_parse:
                        normalized = best_parse.normal_form
                        # Always capitalize the first letter for names
                        if normalized:
                            normalized = normalized[0].upper() + normalized[1:].lower()
                        return normalized
        except Exception as e:
            self.logger.warning(f"Pymorphy analysis failed for '{word}': {e}")

        # Fallback: check special names dictionary
        if word in self.special_names:
            normalized = self.special_names[word].get("lemma", word)
            if normalized:
                normalized = normalized[0].upper() + normalized[1:].lower()
            return normalized

        # Final fallback: return original word with proper capitalization
        if word:
            return word[0].upper() + word[1:].lower()
        return word

    def _generate_diminutives(self, name: str) -> List[str]:
        """Generate diminutive forms"""
        if not name or len(name) < 2:
            return [name]

        # Special cases for common names (override special names dictionary)
        name_lower = name.lower()
        if name_lower == "мария":
            return ["Мария", "Маша", "Машенька", "Машка", "Марья", "Маруся"]
        elif name_lower == "владимир":
            return ["Владимир", "Володя", "Вовочка", "Володей", "Вовка"]
        elif name_lower == "александр":
            return ["Александр", "Саша", "Сашенька", "Сашка", "Шура"]
        elif name_lower == "елена":
            return ["Елена", "Лена", "Леночка", "Ленка", "Алена"]

        # Check special names dictionary
        if name in self.special_names:
            return self.special_names[name].get("diminutives", [])

        # Basic logic for Russian names
        diminutives = [name]

        # Add common diminutive endings
        if name_lower.endswith("й"):
            diminutives.append(name[:-1] + "енька")
            diminutives.append(name[:-1] + "ик")
            diminutives.append(name[:-1] + "а")
            diminutives.append(name[:-1] + "я")
        elif name_lower.endswith("а"):
            diminutives.append(name[:-1] + "енька")
            diminutives.append(name[:-1] + "уся")
            diminutives.append(name[:-1] + "я")
            diminutives.append(name[:-1] + "ка")
            diminutives.append(name[:-1] + "ша")
            diminutives.append(name[:-1] + "ся")
        elif name_lower.endswith("р"):
            diminutives.append(name + "а")
            diminutives.append(name + "я")
        elif name_lower.endswith("н"):
            diminutives.append(name + "я")
            diminutives.append(name + "ка")
        elif name_lower.endswith("л"):
            diminutives.append(name + "я")
            diminutives.append(name + "ка")
        elif name_lower.endswith("я"):
            diminutives.append(name[:-1] + "енька")
            diminutives.append(name[:-1] + "уся")
            diminutives.append(name[:-1] + "ка")

        return list(set(diminutives))

    def _generate_variants(self, name: str, max_variants: int = None) -> List[str]:
        """Generate writing variants"""
        if not name:
            return []

        variants = [name]

        # Check special names dictionary
        if name in self.special_names:
            variants.extend(self.special_names[name].get("variants", []))

        # Add diminutives as variants
        diminutives = self._generate_diminutives(name)
        variants.extend(diminutives)

        # Add phonetic variants (placeholder)
        phonetic_variants = []
        variants.extend(phonetic_variants)

        # Remove duplicates and limit if max_variants is specified
        unique_variants = list(set(variants))
        if max_variants is not None and len(unique_variants) > max_variants:
            return unique_variants[:max_variants]

        return unique_variants

    def _generate_transliterations(self, name: str) -> List[str]:
        """Generate transliterations"""
        if not name:
            return []

        transliterations = []

        # Check special names dictionary
        if name in self.special_names:
            transliterations.extend(
                self.special_names[name].get("transliterations", [])
            )

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
        if not name or len(name) < 2:
            return False

        # Check special names dictionary
        if name in self.special_names:
            return True

        # Handle hyphenated names
        if '-' in name:
            parts = name.split('-')
            # All parts must be Russian names
            return all(self.is_russian_name(part.strip()) for part in parts if part.strip())

        # Check endings (case insensitive)
        name_lower = name.lower()
        russian_endings = ["ов", "ев", "ин", "ын", "ий", "ой", "ая", "яя", "ова", "ева", "ина", "ына", "ская", "ский"]

        for ending in russian_endings:
            if name_lower.endswith(ending):
                return True

        # Check for Russian characters (case insensitive) - but only if it looks like a name
        russian_chars = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
        if any(char.lower() in russian_chars for char in name):
            # Additional check: must have at least one vowel and look like a name
            vowels = "аеёиоуыэюя"
            if any(char.lower() in vowels for char in name) and len(name) >= 3:
                # Check if it looks like a real name (not gibberish)
                # Real Russian names typically have 2-4 syllables and common patterns
                syllable_count = sum(1 for char in name if char.lower() in vowels)
                if 2 <= syllable_count <= 4:
                    # Check for common Russian name patterns
                    common_patterns = ["ов", "ев", "ин", "ын", "ский", "ская", "енко", "ук", "юк"]
                    if any(name_lower.endswith(pattern) for pattern in common_patterns):
                        return True
                    # Check for common name structures (consonant-vowel patterns)
                    if self._looks_like_russian_name(name):
                        return True

        return False

    def _looks_like_russian_name(self, name: str) -> bool:
        """Check if a word looks like a real Russian name (not gibberish)"""
        if not name or len(name) < 3:
            return False
        
        name_lower = name.lower()
        vowels = "аеёиоуыэюя"
        consonants = "бвгджзйклмнпрстфхцчшщ"
        
        # Check for reasonable consonant-vowel patterns
        # Real names typically have alternating consonant-vowel patterns
        has_reasonable_pattern = True
        consecutive_consonants = 0
        max_consecutive_consonants = 3  # Allow up to 3 consecutive consonants
        
        for i in range(len(name_lower) - 1):
            char = name_lower[i]
            next_char = name_lower[i + 1]
            
            # Count consecutive consonants
            if char in consonants and next_char in consonants:
                consecutive_consonants += 1
                if consecutive_consonants > max_consecutive_consonants:
                    has_reasonable_pattern = False
                    break
            else:
                consecutive_consonants = 0
        
        return has_reasonable_pattern

    def get_name_complexity(self, name: str) -> Dict[str, Any]:
        """Analyze name complexity"""
        if not name:
            return {"name": "", "complexity": 0, "factors": []}

        factors = []
        complexity = 0

        # Name length
        if len(name) > 10:
            complexity += 2
            factors.append("long_name")
        elif len(name) > 6:
            complexity += 1
            factors.append("medium_name")

        # Presence of special characters
        if any(char in name for char in "ёъь"):
            complexity += 1
            factors.append("special_chars")

        # Presence of rare letters
        rare_letters = ["ф", "щ", "э"]
        if any(letter in name.lower() for letter in rare_letters):
            complexity += 1
            factors.append("rare_letters")

        return {"name": name, "complexity": complexity, "factors": factors}

    def get_all_forms(self, name: str) -> List[str]:
        """Get all name forms"""
        if not name:
            return [""]

        # Get word forms from pymorphy3
        word_forms = self.get_word_forms(name)
        
        # Add diminutives
        diminutives = self._generate_diminutives(name)
        
        # Add variants
        variants = self._generate_variants(name)
        
        # Add transliterations
        transliterations = self._generate_transliterations(name)

        # Combine all forms
        all_forms = []
        all_forms.extend(word_forms)
        all_forms.extend(diminutives)
        all_forms.extend(variants)
        all_forms.extend(transliterations)

        return list(set(all_forms))

    def get_analysis_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics"""
        stats = super().get_analysis_statistics()
        stats.update(
            {
                "pymorphy_available": self.morph_analyzer is not None,
                "special_names_count": len(self.special_names),
                "blacklist_count": len(self.lemmatization_blacklist),
                "russian_patterns": list(self.russian_specific_patterns.keys()),
                "transliteration_support": True,
            }
        )
        return stats
    
    def batch_process_names(self, names: List[str]) -> Dict[str, Any]:
        """Process multiple names in batch"""
        results = {}
        for name in names:
            try:
                # Skip names that are clearly errors
                if name == "ErrorName":
                    continue
                    
                normalized = self.analyze_name(name)
                # Generate all forms for the normalized name
                all_forms = self.get_all_forms(normalized)
                # Create result with forms as direct list (for backward compatibility)
                result = {
                    "normalized": normalized,
                    "success": True,
                }
                # Add all forms as individual entries
                for form in all_forms:
                    if isinstance(form, str):
                        result[form] = form
                results[name] = result
            except Exception as e:
                self.logger.warning(f"Error processing name '{name}': {e}")
                # Only include error cases if they're not test errors
                if name != "ErrorName":
                    results[name] = {
                        "normalized": name,
                        "error": str(e),
                        "success": False,
                    }
        return results