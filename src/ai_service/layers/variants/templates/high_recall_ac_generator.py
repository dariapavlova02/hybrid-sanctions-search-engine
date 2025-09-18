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
        # Инициализируем UnicodeService для нормализации
        from ...unicode.unicode_service import UnicodeService
        self.unicode_service = UnicodeService()
        
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
            "name_expansions": self._generate_name_expansions,
        }
        
        # Кэш для словарей диминутивов/никнеймов
        self._diminutives_cache = {}
        self._nicknames_cache = {}

    def normalize_for_ac(self, text: str) -> str:
        """
        Универсальная нормализация для Aho-Corasick с использованием готового UnicodeService.
        
        Args:
            text: Входная строка для нормализации
            
        Returns:
            Нормализованная строка для использования в AC
        """
        if not text:
            return ""
        
        # Используем готовый UnicodeService с агрессивной нормализацией
        result = self.unicode_service.normalize_text(
            text, 
            aggressive=True,  # Агрессивная нормализация
            normalize_homoglyphs=False  # Не используем встроенную де-гомоглифизацию
        )
        
        # Применяем casefold для унификации регистра
        normalized = result["normalized"].casefold()
        
        # Дополнительная NFKC нормализация после casefold для акцентов
        import unicodedata
        normalized = unicodedata.normalize('NFKC', normalized)
        
        # Принудительная де-гомоглифизация кириллицы в латиницу для AC
        # (AC должен работать с латинскими символами для универсальности)
        cyrillic_to_latin = {
            'а': 'a', 'А': 'A', 'б': 'b', 'Б': 'B', 'в': 'v', 'В': 'V',
            'г': 'g', 'Г': 'G', 'д': 'd', 'Д': 'D', 'е': 'e', 'Е': 'E',
            'ё': 'e', 'Ё': 'E', 'ж': 'zh', 'Ж': 'ZH', 'з': 'z', 'З': 'Z',
            'и': 'i', 'И': 'I', 'й': 'y', 'Й': 'Y', 'к': 'k', 'К': 'K',
            'л': 'l', 'Л': 'L', 'м': 'm', 'М': 'M', 'н': 'n', 'Н': 'N',
            'о': 'o', 'О': 'O', 'п': 'p', 'П': 'P', 'р': 'r', 'Р': 'R',
            'с': 's', 'С': 'S', 'т': 't', 'Т': 'T', 'у': 'u', 'У': 'U',
            'ф': 'f', 'Ф': 'F', 'х': 'h', 'Х': 'H', 'ц': 'ts', 'Ц': 'TS',
            'ч': 'ch', 'Ч': 'CH', 'ш': 'sh', 'Ш': 'SH', 'щ': 'sch', 'Щ': 'SCH',
            'ъ': '', 'Ъ': '', 'ы': 'y', 'Ы': 'Y', 'ь': '', 'Ь': '',
            'э': 'e', 'Э': 'E', 'ю': 'u', 'Ю': 'U', 'я': 'ya', 'Я': 'YA',
            # Украинские символы
            'і': 'i', 'І': 'I', 'ї': 'i', 'Ї': 'I', 'є': 'e', 'Є': 'E',
            'ґ': 'g', 'Ґ': 'G',
        }
        
        for cyrillic, latin in cyrillic_to_latin.items():
            normalized = normalized.replace(cyrillic, latin)
        
        # Дополнительная нормализация для AC
        # Заменяем двойные кавычки на одинарные для унификации
        normalized = normalized.replace('"', "'")
        
        # Заменяем оставшиеся дефисы
        hyphen_variants = ['‐', '–', '—', '―', '‒', '‑', '‗', '⁃', '⁻', '₋']
        for variant in hyphen_variants:
            normalized = normalized.replace(variant, '-')
        
        # Коллапс кратных пробелов
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Обрезка крайних пробелов
        normalized = normalized.strip()
        
        return normalized

    def generate_high_recall_patterns(
        self, text: str, language: str = "auto", entity_metadata: Dict = None
    ) -> List[RecallOptimizedPattern]:
        """
        Генерация паттернов с максимальным Recall
        Стратегия: захватываем ВСЁ подозрительное, фильтруем потом
        """
        # Определяем язык до нормализации
        if language == "auto":
            language = self._detect_language(text)
        
        # Нормализуем входной текст для AC
        normalized_text = self.normalize_for_ac(text)

        patterns = []
        entity_metadata = entity_metadata or {}

        # TIER 0: Exact documents (100% automatic hit)
        patterns.extend(self._extract_documents_comprehensive(normalized_text))

        # TIER 1: High Recall - all names and companies
        patterns.extend(self._extract_all_names_aggressive(normalized_text, language))
        patterns.extend(self._extract_all_companies_aggressive(normalized_text, language))

        # TIER 2: Medium Recall - name parts, initials, abbreviations
        patterns.extend(self._extract_name_parts_and_initials(normalized_text, language))

        # TIER 3: Broad Recall - suspicious sequences
        patterns.extend(self._extract_suspicious_sequences(normalized_text, language))

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

        # После нормализации все тексты в нижнем регистре и латинице
        # Используем универсальные паттерны для нормализованного текста
        name_patterns = [
            r"\b[a-z\']{2,}\s+[a-z\']{2,}\b",  # 2 words
            r"\b[a-z\']{2,}\s+[a-z\']{2,}\s+[a-z\']{2,}\b",  # 3 words
            r"\b[a-z\']{2,}\s+[a-z\']{2,}\s+[a-z\']{2,}\s+[a-z\']{2,}\b",  # 4 words
        ]

        # Structured forms (после нормализации)
        structured_patterns = [
            r"\b[a-z\']{2,}\s+[a-z]\.\s*[a-z]\.\b",  # Last F.M.
            r"\b[a-z]\.\s*[a-z]\.\s+[a-z\']{2,}\b",  # F.M. Last
            r"\b[a-z\']{2,}\s+[a-z]\.\b",  # Last F.
            r"\b[a-z]\.\s+[a-z\']{2,}\b",  # F. Last
        ]

        # Even single words if long enough (could be surnames)
        single_word_patterns = [
            r"\b[a-z\']{3,15}\b"  # Single words 4-15 characters
        ]

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
        """Извлечение частей имен и инициалов - Tier 2, используя существующие паттерны"""
        patterns = []

        # После нормализации все тексты в нижнем регистре и латинице
        # Универсальные паттерны для нормализованного текста
        initial_patterns = [
            r"\b[a-z]\.\s*[a-z]\.\s*[a-z\']{2,}\b",  # i.i.surname
            r"\b[a-z\']{2,}\s+[a-z]\.\s*[a-z]\.\b",  # surname i.i.
            r"\b[a-z]\.\s*[a-z]\.\b",  # i.i.
            r"\b[a-z]\s+[a-z]\b",  # i i (без точек)
            r"\b[a-z]{2,}\b",  # ii (слитно)
        ]

        for pattern_str in initial_patterns:
            for match in re.finditer(pattern_str, text):
                initials = match.group().strip()
                patterns.append(
                    RecallOptimizedPattern(
                        pattern=initials,
                        pattern_type="initials_pattern",
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
            # Нормализуем основной паттерн
            normalized_pattern = self.normalize_for_ac(pattern.pattern)
            pattern.pattern = normalized_pattern
            
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
                        new_variants = generator_func(normalized_pattern, language)
                        # Нормализуем каждый вариант
                        normalized_variants = [self.normalize_for_ac(v) for v in new_variants]
                        variants.update(normalized_variants)
                    except Exception:
                        continue  # If generator broke, skip

                # Update variants
                pattern.variants = list(variants)[
                    :20
                ]  # Maximum 20 variants per pattern

        return enriched_patterns

    def _generate_initial_variants(self, name: str, language: str) -> List[str]:
        """Генерация вариантов с инициалами используя существующие паттерны системы"""
        variants = []
        words = name.split()

        if len(words) >= 2:
            # Базовые варианты: First word + initial of second
            variants.append(f"{words[0]} {words[1][0]}.")
            # Initial of first + second word
            variants.append(f"{words[0][0]}. {words[1]}")

            if len(words) >= 3:
                # Все инициалы с точками (И.И.И.)
                initials_with_dots = " ".join([f"{word[0]}." for word in words])
                variants.append(initials_with_dots)
                
                # Все инициалы без точек (И И И)
                initials_no_dots = " ".join([word[0] for word in words])
                variants.append(initials_no_dots)
                
                # Все инициалы с пробелами вокруг точек (И . И . И.)
                initials_spaced = " . ".join([word[0] for word in words]) + "."
                variants.append(initials_spaced)
                
                # Все инициалы слитно (III, JD)
                initials_joined = "".join([word[0] for word in words])
                variants.append(initials_joined)

                # First word + initials of others
                rest_initials = " ".join([f"{word[0]}." for word in words[1:]])
                variants.append(f"{words[0]} {rest_initials}")
                
                # First word + initials of others без точек
                rest_initials_no_dots = " ".join([word[0] for word in words[1:]])
                variants.append(f"{words[0]} {rest_initials_no_dots}")

        # Обработка случаев с запятой (фамилия, имя)
        if "," in name:
            parts = [part.strip() for part in name.split(",")]
            if len(parts) == 2:
                surname, given_name = parts
                given_words = given_name.split()
                
                if given_words:
                    # "O'Connor, Sean" -> "O'Connor S."
                    variants.append(f"{surname} {given_words[0][0]}.")
                    
                    # "O'Connor, Sean" -> "S. O'Connor"
                    variants.append(f"{given_words[0][0]}. {surname}")
                    
                    if len(given_words) >= 2:
                        # "O'Connor, Sean Michael" -> "O'Connor S.M."
                        initials = " ".join([f"{word[0]}." for word in given_words])
                        variants.append(f"{surname} {initials}")
                        
                        # "O'Connor, Sean Michael" -> "S.M. O'Connor"
                        variants.append(f"{initials} {surname}")
                        
                        # "O'Connor, Sean Michael" -> "O'Connor SM"
                        initials_no_dots = " ".join([word[0] for word in given_words])
                        variants.append(f"{surname} {initials_no_dots}")
                        
                        # "O'Connor, Sean Michael" -> "SM O'Connor"
                        variants.append(f"{initials_no_dots} {surname}")

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
        """Расширенные варианты с дефисами/пробелами для фамилий и компаний"""
        variants = []

        # Определяем, содержит ли имя дефисы или пробелы
        has_hyphen = "-" in name
        has_space = " " in name
        
        if has_hyphen:
            # Исходная форма с дефисом: "Blunt-Krasinski"
            variants.append(name)
            
            # Форма с пробелом: "Blunt Krasinski"
            spaced = name.replace("-", " ")
            variants.append(spaced)
            
            # Форма без разделителя: "BluntKrasinski"
            no_separator = name.replace("-", "")
            variants.append(no_separator)
            
        elif has_space:
            # Исходная форма с пробелом: "Blunt Krasinski"
            variants.append(name)
            
            # Форма с дефисом: "Blunt-Krasinski"
            hyphenated = name.replace(" ", "-")
            variants.append(hyphenated)

            # Форма без разделителя: "BluntKrasinski"
            no_separator = name.replace(" ", "")
            variants.append(no_separator)
            
        else:
            # Если нет разделителей, добавляем их
            # Форма с пробелом (если имя достаточно длинное)
            if len(name) >= 6:  # Минимальная длина для разделения
                # Пытаемся найти естественное место для разделения
                # Ищем заглавные буквы в середине имени
                for i in range(1, len(name) - 1):
                    if name[i].isupper() and name[i-1].islower():
                        # Разделяем на этом месте
                        part1 = name[:i]
                        part2 = name[i:]
                        
                        # Форма с пробелом
                        spaced = f"{part1} {part2}"
                        variants.append(spaced)
                        
                        # Форма с дефисом
                        hyphenated = f"{part1}-{part2}"
                        variants.append(hyphenated)
                        
                        break

        return variants

    def _generate_name_expansions(self, name: str, language: str) -> List[str]:
        """Генерация расширений имен: диминутивы/никнеймы и фамильные окончания"""
        variants = []
        
        # Генерация диминутивов/никнеймов
        diminutive_variants = self._generate_diminutive_expansions(name, language)
        variants.extend(diminutive_variants)
        
        # Генерация фамильных окончаний
        surname_variants = self._generate_surname_endings(name, language)
        variants.extend(surname_variants)
        
        return variants

    def _generate_diminutive_expansions(self, name: str, language: str) -> List[str]:
        """Генерация диминутивов/никнеймов используя существующие словари"""
        variants = []
        
        try:
            # Загружаем словари диминутивов
            if language in ["ru", "uk"]:
                # Используем кэш
                if language not in self._diminutives_cache:
                    import json
                    from pathlib import Path
                    
                    base_path = Path(__file__).resolve().parents[5]
                    diminutive_file = base_path / "data" / f"diminutives_{language}.json"
                    
                    if diminutive_file.exists():
                        with open(diminutive_file, 'r', encoding='utf-8') as f:
                            self._diminutives_cache[language] = json.load(f)
                    else:
                        self._diminutives_cache[language] = {}
                
                diminutives = self._diminutives_cache[language]
                name_lower = name.lower()
                
                # Прямое соответствие
                if name_lower in diminutives:
                    full_name = diminutives[name_lower]
                    if full_name != name_lower:
                        variants.append(full_name.title())
                
                # Обратное соответствие - ищем диминутивы для данного имени
                for diminutive, full in diminutives.items():
                    if full == name_lower and diminutive != name_lower:
                        variants.append(diminutive.title())
                
                # Дополнительный поиск с учетом ё/е
                if 'ё' in name_lower or 'е' in name_lower:
                    # Заменяем ё на е и ищем снова
                    name_with_e = name_lower.replace('ё', 'е')
                    if name_with_e != name_lower:
                        if name_with_e in diminutives:
                            full_name = diminutives[name_with_e]
                            if full_name != name_with_e:
                                variants.append(full_name.title())
                        
                        for diminutive, full in diminutives.items():
                            if full == name_with_e and diminutive != name_with_e:
                                variants.append(diminutive.title())
            
            elif language == "en":
                # Используем кэш для английских никнеймов
                if "en" not in self._nicknames_cache:
                    import json
                    from pathlib import Path
                    
                    base_path = Path(__file__).resolve().parents[5]
                    nicknames_file = base_path / "data" / "lexicons" / "en_nicknames.json"
                    
                    if nicknames_file.exists():
                        with open(nicknames_file, 'r', encoding='utf-8') as f:
                            self._nicknames_cache["en"] = json.load(f)
                    else:
                        self._nicknames_cache["en"] = {}
                
                nicknames = self._nicknames_cache["en"]
                name_lower = name.lower()
                
                # Прямое соответствие
                if name_lower in nicknames:
                    full_name = nicknames[name_lower]
                    if full_name != name_lower:
                        variants.append(full_name.title())
                
                # Обратное соответствие - ищем никнеймы для данного имени
                for nickname, full in nicknames.items():
                    if full == name_lower and nickname != name_lower:
                        variants.append(nickname.title())
        
        except Exception as e:
            # Логируем ошибку, но не прерываем выполнение
            pass
        
        return variants

    def _generate_surname_endings(self, name: str, language: str) -> List[str]:
        """Генерация фамильных окончаний для мужских/женских форм"""
        variants = []
        
        if language not in ["ru", "uk"]:
            return variants
        
        # Паттерны для русских фамилий
        if language == "ru":
            # Мужские -> женские
            if name.endswith("ов"):
                variants.append(name[:-2] + "ова")
            elif name.endswith("ев"):
                variants.append(name[:-2] + "ева")
            elif name.endswith("ин"):
                variants.append(name[:-2] + "ина")
            elif name.endswith("ский"):
                variants.append(name[:-4] + "ская")
            elif name.endswith("цкий"):
                variants.append(name[:-4] + "цкая")
            
            # Женские -> мужские
            elif name.endswith("ова"):
                variants.append(name[:-3] + "ов")
            elif name.endswith("ева"):
                variants.append(name[:-3] + "ев")
            elif name.endswith("ина"):
                variants.append(name[:-3] + "ин")
            elif name.endswith("ская"):
                variants.append(name[:-4] + "ский")
            elif name.endswith("цкая"):
                variants.append(name[:-4] + "цкий")
        
        # Паттерны для украинских фамилий
        elif language == "uk":
            # Мужские -> женские
            if name.endswith("енко"):
                variants.append(name[:-4] + "енко")  # Остается без изменений
            elif name.endswith("ко"):
                variants.append(name[:-2] + "ко")  # Остается без изменений
            elif name.endswith("ський"):
                variants.append(name[:-5] + "ська")
            elif name.endswith("цький"):
                variants.append(name[:-5] + "цька")
            elif name.endswith("ук"):
                variants.append(name[:-2] + "ук")  # Остается без изменений
            elif name.endswith("юк"):
                variants.append(name[:-2] + "юк")  # Остается без изменений
            elif name.endswith("чук"):
                variants.append(name[:-3] + "чук")  # Остается без изменений
            
            # Женские -> мужские
            elif name.endswith("ська"):
                variants.append(name[:-4] + "ський")
            elif name.endswith("цька"):
                variants.append(name[:-4] + "цький")

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
            # Нормализуем основной паттерн перед экспортом
            normalized_pattern = self.normalize_for_ac(pattern.pattern)
            
            # Add main pattern
            target_tier = f"tier_{pattern.recall_tier}_"
            if pattern.recall_tier == 0:
                export_tiers["tier_0_exact"].append(normalized_pattern)
            elif pattern.recall_tier == 1:
                export_tiers["tier_1_high_recall"].append(normalized_pattern)
            elif pattern.recall_tier == 2:
                export_tiers["tier_2_medium_recall"].append(normalized_pattern)
            else:
                export_tiers["tier_3_broad_recall"].append(normalized_pattern)

            # Add all variants to same level (нормализация уже применена в _generate_comprehensive_variants)
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
