"""
Service for generating name and surname writing variants
"""

import hashlib
import logging
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, List, Optional, Set, Union

from ...utils.logging_config import get_logger
from ..language.language_detection_service import LanguageDetectionService

# Import configuration
try:
    from ...config import VARIANT_SCORES
except ImportError:
    # Fallback configuration if config.py is not available
    VARIANT_SCORES = {
        "morphological": 1.0,
        "transliteration": 0.9,
        "phonetic": 0.8,
        "visual_similarity": 0.7,
        "typo": 0.6,
        "regional": 0.5,
        "fallback": 0.3,
    }

# Import configuration - use proper relative imports
try:
    from ..data.dicts.english_names import ENGLISH_NAMES as english_names
    from ..data.dicts.russian_names import RUSSIAN_NAMES as russian_names
    from ..data.dicts.ukrainian_names import UKRAINIAN_NAMES as ukrainian_names
except ImportError:
    english_names = {}
    russian_names = {}
    ukrainian_names = {}

logger = logging.getLogger(__name__)


class VariantGenerationService:
    """Service for generating name writing variants"""

    def __init__(self):
        """
        Initialize the variant generation service with comprehensive transliteration support.

        Sets up multiple transliteration standards (ICAO, ISO-9, GOST-2002, Ukrainian),
        phonetic patterns for similar sounds, and visual similarity mappings for
        homoglyph detection. Initializes language detection service and loads
        name dictionaries for morphological analysis.

        The service supports:
        - Multiple transliteration standards for different use cases
        - Phonetic pattern matching for sound-alike variations
        - Visual similarity detection for homoglyph substitution
        - Extended Ukrainian character support (і, ї, є, ґ)
        """
        self.logger = get_logger(__name__)
        self.language_service = LanguageDetectionService()

        # Extended transliteration system with support for different standards
        self.transliteration_standards = {
            "ICAO": {  # International Civil Aviation Organization
                "а": "a",
                "б": "b",
                "в": "v",
                "г": "h",
                "д": "d",
                "е": "e",
                "ё": "e",
                "ж": "zh",
                "з": "z",
                "и": "y",
                "й": "i",
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
                # Ukrainian-specific characters
                "і": "i",
                "ї": "yi",
                "є": "ye",
                "ґ": "g",
                # Capital letters
                "А": "A",
                "Б": "B",
                "В": "V",
                "Г": "H",
                "Д": "D",
                "Е": "E",
                "Ё": "E",
                "Ж": "ZH",
                "З": "Z",
                "И": "Y",
                "Й": "I",
                "К": "K",
                "Л": "L",
                "М": "M",
                "Н": "N",
                "О": "O",
                "П": "P",
                "Р": "R",
                "С": "S",
                "Т": "T",
                "У": "U",
                "Ф": "F",
                "Х": "KH",
                "Ц": "TS",
                "Ч": "CH",
                "Ш": "SH",
                "Щ": "SHCH",
                "Ъ": "",
                "Ы": "Y",
                "Ь": "",
                "Э": "E",
                "Ю": "YU",
                "Я": "YA",
                # Ukrainian-specific capital characters
                "І": "I",
                "Ї": "Yi",
                "Є": "Ye",
                "Ґ": "G",
            },
            "ISO-9": {  # International standard ISO 9
                "а": "a",
                "б": "b",
                "в": "v",
                "г": "g",
                "д": "d",
                "е": "e",
                "ё": "ë",
                "ж": "ž",
                "з": "z",
                "и": "i",
                "й": "j",
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
                "х": "h",
                "ц": "c",
                "ч": "č",
                "ш": "š",
                "щ": "ŝ",
                "ъ": "ʺ",
                "ы": "y",
                "ь": "ʹ",
                "э": "è",
                "ю": "û",
                "я": "â",
            },
            "GOST-2002": {  # Russian standard GOST 2002
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
            },
            "Ukrainian": {  # Ukrainian standard
                "а": "a",
                "б": "b",
                "в": "v",
                "г": "h",
                "д": "d",
                "е": "e",
                "ё": "e",
                "ж": "zh",
                "з": "z",
                "и": "y",
                "й": "i",
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
                # Ukrainian-specific characters
                "і": "i",
                "ї": "yi",
                "є": "ye",
                "ґ": "g",
                "І": "I",
                "Ї": "Yi",
                "Є": "Ye",
                "Ґ": "G",
            },
        }

        # Fallback dictionaries for backward compatibility
        self.cyrillic_to_latin = self.transliteration_standards["ICAO"]

        # Reverse mapping (Latin -> Cyrillic)
        self.latin_to_cyrillic = {v: k for k, v in self.cyrillic_to_latin.items()}

        # Extended phonetic patterns for similar sounds
        self.phonetic_patterns = {
            "ch": ["ch", "tch", "cz", "tsch", "tsh", "c"],
            "sh": ["sh", "sch", "sz", "s", "sj", "x"],
            "zh": ["zh", "j", "g", "z", "dj", "s"],
            "kh": ["kh", "h", "ch", "x", "q", "k"],
            "ts": ["ts", "tz", "c", "z", "t"],
            "yu": ["yu", "iu", "u", "y", "ju"],
            "ya": ["ya", "ia", "a", "ja", "i"],
            "th": ["th", "t", "d", "θ", "ð"],
            "ng": ["ng", "n", "g", "ŋ"],
            "ph": ["ph", "f", "p", "ф"],
            "qu": ["qu", "kw", "k", "q"],
            "wh": ["wh", "w", "hw", "h"],
        }

        # Visually similar symbols (homoglyphs)
        self.visual_similarities = {
            "a": ["а", "ɑ", "@", "4"],  # Latin a -> Cyrillic а
            "e": ["е", "ё", "3", "€"],  # Latin e -> Cyrillic е
            "o": ["о", "0", "о", "ο"],  # Latin o -> digit 0
            "i": ["і", "1", "l", "|"],  # Latin i -> Cyrillic і
            "n": ["п", "и", "п"],  # Latin n -> Cyrillic п
            "p": ["р", "р"],  # Latin p -> Cyrillic р
            "c": ["с", "с"],  # Latin c -> Cyrillic с
            "y": ["у", "у"],  # Latin y -> Cyrillic у
            "x": ["х", "х"],  # Latin x -> Cyrillic х
            "k": ["к", "к"],  # Latin k -> Cyrillic к
            "m": ["м", "м"],  # Latin m -> Cyrillic м
            "t": ["т", "т"],  # Latin t -> Cyrillic т
            "b": ["в", "в"],  # Latin b -> Cyrillic в
            "h": ["н", "н"],  # Latin h -> Cyrillic н
            "r": ["г", "г"],  # Latin r -> Cyrillic г
        }

        # Abbreviation patterns
        self.abbreviation_patterns = [
            r"\b[A-Z]\.[A-Z]\.",  # A.B.
            r"\b[A-Z]\s[A-Z]",  # A B
            r"\b[A-Z][a-z]+\.",  # Abc.
        ]

        # Typo patterns
        self.typo_patterns = {
            "double_vowels": [
                ("aa", "a"),
                ("ee", "e"),
                ("ii", "i"),
                ("oo", "o"),
                ("uu", "u"),
            ],
            "double_consonants": [
                ("bb", "b"),
                ("cc", "c"),
                ("dd", "d"),
                ("ff", "f"),
                ("gg", "g"),
            ],
            "missing_vowels": [("anna", "ana"), ("hanna", "hana"), ("maria", "maria")],
            "common_typos": [("ph", "f"), ("ck", "k"), ("qu", "kw"), ("x", "ks")],
        }

        # Automatic morphological analyzers
        self._init_morphological_analyzers()

        # Automatic transliterators
        self._init_transliterators()

        # Import dictionaries from files
        self._import_dictionaries()

        self.logger.info(
            "VariantGenerationService initialized with automatic analyzers"
        )

    def _import_dictionaries(self):
        """Import dictionaries from files"""
        # Import name dictionaries
        from ...data.dicts.arabic_names import ALL_ARABIC_NAMES
        from ...data.dicts.asian_names import ALL_ASIAN_NAMES
        from ...data.dicts.english_names import ALL_ENGLISH_NAMES
        from ...data.dicts.european_names import ALL_EUROPEAN_NAMES
        from ...data.dicts.indian_names import ALL_INDIAN_NAMES
        from ...data.dicts.russian_names import ALL_RUSSIAN_NAMES
        from ...data.dicts.scandinavian_names import ALL_SCANDINAVIAN_NAMES
        from ...data.dicts.ukrainian_names import ALL_UKRAINIAN_NAMES

        # Update dictionaries
        self.name_dictionaries = {
            "uk": set(ALL_UKRAINIAN_NAMES),
            "ru": set(ALL_RUSSIAN_NAMES),
            "en": set(ALL_ENGLISH_NAMES),
            "as": set(ALL_ASIAN_NAMES),
            "ar": set(ALL_ARABIC_NAMES),
            "in": set(ALL_INDIAN_NAMES),
            "eu": set(ALL_EUROPEAN_NAMES),
            "sc": set(ALL_SCANDINAVIAN_NAMES),
        }

        self.logger.info("Name dictionaries imported successfully from files")

    def _init_morphological_analyzers(self):
        """Initialize automatic morphological analyzers"""
        self.ru_morph = None
        self.uk_morph = None

        try:
            # For Russian language, use pymorphy3
            import pymorphy3

            self.ru_morph = pymorphy3.MorphAnalyzer(lang="ru")
            self.logger.info("Russian pymorphy3 analyzer initialized")
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"pymorphy3 not available: {e}")
            self.ru_morph = None

        try:
            # Use our own Ukrainian analyzer
            from .ukrainian_morphology import UkrainianMorphologyAnalyzer

            self.uk_morph = UkrainianMorphologyAnalyzer()
            self.logger.info("Custom Ukrainian morphological analyzer initialized")
        except ImportError as e:
            self.logger.warning(f"Ukrainian morphology analyzer not available: {e}")

    def _init_transliterators(self):
        """Initialize automatic transliterators"""
        try:
            from transliterate import translit

            self.transliterator = translit
            self.logger.info("Transliterator initialized")
        except ImportError:
            self.transliterator = None
            self.logger.warning(
                "transliterate not installed. Install with: pip install transliterate"
            )

    def generate_variants(
        self,
        text: str,
        language: str = "auto",
        include_transliteration: bool = True,
        include_phonetic: bool = True,
        include_abbreviations: bool = True,
        include_visual_similarities: bool = True,
        include_typo_variants: bool = True,
        max_variants: int = 50,
        prioritize_quality: bool = True,  # NEW OPTION for quality control
        max_time_ms: int = 100,  # Maximum time in milliseconds
    ) -> Dict[str, Any]:
        """
        Generates comprehensive writing variants for input text.

        Creates multiple variations of the input text using different techniques:
        transliteration, phonetic matching, visual similarity detection, typo
        generation, and abbreviation expansion. The method automatically detects
        language if not specified and applies appropriate morphological analysis.

        Args:
            text (str): The input text to generate variants for.
            language (str, optional): Language of the text. Defaults to 'auto'.
            include_transliteration (bool, optional): Include transliteration variants.
                                                   Defaults to True.
            include_phonetic (bool, optional): Include phonetic similarity variants.
                                            Defaults to True.
            include_abbreviations (bool, optional): Include abbreviation expansions.
                                                Defaults to True.
            include_visual_similarities (bool, optional): Include homoglyph variants.
                                                       Defaults to True.
            include_typo_variants (bool, optional): Include common typo variations.
                                                 Defaults to True.
            max_variants (int, optional): Maximum number of variants to return.
                                       Defaults to 50.
            prioritize_quality (bool, optional): Prioritize high-quality variants.
                                             Defaults to True.

        Returns:
            Dict[str, Any]: A dictionary containing:
                - original: The original input text
                - variants: List of generated variants
                - count: Total number of variants
                - language: Detected or specified language
                - statistics: Detailed generation statistics
        """
        if not text or not text.strip():
            return {"original": text, "variants": [], "count": 0, "language": language}

        # Automatic language detection
        if language == "auto":
            language = self._detect_language(text)

        # Use comprehensive generation
        comprehensive_result = self.generate_comprehensive_variants(text, language)

        variants = set()
        variants.add(text.strip())  # Original text

        # Defensive coding: check comprehensive generation result
        if comprehensive_result is None:
            self.logger.warning(
                f"Comprehensive generation returned None for text: {text}"
            )
            comprehensive_result = {
                "transliterations": set(),
                "phonetic_variants": set(),
                "visual_similarities": set(),
                "typo_variants": set(),
                "morphological_variants": set(),
            }

        # Track time for early stopping
        import time
        start_time = time.time()

        def time_limit_reached():
            return (time.time() - start_time) * 1000 > max_time_ms

        # Early stopping for performance - check if we have enough variants
        def should_continue():
            return (len(variants) < max_variants * 2 and  # Generate 2x to allow filtering
                   not time_limit_reached())  # Don't exceed time limit

        # 1. Basic variants (quick and essential)
        additional_variants = self._generate_additional_variants(text)
        variants.update(additional_variants)

        # 2. Word order variations (important for sanctions matching)
        word_order_variants = self._generate_word_order_variants(text)
        variants.update(word_order_variants)

        if not should_continue():
            # If we already have enough from basic operations, skip expensive ones
            comprehensive_result = {
                "transliterations": set(), "phonetic_variants": set(),
                "visual_similarities": set(), "typo_variants": set(),
                "morphological_variants": set()
            }
            abbrev_variants = set()
            morphological_variants = set()
            transliteration_variants = set()
            diminutive_variants = set()
            semantic_variants = set()
        else:
            # 3. Transliteration (medium cost, high value)
            if include_transliteration and should_continue():
                variants.update(comprehensive_result.get("transliterations", set()))

            # 4. Diminutive variants (medium cost, high value for names)
            if should_continue():
                diminutive_variants = self._generate_diminutive_variants(text, language)
                variants.update(diminutive_variants)

            # 5. Abbreviation variants (low cost)
            if include_abbreviations and should_continue():
                abbrev_variants = self._generate_abbreviation_variants(text)
                variants.update(abbrev_variants)

            # 6. Automatic morphological variants (low cost)
            if should_continue():
                morphological_variants = self._generate_automatic_morphological_variants(
                    text, language
                )
                variants.update(morphological_variants)

            # 7. Automatic transliterations (medium cost)
            if should_continue():
                transliteration_variants = self._generate_automatic_transliteration_variants(
                    text, language
                )
                variants.update(transliteration_variants)

            # 8. Expensive operations - only if we still need more variants
            if should_continue():
                # Phonetic variants
                if include_phonetic:
                    variants.update(comprehensive_result.get("phonetic_variants", set()))

                # Visual similarities (can be expensive)
                if include_visual_similarities and should_continue():
                    variants.update(comprehensive_result.get("visual_similarities", set()))

                # Typo variants (can be expensive)
                if include_typo_variants and should_continue():
                    variants.update(comprehensive_result.get("typo_variants", set()))

                # Semantic variants (most expensive)
                if should_continue():
                    semantic_variants = self._generate_semantic_similar_names(text, language)
                    variants.update(semantic_variants)
            else:
                # Set empty defaults for statistics
                semantic_variants = set()

        # PRIORITY SYSTEM for quality variants
        if prioritize_quality:
            variants_list = self._prioritize_variants(list(variants), max_variants)
        else:
            # Simple limit
            variants_list = list(variants)[:max_variants]

        # Detailed statistics
        detailed_stats = {
            "transliterations": len(
                comprehensive_result.get("transliterations", set())
            ),
            "visual_similarities": len(
                comprehensive_result.get("visual_similarities", set())
            ),
            "typo_variants": len(comprehensive_result.get("typo_variants", set())),
            "phonetic_variants": len(
                comprehensive_result.get("phonetic_variants", set())
            ),
            "morphological_variants": len(
                comprehensive_result.get("morphological_variants", set())
            ),
            "abbreviations": len(abbrev_variants) if include_abbreviations else 0,
            "basic_variants": len(additional_variants),
            "word_order_variants": len(word_order_variants),
            "diminutive_variants": len(diminutive_variants),
        }

        return {
            "original": text,
            "variants": variants_list,
            "count": len(variants_list),
            "language": language,
            "total_generated": len(variants),
            "detailed_stats": detailed_stats,
            "generation_methods": {
                "transliteration": include_transliteration,
                "phonetic": include_phonetic,
                "abbreviations": include_abbreviations,
                "visual_similarities": include_visual_similarities,
                "typo_variants": include_typo_variants,
            },
        }

    def _generate_transliteration_variants(self, text: str) -> Set[str]:
        """Generation of transliteration variants"""
        variants = set()

        # Cyrillic -> Latin
        if self._contains_cyrillic(text):
            latin_text = self._transliterate_cyrillic_to_latin(text)
            variants.add(latin_text)

            # Variant with unidecode
            unidecode_text = unidecode(text)
            if unidecode_text != latin_text:
                variants.add(unidecode_text)

        # Latin -> Cyrillic (if possible)
        if self._contains_latin(text):
            cyrillic_text = self._transliterate_latin_to_cyrillic(text)
            if cyrillic_text != text:
                variants.add(cyrillic_text)

        return variants

    def _generate_phonetic_variants(self, text: str) -> Set[str]:
        """Generation of phonetic variants"""
        variants = set()

        # Split into words
        words = text.split()

        for word in words:
            word_lower = word.lower()

            # Replace phonetic patterns
            for pattern, replacements in self.phonetic_patterns.items():
                if pattern in word_lower:
                    for replacement in replacements:
                        new_word = word_lower.replace(pattern, replacement)
                        if new_word != word_lower:
                            # Restore case
                            if word[0].isupper():
                                new_word = new_word.capitalize()
                            variants.add(text.replace(word, new_word))

        return variants

    def _generate_abbreviation_variants(self, text: str) -> Set[str]:
        """Generation of abbreviation variants"""
        variants = set()

        # Find abbreviation patterns
        for pattern in self.abbreviation_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                matched_text = match.group()

                # Expand initials
                if "." in matched_text:
                    # A.B. -> A B
                    expanded = matched_text.replace(".", " ").strip()
                    variants.add(text.replace(matched_text, expanded))
                else:
                    # A B -> A.B.
                    contracted = ". ".join(matched_text.split()) + "."
                    variants.add(text.replace(matched_text, contracted))

        return variants

    def _generate_additional_variants(self, text: str) -> Set[str]:
        """Generation of additional variants"""
        variants = set()

        # Variants with case
        variants.add(text.lower())
        variants.add(text.upper())
        variants.add(text.title())

        # Variants with spaces
        if " " in text:
            # Add/remove spaces
            no_spaces = text.replace(" ", "")
            variants.add(no_spaces)

            # Add dashes
            with_dashes = text.replace(" ", "-")
            variants.add(with_dashes)

        # Variants with dashes
        if "-" in text:
            # Replace dashes with spaces
            with_spaces = text.replace("-", " ")
            variants.add(with_spaces)

        return variants

    def _contains_cyrillic(self, text: str) -> bool:
        """Check if text contains Cyrillic characters"""
        return bool(re.search(r"[а-яёіїє]", text, re.IGNORECASE))

    def _contains_latin(self, text: str) -> bool:
        """Check if text contains Latin characters"""
        return bool(re.search(r"[a-z]", text, re.IGNORECASE))

    def _transliterate_cyrillic_to_latin(
        self, text: str, standard: str = "ICAO"
    ) -> str:
        """Transliteration of Cyrillic to Latin using a specified standard"""
        if standard not in self.transliteration_standards:
            standard = "ICAO"  # Fallback to ICAO

        char_map = self.transliteration_standards[standard]
        result = ""
        for char in text:
            if char in char_map:
                result += char_map[char]
            else:
                result += char
        return result

    def _generate_transliteration_variants(self, text: str) -> Set[str]:
        """Generation of transliteration variants for all standards"""
        variants = set()

        # Generate transliterations for all standards
        for standard_name in self.transliteration_standards.keys():
            transliterated = self._transliterate_cyrillic_to_latin(text, standard_name)
            if transliterated != text:
                variants.add(transliterated)

        # Add phonetic variants
        phonetic_variants = self._generate_phonetic_transliteration_variants(text)
        variants.update(phonetic_variants)

        return variants

    def _generate_phonetic_transliteration_variants(self, text: str) -> Set[str]:
        """Generation of phonetic transliteration variants"""
        variants = set()

        # Replace similar sounds
        phonetic_replacements = {
            "zh": ["j", "g", "z"],
            "kh": ["h", "ch", "x", "q"],
            "ts": ["tz", "c", "z"],
            "ch": ["tch", "cz", "tsch"],
            "sh": ["sch", "sz", "s"],
            "yu": ["iu", "u", "y"],
            "ya": ["ia", "a", "ja"],
        }

        # Apply phonetic replacements to the base transliteration
        base_translit = self._transliterate_cyrillic_to_latin(text, "ICAO")

        for pattern, alternatives in phonetic_replacements.items():
            if pattern in base_translit.lower():
                for alt in alternatives:
                    if alt != pattern:
                        variant = base_translit.lower().replace(pattern, alt)
                        variants.add(variant)

        return variants

    def _transliterate_latin_to_cyrillic(self, text: str) -> str:
        """Transliteration of Latin to Cyrillic"""
        result = ""
        i = 0
        while i < len(text):
            # Check for two-character patterns
            if i < len(text) - 1:
                two_char = text[i : i + 2].lower()
                if two_char in self.latin_to_cyrillic:
                    result += self.latin_to_cyrillic[two_char]
                    i += 2
                    continue

            # Check for single-character patterns
            char = text[i].lower()
            if char in self.latin_to_cyrillic:
                result += self.latin_to_cyrillic[char]
            else:
                result += text[i]
            i += 1

        return result

    def generate_variants_batch(
        self,
        texts: List[str],
        language: str = "auto",
        include_transliteration: bool = True,
        include_phonetic: bool = True,
        include_abbreviations: bool = True,
        max_variants: int = 20,
    ) -> List[Dict]:
        """Batch generation of variants"""
        results = []
        for text in texts:
            result = self.generate_variants(
                text=text,
                language=language,
                include_transliteration=include_transliteration,
                include_phonetic=include_phonetic,
                include_abbreviations=include_abbreviations,
                max_variants=max_variants,
            )
            results.append(result)
        return results

    def get_similarity_score(self, text1: str, text2: str) -> float:
        """Calculation of similarity between texts"""
        # Simple similarity algorithm based on common characters
        if text1 == text2:
            return 1.0

        # Normalize texts
        norm1 = self._normalize_for_comparison(text1)
        norm2 = self._normalize_for_comparison(text2)

        if norm1 == norm2:
            return 0.9

        # Calculate similarity
        common_chars = set(norm1) & set(norm2)
        total_chars = set(norm1) | set(norm2)

        if not total_chars:
            return 0.0

        return len(common_chars) / len(total_chars)

    def _normalize_for_comparison(self, text: str) -> str:
        """Normalization of text for comparison"""
        # Convert to lowercase
        text = text.lower()

        # Remove spaces and punctuation
        text = re.sub(r"[^\w]", "", text)

        # Normalize Unicode
        text = unicodedata.normalize("NFKC", text)

        return text

    def find_best_matches(
        self,
        query: str,
        candidates: List[str],
        threshold: float = 0.7,
        max_results: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Finds the best matching candidates for a given query text.

        Compares the query text against a list of candidates using similarity
        scoring and returns the best matches above the specified threshold.
        Results are sorted by similarity score in descending order.

        Args:
            query (str): The text to search for matches.
            candidates (List[str]): List of candidate texts to compare against.
            threshold (float, optional): Minimum similarity score (0.0 to 1.0).
                                      Defaults to 0.7.
            max_results (int, optional): Maximum number of results to return.
                                       Defaults to 10.

        Returns:
            List[Dict[str, Any]]: List of match dictionaries, each containing:
                - text: The candidate text that matched
                - score: Similarity score (0.0 to 1.0)
                - query: The original query text
        """
        matches = []

        for candidate in candidates:
            score = self.get_similarity_score(query, candidate)
            if score >= threshold:
                matches.append({"text": candidate, "score": score, "query": query})

        # Sort by score
        matches.sort(key=lambda x: x["score"], reverse=True)

        return matches[:max_results]

    def _generate_visual_similarity_variants(self, text: str) -> Set[str]:
        """Generation of visually similar variants"""
        variants = set()

        for char in text.lower():
            if char in self.visual_similarities:
                for similar_char in self.visual_similarities[char]:
                    new_text = text.lower().replace(char, similar_char)
                    if new_text != text.lower():
                        variants.add(new_text)

        return variants

    def _generate_typo_variants(self, text: str, max_typos: int = 3) -> Set[str]:
        """Generation of typo variants"""
        variants = set()

        if max_typos <= 0:
            return variants

        # Simple typos (replacement of adjacent keys)
        for i, char in enumerate(text.lower()):
            if char in self.typo_patterns:
                for typo_char in self.typo_patterns[char]:
                    new_text = text[:i] + typo_char + text[i + 1 :]
                    variants.add(new_text)

        # Add Cyrillic typos
        cyrillic_typo_patterns = {
            "а": ["я", "о", "е"],
            "е": ["ё", "и", "а"],
            "и": ["й", "ы", "е"],
            "о": ["а", "е", "у"],
            "у": ["ю", "о", "и"],
            "р": ["г", "п", "р"],
            "п": ["р", "н", "п"],
            "н": ["п", "м", "н"],
            "с": ["з", "х", "с"],
            "т": ["ь", "н", "т"],
        }

        for i, char in enumerate(text.lower()):
            if char in cyrillic_typo_patterns:
                for typo_char in cyrillic_typo_patterns[char]:
                    new_text = text[:i] + typo_char + text[i + 1 :]
                    variants.add(new_text)

        # Limit the number of variants
        return set(list(variants)[:max_typos])

    def _generate_automatic_morphological_variants(
        self, text: str, language: str
    ) -> Set[str]:
        """Automatic generation of morphological variants"""
        variants = set()

        # Simple variants
        variants.add(text.lower())
        variants.add(text.upper())
        variants.add(text.title())

        return variants

    def _generate_automatic_transliteration_variants(
        self, text: str, language: str
    ) -> Set[str]:
        """Automatic generation of transliterations"""
        return self._generate_transliteration_variants(text)

    def _generate_word_order_variants(self, text: str) -> Set[str]:
        """
        Generate word order variations for complex names.

        For example:
        - "Rinat Akhmetov" -> "Akhmetov Rinat"
        - "John Michael Smith" -> "Smith John Michael", "Michael John Smith", etc.

        This is especially useful for sanctions matching where names might be stored
        in different orders (given name first vs family name first).

        Args:
            text: Input text with potentially multiple words

        Returns:
            Set of word order variations
        """
        variants = set()

        if not text or not text.strip():
            return variants

        # Split into words, filtering out empty strings
        words = [word.strip() for word in text.split() if word.strip()]

        # Only generate variants for 2-4 words (typical name structures)
        # More than 4 words creates too many combinations and is unlikely to be a name
        if len(words) < 2 or len(words) > 4:
            return variants

        # Check if this looks like a name (capitalized words)
        if not all(self._is_likely_name_word(word) for word in words):
            return variants

        # Generate permutations based on number of words
        if len(words) == 2:
            # Simple case: "First Last" -> "Last First"
            variants.add(f"{words[1]} {words[0]}")

        elif len(words) == 3:
            # Three words: assume "First Middle Last" format
            # Common variations:
            # - "Last First Middle" (family name first)
            # - "First Last Middle" (move middle to end)
            # - "Middle First Last" (middle name first - less common)
            variants.add(f"{words[2]} {words[0]} {words[1]}")  # Last First Middle
            variants.add(f"{words[0]} {words[2]} {words[1]}")  # First Last Middle
            variants.add(f"{words[1]} {words[0]} {words[2]}")  # Middle First Last

        elif len(words) == 4:
            # Four words: more complex, limit to most common patterns
            # Assume "First Middle1 Middle2 Last" or "Title First Middle Last"
            # Most common: put last word first
            variants.add(f"{words[3]} {words[0]} {words[1]} {words[2]}")  # Last First Middle1 Middle2
            variants.add(f"{words[0]} {words[3]} {words[1]} {words[2]}")  # First Last Middle1 Middle2

        # Add variations with different separators
        original_variants = list(variants)
        for variant in original_variants:
            # Add comma-separated version (formal name format)
            comma_parts = variant.split(' ', 1)
            if len(comma_parts) == 2:
                variants.add(f"{comma_parts[0]}, {comma_parts[1]}")

        self.logger.debug(f"Generated {len(variants)} word order variants for '{text}'")
        return variants

    def _is_likely_name_word(self, word: str) -> bool:
        """
        Check if a word is likely part of a name.

        Args:
            word: Word to check

        Returns:
            True if word looks like part of a name
        """
        if len(word) < 2:
            return False

        # Names typically start with capital letter
        if not word[0].isupper():
            return False

        # Avoid common non-name words that might be capitalized
        non_name_words = {
            # English
            'THE', 'AND', 'OR', 'BUT', 'FOR', 'WITH', 'FROM', 'TO', 'AT', 'BY',
            'IN', 'ON', 'OF', 'AS', 'IS', 'WAS', 'ARE', 'WERE', 'BE', 'BEEN',
            'HAVE', 'HAS', 'HAD', 'DO', 'DOES', 'DID', 'WILL', 'WOULD', 'SHALL',
            # Russian
            'И', 'ИЛИ', 'НО', 'ДЛЯ', 'С', 'ОТ', 'ДО', 'НА', 'В', 'ПО', 'ЗА',
            'ПРИ', 'БЕЗ', 'ЧЕРЕЗ', 'ПОСЛЕ', 'ДА', 'НЕТ',
            # Ukrainian
            'І', 'АБО', 'АЛЕ', 'ДЛЯ', 'З', 'ВІД', 'ДО', 'НА', 'В', 'ПО', 'ЗА',
            'ПРИ', 'БЕЗ', 'ЧЕРЕЗ', 'ПІСЛЯ', 'ТАК', 'НІ',
            # Common organizational terms
            'LLC', 'INC', 'LTD', 'CORP', 'CO', 'ООО', 'ТОВ', 'ПАТ', 'БАНК'
        }

        if word.upper() in non_name_words:
            return False

        # Names typically contain only letters, apostrophes, hyphens
        if not re.match(r"^[a-zA-Zа-яА-ЯіїєґІЇЄҐ'-]+$", word):
            return False

        return True

    @lru_cache(maxsize=128)
    def _generate_diminutive_variants_cached(self, name: str, language: str) -> tuple:
        """Cached version that returns tuple for hashability"""
        diminutives = self._generate_diminutive_variants_impl(name, language)
        return tuple(sorted(diminutives))

    def _generate_diminutive_variants(self, name: str, language: str) -> Set[str]:
        """Public method that returns Set"""
        return set(self._generate_diminutive_variants_cached(name, language))

    def _generate_diminutive_variants_impl(self, name: str, language: str) -> Set[str]:
        """
        Generate diminutive variants for a given name.

        For example: "Александр" -> ["Саня", "Сашок", "Шура", "Санечка", "Сашенька"]

        Args:
            name: Full name to generate diminutives for
            language: Language of the name (ru/uk)

        Returns:
            Set of diminutive variants
        """
        diminutives = set()

        if not name or len(name) < 2:
            return diminutives

        # Import diminutives dictionaries
        try:
            from ...data.dicts.diminutives_extra import (
                EXTRA_DIMINUTIVES_RU,
                EXTRA_DIMINUTIVES_UK,
            )

            # Check both exact match and case-insensitive match
            diminutives_dict = {}
            if language == "ru" or language == "auto":
                diminutives_dict.update(EXTRA_DIMINUTIVES_RU)
            if language == "uk" or language == "auto":
                diminutives_dict.update(EXTRA_DIMINUTIVES_UK)

            # Direct match
            if name in diminutives_dict:
                diminutives.update(diminutives_dict[name])

            # Case-insensitive match
            name_lower = name.lower()
            name_title = name.title()
            for full_name, diminutives_list in diminutives_dict.items():
                if full_name.lower() == name_lower or full_name == name_title:
                    diminutives.update(diminutives_list)
                    break

            self.logger.debug(f"Generated {len(diminutives)} diminutives for '{name}'")

        except ImportError:
            self.logger.warning("EXTRA_DIMINUTIVES not available for diminutive generation")

        return diminutives

    def _generate_semantic_similar_names(self, text: str, language: str) -> Set[str]:
        """Generation of semantically similar names (placeholder)"""
        # Placeholder - in a real system, this would be the embedding logic
        return set()

    def get_variant_statistics(self) -> Dict[str, Any]:
        """Statistics of variants"""
        return {
            "morphological_analyzers": {
                "russian": self.ru_morph is not None,
                "ukrainian": self.uk_morph is not None,
            },
            "transliterator": self.transliterator is not None,
            "fallback_dictionaries": {
                lang: len(names) for lang, names in self.name_dictionaries.items()
            },
        }

    def _generate_advanced_phonetic_variants(self, text: str) -> Set[str]:
        """Advanced generation of phonetic variants"""
        variants = set()

        # Basic phonetic variants
        for pattern, alternatives in self.phonetic_patterns.items():
            if pattern in text.lower():
                for alt in alternatives:
                    if alt != pattern:
                        variant = text.lower().replace(pattern, alt)
                        variants.add(variant)

        # Optimized: Limited variants with missing vowels (only for short names)
        if len(text) <= 8:  # Only for short names to avoid "noise"
            vowels = "aeiouаеіоуяюєї"
            vowel_positions = [
                i for i, char in enumerate(text) if char.lower() in vowels
            ]

            # Limit to 3 variants with missing vowels
            for i in vowel_positions[:3]:
                variant = text[:i] + text[i + 1 :]
                if len(variant) >= 2:
                    variants.add(variant)

        # REMOVED: Adding vowels - created too much noise

        return variants

    def generate_comprehensive_variants(
        self, text: str, language: str = "auto"
    ) -> Dict[str, Set[str]]:
        """Complex generation of all types of variants"""
        all_variants = {
            "original": {text},
            "transliterations": set(),
            "visual_similarities": set(),
            "typo_variants": set(),
            "phonetic_variants": set(),
            "morphological_variants": set(),
        }

        # Transliterations
        if self._contains_cyrillic(text):
            all_variants["transliterations"] = self._generate_transliteration_variants(
                text
            )

        # Visual similarities
        all_variants["visual_similarities"] = self._generate_visual_similarity_variants(
            text
        )

        # Typos
        all_variants["typo_variants"] = self._generate_typo_variants(text)

        # Phonetic variants
        all_variants["phonetic_variants"] = self._generate_advanced_phonetic_variants(
            text
        )

        # Morphological variants
        if language == "uk":
            all_variants["morphological_variants"] = (
                self._generate_ukrainian_morphological_variants(text)
            )
        elif language == "ru":
            all_variants["morphological_variants"] = (
                self._generate_russian_morphological_variants(text)
            )

        # Total number of unique variants
        all_unique = set()
        for variant_set in all_variants.values():
            all_unique.update(variant_set)

        all_variants["total_unique"] = all_unique
        all_variants["count"] = len(all_unique)

        return all_variants

    def _prioritize_variants(
        self, variants: List[str], max_variants: int = 50
    ) -> List[str]:
        """
        Prioritization of variants based on their type and importance

        Args:
            variants: List of variants to prioritize
            max_variants: Maximum number of variants

        Returns:
            Prioritized list of variants
        """
        if not variants:
            return []

        if len(variants) <= max_variants:
            return variants

        # Classify variants by type
        morphological = []
        transliterations = []
        phonetic = []
        others = []

        for variant in variants:
            if self._is_morphological_variant(variant):
                morphological.append(variant)
            elif (
                self._is_transliteration_variant(variant)
                and variant not in morphological
            ):
                transliterations.append(variant)
            elif (
                self._is_phonetic_variant(variant)
                and variant not in morphological
                and variant not in transliterations
            ):
                phonetic.append(variant)
            elif (
                variant not in morphological
                and variant not in transliterations
                and variant not in phonetic
            ):
                others.append(variant)

        # Calculate the number of variants for each type based on weights
        total_weight = sum(VARIANT_SCORES.values())

        # Distribute variants proportionally to weights
        morphological_count = int(
            (VARIANT_SCORES["morphological"] / total_weight) * max_variants
        )
        transliteration_count = int(
            (VARIANT_SCORES["transliteration"] / total_weight) * max_variants
        )
        phonetic_count = int((VARIANT_SCORES["phonetic"] / total_weight) * max_variants)
        visual_count = int(
            (VARIANT_SCORES["visual_similarity"] / total_weight) * max_variants
        )
        typo_count = int((VARIANT_SCORES["typo"] / total_weight) * max_variants)
        regional_count = int((VARIANT_SCORES["regional"] / total_weight) * max_variants)
        fallback_count = int((VARIANT_SCORES["fallback"] / total_weight) * max_variants)

        # Collect by priority
        prioritized = []

        prioritized.extend(morphological[:morphological_count])
        prioritized.extend(transliterations[:transliteration_count])
        prioritized.extend(phonetic[:phonetic_count])
        prioritized.extend(others[:fallback_count])

        # Supplement to max_variants if needed
        remaining_slots = max_variants - len(prioritized)
        if remaining_slots > 0:
            remaining_variants = [v for v in variants if v not in prioritized]
            prioritized.extend(remaining_variants[:remaining_slots])

        return prioritized[:max_variants]

    def _is_morphological_variant(self, variant: str) -> bool:
        """Check if variant is morphological"""
        # Morphological variants usually contain Cyrillic and have different endings
        return bool(re.search(r"[а-яёіїєґА-ЯЁІЇЄҐ]", variant))

    def _is_transliteration_variant(self, variant: str) -> bool:
        """Check if variant is transliteration"""
        # Transliterations usually contain combinations like 'zh', 'kh', 'ch', 'sh'
        return bool(re.search(r"(zh|kh|ch|sh|ts|yu|ya)", variant.lower()))

    def _is_phonetic_variant(self, variant: str) -> bool:
        """Check if variant is phonetic"""
        # Phonetic variants have similar length and structure
        return len(variant) >= 3 and not self._contains_obvious_typos(variant)

    def _contains_obvious_typos(self, variant: str) -> bool:
        """Check for obvious typos (digits, repeated characters)"""
        return bool(re.search(r"[0-9]|(.)\1{2,}", variant))

    def analyze_names(
        self,
        text: str,
        language: str = "auto",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Analysis of names in text with generation of morphological variants

        Args:
            text: Text to analyze
            language: Text language
            options: Additional analysis options

        Returns:
            Dict with analysis results
        """
        if not text or not text.strip():
            return {}

        # Automatic language detection
        if language == "auto":
            language = self._detect_language(text)

        # Split text into potential names
        words = text.strip().split()
        analyzed_names = []

        for word in words:
            if len(word) >= 2 and word[0].isupper():  # Potential name
                name_analysis = self._analyze_single_name(word, language)
                if name_analysis:
                    analyzed_names.append(name_analysis)

        # Aggregate results
        all_variants = set([text])
        all_declensions = []
        all_diminutives = []
        all_transliterations = []
        all_forms = []

        for analysis in analyzed_names:
            all_declensions.extend(analysis.get("declensions", []))
            all_diminutives.extend(analysis.get("diminutives", []))
            all_transliterations.extend(analysis.get("transliterations", []))
            all_forms.extend(analysis.get("all_forms", []))

            # Add all variants to the overall set
            all_variants.update(analysis.get("declensions", []))
            all_variants.update(analysis.get("diminutives", []))
            all_variants.update(analysis.get("transliterations", []))
            all_variants.update(analysis.get("all_forms", []))

            normal_form = analysis.get("normal_form", "")
            if normal_form:
                all_variants.add(normal_form)

        return {
            "original_text": text,
            "language": language,
            "analyzed_names": analyzed_names,
            "declensions": list(set(all_declensions)),
            "diminutives": list(set(all_diminutives)),
            "transliterations": list(set(all_transliterations)),
            "all_forms": list(set(all_forms)),
            "variants": list(all_variants),
            "total_variants": len(all_variants),
        }

    def _analyze_single_name(
        self, name: str, language: str
    ) -> Optional[Dict[str, Any]]:
        """Analysis of a single name"""
        try:
            # Basic analysis
            analysis = {
                "name": name,
                "normal_form": name,
                "declensions": [],
                "diminutives": [],
                "transliterations": [],
                "all_forms": [],
            }

            # Morphological analysis
            if language == "ru" and self.ru_morph:
                morphological_variants = self._generate_russian_morphological_variants(
                    name
                )
                analysis["declensions"] = list(morphological_variants)
                analysis["all_forms"].extend(morphological_variants)
            elif language == "uk" and self.uk_morph:
                morphological_variants = (
                    self._generate_ukrainian_morphological_variants(name)
                )
                analysis["declensions"] = list(morphological_variants)
                analysis["all_forms"].extend(morphological_variants)

            # Diminutives generation
            diminutives = self._generate_diminutive_variants(name, language)
            analysis["diminutives"] = list(diminutives)
            analysis["all_forms"].extend(diminutives)

            # Transliterations
            if self._contains_cyrillic(name):
                transliterations = self._generate_transliteration_variants(name)
                analysis["transliterations"] = list(transliterations)

            return analysis

        except Exception as e:
            self.logger.warning(f"Failed to analyze name '{name}': {e}")
            return None

    def _basic_transliterate(self, text: str) -> str:
        """Basic Cyrillic to Latin transliteration"""
        return self._transliterate_cyrillic_to_latin(text, "ICAO")

    def _apply_transliteration_standard(self, text: str, standard: str) -> str:
        """Application of a specific transliteration standard"""
        return self._transliterate_cyrillic_to_latin(text, standard)

    def generate_visual_similarities(self, text: str) -> List[str]:
        """Generation of visually similar variants"""
        return list(self._generate_visual_similarity_variants(text))

    def generate_typo_variants(self, text: str, max_typos: int = 3) -> List[str]:
        """Generation of typo variants"""
        return list(self._generate_typo_variants(text, max_typos))

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculation of similarity between two texts"""
        if text1 == text2:
            return 1.0

        # Simple Levenshtein algorithm
        len1, len2 = len(text1), len(text2)
        if len1 == 0:
            return 0.0
        if len2 == 0:
            return 0.0

        # Create matrix
        matrix = [[0] * (len2 + 1) for _ in range(len1 + 1)]

        for i in range(len1 + 1):
            matrix[i][0] = i
        for j in range(len2 + 1):
            matrix[0][j] = j

        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                if text1[i - 1] == text2[j - 1]:
                    matrix[i][j] = matrix[i - 1][j - 1]
                else:
                    matrix[i][j] = min(
                        matrix[i - 1][j] + 1,  # deletion
                        matrix[i][j - 1] + 1,  # insertion
                        matrix[i - 1][j - 1] + 1,  # substitution
                    )

        max_len = max(len1, len2)
        return 1.0 - (matrix[len1][len2] / max_len)

    def generate_keyboard_layout_variants(self, text: str) -> List[str]:
        """Generation of variants with keyboard layout"""
        # QWERTY -> QWERTY-UK (Latin -> Cyrillic)
        qwerty_to_cyrillic = {
            "q": "й",
            "w": "ц",
            "e": "у",
            "r": "к",
            "t": "е",
            "y": "н",
            "u": "г",
            "i": "ш",
            "o": "щ",
            "p": "з",
            "a": "ф",
            "s": "і",
            "d": "в",
            "f": "а",
            "g": "п",
            "h": "р",
            "j": "о",
            "k": "л",
            "l": "д",
            "z": "я",
            "x": "ч",
            "c": "с",
            "v": "м",
            "b": "и",
            "n": "т",
            "m": "ь",
        }

        # Cyrillic -> Latin
        cyrillic_to_qwerty = {v: k for k, v in qwerty_to_cyrillic.items()}

        variants = []

        # Latin -> Cyrillic
        cyrillic_variant = []
        for char in text.lower():
            if char in qwerty_to_cyrillic:
                cyrillic_variant.append(qwerty_to_cyrillic[char])
            else:
                cyrillic_variant.append(char)
        variants.append("".join(cyrillic_variant))

        # Cyrillic -> Latin
        latin_variant = []
        for char in text.lower():
            if char in cyrillic_to_qwerty:
                latin_variant.append(cyrillic_to_qwerty[char])
            else:
                latin_variant.append(char)
        variants.append("".join(latin_variant))

        return variants

    def _get_morphological_variants(self, text: str, language: str) -> Set[str]:
        """Getting morphological variants"""
        # Simple implementation
        variants = set()
        variants.add(text.lower())
        variants.add(text.upper())
        variants.add(text.title())
        return variants

    def generate_comprehensive_variants(
        self, text: str, language: str
    ) -> Dict[str, Any]:
        """Generation of comprehensive variants"""
        result = {
            "transliterations": list(self._generate_transliteration_variants(text)),
            "phonetic_variants": list(self._generate_phonetic_variants(text)),
            "visual_similarities": list(
                self._generate_visual_similarity_variants(text)
            ),
            "typo_variants": list(self._generate_typo_variants(text)),
            "count": 0,
        }

        # Count total
        total_count = sum(
            len(variants) for variants in result.values() if isinstance(variants, list)
        )
        result["count"] = total_count

        return result

    def _detect_language(self, text: str) -> str:
        """Automatic language detection of text"""
        try:
            # Simple rules for language detection
            ukrainian_chars = set("іїєґІЇЄҐ")
            russian_chars = set("ёъыэЁЪЫЭ")

            uk_count = sum(1 for char in text if char in ukrainian_chars)
            ru_count = sum(1 for char in text if char in russian_chars)

            if uk_count > 0:
                return "uk"
            elif ru_count > 0:
                return "ru"
            elif any(ord(char) > 127 for char in text):
                # Cyrillic characters present, but not specific
                return "ru"  # Fallback to Russian
            else:
                return "en"
        except:
            return "en"  # Fallback to English

    def _generate_russian_morphological_variants(self, word: str) -> Set[str]:
        """Generation of Russian morphological variants"""
        variants = set()

        try:
            if self.ru_morph:
                parsed = self.ru_morph.parse(word)
                if parsed:
                    # Take the first analysis
                    morph = parsed[0]

                    # Generate all possible forms
                    for form in morph.lexeme:
                        variants.add(form.word)

        except Exception as e:
            self.logger.debug(
                f"Error generating Russian morphological variants for '{word}': {e}"
            )

        return variants

    def _generate_ukrainian_morphological_variants(self, word: str) -> Set[str]:
        """Generation of Ukrainian morphological variants"""
        variants = set()

        try:
            if hasattr(self.uk_morph, "get_all_forms"):
                # Use our own Ukrainian analyzer
                all_forms = self.uk_morph.get_all_forms(word)
                variants.update(all_forms)

        except Exception as e:
            self.logger.debug(
                f"Error generating Ukrainian morphological variants for '{word}': {e}"
            )

        return variants
