"""
High-Recall AC Pattern Generator для санкционного скрининга
ПРИОРИТЕТ: Максимальный Recall (не пропускать санкционных лиц)
Стратегия: Лучше 10 ложных срабатываний, чем 1 пропущенное санкционное лицо
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass
class RecallOptimizedPattern:
    """Паттерн, оптимизированный для максимального Recall"""

    pattern: str
    pattern_type: str
    recall_tier: int  # 0=exact, 1=high_recall, 2=medium_recall, 3=broad_recall
    precision_hint: float  # Expected precision (for subsequent filtering)
    variants: List[str]  # Automatic variants
    language: str
    source_confidence: float = 1.0


class HighRecallACGenerator:
    """
    Генератор паттернов с максимальным Recall для санкционного скрининга
    Философия: "Catch everything, filter later"
    """

    def __init__(self):
        # Stop words that should NEVER be patterns
        self.absolute_stop_words = {
            "ru": {
                "и",
                "в",
                "на",
                "с",
                "по",
                "для",
                "от",
                "до",
                "из",
                "год",
                "лет",
                "рублей",
                "грн",
            },
            "uk": {
                "і",
                "в",
                "на",
                "з",
                "по",
                "для",
                "від",
                "до",
                "із",
                "рік",
                "років",
                "гривень",
            },
            "en": {
                "and",
                "in",
                "on",
                "with",
                "for",
                "from",
                "to",
                "year",
                "years",
                "usd",
                "eur",
            },
        }

        # Context words (help but NOT required)
        self.context_hints = {
            "ru": [
                "платеж",
                "получатель",
                "отправитель",
                "договор",
                "паспорт",
                "от",
                "для",
            ],
            "uk": [
                "платіж",
                "одержувач",
                "відправник",
                "договір",
                "паспорт",
                "від",
                "для",
            ],
            "en": [
                "payment",
                "beneficiary",
                "sender",
                "contract",
                "passport",
                "from",
                "to",
            ],
        }

        # Documents - exact patterns (Tier 0)
        self.document_patterns = {
            "passport": [r"\b[A-ZА-Я]{2}\d{6,8}\b"],
            "tax_id": [r"\b\d{10,12}\b"],
            "edrpou": [r"\b\d{6,8}\b"],
            "iban": [r"\b[A-Z]{2}\d{2}[A-Z0-9]{15,32}\b"],
        }

        # Legal forms
        self.legal_entities = {
            "ru": ["ООО", "ЗАО", "ОАО", "ПАО", "ИП", "АО", "ТОО", "УП", "ЧУП"],
            "uk": ["ТОВ", "ПАТ", "АТ", "ПрАТ", "ФОП", "КТ", "ДП", "УП"],
            "en": ["LLC", "Inc", "Ltd", "Corp", "Co", "LP", "LLP", "PC", "PLLC"],
        }

        # Name variant generators
        self.name_variants_generators = {
            "initials": self._generate_initial_variants,
            "transliteration": self._generate_translit_variants,
            "spacing": self._generate_spacing_variants,
            "hyphenation": self._generate_hyphen_variants,
        }

    def generate_high_recall_patterns(
        self, text: str, language: str = "auto", entity_metadata: Dict = None
    ) -> List[RecallOptimizedPattern]:
        """
        Генерация паттернов с максимальным Recall
        Стратегия: захватываем ВСЁ подозрительное, фильтруем потом
        """
        if language == "auto":
            language = self._detect_language(text)

        patterns = []
        entity_metadata = entity_metadata or {}

        # TIER 0: Exact documents (100% automatic hit)
        patterns.extend(self._extract_documents_comprehensive(text))

        # TIER 1: High Recall - all names and companies
        patterns.extend(self._extract_all_names_aggressive(text, language))
        patterns.extend(self._extract_all_companies_aggressive(text, language))

        # TIER 2: Medium Recall - name parts, initials, abbreviations
        patterns.extend(self._extract_name_parts_and_initials(text, language))

        # TIER 3: Broad Recall - suspicious sequences
        patterns.extend(self._extract_suspicious_sequences(text, language))

        # Generate automatic variants for all patterns
        patterns_with_variants = self._generate_comprehensive_variants(
            patterns, language
        )

        # Final processing: remove only absolutely impossible ones
        filtered_patterns = self._minimal_filtering(patterns_with_variants, language)

        return filtered_patterns

    def _extract_documents_comprehensive(
        self, text: str
    ) -> List[RecallOptimizedPattern]:
        """Извлечение всех документов - Tier 0 (точные)"""
        patterns = []

        for doc_type, regexes in self.document_patterns.items():
            for regex in regexes:
                for match in re.finditer(regex, text):
                    doc_number = match.group().strip()

                    patterns.append(
                        RecallOptimizedPattern(
                            pattern=doc_number,
                            pattern_type=f"document_{doc_type}",
                            recall_tier=0,
                            precision_hint=0.99,
                            variants=[],
                            language="universal",
                        )
                    )

        return patterns

    def _extract_all_names_aggressive(
        self, text: str, language: str
    ) -> List[RecallOptimizedPattern]:
        """Агрессивное извлечение ВСЕХ возможных имен - Tier 1"""
        patterns = []

        if language in ["ru", "uk"]:
            # All word sequences with capital letters (2-4 words)
            name_patterns = [
                r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\b",  # 2 words
                r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\b",  # 3 words
                r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{1,}\b",  # 4 words
            ]

            # Structured forms
            structured_patterns = [
                r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\b",  # Last F.M.
                r"\b[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b",  # F.M. Last
                r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ]\.\b",  # Last F.
                r"\b[А-ЯІЇЄҐ]\.\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b",  # F. Last
            ]

            # Even single words if long enough (could be surnames)
            single_word_patterns = [
                r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{3,15}\b"  # Single words 4-15 characters
            ]

        else:  # English
            name_patterns = [
                r"\b[A-Z][a-z\']{1,}\s+[A-Z][a-z\']{1,}\b",
                r"\b[A-Z][a-z\']{1,}\s+[A-Z][a-z\']{1,}\s+[A-Z][a-z\']{1,}\b",
                r"\b[A-Z][a-z\']{1,}\s+[A-Z][a-z\']{1,}\s+[A-Z][a-z\']{1,}\s+[A-Z][a-z\']{1,}\b",
            ]

            structured_patterns = [
                r"\b[A-Z][a-z\']{2,}\s+[A-Z]\.\s*[A-Z]\.\b",
                r"\b[A-Z]\.\s*[A-Z]\.\s+[A-Z][a-z\']{2,}\b",
                r"\b[A-Z][a-z\']{2,}\s+[A-Z]\.\b",
                r"\b[A-Z]\.\s+[A-Z][a-z\']{2,}\b",
            ]

            single_word_patterns = [r"\b[A-Z][a-z\']{3,15}\b"]

        # Extract full names
        for pattern in name_patterns:
            for match in re.finditer(pattern, text):
                name = match.group().strip()
                if self._is_potential_name(name, language):
                    patterns.append(
                        RecallOptimizedPattern(
                            pattern=name,
                            pattern_type="full_name_aggressive",
                            recall_tier=1,
                            precision_hint=0.7,  # May have many FP but won't miss
                            variants=[],
                            language=language,
                        )
                    )

        # Extract structured forms
        for pattern in structured_patterns:
            for match in re.finditer(pattern, text):
                name = match.group().strip()
                patterns.append(
                    RecallOptimizedPattern(
                        pattern=name,
                        pattern_type="structured_name_aggressive",
                        recall_tier=1,
                        precision_hint=0.8,
                        variants=[],
                        language=language,
                    )
                )

        # Extract single words (potential surnames)
        # But only if there are context clues OR word is unique enough
        for pattern in single_word_patterns:
            for match in re.finditer(pattern, text):
                word = match.group().strip()
                if self._could_be_surname(word, text, language):
                    patterns.append(
                        RecallOptimizedPattern(
                            pattern=word,
                            pattern_type="potential_surname",
                            recall_tier=2,  # Medium recall for single words
                            precision_hint=0.3,  # Many FP expected
                            variants=[],
                            language=language,
                        )
                    )

        return patterns

    def _extract_all_companies_aggressive(
        self, text: str, language: str
    ) -> List[RecallOptimizedPattern]:
        """Агрессивное извлечение всех компаний"""
        patterns = []

        if language not in self.legal_entities:
            return patterns

        legal_forms = self.legal_entities[language]

        # Search for any combinations with legal forms
        for legal_form in legal_forms:
            # Form + name
            pattern1 = rf'\b{re.escape(legal_form)}\s+[""«]?([^""»\n]{{2,30}})[""»]?'
            # Name + form
            pattern2 = rf'[""«]?([^""»\n]{{2,30}})[""»]?\s+{re.escape(legal_form)}\b'

            for pattern in [pattern1, pattern2]:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    full_match = match.group().strip()
                    company_name = (
                        match.group(1).strip() if match.groups() else full_match
                    )

                    if len(company_name) >= 2:
                        patterns.append(
                            RecallOptimizedPattern(
                                pattern=full_match,
                                pattern_type="company_with_legal_form",
                                recall_tier=1,
                                precision_hint=0.85,
                                variants=[],
                                language=language,
                            )
                        )

        # Also search for companies in quotes (without legal forms)
        quoted_pattern = r'[""«]([^""»\n]{3,25})[""»]'
        for match in re.finditer(quoted_pattern, text):
            company_name = match.group(1).strip()
            if self._could_be_company_name(company_name, language):
                patterns.append(
                    RecallOptimizedPattern(
                        pattern=company_name,
                        pattern_type="quoted_company",
                        recall_tier=2,
                        precision_hint=0.6,
                        variants=[],
                        language=language,
                    )
                )

        return patterns

    def _extract_name_parts_and_initials(
        self, text: str, language: str
    ) -> List[RecallOptimizedPattern]:
        """Извлечение частей имен и инициалов - Tier 2"""
        patterns = []

        # Initials separately
        if language in ["ru", "uk"]:
            initial_pattern = r"\b[А-ЯІЇЄҐ]\.[А-ЯІЇЄҐ]?\."
        else:
            initial_pattern = r"\b[A-Z]\.[A-Z]?\."

        for match in re.finditer(initial_pattern, text):
            initials = match.group().strip()
            patterns.append(
                RecallOptimizedPattern(
                    pattern=initials,
                    pattern_type="initials_only",
                    recall_tier=2,
                    precision_hint=0.2,  # Very many FP
                    variants=[],
                    language=language,
                )
            )

        return patterns

    def _extract_suspicious_sequences(
        self, text: str, language: str
    ) -> List[RecallOptimizedPattern]:
        """Извлечение подозрительных последовательностей - Tier 3"""
        patterns = []

        # Capital letter sequences (could be name/company abbreviations)
        caps_pattern = r"\b[A-ZА-ЯІЇЄҐ]{2,6}\b"
        for match in re.finditer(caps_pattern, text):
            caps_seq = match.group().strip()
            if len(caps_seq) >= 2 and caps_seq not in self.absolute_stop_words.get(
                language, set()
            ):
                patterns.append(
                    RecallOptimizedPattern(
                        pattern=caps_seq,
                        pattern_type="caps_sequence",
                        recall_tier=3,
                        precision_hint=0.1,  # Very low precision but may catch abbreviations
                        variants=[],
                        language=language,
                    )
                )

        return patterns

    def _is_potential_name(self, name: str, language: str) -> bool:
        """Проверка, может ли быть именем (очень либеральная)"""
        if len(name) < 3:
            return False

        words = name.split()
        if len(words) > 4:  # Too long
            return False

        # Exclude obvious non-names (only whole words)
        if language in self.absolute_stop_words:
            name_lower = name.lower()
            words = name_lower.split()
            # Check only whole words, not substrings
            if any(word in self.absolute_stop_words[language] for word in words):
                return False

        return True

    def _could_be_surname(self, word: str, text: str, language: str) -> bool:
        """Может ли одиночное слово быть фамилией"""
        if len(word) < 4:  # Too short for surname
            return False

        # Exclude stop words
        if language in self.absolute_stop_words:
            if word.lower() in self.absolute_stop_words[language]:
                return False

        # If there are context clues nearby - take it
        if language in self.context_hints:
            for hint in self.context_hints[language]:
                if hint in text.lower():
                    return True

        # If word is long enough and unique - take it
        if len(word) >= 6:
            return True

        return False

    def _could_be_company_name(self, name: str, language: str) -> bool:
        """Может ли быть названием компании"""
        if len(name) < 3:
            return False

        # Exclude obvious non-names
        if language in self.absolute_stop_words:
            name_lower = name.lower()
            stop_words_count = sum(
                1
                for stop_word in self.absolute_stop_words[language]
                if stop_word in name_lower
            )
            # If more than half words are stop words, probably not a company
            word_count = len(name.split())
            if word_count > 0 and stop_words_count / word_count > 0.5:
                return False

        return True

    def _generate_comprehensive_variants(
        self, patterns: List[RecallOptimizedPattern], language: str
    ) -> List[RecallOptimizedPattern]:
        """Генерация всех возможных вариантов для каждого паттерна"""
        enriched_patterns = []

        for pattern in patterns:
            # Base pattern
            enriched_patterns.append(pattern)

            # Generate variants only for names and companies
            if pattern.pattern_type in [
                "full_name_aggressive",
                "structured_name_aggressive",
                "company_with_legal_form",
            ]:
                variants = set()

                # Apply all variant generators
                for (
                    generator_name,
                    generator_func,
                ) in self.name_variants_generators.items():
                    try:
                        new_variants = generator_func(pattern.pattern, language)
                        variants.update(new_variants)
                    except Exception:
                        continue  # If generator broke, skip

                # Update variants
                pattern.variants = list(variants)[
                    :20
                ]  # Maximum 20 variants per pattern

        return enriched_patterns

    def _generate_initial_variants(self, name: str, language: str) -> List[str]:
        """Генерация вариантов с инициалами"""
        variants = []
        words = name.split()

        if len(words) >= 2:
            # First word + initial of second
            variants.append(f"{words[0]} {words[1][0]}.")

            # Initial of first + second word
            variants.append(f"{words[0][0]}. {words[1]}")

            if len(words) >= 3:
                # All initials
                initials = " ".join([f"{word[0]}." for word in words])
                variants.append(initials)

                # First word + initials of others
                rest_initials = " ".join([f"{word[0]}." for word in words[1:]])
                variants.append(f"{words[0]} {rest_initials}")

        return variants

    def _generate_translit_variants(self, name: str, language: str) -> List[str]:
        """Простая транслитерация"""
        # Basic replacements for Cyrillic <-> Latin
        if language in ["ru", "uk"]:
            translit_map = {
                "а": "a",
                "е": "e",
                "о": "o",
                "р": "p",
                "у": "u",
                "х": "x",
                "с": "c",
            }
            variants = []
            translit_name = name.lower()
            for cyrillic, latin in translit_map.items():
                if cyrillic in translit_name:
                    variant = translit_name.replace(cyrillic, latin).title()
                    if variant != name:
                        variants.append(variant)
        else:
            # Reverse transliteration for Latin
            variants = []

        return variants

    def _generate_spacing_variants(self, name: str, language: str) -> List[str]:
        """Варианты с разными пробелами"""
        variants = []

        # Remove extra spaces
        clean_name = re.sub(r"\s+", " ", name.strip())
        if clean_name != name:
            variants.append(clean_name)

        # Remove all spaces
        no_spaces = name.replace(" ", "")
        if len(no_spaces) >= 4:
            variants.append(no_spaces)

        return variants

    def _generate_hyphen_variants(self, name: str, language: str) -> List[str]:
        """Варианты с дефисами"""
        variants = []

        # Replace spaces with hyphens
        hyphenated = name.replace(" ", "-")
        if hyphenated != name:
            variants.append(hyphenated)

        # Remove hyphens
        no_hyphens = name.replace("-", " ").replace("  ", " ")
        if no_hyphens != name:
            variants.append(no_hyphens)

        return variants

    def _minimal_filtering(
        self, patterns: List[RecallOptimizedPattern], language: str
    ) -> List[RecallOptimizedPattern]:
        """Минимальная фильтрация - убираем только очевидно невозможное"""
        filtered = []

        seen_patterns = set()

        for pattern in patterns:
            # Remove duplicates (normalize to lowercase)
            pattern_key = pattern.pattern.lower().strip()

            if pattern_key in seen_patterns:
                continue

            # Remove only critically short or obviously system ones
            if len(pattern.pattern.strip()) < 2:
                continue

            # Remove absolute stop words
            if (
                language in self.absolute_stop_words
                and pattern.pattern.lower() in self.absolute_stop_words[language]
            ):
                continue

            seen_patterns.add(pattern_key)
            filtered.append(pattern)

        # Sort: first high Recall, then by length
        filtered.sort(key=lambda x: (x.recall_tier, -len(x.pattern)))

        # Limit total quantity for performance
        return filtered[:200]  # Maximum 200 patterns

    def _detect_language(self, text: str) -> str:
        """Определение языка"""
        cyrillic = len(re.findall(r"[а-яіїєёА-ЯІЇЄЁҐ]", text))
        latin = len(re.findall(r"[a-zA-Z]", text))

        if cyrillic > 0:
            ukrainian = len(re.findall(r"[іїєґІЇЄҐ]", text))
            return "uk" if ukrainian > 0 else "ru"
        elif latin > 0:
            return "en"
        else:
            return "ru"  # Default

    def export_for_high_recall_ac(
        self, patterns: List[RecallOptimizedPattern]
    ) -> Dict[str, List[str]]:
        """
        Экспорт для многоуровневого AC с максимальным Recall
        """
        export_tiers = {
            "tier_0_exact": [],  # Documents - automatic hit
            "tier_1_high_recall": [],  # Full names/companies - high priority
            "tier_2_medium_recall": [],  # Name parts, single surnames - medium priority
            "tier_3_broad_recall": [],  # Initials, abbreviations - for completeness
        }

        for pattern in patterns:
            # Add main pattern
            target_tier = f"tier_{pattern.recall_tier}_"
            if pattern.recall_tier == 0:
                export_tiers["tier_0_exact"].append(pattern.pattern)
            elif pattern.recall_tier == 1:
                export_tiers["tier_1_high_recall"].append(pattern.pattern)
            elif pattern.recall_tier == 2:
                export_tiers["tier_2_medium_recall"].append(pattern.pattern)
            else:
                export_tiers["tier_3_broad_recall"].append(pattern.pattern)

            # Add all variants to same level
            for variant in pattern.variants:
                if pattern.recall_tier == 0:
                    export_tiers["tier_0_exact"].append(variant)
                elif pattern.recall_tier == 1:
                    export_tiers["tier_1_high_recall"].append(variant)
                elif pattern.recall_tier == 2:
                    export_tiers["tier_2_medium_recall"].append(variant)
                else:
                    export_tiers["tier_3_broad_recall"].append(variant)

        # Remove duplicates in each level
        for tier in export_tiers:
            export_tiers[tier] = list(set(export_tiers[tier]))

        return export_tiers

    def get_recall_statistics(self, patterns: List[RecallOptimizedPattern]) -> Dict:
        """Статистика по Recall-оптимизации"""
        if not patterns:
            return {}

        tier_distribution = {0: 0, 1: 0, 2: 0, 3: 0}
        precision_expectations = []
        total_variants = 0

        for pattern in patterns:
            tier_distribution[pattern.recall_tier] += 1
            precision_expectations.append(pattern.precision_hint)
            total_variants += len(pattern.variants)

        return {
            "total_patterns": len(patterns),
            "total_variants": total_variants,
            "total_searchable_items": len(patterns) + total_variants,
            "tier_distribution": {
                "tier_0_exact": tier_distribution[0],
                "tier_1_high_recall": tier_distribution[1],
                "tier_2_medium_recall": tier_distribution[2],
                "tier_3_broad_recall": tier_distribution[3],
            },
            "expected_precision": {
                "average": sum(precision_expectations) / len(precision_expectations),
                "tier_0": sum(p.precision_hint for p in patterns if p.recall_tier == 0)
                / max(1, tier_distribution[0]),
                "tier_1": sum(p.precision_hint for p in patterns if p.recall_tier == 1)
                / max(1, tier_distribution[1]),
                "tier_2": sum(p.precision_hint for p in patterns if p.recall_tier == 2)
                / max(1, tier_distribution[2]),
                "tier_3": sum(p.precision_hint for p in patterns if p.recall_tier == 3)
                / max(1, tier_distribution[3]),
            },
        }
