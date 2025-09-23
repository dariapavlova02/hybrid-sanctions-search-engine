#!/usr/bin/env python3
"""
High-Recall AC Pattern Generator

Generates comprehensive pattern sets for Aho-Corasick search across 4 tiers:
- Tier 0: Exact documents/IDs (100% precision)
- Tier 1: High-precision names/companies with safe variants
- Tier 2: Morphological and structured variants (medium recall)
- Tier 3: Aggressive broad recall with post-filtering required

Key principles:
- Canon first, then variants
- No single-word name patterns to avoid FP
- Max 1000 variants per entity
- Progressive accuracy degradation by tier
"""

import json
import re
import time
import unicodedata
from ..unicode.unicode_service import UnicodeService
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from functools import lru_cache

from ...utils.logging_config import get_logger


class PatternTier(Enum):
    """Pattern generation tiers with accuracy guarantees"""
    TIER_0 = 0  # Exact matches - 100% precision
    TIER_1 = 1  # High precision - safe variants
    TIER_2 = 2  # Medium recall - structured forms
    TIER_3 = 3  # Broad recall - aggressive patterns


class PatternType(Enum):
    """Types of patterns generated"""
    # Tier 0 types
    DOCUMENT_ID = "document_id"
    TAX_NUMBER = "tax_number"
    PASSPORT = "passport"
    IBAN = "iban"
    FULL_NAME_CANON = "full_name_canon"
    COMPANY_CANON = "company_canon"

    # Tier 1 types
    FULL_NAME_VARIANT = "full_name_variant"
    NICKNAME_EXPANSION = "nickname_expansion"
    GENDER_VARIANT = "gender_variant"
    APOSTROPHE_VARIANT = "apostrophe_variant"
    TRANSLITERATION = "transliteration"
    COMPANY_FORM_VARIANT = "company_form_variant"

    # Tier 2 types
    INITIALS_VARIANT = "initials_variant"
    HYPHEN_VARIANT = "hyphen_variant"
    COMPANY_NO_FORM = "company_no_form"
    MORPHOLOGICAL = "morphological"

    # Tier 3 types
    AGGRESSIVE_CAPS = "aggressive_caps"
    BROAD_MATCH = "broad_match"
    ABBREVIATION = "abbreviation"
    SURNAME_ONLY = "surname_only"
    SYLLABLE = "syllable"
    PARTIAL_MATCH = "partial_match"
    SINGLE_WORD = "single_word"
    AGGRESSIVE_MORPH = "aggressive_morph"


@dataclass
class PatternMetadata:
    """Metadata for generated patterns"""
    tier: PatternTier
    pattern_type: PatternType
    language: str
    confidence: float
    source_field: str
    hints: Dict[str, Any] = field(default_factory=dict)
    requires_context: bool = False
    min_length: int = 0


@dataclass
class GeneratedPattern:
    """Container for generated AC patterns"""
    pattern: str
    canonical: str
    metadata: PatternMetadata
    entity_id: str
    entity_type: str  # 'person' or 'company'


class LanguageDetector:
    """Simple language detection for pattern generation"""

    @staticmethod
    def detect_script(text: str) -> str:
        """Detect script type: cyrillic, latin, mixed"""
        if not text:
            return "unknown"

        cyrillic_count = sum(1 for c in text if '\u0400' <= c <= '\u04FF')
        latin_count = sum(1 for c in text if 'A' <= c <= 'Z' or 'a' <= c <= 'z')
        total_letters = cyrillic_count + latin_count

        if total_letters == 0:
            return "unknown"

        cyrillic_ratio = cyrillic_count / total_letters
        if cyrillic_ratio > 0.7:
            return "cyrillic"
        elif cyrillic_ratio < 0.3:
            return "latin"
        else:
            return "mixed"

    @staticmethod
    def detect_language(text: str) -> str:
        """Detect language: ru, uk, en"""
        script = LanguageDetector.detect_script(text)

        if script == "latin":
            return "en"
        elif script == "cyrillic":
            # Simple heuristics for RU vs UK
            uk_markers = ['ї', 'є', 'і', 'ґ', 'йо', 'ич', 'ич']
            if any(marker in text.lower() for marker in uk_markers):
                return "uk"
            return "ru"
        else:
            return "mixed"


class TextCanonicalizer:
    """Text canonicalization for AC patterns"""

    @staticmethod
    @lru_cache(maxsize=1000)
    def normalize_for_ac(text: str) -> str:
        """
        Canonical normalization for AC patterns:
        NFKC → apostrophe unification → hyphen normalization →
        space collapse → deglyph → trim
        """
        if not text:
            return ""

        # 1. NFKC normalization
        text = unicodedata.normalize('NFKC', text)

        # 2. Apostrophe unification
        text = re.sub(r'[''`]', "'", text)

        # 3. Hyphen normalization
        text = re.sub(r'[−–—−]', '-', text)

        # 4. Collapse spaces and other whitespace
        text = re.sub(r'\s+', ' ', text)

        # 5. Homoglyph normalization using UnicodeService
        unicode_service = UnicodeService()
        unicode_result = unicode_service.normalize_text(text, normalize_homoglyphs=True)
        text = unicode_result["normalized"]

        # 6. Trim
        return text.strip()

    @staticmethod
    def casefold_by_language(text: str, language: str) -> str:
        """Language-aware case folding"""
        if language in ['ru', 'uk']:
            # Cyrillic casefold
            return text.lower()
        else:
            # English casefold
            return text.casefold()


class DocumentPatternGenerator:
    """Generates Tier 0 document patterns (100% precision)"""

    def __init__(self):
        self.logger = get_logger(__name__)

    def generate_itn_patterns(self, itn: str) -> List[GeneratedPattern]:
        """Generate ІПН/ИНН patterns"""
        patterns = []
        if not itn or not re.match(r'\d{10,12}$', itn):
            return patterns

        # Canonical form
        canonical = TextCanonicalizer.normalize_for_ac(itn)
        metadata = PatternMetadata(
            tier=PatternTier.TIER_0,
            pattern_type=PatternType.TAX_NUMBER,
            language="numeric",
            confidence=1.0,
            source_field="itn"
        )

        patterns.append(GeneratedPattern(
            pattern=canonical,
            canonical=canonical,
            metadata=metadata,
            entity_id="",  # Will be set by caller
            entity_type="person"
        ))

        return patterns

    def generate_passport_patterns(self, passport: str) -> List[GeneratedPattern]:
        """Generate passport patterns with variants"""
        patterns = []
        if not passport:
            return patterns

        # Basic passport format: AA123456
        passport_match = re.match(r'([A-Za-z]{2})(\d{6})', passport.replace(' ', '').replace('-', ''))
        if not passport_match:
            return patterns

        letters, numbers = passport_match.groups()

        # Canonical form
        canonical = f"{letters.upper()}{numbers}"
        base_metadata = PatternMetadata(
            tier=PatternTier.TIER_0,
            pattern_type=PatternType.PASSPORT,
            language="mixed",
            confidence=1.0,
            source_field="passport"
        )

        # Generate variants
        variants = [
            canonical,  # AA123456
            f"{letters.upper()}-{numbers}",  # AA-123456
            f"{letters.upper()} {numbers}",  # AA 123456
            f"{letters.lower()}{numbers}",  # aa123456
        ]

        for variant in variants:
            patterns.append(GeneratedPattern(
                pattern=variant,
                canonical=canonical,
                metadata=base_metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def generate_iban_patterns(self, iban: str) -> List[GeneratedPattern]:
        """Generate IBAN patterns"""
        patterns = []
        if not iban:
            return patterns

        # Clean IBAN
        clean_iban = re.sub(r'\s+', '', iban.upper())
        if not re.match(r'UA\d{2}[A-Z0-9]{25}$', clean_iban):
            return patterns

        canonical = clean_iban
        metadata = PatternMetadata(
            tier=PatternTier.TIER_0,
            pattern_type=PatternType.IBAN,
            language="mixed",
            confidence=1.0,
            source_field="iban"
        )

        # Generate space variants
        variants = [
            canonical,  # Solid
            ' '.join([canonical[i:i+4] for i in range(0, len(canonical), 4)]),  # Spaced every 4
        ]

        for variant in variants:
            patterns.append(GeneratedPattern(
                pattern=variant,
                canonical=canonical,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns


class NamePatternGenerator:
    """Generates name patterns across tiers"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Stop words by language
        self.stop_words = {
            "ru": {"и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о"},
            "uk": {"і", "в", "на", "з", "по", "для", "від", "до", "із", "к", "о"},
            "en": {"and", "in", "on", "with", "for", "from", "to", "of", "at"},
        }

        # Nickname dictionaries (implement full dictionaries)
        self.nicknames = {
            "en": {
                "William": ["Bill", "Billy", "Will"],
                "Robert": ["Bob", "Bobby", "Rob"],
                "Elizabeth": ["Liz", "Beth", "Betty"],
                "Alexander": ["Alex", "Al"],
            },
            "ru": {
                "Александр": ["Саша", "Шура", "Алекс"],
                "Владимир": ["Володя", "Вова"],
                "Екатерина": ["Катя", "Катерина"],
                "Дмитрий": ["Дима", "Митя"],
            },
            "uk": {
                "Олександр": ["Саша", "Олесь"],
                "Володимир": ["Володя", "Вова"],
                "Катерина": ["Катя", "Катруся"],
                "Петро": ["Петрик", "Петя"],
            }
        }

        # Gender mapping for surnames
        self.gender_variants = {
            "ru": [
                (r'(.+)ов$', r'\1ова'),  # Иванов -> Иванова
                (r'(.+)ев$', r'\1ева'),  # Лебедев -> Лебедева
                (r'(.+)ин$', r'\1ина'),  # Пушкин -> Пушкина
                (r'(.+)ский$', r'\1ская'),  # Достоевский -> Достоевская
            ],
            "uk": [
                (r'(.+)ський$', r'\1ська'),  # Левицький -> Левицька
                (r'(.+)енко$', r'\1енко'),  # Шевченко (no change)
                (r'(.+)ук$', r'\1ук'),  # Ковалюк (no change)
            ]
        }

    def is_full_name(self, name: str) -> bool:
        """Check if name has at least 2 words (avoid single names)"""
        words = name.strip().split()
        return len(words) >= 2

    def generate_tier_0_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 0: Exact canonical names only"""
        patterns = []
        if not self.is_full_name(name):
            return patterns

        canonical = TextCanonicalizer.normalize_for_ac(name)
        metadata = PatternMetadata(
            tier=PatternTier.TIER_0,
            pattern_type=PatternType.FULL_NAME_CANON,
            language=language,
            confidence=1.0,
            source_field="name"
        )

        patterns.append(GeneratedPattern(
            pattern=canonical,
            canonical=canonical,
            metadata=metadata,
            entity_id="",
            entity_type="person"
        ))

        return patterns

    def generate_tier_1_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 1: Safe high-precision variants"""
        patterns = []
        if not self.is_full_name(name):
            return patterns

        canonical = TextCanonicalizer.normalize_for_ac(name)
        words = canonical.split()

        # 1. Nickname expansions
        patterns.extend(self._generate_nickname_variants(words, language))

        # 2. Gender variants for surnames
        patterns.extend(self._generate_gender_variants(words, language))

        # 3. Apostrophe variants
        patterns.extend(self._generate_apostrophe_variants(canonical, language))

        # 4. Simple transliteration (if mixed script)
        if language == "mixed":
            patterns.extend(self._generate_transliteration_variants(canonical))

        # 5. Case variants (different capitalizations)
        patterns.extend(self._generate_case_variants(canonical, language))

        # 6. Simple word reordering variants (safe swaps)
        patterns.extend(self._generate_word_order_variants(words, language))

        # 7. Basic punctuation variants
        patterns.extend(self._generate_punctuation_variants(canonical, language))

        # 8. Safe letter variants (common substitutions)
        patterns.extend(self._generate_safe_letter_variants(canonical, language))

        return patterns

    def generate_tier_2_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 2: Structured forms and morphological variants"""
        patterns = []
        if not self.is_full_name(name):
            return patterns

        canonical = TextCanonicalizer.normalize_for_ac(name)
        words = canonical.split()

        # 1. Initial variants (if 3+ words suggesting middle name/patronymic)
        if len(words) >= 3:
            patterns.extend(self._generate_initial_variants(words, language))

        # 2. Hyphen variants
        patterns.extend(self._generate_hyphen_variants(words, language))

        # 3. Morphological variants (basic cases)
        patterns.extend(self._generate_morphological_variants(words, language))

        return patterns

    def generate_tier_3_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 3: Aggressive broad recall patterns"""
        patterns = []

        canonical = TextCanonicalizer.normalize_for_ac(name)
        words = canonical.split()

        # 1. Aggressive capitalized sequences (1-4 words, remove min length restriction)
        patterns.extend(self._generate_aggressive_caps_patterns(words, language))

        # 2. Abbreviations and acronyms
        patterns.extend(self._generate_abbreviation_patterns(words, language))

        # 3. Single surname patterns (only with context requirement)
        if len(words) >= 2:
            patterns.extend(self._generate_single_surname_patterns(words, language))

        # 4. Syllable patterns for long words
        patterns.extend(self._generate_syllable_patterns(words, language))

        # 5. Partial word matches (substrings)
        patterns.extend(self._generate_partial_word_patterns(words, language))

        # 6. All single words (with context requirement)
        patterns.extend(self._generate_single_word_patterns(words, language))

        # 7. Aggressive morphological expansions (if Cyrillic)
        if language in ["ru", "uk"]:
            patterns.extend(self._generate_aggressive_morphological_patterns(words, language))

        return patterns

    def _generate_nickname_variants(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate nickname expansion variants"""
        patterns = []
        nicknames_dict = self.nicknames.get(language, {})

        for i, word in enumerate(words):
            for full_name, nicknames in nicknames_dict.items():
                if word in nicknames:
                    # Replace nickname with full name
                    new_words = words.copy()
                    new_words[i] = full_name
                    pattern = " ".join(new_words)

                    metadata = PatternMetadata(
                        tier=PatternTier.TIER_1,
                        pattern_type=PatternType.NICKNAME_EXPANSION,
                        language=language,
                        confidence=0.9,
                        source_field="name",
                        hints={"original_nickname": word, "expansion": full_name}
                    )

                    patterns.append(GeneratedPattern(
                        pattern=pattern,
                        canonical=" ".join(words),
                        metadata=metadata,
                        entity_id="",
                        entity_type="person"
                    ))

        return patterns

    def _generate_gender_variants(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate gender variants for surnames"""
        patterns = []
        if language not in self.gender_variants:
            return patterns

        # Typically the last word is surname
        surname = words[-1]

        # Skip patronymics (отчества) - they don't need gender variants
        if self._is_patronymic(surname):
            return patterns

        # Skip mixed script words that cause regex errors
        if self._has_mixed_script(surname):
            return patterns

        variants = self.gender_variants[language]

        for pattern_male, pattern_female in variants:
            try:
                # Male to female
                match_result = self._safe_regex_match(pattern_male, surname)
                if match_result:
                    female_surname = self._safe_regex_sub(pattern_male, pattern_female, surname)
                    if female_surname and female_surname != surname:  # Only if actually changed
                        new_words = words[:-1] + [female_surname]

                        metadata = PatternMetadata(
                            tier=PatternTier.TIER_1,
                            pattern_type=PatternType.GENDER_VARIANT,
                            language=language,
                            confidence=0.85,
                            source_field="name",
                            hints={"gender_change": "male_to_female"}
                        )

                        patterns.append(GeneratedPattern(
                            pattern=" ".join(new_words),
                            canonical=" ".join(words),
                            metadata=metadata,
                            entity_id="",
                            entity_type="person"
                        ))

                # Female to male
                match_result = self._safe_regex_match(pattern_female, surname)
                if match_result:
                    male_surname = self._safe_regex_sub(pattern_female, pattern_male, surname)
                    if male_surname and male_surname != surname:  # Only if actually changed
                        new_words = words[:-1] + [male_surname]

                        metadata = PatternMetadata(
                            tier=PatternTier.TIER_1,
                            pattern_type=PatternType.GENDER_VARIANT,
                            language=language,
                            confidence=0.85,
                            source_field="name",
                            hints={"gender_change": "female_to_male"}
                        )

                        patterns.append(GeneratedPattern(
                            pattern=" ".join(new_words),
                            canonical=" ".join(words),
                            metadata=metadata,
                            entity_id="",
                            entity_type="person"
                        ))

            except Exception as e:
                self.logger.warning(f"Error in gender variants for {surname}: {e}")
                continue

        return patterns

    def _is_patronymic(self, word: str) -> bool:
        """Check if word is a patronymic (отчество)"""
        # Common patronymic endings - handle mixed scripts
        patronymic_patterns = [
            # Pure Cyrillic
            r'.*ович$', r'.*евич$', r'.*івич$',  # male patronymics
            r'.*овна$', r'.*евна$', r'.*івна$',  # female patronymics
            # Mixed script variants (common in corrupted data)
            r'.*o[в]ич$', r'.*e[в]ич$', r'.*і[в]ич$',  # latin 'o', 'e' + cyrillic
            r'.*o[в]нa$', r'.*e[в]нa$', r'.*і[в]нa$',  # mixed female forms
            r'.*ільєвнa$', r'.*[оо][в]іч$', r'.*[еe][в]іч$',  # other mixed combinations
        ]

        for pattern in patronymic_patterns:
            if re.search(pattern, word, re.IGNORECASE):
                return True
        return False

    def _has_mixed_script(self, word: str) -> bool:
        """Check if word contains both Cyrillic and Latin characters"""
        has_cyrillic = bool(re.search(r'[а-яёіїєґ]', word, re.IGNORECASE))
        has_latin = bool(re.search(r'[a-z]', word, re.IGNORECASE))
        return has_cyrillic and has_latin

    def _safe_regex_match(self, pattern: str, text: str) -> bool:
        """Safely check if regex pattern matches text"""
        try:
            return bool(re.match(pattern, text))
        except re.error:
            return False

    def _safe_regex_sub(self, pattern: str, replacement: str, text: str) -> str:
        """Safely apply regex substitution with group validation"""
        try:
            # First check if pattern matches
            if not re.match(pattern, text):
                return None

            # Validate that replacement references valid groups
            match = re.match(pattern, text)
            if not match:
                return None

            # Check if replacement string references groups that exist
            try:
                # Test the substitution on a match
                result = re.sub(pattern, replacement, text)
                return result
            except re.error:
                # If substitution fails, return None
                return None
        except Exception:
            return None

    def _generate_apostrophe_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate apostrophe variants"""
        patterns = []

        if "'" in name:
            # Generate variant with typographic apostrophe
            variant = name.replace("'", "'")

            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.APOSTROPHE_VARIANT,
                language=language,
                confidence=0.95,
                source_field="name",
                hints={"apostrophe_variant": True}
            )

            patterns.append(GeneratedPattern(
                pattern=variant,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def _generate_transliteration_variants(self, name: str) -> List[GeneratedPattern]:
        """Basic transliteration variants for mixed scripts"""
        patterns = []

        # Simple cyrillic to latin mapping (extend as needed)
        translit_map = {
            'а': 'a', 'е': 'e', 'и': 'i', 'о': 'o', 'у': 'u', 'ы': 'y',
            'э': 'e', 'ю': 'yu', 'я': 'ya',
            'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ж': 'zh', 'з': 'z',
            'к': 'k', 'л': 'l', 'м': 'm', 'н': 'n', 'п': 'p', 'р': 'r',
            'с': 's', 'т': 't', 'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch',
            'ш': 'sh', 'щ': 'shch', 'ь': '', 'ъ': '', 'ё': 'yo'
        }

        transliterated = ""
        for char in name.lower():
            transliterated += translit_map.get(char, char)

        # Capitalize appropriately
        words = transliterated.split()
        transliterated = " ".join(word.capitalize() for word in words)

        if transliterated != name:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.TRANSLITERATION,
                language="mixed",
                confidence=0.8,
                source_field="name",
                hints={"transliteration": True}
            )

            patterns.append(GeneratedPattern(
                pattern=transliterated,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def _generate_case_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate different case variants"""
        patterns = []

        # Generate UPPERCASE variant
        upper_variant = name.upper()
        if upper_variant != name:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.FULL_NAME_VARIANT,
                language=language,
                confidence=0.9,
                source_field="name",
                hints={"case_variant": "upper"}
            )
            patterns.append(GeneratedPattern(
                pattern=upper_variant,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        # Generate lowercase variant
        lower_variant = name.lower()
        if lower_variant != name:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.FULL_NAME_VARIANT,
                language=language,
                confidence=0.9,
                source_field="name",
                hints={"case_variant": "lower"}
            )
            patterns.append(GeneratedPattern(
                pattern=lower_variant,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        # Generate Title Case variant (if different from current)
        title_variant = name.title()
        if title_variant != name:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.FULL_NAME_VARIANT,
                language=language,
                confidence=0.85,
                source_field="name",
                hints={"case_variant": "title"}
            )
            patterns.append(GeneratedPattern(
                pattern=title_variant,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def _generate_word_order_variants(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate safe word order variants"""
        patterns = []

        if len(words) == 2:
            # Swap first and last name
            swapped = f"{words[1]} {words[0]}"
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.FULL_NAME_VARIANT,
                language=language,
                confidence=0.8,
                source_field="name",
                hints={"word_order": "surname_first"}
            )
            patterns.append(GeneratedPattern(
                pattern=swapped,
                canonical=" ".join(words),
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        elif len(words) == 3:
            # Generate surname-first variants
            given, middle, surname = words
            variants = [
                f"{surname} {given} {middle}",  # Surname Given Middle
                f"{surname}, {given} {middle}",  # Surname, Given Middle
            ]

            for variant in variants:
                metadata = PatternMetadata(
                    tier=PatternTier.TIER_1,
                    pattern_type=PatternType.FULL_NAME_VARIANT,
                    language=language,
                    confidence=0.75,
                    source_field="name",
                    hints={"word_order": "surname_first_formal"}
                )
                patterns.append(GeneratedPattern(
                    pattern=variant,
                    canonical=" ".join(words),
                    metadata=metadata,
                    entity_id="",
                    entity_type="person"
                ))

        return patterns

    def _generate_punctuation_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate punctuation variants"""
        patterns = []

        # Remove all punctuation
        no_punct = re.sub(r'[.,\-\']', '', name)
        if no_punct != name and no_punct.strip():
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.FULL_NAME_VARIANT,
                language=language,
                confidence=0.85,
                source_field="name",
                hints={"punctuation": "removed"}
            )
            patterns.append(GeneratedPattern(
                pattern=no_punct,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        # Add periods after initials (if not already present)
        period_variant = re.sub(r'\b([A-ZА-ЯЁ])\b', r'\1.', name)
        if period_variant != name:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.FULL_NAME_VARIANT,
                language=language,
                confidence=0.8,
                source_field="name",
                hints={"punctuation": "periods_added"}
            )
            patterns.append(GeneratedPattern(
                pattern=period_variant,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def _generate_safe_letter_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate safe letter substitution variants"""
        patterns = []

        # Common safe substitutions (homoglyphs and typos)
        safe_substitutions = [
            ('ё', 'е'),  # Russian yo -> e
            ('і', 'i'),  # Ukrainian i -> Latin i
            ('Ё', 'Е'),  # Russian YO -> YE
            ('І', 'I'),  # Ukrainian I -> Latin I
        ]

        for original_char, replacement_char in safe_substitutions:
            if original_char in name:
                variant = name.replace(original_char, replacement_char)
                if variant != name:
                    metadata = PatternMetadata(
                        tier=PatternTier.TIER_1,
                        pattern_type=PatternType.FULL_NAME_VARIANT,
                        language=language,
                        confidence=0.85,
                        source_field="name",
                        hints={"letter_variant": f"{original_char}→{replacement_char}"}
                    )
                    patterns.append(GeneratedPattern(
                        pattern=variant,
                        canonical=name,
                        metadata=metadata,
                        entity_id="",
                        entity_type="person"
                    ))

        return patterns

    def _generate_initial_variants(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate initial variants for names with middle names/patronymics"""
        patterns = []

        if len(words) < 3:
            return patterns

        # Assume: Given Middle Surname or Given Patronymic Surname
        given, middle, surname = words[0], words[1], words[2]

        # Generate variants
        variants = [
            f"{given} {middle[0]}. {surname}",  # Given M. Surname
            f"{given[0]}. {middle[0]}. {surname}",  # G. M. Surname
            f"{surname} {given[0]}. {middle[0]}.",  # Surname G. M.
            f"{surname} {given[0]}.",  # Surname G.
        ]

        for variant in variants:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_2,
                pattern_type=PatternType.INITIALS_VARIANT,
                language=language,
                confidence=0.7,
                source_field="name",
                hints={"initials": True},
                requires_context=True  # Initials need context confirmation
            )

            patterns.append(GeneratedPattern(
                pattern=variant,
                canonical=" ".join(words),
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def _generate_hyphen_variants(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate hyphen connection/separation variants"""
        patterns = []

        if len(words) < 2:
            return patterns

        # For compound surnames or names
        original = " ".join(words)

        # Generate hyphenated and concatenated variants
        variants = [
            "-".join(words),  # Word-Word-Word
            "".join(words),   # WordWordWord
        ]

        for variant in variants:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_2,
                pattern_type=PatternType.HYPHEN_VARIANT,
                language=language,
                confidence=0.6,
                source_field="name",
                hints={"hyphen_variant": True}
            )

            patterns.append(GeneratedPattern(
                pattern=variant,
                canonical=original,
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def _generate_morphological_variants(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate basic morphological case variants"""
        patterns = []

        if language not in ['ru', 'uk']:
            return patterns

        # Basic case endings for Russian/Ukrainian
        case_patterns = {
            'ru': [
                (r'(.+)ь$', r'\1я'),     # -ь → -я (genitive)
                (r'(.+)а$', r'\1у'),     # -а → -у (dative)
                (r'(.+)ий$', r'\1ого'),  # -ий → -ого (genitive)
            ],
            'uk': [
                (r'(.+)енко$', r'\1енка'),  # -енко → -енка (genitive)
                (r'(.+)ич$', r'\1ича'),     # -ич → -ича (genitive)
            ]
        }

        patterns_list = case_patterns.get(language, [])
        original = " ".join(words)

        for pattern, replacement in patterns_list:
            variant_words = []
            for word in words:
                if re.match(pattern, word):
                    variant_words.append(re.sub(pattern, replacement, word))
                else:
                    variant_words.append(word)

            variant = " ".join(variant_words)
            if variant != original:
                metadata = PatternMetadata(
                    tier=PatternTier.TIER_2,
                    pattern_type=PatternType.MORPHOLOGICAL,
                    language=language,
                    confidence=0.65,
                    source_field="name",
                    hints={"morphological": True}
                )

                patterns.append(GeneratedPattern(
                    pattern=variant,
                    canonical=original,
                    metadata=metadata,
                    entity_id="",
                    entity_type="person"
                ))

        return patterns

    def _generate_aggressive_caps_patterns(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate aggressive capitalized patterns for Tier 3"""
        patterns = []

        # Check if words are not stop words
        stop_words = self.stop_words.get(language, set())
        clean_words = [word for word in words if word.lower() not in stop_words]

        # Generate broad match patterns - 2+ words for caps sequences
        for i in range(len(clean_words)):
            for j in range(i + 2, min(i + 5, len(clean_words) + 1)):  # 2-4 word sequences
                sequence = clean_words[i:j]
                pattern = " ".join(sequence)

                # Confidence based on sequence length
                confidence = 0.3

                metadata = PatternMetadata(
                    tier=PatternTier.TIER_3,
                    pattern_type=PatternType.AGGRESSIVE_CAPS,
                    language=language,
                    confidence=confidence,
                    source_field="name",
                    hints={"aggressive_match": True, "word_count": len(sequence)},
                    requires_context=True
                )

                patterns.append(GeneratedPattern(
                    pattern=pattern,
                    canonical=" ".join(words),
                    metadata=metadata,
                    entity_id="",
                    entity_type="person"
                ))

        return patterns

    def _generate_abbreviation_patterns(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate abbreviation patterns"""
        patterns = []

        # Generate initials-based abbreviations
        if len(words) >= 2:
            # Simple initials
            initials = "".join(word[0].upper() for word in words if word)
            if 2 <= len(initials) <= 6:  # Reasonable abbreviation length

                metadata = PatternMetadata(
                    tier=PatternTier.TIER_3,
                    pattern_type=PatternType.ABBREVIATION,
                    language=language,
                    confidence=0.25,
                    source_field="name",
                    hints={"abbreviation_type": "initials"},
                    requires_context=True
                )

                patterns.append(GeneratedPattern(
                    pattern=initials,
                    canonical=" ".join(words),
                    metadata=metadata,
                    entity_id="",
                    entity_type="person"
                ))

        return patterns

    def _generate_single_surname_patterns(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate single surname patterns with strict context requirements"""
        patterns = []

        # Only for surnames that are long enough and look surname-like
        surname = words[-1]  # Assume last word is surname

        if len(surname) >= 4:  # Minimum length to avoid common words
            metadata = PatternMetadata(
                tier=PatternTier.TIER_3,
                pattern_type=PatternType.SURNAME_ONLY,
                language=language,
                confidence=0.2,
                source_field="name",
                hints={"single_surname": True, "requires_payment_context": True},
                requires_context=True
            )

            patterns.append(GeneratedPattern(
                pattern=surname,
                canonical=" ".join(words),
                metadata=metadata,
                entity_id="",
                entity_type="person"
            ))

        return patterns

    def _generate_syllable_patterns(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate syllable-based patterns for long words"""
        patterns = []

        for word in words:
            if len(word) >= 6:  # Only for long words
                # Generate prefix patterns (first 3-4 characters)
                for length in [3, 4]:
                    if len(word) > length:
                        prefix = word[:length]
                        metadata = PatternMetadata(
                            tier=PatternTier.TIER_3,
                            pattern_type=PatternType.SYLLABLE,
                            language=language,
                            confidence=0.2,
                            source_field="name",
                            hints={"syllable_type": "prefix", "from_word": word},
                            requires_context=True
                        )
                        patterns.append(GeneratedPattern(
                            pattern=prefix,
                            canonical=" ".join(words),
                            metadata=metadata,
                            entity_id="",
                            entity_type="person"
                        ))

                # Generate suffix patterns (last 3-4 characters)
                for length in [3, 4]:
                    if len(word) > length:
                        suffix = word[-length:]
                        metadata = PatternMetadata(
                            tier=PatternTier.TIER_3,
                            pattern_type=PatternType.SYLLABLE,
                            language=language,
                            confidence=0.15,
                            source_field="name",
                            hints={"syllable_type": "suffix", "from_word": word},
                            requires_context=True
                        )
                        patterns.append(GeneratedPattern(
                            pattern=suffix,
                            canonical=" ".join(words),
                            metadata=metadata,
                            entity_id="",
                            entity_type="person"
                        ))

        return patterns

    def _generate_partial_word_patterns(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate partial word patterns (substrings)"""
        patterns = []

        for word in words:
            if len(word) >= 5:  # Only for reasonably long words
                # Generate middle substrings
                for start in range(1, len(word) - 2):
                    for end in range(start + 3, min(start + 6, len(word))):
                        substring = word[start:end]
                        if len(substring) >= 3:
                            metadata = PatternMetadata(
                                tier=PatternTier.TIER_3,
                                pattern_type=PatternType.PARTIAL_MATCH,
                                language=language,
                                confidence=0.1,
                                source_field="name",
                                hints={"partial_type": "substring", "from_word": word},
                                requires_context=True
                            )
                            patterns.append(GeneratedPattern(
                                pattern=substring,
                                canonical=" ".join(words),
                                metadata=metadata,
                                entity_id="",
                                entity_type="person"
                            ))

        return patterns

    def _generate_single_word_patterns(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate single word patterns with strict context requirements"""
        patterns = []

        stop_words = self.stop_words.get(language, set())

        for word in words:
            # Only long, non-stop words
            if len(word) >= 4 and word.lower() not in stop_words:
                metadata = PatternMetadata(
                    tier=PatternTier.TIER_3,
                    pattern_type=PatternType.SINGLE_WORD,
                    language=language,
                    confidence=0.25,
                    source_field="name",
                    hints={"single_word": True, "requires_payment_context": True},
                    requires_context=True
                )
                patterns.append(GeneratedPattern(
                    pattern=word,
                    canonical=" ".join(words),
                    metadata=metadata,
                    entity_id="",
                    entity_type="person"
                ))

        return patterns

    def _generate_aggressive_morphological_patterns(self, words: List[str], language: str) -> List[GeneratedPattern]:
        """Generate aggressive morphological patterns for Cyrillic languages"""
        patterns = []

        if language not in ["ru", "uk"]:
            return patterns

        # Aggressive case endings for each word
        aggressive_endings = {
            "ru": ["а", "ы", "е", "ом", "ой", "ым", "ах", "ами", "у", "и"],
            "uk": ["а", "и", "е", "ом", "ою", "им", "ах", "ами", "у", "і", "ій"]
        }

        endings = aggressive_endings.get(language, [])

        for word in words:
            if len(word) >= 4:  # Only for reasonable length words
                # Generate word with different endings
                for ending in endings:
                    # Try to replace last 1-2 characters with new ending
                    for cut_length in [1, 2]:
                        if len(word) > cut_length:
                            stem = word[:-cut_length]
                            new_word = stem + ending

                            if new_word != word:  # Only if actually different
                                # Replace the word in context
                                new_words = []
                                for w in words:
                                    if w == word:
                                        new_words.append(new_word)
                                    else:
                                        new_words.append(w)

                                metadata = PatternMetadata(
                                    tier=PatternTier.TIER_3,
                                    pattern_type=PatternType.AGGRESSIVE_MORPH,
                                    language=language,
                                    confidence=0.2,
                                    source_field="name",
                                    hints={"morphological_expansion": True, "ending": ending},
                                    requires_context=True
                                )
                                patterns.append(GeneratedPattern(
                                    pattern=" ".join(new_words),
                                    canonical=" ".join(words),
                                    metadata=metadata,
                                    entity_id="",
                                    entity_type="person"
                                ))

        return patterns


class CompanyPatternGenerator:
    """Generates company patterns across tiers"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Legal forms mapping
        self.legal_forms = {
            "ru": ["ООО", "ЗАО", "ОАО", "ИП", "ТОВ"],
            "uk": ["ТОВ", "ПП", "ФОП", "ПАТ", "ПрАТ"],
            "en": ["LLC", "Ltd", "Corp", "Inc", "Co"],
        }

        # Form synonyms
        self.form_synonyms = {
            "LLC": ["Ltd", "Limited"],
            "ООО": ["Общество с ограниченной ответственностью"],
            "ТОВ": ["Товариство з обмеженою відповідальністю"],
        }

    def generate_tier_0_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 0: Exact company names with forms"""
        patterns = []

        canonical = TextCanonicalizer.normalize_for_ac(name)

        # Check for quoted company names with forms
        quoted_match = re.search(r'([А-Яа-яA-Za-z\s]+)\s*["""«»]\s*([^"""«»]+)\s*["""«»]', name)
        if quoted_match:
            form, company_name = quoted_match.groups()

            # Generate form + "name" and "name" + form variants
            variants = [
                f'{form} "{company_name}"',
                f'"{company_name}" {form}',
            ]

            for variant in variants:
                metadata = PatternMetadata(
                    tier=PatternTier.TIER_0,
                    pattern_type=PatternType.COMPANY_CANON,
                    language=language,
                    confidence=1.0,
                    source_field="name"
                )

                patterns.append(GeneratedPattern(
                    pattern=variant,
                    canonical=canonical,
                    metadata=metadata,
                    entity_id="",
                    entity_type="company"
                ))
        else:
            # Simple canonical company name
            metadata = PatternMetadata(
                tier=PatternTier.TIER_0,
                pattern_type=PatternType.COMPANY_CANON,
                language=language,
                confidence=1.0,
                source_field="name"
            )

            patterns.append(GeneratedPattern(
                pattern=canonical,
                canonical=canonical,
                metadata=metadata,
                entity_id="",
                entity_type="company"
            ))

        return patterns

    def generate_tier_1_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 1: Safe company variants with forms"""
        patterns = []

        canonical = TextCanonicalizer.normalize_for_ac(name)

        # 1. Quote variants
        patterns.extend(self._generate_quote_variants(canonical, language))

        # 2. Case variants for company names
        patterns.extend(self._generate_company_case_variants(canonical, language))

        # 3. Alternative legal form positions
        patterns.extend(self._generate_form_position_variants(canonical, language))

        # 4. Punctuation variants for companies
        patterns.extend(self._generate_company_punctuation_variants(canonical, language))

        return patterns

    def generate_tier_2_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 2: Company names without forms, form synonyms"""
        patterns = []

        canonical = TextCanonicalizer.normalize_for_ac(name)

        # Extract quoted names without forms
        patterns.extend(self._generate_no_form_variants(canonical, language))

        # Form synonyms
        patterns.extend(self._generate_form_synonym_variants(canonical, language))

        return patterns

    def generate_tier_3_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Tier 3: Aggressive company patterns"""
        patterns = []

        canonical = TextCanonicalizer.normalize_for_ac(name)

        # 1. Aggressive company name patterns
        patterns.extend(self._generate_aggressive_company_patterns(canonical, language))

        # 2. Single significant company words
        patterns.extend(self._generate_company_single_words(canonical, language))

        # 3. Company abbreviations
        patterns.extend(self._generate_company_abbreviations(canonical, language))

        # 4. Partial company name matches
        patterns.extend(self._generate_company_partial_matches(canonical, language))

        return patterns

    def _generate_quote_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate different quote variants"""
        patterns = []

        # Different quote types
        quote_variants = [
            ('"', '"'),  # ASCII quotes
            ('«', '»'),  # French quotes
            ('"', '"'),  # Smart quotes
        ]

        for open_quote, close_quote in quote_variants:
            # Replace existing quotes
            variant = re.sub(r'["""«»]', open_quote, name)
            variant = re.sub(r'["""«»]', close_quote, variant)

            if variant != name:
                metadata = PatternMetadata(
                    tier=PatternTier.TIER_1,
                    pattern_type=PatternType.COMPANY_FORM_VARIANT,
                    language=language,
                    confidence=0.9,
                    source_field="name",
                    hints={"quote_variant": True}
                )

                patterns.append(GeneratedPattern(
                    pattern=variant,
                    canonical=name,
                    metadata=metadata,
                    entity_id="",
                    entity_type="company"
                ))

        return patterns

    def _generate_company_case_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate case variants for company names"""
        patterns = []

        # Generate UPPERCASE variant
        upper_variant = name.upper()
        if upper_variant != name:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.COMPANY_FORM_VARIANT,
                language=language,
                confidence=0.85,
                source_field="name",
                hints={"case_variant": "upper"}
            )
            patterns.append(GeneratedPattern(
                pattern=upper_variant,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="company"
            ))

        # Generate Title Case variant
        title_variant = name.title()
        if title_variant != name:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.COMPANY_FORM_VARIANT,
                language=language,
                confidence=0.8,
                source_field="name",
                hints={"case_variant": "title"}
            )
            patterns.append(GeneratedPattern(
                pattern=title_variant,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="company"
            ))

        return patterns

    def _generate_form_position_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate variants with legal forms in different positions"""
        patterns = []

        # Check for legal forms in the name
        legal_forms_all = []
        for forms_list in self.legal_forms.values():
            legal_forms_all.extend(forms_list)

        for form in legal_forms_all:
            if form in name:
                # Try moving form to beginning/end
                name_without_form = name.replace(form, '').strip()
                if name_without_form:
                    variants = [
                        f"{form} {name_without_form}",  # Form first
                        f"{name_without_form} {form}",  # Form last
                    ]

                    for variant in variants:
                        if variant != name and variant.strip():
                            metadata = PatternMetadata(
                                tier=PatternTier.TIER_1,
                                pattern_type=PatternType.COMPANY_FORM_VARIANT,
                                language=language,
                                confidence=0.8,
                                source_field="name",
                                hints={"form_repositioned": form}
                            )
                            patterns.append(GeneratedPattern(
                                pattern=variant,
                                canonical=name,
                                metadata=metadata,
                                entity_id="",
                                entity_type="company"
                            ))

        return patterns

    def _generate_company_punctuation_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate punctuation variants for companies"""
        patterns = []

        # Remove all punctuation
        no_punct = re.sub(r'[.,\-\"\'«»]', ' ', name)
        no_punct = re.sub(r'\s+', ' ', no_punct).strip()
        if no_punct != name and no_punct:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_1,
                pattern_type=PatternType.COMPANY_FORM_VARIANT,
                language=language,
                confidence=0.8,
                source_field="name",
                hints={"punctuation": "removed"}
            )
            patterns.append(GeneratedPattern(
                pattern=no_punct,
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="company"
            ))

        # Add standard quotes around company core (if not present)
        if '"' not in name and '«' not in name:
            # Try to identify the company core (non-legal form words)
            words = name.split()
            legal_forms_all = []
            for forms_list in self.legal_forms.values():
                legal_forms_all.extend(forms_list)

            core_words = [word for word in words
                         if not any(form.lower() in word.lower() for form in legal_forms_all)]

            if core_words:
                core = ' '.join(core_words)
                legal_part = ' '.join(word for word in words if word not in core_words)

                if legal_part:
                    quoted_variant = f'{legal_part} "{core}"'
                    metadata = PatternMetadata(
                        tier=PatternTier.TIER_1,
                        pattern_type=PatternType.COMPANY_FORM_VARIANT,
                        language=language,
                        confidence=0.75,
                        source_field="name",
                        hints={"punctuation": "quotes_added"}
                    )
                    patterns.append(GeneratedPattern(
                        pattern=quoted_variant,
                        canonical=name,
                        metadata=metadata,
                        entity_id="",
                        entity_type="company"
                    ))

        return patterns

    def _generate_no_form_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Extract company names without legal forms"""
        patterns = []

        # Extract quoted content
        quoted_matches = re.findall(r'["""«»]([^"""«»]+)["""«»]', name)

        for quoted_name in quoted_matches:
            metadata = PatternMetadata(
                tier=PatternTier.TIER_2,
                pattern_type=PatternType.COMPANY_NO_FORM,
                language=language,
                confidence=0.7,
                source_field="name",
                hints={"no_legal_form": True},
                requires_context=True
            )

            patterns.append(GeneratedPattern(
                pattern=f'"{quoted_name}"',
                canonical=name,
                metadata=metadata,
                entity_id="",
                entity_type="company"
            ))

        return patterns

    def _generate_form_synonym_variants(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate variants with legal form synonyms"""
        patterns = []

        for form, synonyms in self.form_synonyms.items():
            if form in name:
                for synonym in synonyms:
                    variant = name.replace(form, synonym)

                    metadata = PatternMetadata(
                        tier=PatternTier.TIER_2,
                        pattern_type=PatternType.COMPANY_FORM_VARIANT,
                        language=language,
                        confidence=0.6,
                        source_field="name",
                        hints={"form_synonym": f"{form} -> {synonym}"}
                    )

                    patterns.append(GeneratedPattern(
                        pattern=variant,
                        canonical=name,
                        metadata=metadata,
                        entity_id="",
                        entity_type="company"
                    ))

        return patterns

    def _generate_aggressive_company_patterns(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate aggressive company patterns for Tier 3"""
        patterns = []

        # Extract any capitalized sequences without forms or quotes
        words = name.split()
        cap_words = [word for word in words if word and word[0].isupper()]

        if len(cap_words) >= 2:
            # Generate patterns for capitalized sequences
            for i in range(len(cap_words)):
                for j in range(i + 2, min(i + 5, len(cap_words) + 1)):
                    sequence = cap_words[i:j]
                    pattern = " ".join(sequence)

                    metadata = PatternMetadata(
                        tier=PatternTier.TIER_3,
                        pattern_type=PatternType.BROAD_MATCH,
                        language=language,
                        confidence=0.25,
                        source_field="name",
                        hints={"aggressive_company": True, "word_count": len(sequence)},
                        requires_context=True
                    )

                    patterns.append(GeneratedPattern(
                        pattern=pattern,
                        canonical=name,
                        metadata=metadata,
                        entity_id="",
                        entity_type="company"
                    ))

        return patterns

    def _generate_company_single_words(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate single significant company words"""
        patterns = []

        words = name.split()

        # Common company words to ignore
        ignored_words = {
            "ru": {"общество", "ограниченной", "ответственностью", "закрытое", "акционерное"},
            "uk": {"товариство", "обмеженою", "відповідальністю", "приватне", "акціонерне"},
            "en": {"limited", "liability", "company", "corporation", "incorporated"}
        }

        ignore_set = ignored_words.get(language, set())

        for word in words:
            # Extract core company words (not legal forms or common words)
            if (len(word) >= 4 and
                word.lower() not in ignore_set and
                not any(form.lower() in word.lower() for form_list in self.legal_forms.values() for form in form_list)):

                metadata = PatternMetadata(
                    tier=PatternTier.TIER_3,
                    pattern_type=PatternType.SINGLE_WORD,
                    language=language,
                    confidence=0.3,
                    source_field="name",
                    hints={"company_single_word": True, "requires_payment_context": True},
                    requires_context=True
                )
                patterns.append(GeneratedPattern(
                    pattern=word,
                    canonical=name,
                    metadata=metadata,
                    entity_id="",
                    entity_type="company"
                ))

        return patterns

    def _generate_company_abbreviations(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate company abbreviations"""
        patterns = []

        words = name.split()

        # Find significant words (capitalized, not legal forms)
        significant_words = []
        for word in words:
            if (word and word[0].isupper() and len(word) >= 3 and
                not any(form.lower() in word.lower() for form_list in self.legal_forms.values() for form in form_list)):
                significant_words.append(word)

        if len(significant_words) >= 2:
            # Generate initials
            initials = "".join(word[0].upper() for word in significant_words)
            if 2 <= len(initials) <= 6:
                metadata = PatternMetadata(
                    tier=PatternTier.TIER_3,
                    pattern_type=PatternType.ABBREVIATION,
                    language=language,
                    confidence=0.25,
                    source_field="name",
                    hints={"company_abbreviation": True},
                    requires_context=True
                )
                patterns.append(GeneratedPattern(
                    pattern=initials,
                    canonical=name,
                    metadata=metadata,
                    entity_id="",
                    entity_type="company"
                ))

        return patterns

    def _generate_company_partial_matches(self, name: str, language: str) -> List[GeneratedPattern]:
        """Generate partial company name matches"""
        patterns = []

        words = name.split()

        for word in words:
            if len(word) >= 6:  # Only for long words
                # Generate prefix/suffix patterns
                for length in [3, 4, 5]:
                    if len(word) > length:
                        # Prefix
                        prefix = word[:length]
                        metadata = PatternMetadata(
                            tier=PatternTier.TIER_3,
                            pattern_type=PatternType.PARTIAL_MATCH,
                            language=language,
                            confidence=0.15,
                            source_field="name",
                            hints={"partial_type": "prefix", "from_word": word},
                            requires_context=True
                        )
                        patterns.append(GeneratedPattern(
                            pattern=prefix,
                            canonical=name,
                            metadata=metadata,
                            entity_id="",
                            entity_type="company"
                        ))

                        # Suffix
                        suffix = word[-length:]
                        metadata = PatternMetadata(
                            tier=PatternTier.TIER_3,
                            pattern_type=PatternType.PARTIAL_MATCH,
                            language=language,
                            confidence=0.1,
                            source_field="name",
                            hints={"partial_type": "suffix", "from_word": word},
                            requires_context=True
                        )
                        patterns.append(GeneratedPattern(
                            pattern=suffix,
                            canonical=name,
                            metadata=metadata,
                            entity_id="",
                            entity_type="company"
                        ))

        return patterns


class HighRecallACGenerator:
    """Main high-recall AC pattern generator"""

    def __init__(self):
        self.logger = get_logger(__name__)
        self.language_detector = LanguageDetector()
        self.document_generator = DocumentPatternGenerator()
        self.name_generator = NamePatternGenerator()
        self.company_generator = CompanyPatternGenerator()

        # Pattern limits by tier
        self.tier_limits = {
            PatternTier.TIER_0: 3,    # 1-3 variants per pattern
            PatternTier.TIER_1: 8,    # up to 8 safe variants per name
            PatternTier.TIER_2: 12,   # up to 12 structured variants
            PatternTier.TIER_3: 200,  # global cap for tier 3
        }

        # Stop words by language
        self.stop_words = {
            "ru": {"и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о"},
            "uk": {"і", "в", "на", "з", "по", "для", "від", "до", "із", "к", "о"},
            "en": {"and", "in", "on", "with", "for", "from", "to", "of", "at"},
        }

    def generate_patterns_for_person(self, person_data: Dict[str, Any]) -> List[GeneratedPattern]:
        """Generate all patterns for a person entity"""
        patterns = []
        entity_id = str(person_data.get('id', ''))

        # Tier 0: Documents
        if person_data.get('itn'):
            doc_patterns = self.document_generator.generate_itn_patterns(person_data['itn'])
            for pattern in doc_patterns:
                pattern.entity_id = entity_id
            patterns.extend(doc_patterns)

        if person_data.get('itn_import'):
            doc_patterns = self.document_generator.generate_itn_patterns(person_data['itn_import'])
            for pattern in doc_patterns:
                pattern.entity_id = entity_id
            patterns.extend(doc_patterns)

        # Names from different fields
        name_fields = ['name', 'name_ru', 'name_en']
        for field in name_fields:
            if person_data.get(field):
                name = person_data[field]
                language = self.language_detector.detect_language(name)

                # Tier 0: Canonical names
                tier0_patterns = self.name_generator.generate_tier_0_patterns(name, language)
                for pattern in tier0_patterns:
                    pattern.entity_id = entity_id
                patterns.extend(tier0_patterns)

                # Tier 1: High precision variants
                tier1_patterns = self.name_generator.generate_tier_1_patterns(name, language)
                for pattern in tier1_patterns:
                    pattern.entity_id = entity_id
                patterns.extend(tier1_patterns)

                # Tier 2: Structured variants
                tier2_patterns = self.name_generator.generate_tier_2_patterns(name, language)
                for pattern in tier2_patterns:
                    pattern.entity_id = entity_id
                patterns.extend(tier2_patterns)

                # Tier 3: Aggressive broad recall
                tier3_patterns = self.name_generator.generate_tier_3_patterns(name, language)
                for pattern in tier3_patterns:
                    pattern.entity_id = entity_id
                patterns.extend(tier3_patterns)

        # Apply tier limits
        patterns = self._apply_tier_limits(patterns)

        return patterns

    def generate_patterns_for_company(self, company_data: Dict[str, Any]) -> List[GeneratedPattern]:
        """Generate all patterns for a company entity"""
        patterns = []
        entity_id = str(company_data.get('id', ''))

        # Company name
        if company_data.get('name'):
            name = company_data['name']
            language = self.language_detector.detect_language(name)

            # Tier 0: Canonical companies
            tier0_patterns = self.company_generator.generate_tier_0_patterns(name, language)
            for pattern in tier0_patterns:
                pattern.entity_id = entity_id
            patterns.extend(tier0_patterns)

            # Tier 1: Safe variants
            tier1_patterns = self.company_generator.generate_tier_1_patterns(name, language)
            for pattern in tier1_patterns:
                pattern.entity_id = entity_id
            patterns.extend(tier1_patterns)

            # Tier 2: Forms and synonyms
            tier2_patterns = self.company_generator.generate_tier_2_patterns(name, language)
            for pattern in tier2_patterns:
                pattern.entity_id = entity_id
            patterns.extend(tier2_patterns)

            # Tier 3: Aggressive patterns
            tier3_patterns = self.company_generator.generate_tier_3_patterns(name, language)
            for pattern in tier3_patterns:
                pattern.entity_id = entity_id
            patterns.extend(tier3_patterns)

        # Documents
        if company_data.get('tax_number'):
            doc_patterns = self.document_generator.generate_itn_patterns(company_data['tax_number'])
            for pattern in doc_patterns:
                pattern.entity_id = entity_id
                pattern.entity_type = "company"
            patterns.extend(doc_patterns)

        # Apply tier limits
        patterns = self._apply_tier_limits(patterns)

        return patterns

    def generate_patterns_for_terrorism(self, terrorism_data: Dict[str, Any]) -> List[GeneratedPattern]:
        """Generate all patterns for a terrorism entity (treated as person with terrorism entity_type)"""
        patterns = []
        entity_id = str(terrorism_data.get('id', ''))

        # Tier 0: Documents
        if terrorism_data.get('itn'):
            doc_patterns = self.document_generator.generate_itn_patterns(terrorism_data['itn'])
            for pattern in doc_patterns:
                pattern.entity_id = entity_id
                pattern.entity_type = "terrorism"
            patterns.extend(doc_patterns)

        if terrorism_data.get('passport_number'):
            doc_patterns = self.document_generator.generate_passport_patterns(terrorism_data['passport_number'])
            for pattern in doc_patterns:
                pattern.entity_id = entity_id
                pattern.entity_type = "terrorism"
            patterns.extend(doc_patterns)

        # Names
        names_to_process = []
        if terrorism_data.get('name'):
            names_to_process.append(terrorism_data['name'])
        if terrorism_data.get('name_en'):
            names_to_process.append(terrorism_data['name_en'])

        for name in names_to_process:
            if not name or not name.strip():
                continue

            language = self.language_detector.detect_language(name)

            # Tier 0: Canonical names
            tier0_patterns = self.name_generator.generate_tier_0_patterns(name, language)
            for pattern in tier0_patterns:
                pattern.entity_id = entity_id
                pattern.entity_type = "terrorism"
            patterns.extend(tier0_patterns)

            # Tier 1: Safe variants
            tier1_patterns = self.name_generator.generate_tier_1_patterns(name, language)
            for pattern in tier1_patterns:
                pattern.entity_id = entity_id
                pattern.entity_type = "terrorism"
            patterns.extend(tier1_patterns)

            # Tier 2: Morphological and structured variants
            tier2_patterns = self.name_generator.generate_tier_2_patterns(name, language)
            for pattern in tier2_patterns:
                pattern.entity_id = entity_id
                pattern.entity_type = "terrorism"
            patterns.extend(tier2_patterns)

            # Tier 3: Aggressive recall patterns
            tier3_patterns = self.name_generator.generate_tier_3_patterns(name, language)
            for pattern in tier3_patterns:
                pattern.entity_id = entity_id
                pattern.entity_type = "terrorism"
            patterns.extend(tier3_patterns)

        # Apply tier limits
        patterns = self._apply_tier_limits(patterns)

        return patterns

    def _apply_tier_limits(self, patterns: List[GeneratedPattern]) -> List[GeneratedPattern]:
        """Apply tier-specific limits to pattern generation"""
        tier_counts = defaultdict(int)
        filtered_patterns = []

        # Sort by tier and confidence for prioritization
        patterns.sort(key=lambda p: (p.metadata.tier.value, -p.metadata.confidence))

        for pattern in patterns:
            tier = pattern.metadata.tier
            if tier_counts[tier] < self.tier_limits[tier]:
                filtered_patterns.append(pattern)
                tier_counts[tier] += 1

        return filtered_patterns

    def export_for_ac(self, patterns: List[GeneratedPattern]) -> List[Dict[str, Any]]:
        """Export patterns in AC-compatible format"""
        ac_patterns = []

        for pattern in patterns:
            ac_pattern = {
                "pattern": pattern.pattern,
                "tier": pattern.metadata.tier.value,
                "type": pattern.metadata.pattern_type.value,
                "lang": pattern.metadata.language,
                "hints": pattern.metadata.hints,
                "entity_id": pattern.entity_id,
                "entity_type": pattern.entity_type,
                "confidence": pattern.metadata.confidence,
                "requires_context": pattern.metadata.requires_context,
                "canonical": pattern.canonical,
            }
            ac_patterns.append(ac_pattern)

        return ac_patterns

    def generate_full_corpus(self,
                           persons_file: str = None,
                           companies_file: str = None,
                           terrorism_file: str = None) -> Dict[str, Any]:
        """Generate full pattern corpus from sanctions data"""
        start_time = time.time()

        all_patterns = []
        stats = {
            "persons_processed": 0,
            "companies_processed": 0,
            "terrorism_processed": 0,
            "patterns_generated": 0,
            "tier_distribution": defaultdict(int),
            "processing_time": 0
        }

        # Process persons
        if persons_file:
            try:
                with open(persons_file, 'r', encoding='utf-8') as f:
                    persons_data = json.load(f)

                for person in persons_data:
                    patterns = self.generate_patterns_for_person(person)
                    all_patterns.extend(patterns)
                    stats["persons_processed"] += 1

                    # Update tier distribution
                    for pattern in patterns:
                        stats["tier_distribution"][pattern.metadata.tier.value] += 1

            except Exception as e:
                self.logger.error(f"Error processing persons file: {e}")

        # Process companies
        if companies_file:
            try:
                with open(companies_file, 'r', encoding='utf-8') as f:
                    companies_data = json.load(f)

                for company in companies_data:
                    patterns = self.generate_patterns_for_company(company)
                    all_patterns.extend(patterns)
                    stats["companies_processed"] += 1

                    # Update tier distribution
                    for pattern in patterns:
                        stats["tier_distribution"][pattern.metadata.tier.value] += 1

            except Exception as e:
                self.logger.error(f"Error processing companies file: {e}")

        # Process terrorism blacklist
        if terrorism_file:
            try:
                with open(terrorism_file, 'r', encoding='utf-8') as f:
                    terrorism_data = json.load(f)

                for entity in terrorism_data:
                    patterns = self.generate_patterns_for_terrorism(entity)
                    all_patterns.extend(patterns)
                    stats["terrorism_processed"] += 1

                    # Update tier distribution
                    for pattern in patterns:
                        stats["tier_distribution"][pattern.metadata.tier.value] += 1

            except Exception as e:
                self.logger.error(f"Error processing terrorism file: {e}")

        stats["patterns_generated"] = len(all_patterns)
        stats["processing_time"] = time.time() - start_time

        # Export for AC
        ac_patterns = self.export_for_ac(all_patterns)

        return {
            "patterns": ac_patterns,
            "statistics": dict(stats),
            "generation_timestamp": time.time(),
            "generator_version": "1.0.0"
        }


# Example usage and testing
if __name__ == "__main__":
    generator = HighRecallACGenerator()

    # Test with sample data
    sample_person = {
        "id": 1,
        "name": "Ковриков Роман Валерійович",
        "name_en": "Kovrykov Roman Valeriiovych",
        "itn": "782611846337",
        "birthdate": "1976-08-09"
    }

    sample_company = {
        "id": 1,
        "name": 'ООО "РОМАШКА"',
        "tax_number": "1234567890"
    }

    print("Generating patterns for person...")
    person_patterns = generator.generate_patterns_for_person(sample_person)
    print(f"Generated {len(person_patterns)} patterns for person")

    for pattern in person_patterns[:5]:  # Show first 5
        print(f"  Tier {pattern.metadata.tier.value}: {pattern.pattern} ({pattern.metadata.pattern_type.value})")

    print("\nGenerating patterns for company...")
    company_patterns = generator.generate_patterns_for_company(sample_company)
    print(f"Generated {len(company_patterns)} patterns for company")

    for pattern in company_patterns[:5]:  # Show first 5
        print(f"  Tier {pattern.metadata.tier.value}: {pattern.pattern} ({pattern.metadata.pattern_type.value})")