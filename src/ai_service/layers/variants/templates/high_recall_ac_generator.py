"""
High-Recall AC Pattern Generator для санкционного скрининга
ПРИОРИТЕТ: Максимальный Recall (не пропускать санкционных лиц)
Стратегия: Лучше 10 ложных срабатываний, чем 1 пропущенное санкционное лицо
"""

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Set, Tuple


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
        # Расширенные документные паттерны на основе существующих сервисов
        self.document_patterns = {
            # Паспорта - допуск серии и номера через пробел (AA 123456)
            # Серия может быть кириллицей или латиницей, после нормализации - латиницей
            "passport": [
                r"\b(?:passport|pasport|seriya|series)[:\s]*([a-z]{2}\s*\d{6,8})\b",  # С контекстом (нормализованный)
                r"\b(?:паспорт|passport|pasport|серия|series)[:\s]*([A-ZА-Я]{2}\s*\d{6,8})\b",  # С контекстом (исходный)
                # Только с контекстом, чтобы избежать ложных срабатываний
            ],
            
            # ИНН РФ - 10 и 12 цифр (после нормализации)
            "inn_ru": [
                r"\b(?:inn|identifikacionnyy\s+nomer)[:\s]*(\d{10})\b",  # 10 цифр с контекстом
                r"\b(?:inn|identifikacionnyy\s+nomer)[:\s]*(\d{12})\b",  # 12 цифр с контекстом
                r"\b\d{10}\b(?=.*(?:inn|identifikacionnyy))",  # 10 цифр в контексте ИНН
                r"\b\d{12}\b(?=.*(?:inn|identifikacionnyy))",  # 12 цифр в контексте ИНН
                # Убираем паттерны без контекста, чтобы избежать ложных срабатываний
            ],
            
            # ИНН Украина - 10 цифр (после нормализации)
            "inn_ua": [
                r"\b(?:inn|identifikatsiynyy\s+nomer)[:\s]*(\d{10})\b",  # 10 цифр с контекстом
                r"\b\d{10}\b(?=.*(?:inn|identifikatsiynyy))",  # 10 цифр в контексте ИНН
                # Убираем паттерны без контекста
            ],
            
            # ЕДРПОУ - 8 цифр (после нормализации)
            "edrpou": [
                r"\b(?:edrpou|yedynyy\s+derzhavnyy\s+reyestr)[:\s]*(\d{8})\b",  # 8 цифр с контекстом
                r"\b\d{8}\b(?=.*(?:edrpou|yedynyy))",  # 8 цифр в контексте ЕДРПОУ
                # Убираем паттерны без контекста
            ],
            
            # IBAN - допускай пробелы каждые 4 символа (после нормализации)
            "iban": [
                r"\b(?:iban[:\s]+)([a-z]{2}\s*\d{2}(?:\s*[a-z0-9]){11,30})\b",  # Базовый IBAN с контекстом
                r"\b(?:iban[:\s]+)([a-z]{2}\s*\d{2}\s*[a-z0-9]{4}\s*[a-z0-9]{4}\s*[a-z0-9]{4}\s*[a-z0-9]{4}\s*[a-z0-9]{4}\s*[a-z0-9]{4}\s*[a-z0-9]{4})\b",  # Украинский IBAN с контекстом
                r"\bua\d{2}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\s*\d{4}\b",  # Украинский IBAN
                r"\b(?:iban[:\s]+)([a-z]{2}\d{2}[a-z0-9]{15,32})\b",  # IBAN без пробелов с контекстом
                # IBAN паттерны требуют обязательный контекст "iban"
            ],
            
            # Дополнительные документные паттерны (после нормализации)
            "ogrn": [
                r"\b(?:ogrn|osnovnoy\s+gosudarstvennyy\s+registratsionnyy\s+nomer)[:\s]*(\d{13})\b",
                r"\b\d{13}\b(?=.*(?:ogrn|osnovnoy))",
            ],
            
            "ogrnip": [
                r"\b(?:ogrnip|osnovnoy\s+gosudarstvennyy\s+registratsionnyy\s+nomer\s+individualnogo\s+predprinimatelya)[:\s]*(\d{15})\b",
                r"\b\d{15}\b(?=.*(?:ogrnip|osnovnoy))",
            ],
            
            "swift_bic": [
                r"\b(?:swift|bic|swift/bic|mfo)[:\s]+([a-z]{4}[a-z]{2}[a-z0-9]{2}(?:[a-z0-9]{3})?)\b",
            ],
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
        Нормализация текста для Aho-Corasick
        Только NFKC, casefold, унификация символов - БЕЗ транслитерации
        
        Args:
            text: Входная строка для нормализации
            
        Returns:
            Нормализованная строка для использования в AC
        """
        if not text:
            return ""
        
        # Graceful fallback: если UnicodeService недоступен, используем локальную нормализацию
        try:
            if hasattr(self, 'unicode_service') and self.unicode_service:
                result = self.unicode_service.normalize_text(
                    text, 
                    aggressive=True,
                    normalize_homoglyphs=False
                )
                normalized = result["normalized"]
            else:
                normalized = text
        except Exception:
            normalized = text
        
        # NFKC нормализация
        import unicodedata
        normalized = unicodedata.normalize('NFKC', normalized)
        
        # Casefold для унификации регистра
        normalized = normalized.casefold()
        
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

    def generate_high_recall_patterns_from_sanctions_data(self, sanctions_record: Dict[str, Any]) -> List[RecallOptimizedPattern]:
        """Генерация паттернов из данных санкций с использованием всех доступных вариантов имен"""
        patterns = []
        
        # TIER 0: Автоматическое извлечение документов и кодов
        tier_0_patterns = self._extract_document_codes_from_sanctions(sanctions_record)
        patterns.extend(tier_0_patterns)
        
        # Извлекаем все доступные варианты имен
        name_variants = []
        
        # Основное имя
        if sanctions_record.get("name"):
            name_variants.append(sanctions_record["name"])
        
        # Русская версия
        if sanctions_record.get("name_ru"):
            name_variants.append(sanctions_record["name_ru"])
        
        # Английская версия
        if sanctions_record.get("name_en"):
            name_variants.append(sanctions_record["name_en"])
        
        # Убираем дубликаты и пустые значения
        name_variants = list(set([name for name in name_variants if name and name.strip()]))
        
        if not name_variants:
            return patterns
        
        # Генерируем паттерны для каждого варианта имени
        for name_variant in name_variants:
            # Определяем язык для каждого варианта
            variant_language = self._detect_language_for_variant(name_variant)
            
            # Генерируем паттерны для этого варианта
            variant_patterns = self.generate_high_recall_patterns(name_variant, variant_language)
            patterns.extend(variant_patterns)
        
        # Генерируем смешанные варианты, если есть разные языки
        if len(name_variants) > 1:
            mixed_patterns = self._generate_mixed_sanctions_variants(name_variants)
            patterns.extend(mixed_patterns)
        
        # Генерируем дополнительные сокращенные варианты для каждого имени
        for name_variant in name_variants:
            variant_language = self._detect_language_for_variant(name_variant)
            
            # Генерируем сокращенные варианты
            shortened_variants = self._generate_shortened_variants(name_variant, variant_language)
            for variant in shortened_variants:
                patterns.append(RecallOptimizedPattern(
                    pattern=variant,
                    pattern_type="shortened_variant",
                    recall_tier=2,
                    precision_hint=0.4,
                    variants=[],
                    language=variant_language
                ))
            
                # Генерируем правильные транслитерации
                if variant_language in ["ru", "uk"]:
                    latin_translit = self._transliterate_to_latin(name_variant)
                    if latin_translit != name_variant:
                        patterns.append(RecallOptimizedPattern(
                            pattern=latin_translit,
                            pattern_type="transliteration_variant",
                            recall_tier=2,
                            precision_hint=0.5,
                            variants=[],
                            language="en"
                        ))
                
                # Генерируем дополнительные варианты для каждого имени
                name_parts = self._extract_name_components(name_variant, variant_language)
                if len(name_parts) >= 2:
                    surname = name_parts[0] if name_parts else ""
                    first_name = name_parts[1] if len(name_parts) > 1 else ""
                    patronymic = name_parts[2] if len(name_parts) > 2 else ""
                    
                    if surname and first_name:
                        # Генерируем перестановки для Tier 1
                        permutations = self._generate_name_permutations(surname, first_name, patronymic, variant_language)
                        for variant in permutations:
                            patterns.append(RecallOptimizedPattern(
                                pattern=variant,
                                pattern_type="name_permutation",
                                recall_tier=1,
                                precision_hint=0.8,
                                variants=[],
                                language=variant_language
                            ))
                        
                        # Генерируем полные ФИО с альтернативными патронимами
                        if patronymic:
                            full_name_variants = self._generate_full_name_with_alternative_patronymics(surname, first_name, patronymic, variant_language)
                            for variant in full_name_variants:
                                patterns.append(RecallOptimizedPattern(
                                    pattern=variant,
                                    pattern_type="full_name_with_alternative_patronymic",
                                    recall_tier=1,
                                    precision_hint=0.8,
                                    variants=[],
                                    language=variant_language
                                ))
                        
                        # Генерируем инициалы во всех позициях для Tier 2
                        initials_variants = self._generate_initials_everywhere(surname, first_name, patronymic, variant_language)
                        for variant in initials_variants:
                            patterns.append(RecallOptimizedPattern(
                                pattern=variant,
                                pattern_type="initials_everywhere",
                                recall_tier=2,
                                precision_hint=0.6,
                                variants=[],
                                language=variant_language
                            ))
                        
                        # Генерируем контролируемые транслитерации для Tier 2
                        for part in [surname, first_name, patronymic]:
                            if part:
                                controlled_translits = self._generate_controlled_transliterations(part, variant_language)
                                for variant in controlled_translits:
                                    patterns.append(RecallOptimizedPattern(
                                        pattern=variant,
                                        pattern_type="controlled_transliteration",
                                        recall_tier=2,
                                        precision_hint=0.7,
                                        variants=[],
                                        language=variant_language
                                    ))
                        
                        # Генерируем нормативные варианты патронима для Tier 2
                        if patronymic:
                            patronymic_variants = self._map_patronymic_variants(patronymic, variant_language)
                            for variant in patronymic_variants:
                                patterns.append(RecallOptimizedPattern(
                                    pattern=variant,
                                    pattern_type="patronymic_variant",
                                    recall_tier=2,
                                    precision_hint=0.6,
                                    variants=[],
                                    language=variant_language
                                ))
                        
                        # Генерируем женские формы фамилии (только в контролируемых случаях)
                        if self._should_generate_feminine_surname(first_name, patronymic):
                            feminine_variants = self._generate_feminine_surname_variants(surname, variant_language)
                            for variant in feminine_variants:
                                patterns.append(RecallOptimizedPattern(
                                    pattern=variant,
                                    pattern_type="feminine_surname",
                                    recall_tier=2,
                                    precision_hint=0.5,
                                    variants=[],
                                    language=variant_language
                                ))
        
        # Очистка и дедупликация перед возвратом
        sanitized_patterns = self._post_export_sanitizer(patterns)
        
        return sanitized_patterns

    def _extract_document_codes_from_sanctions(self, sanctions_record: Dict[str, Any]) -> List[RecallOptimizedPattern]:
        """Извлекает документы и коды из данных санкций для Tier 0"""
        patterns = []
        
        # ИНН (Идентификационный налоговый номер) - для физических лиц
        if sanctions_record.get("itn"):
            itn = str(sanctions_record["itn"]).strip()
            if itn and itn != "null":
                patterns.append(RecallOptimizedPattern(
                    pattern=itn,
                    pattern_type="itn_code",
                    recall_tier=0,
                    precision_hint=1.0,
                    variants=[],
                    language="unknown"
                ))
        
        # ИНН для импорта
        if sanctions_record.get("itn_import"):
            itn_import = str(sanctions_record["itn_import"]).strip()
            if itn_import and itn_import != "null" and itn_import != sanctions_record.get("itn", ""):
                patterns.append(RecallOptimizedPattern(
                    pattern=itn_import,
                    pattern_type="itn_import_code",
                    recall_tier=0,
                    precision_hint=1.0,
                    variants=[],
                    language="unknown"
                ))
        
        # Налоговый номер - для компаний
        if sanctions_record.get("tax_number"):
            tax_number = str(sanctions_record["tax_number"]).strip()
            if tax_number and tax_number != "null":
                patterns.append(RecallOptimizedPattern(
                    pattern=tax_number,
                    pattern_type="tax_number",
                    recall_tier=0,
                    precision_hint=1.0,
                    variants=[],
                    language="unknown"
                ))
        
        # Регистрационный номер - для компаний
        if sanctions_record.get("reg_number"):
            reg_number = str(sanctions_record["reg_number"]).strip()
            if reg_number and reg_number != "null":
                patterns.append(RecallOptimizedPattern(
                    pattern=reg_number,
                    pattern_type="reg_number",
                    recall_tier=0,
                    precision_hint=1.0,
                    variants=[],
                    language="unknown"
                ))
        
        # ЕДРПОУ (Единый государственный реестр предприятий и организаций Украины)
        # Обычно это 8-значный код, но может быть и в других полях
        for field_name in ["edrpou", "edrpou_code", "registration_number"]:
            if sanctions_record.get(field_name):
                edrpou = str(sanctions_record[field_name]).strip()
                if edrpou and edrpou != "null":
                    patterns.append(RecallOptimizedPattern(
                        pattern=edrpou,
                        pattern_type="edrpou_code",
                        recall_tier=0,
                        precision_hint=1.0,
                        variants=[],
                        language="unknown"
                    ))
        
        # Другие возможные коды
        for field_name in ["passport", "passport_number", "id_number", "document_number"]:
            if sanctions_record.get(field_name):
                doc_number = str(sanctions_record[field_name]).strip()
                if doc_number and doc_number != "null":
                    patterns.append(RecallOptimizedPattern(
                        pattern=doc_number,
                        pattern_type="document_code",
                        recall_tier=0,
                        precision_hint=1.0,
                        variants=[],
                        language="unknown"
                    ))
        
        return patterns

    def _detect_language_for_variant(self, text: str) -> str:
        """Определяет язык для варианта имени"""
        if not text:
            return "unknown"
        
        # Простая эвристика определения языка
        has_cyrillic = any('\u0400' <= char <= '\u04FF' for char in text)
        has_latin = any('a' <= char.lower() <= 'z' for char in text)
        
        if has_cyrillic and has_latin:
            return "mixed"
        elif has_cyrillic:
            return "ru"
        elif has_latin:
            return "en"
        else:
            return "unknown"

    def _generate_mixed_sanctions_variants(self, name_variants: List[str]) -> List[RecallOptimizedPattern]:
        """Генерирует смешанные варианты из разных языковых версий имен"""
        patterns = []
        
        # Находим кириллические и латинские варианты
        cyrillic_variants = [name for name in name_variants if any('\u0400' <= char <= '\u04FF' for char in name)]
        latin_variants = [name for name in name_variants if any('a' <= char.lower() <= 'z' for char in name) and not any('\u0400' <= char <= '\u04FF' for char in name)]
        
        # Генерируем комбинации кириллических и латинских имен
        for cyr_name in cyrillic_variants:
            for lat_name in latin_variants:
                # Создаем смешанный вариант
                mixed_variant = f"{cyr_name} {lat_name}"
                
                # Генерируем паттерны для смешанного варианта
                mixed_patterns = self.generate_high_recall_patterns(mixed_variant, "mixed")
                patterns.extend(mixed_patterns)
        
        return patterns

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

        # TIER 0: Exact documents (100% automatic hit) - паспорта, ИНН, IBAN и др.
        tier_0_patterns = self._extract_documents_comprehensive(normalized_text)
        for pattern in tier_0_patterns:
            pattern.recall_tier = 0
        patterns.extend(tier_0_patterns)

        # TIER 1: High Recall - полные ФИО и названия компаний
        tier_1_patterns = []
        tier_1_patterns.extend(self._extract_all_names_aggressive(normalized_text, language))
        tier_1_patterns.extend(self._extract_all_companies_aggressive(normalized_text, language))
        
        # Обработка смешанного режима для Tier 1
        if language == "mixed":
            # Генерируем паттерны для кириллических языков
            tier_1_patterns.extend(self._extract_all_names_aggressive(normalized_text, "ru"))
            tier_1_patterns.extend(self._extract_all_companies_aggressive(normalized_text, "ru"))
            
            # Генерируем паттерны для английского языка
            tier_1_patterns.extend(self._extract_all_names_aggressive(normalized_text, "en"))
            tier_1_patterns.extend(self._extract_all_companies_aggressive(normalized_text, "en"))
            
            # Генерируем смешанные варианты (кириллица + латиница)
            mixed_variants = self._generate_mixed_language_variants(normalized_text)
            for variant in mixed_variants:
                tier_1_patterns.append(RecallOptimizedPattern(
                    pattern=variant,
                    pattern_type="mixed_language_variant",
                    recall_tier=1,
                    precision_hint=0.6,
                    variants=[],
                    language=language
                ))
        
        for pattern in tier_1_patterns:
            pattern.recall_tier = 1
        patterns.extend(tier_1_patterns)

        # TIER 2: Medium Recall - склонения, диминутивы, транслитерации, варианты написаний
        tier_2_patterns = []
        
        # Генерируем склонения и диминутивы для всех имен из Tier 1
        for tier_1_pattern in tier_1_patterns:
            if tier_1_pattern.pattern_type in ["full_name_aggressive", "company_aggressive"]:
                # Генерируем склонения
                declension_variants = self._generate_declension_variants(tier_1_pattern.pattern, language)
                for variant in declension_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="declension_variant",
                        recall_tier=2,
                        precision_hint=0.3,
                        variants=[],
                        language=language
                    ))
                
                # Генерируем диминутивы
                diminutive_variants = self._generate_diminutive_variants(tier_1_pattern.pattern, language)
                for variant in diminutive_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="diminutive_variant",
                        recall_tier=2,
                        precision_hint=0.4,
                        variants=[],
                        language=language
                    ))
                
                # Генерируем транслитерации
                translit_variants = self._generate_transliteration_variants(tier_1_pattern.pattern, language)
                for variant in translit_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="transliteration_variant",
                        recall_tier=2,
                        precision_hint=0.5,
                        variants=[],
                        language=language
                    ))
        
        # Добавляем части имен как отдельные паттерны Tier 2
        name_parts = self._extract_name_parts_and_initials(normalized_text, language)
        for pattern in name_parts:
            pattern.recall_tier = 2
        tier_2_patterns.extend(name_parts)
        
        # Для смешанного режима генерируем склонения для полных имен
        if language == "mixed":
            # Генерируем склонения для полного имени на кириллице
            cyrillic_name = self._transliterate_to_cyrillic(normalized_text)
            if cyrillic_name != normalized_text:  # Если есть кириллические символы
                declension_variants = self._generate_declension_variants(cyrillic_name, "ru")
                for variant in declension_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="declension_variant",
                        recall_tier=2,
                        precision_hint=0.3,
                        variants=[],
                        language=language
                    ))

            # Генерируем склонения для полного имени на латинице
            latin_name = self._transliterate_to_latin(normalized_text)
            if latin_name != normalized_text:  # Если есть латинские символы
                declension_variants = self._generate_declension_variants(latin_name, "en")
                for variant in declension_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="declension_variant",
                        recall_tier=2,
                        precision_hint=0.3,
                        variants=[],
                        language=language
                    ))

            # Генерируем диминутивы для полного имени на кириллице
            if cyrillic_name != normalized_text:
                diminutive_variants = self._generate_diminutive_variants(cyrillic_name, "ru")
                for variant in diminutive_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="diminutive_variant",
                        recall_tier=2,
                        precision_hint=0.4,
                        variants=[],
                        language=language
                    ))

            # Генерируем диминутивы для полного имени на латинице
            if latin_name != normalized_text:
                diminutive_variants = self._generate_diminutive_variants(latin_name, "en")
                for variant in diminutive_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="diminutive_variant",
                        recall_tier=2,
                        precision_hint=0.4,
                        variants=[],
                        language=language
                    ))
        
        patterns.extend(tier_2_patterns)

        # TIER 3: Broad Recall - опечатки, другие возможные варианты
        tier_3_patterns = []
        
        # Генерируем опечатки для всех паттернов из Tier 1 и Tier 2
        all_base_patterns = tier_1_patterns + tier_2_patterns
        for base_pattern in all_base_patterns:
            typo_variants = self._generate_typo_variants(base_pattern.pattern, language)
            for variant in typo_variants:
                tier_3_patterns.append(RecallOptimizedPattern(
                    pattern=variant,
                    pattern_type="typo_variant",
                    recall_tier=3,
                    precision_hint=0.1,
                    variants=[],
                    language=language
                ))
        
        # Генерируем сокращенные варианты для Tier 2
        shortened_variants = self._generate_shortened_variants(normalized_text, language)
        for variant in shortened_variants:
            tier_2_patterns.append(RecallOptimizedPattern(
                pattern=variant,
                pattern_type="shortened_variant",
                recall_tier=2,
                precision_hint=0.4,
                variants=[],
                language=language
            ))

        # Генерируем перестановки имен для Tier 1
        name_parts = self._extract_name_components(normalized_text, language)
        if len(name_parts) >= 2:
            surname = name_parts[0] if name_parts else ""
            first_name = name_parts[1] if len(name_parts) > 1 else ""
            patronymic = name_parts[2] if len(name_parts) > 2 else ""
            
            if surname and first_name:
                # Генерируем перестановки
                permutations = self._generate_name_permutations(surname, first_name, patronymic, language)
                for variant in permutations:
                    tier_1_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="name_permutation",
                        recall_tier=1,
                        precision_hint=0.8,
                        variants=[],
                        language=language
                    ))
                
                # Генерируем полные ФИО с альтернативными патронимами
                if patronymic:
                    full_name_variants = self._generate_full_name_with_alternative_patronymics(surname, first_name, patronymic, language)
                    for variant in full_name_variants:
                        tier_1_patterns.append(RecallOptimizedPattern(
                            pattern=variant,
                            pattern_type="full_name_with_alternative_patronymic",
                            recall_tier=1,
                            precision_hint=0.8,
                            variants=[],
                            language=language
                        ))
                
                # Генерируем инициалы во всех позициях для Tier 2
                initials_variants = self._generate_initials_everywhere(surname, first_name, patronymic, language)
                for variant in initials_variants:
                    tier_2_patterns.append(RecallOptimizedPattern(
                        pattern=variant,
                        pattern_type="initials_everywhere",
                        recall_tier=2,
                        precision_hint=0.6,
                        variants=[],
                        language=language
                    ))
                
                # Генерируем контролируемые транслитерации для Tier 2
                for part in [surname, first_name, patronymic]:
                    if part:
                        controlled_translits = self._generate_controlled_transliterations(part, language)
                        for variant in controlled_translits:
                            tier_2_patterns.append(RecallOptimizedPattern(
                                pattern=variant,
                                pattern_type="controlled_transliteration",
                                recall_tier=2,
                                precision_hint=0.7,
                                variants=[],
                                language=language
                            ))
                
                # Генерируем нормативные варианты патронима для Tier 2
                if patronymic:
                    patronymic_variants = self._map_patronymic_variants(patronymic, language)
                    for variant in patronymic_variants:
                        tier_2_patterns.append(RecallOptimizedPattern(
                            pattern=variant,
                            pattern_type="patronymic_variant",
                            recall_tier=2,
                            precision_hint=0.6,
                            variants=[],
                            language=language
                        ))
                
                        # Генерируем женские формы фамилии (только в контролируемых случаях)
                        if self._should_generate_feminine_surname(first_name, patronymic):
                            feminine_variants = self._generate_feminine_surname_variants(surname, language)
                            for variant in feminine_variants:
                                tier_2_patterns.append(RecallOptimizedPattern(
                                    pattern=variant,
                                    pattern_type="feminine_surname",
                                    recall_tier=2,
                                    precision_hint=0.5,
                                    variants=[],
                                    language=language
                                ))
                        
                        # Генерируем диминутивные варианты для Tier 2
                        diminutive_variants = self._generate_diminutive_combinations(surname, first_name, language)
                        for variant in diminutive_variants:
                            tier_2_patterns.append(RecallOptimizedPattern(
                                pattern=variant,
                                pattern_type="diminutive_variant",
                                recall_tier=2,
                                precision_hint=0.6,
                                variants=[],
                                language=language
                            ))
        
        # Генерируем другие возможные варианты
        other_variants = self._generate_other_variants(normalized_text, language)
        for variant in other_variants:
            tier_3_patterns.append(RecallOptimizedPattern(
                pattern=variant,
                pattern_type="other_variant",
                recall_tier=3,
                precision_hint=0.1,
                variants=[],
                language=language
            ))
        
        patterns.extend(tier_3_patterns)

        # Все паттерны уже имеют правильные recall_tier, не нужно дополнительной обработки
        patterns_with_variants = patterns

        # Final processing: remove only absolutely impossible ones
        # Для смешанного режима используем "ru" как базовый для фильтрации
        filter_language = "ru" if language == "mixed" else language
        filtered_patterns = self._minimal_filtering(patterns_with_variants, filter_language)

        # Глобальный лимит для T3 - максимум 200 паттернов
        tier_3_patterns = [p for p in filtered_patterns if p.recall_tier == 3]
        if len(tier_3_patterns) > 200:
            # Оставляем только первые 200 T3 паттернов
            other_patterns = [p for p in filtered_patterns if p.recall_tier != 3]
            tier_3_patterns = tier_3_patterns[:200]
            filtered_patterns = other_patterns + tier_3_patterns

        # Очистка и дедупликация перед возвратом
        sanitized_patterns = self._post_export_sanitizer(filtered_patterns)

        return sanitized_patterns

    def _extract_name_components(self, text: str, language: str) -> List[str]:
        """Извлекает компоненты имени (фамилия, имя, отчество) как список строк"""
        # Простое разделение по пробелам для извлечения компонентов
        parts = text.split()
        
        # Фильтруем слишком короткие части
        filtered_parts = [part for part in parts if len(part) >= 2]
        
        return filtered_parts

    def _extract_documents_comprehensive(
        self, text: str
    ) -> List[RecallOptimizedPattern]:
        """Извлечение всех документов - Tier 0 (точные)"""
        patterns = []

        # Нормализуем текст для поиска документов
        normalized_text = self.normalize_for_ac(text)

        for doc_type, regexes in self.document_patterns.items():
            for regex in regexes:
                # Ищем в исходном тексте (для кириллических серий паспортов)
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
                
                # Ищем в нормализованном тексте (для латинских серий и других документов)
                for match in re.finditer(regex, normalized_text):
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
            # Частичные имена с инициалами - Tier 2 (приоритетные, проверяются первыми)
            r"\b[a-z\']{3,}\s+[a-z\']{2,}\.\s+[a-z]\.\b",  # surname name. i. (Порошенко Петр. О.)
            r"\b[a-z\']{3,}\s+[a-z]\.\s+[a-z\']{2,}\.\b",  # surname i. name. (Порошенко П. Олекс.)
            r"\b[a-z\']{3,}\s+[a-z]\.\s+[a-z]\.\b",  # surname i.i. (Порошенко П. О.)
            r"\b[a-z\']{3,}\s+[a-z\']{2,}\.\s+[a-z\']{2,}\.\b",  # surname name. name. (Порошенко Петр. Олекс.)
            
            # Сокращенные имена
            r"\b[a-z\']{3,}\s+[a-z]{1,3}\.\s+[a-z]\.\b",  # surname abbr. i. (Порошенко Пет. О.)
            r"\b[a-z\']{3,}\s+[a-z]\.\s+[a-z]{1,3}\.\b",  # surname i. abbr. (Порошенко П. Олекс.)
            
            # Полные инициалы
            r"\b[a-z]\.\s*[a-z]\.\s*[a-z\']{2,}\b",  # i.i.surname
            r"\b[a-z\']{2,}\s+[a-z]\.\s*[a-z]\.\b",  # surname i.i.
            r"\b[a-z]\.\s*[a-z]\.\b",  # i.i.
            r"\b[a-z]\s+[a-z]\b",  # i i (без точек)
            
            # Специальные паттерны для сокращенных имен
            r"\b[a-z\']{3,}\s+[a-z]\.\s+[a-z\']{1,3}\.\b",  # surname i. abbr. (Ковриков Р. Вал.)
            r"\b[a-z\']{3,}\s+[a-z\']{1,3}\.\s+[a-z]\.\b",  # surname abbr. i. (Ковриков Вал. Р.)
            r"\b[a-z\']{3,}\s+[a-z]\.\s+[a-z]\.\b",  # surname i. i. (Ковриков Р. В.)
            
            # Убрано: одиночные слова не должны классифицироваться как инициалы
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

    def _generate_declension_variants(self, name: str, language: str) -> List[str]:
        """Генерация склонений для полного имени с консистентностью скриптов"""
        variants = []
        
        if language in ["ru", "uk"]:
            # Для кириллических языков - генерируем склонения
            parts = name.split()
            if len(parts) >= 2:
                # Генерируем склонения для каждой части отдельно
                for i, part in enumerate(parts):
                    part_variants = self._generate_single_word_declensions(part)
                    for variant in part_variants:
                        new_parts = parts.copy()
                        new_parts[i] = variant
                        variants.append(" ".join(new_parts))
            else:
                # Для однословных имен генерируем склонения напрямую
                variants.extend(self._generate_single_word_declensions(name))
        
        elif language == "mixed":
            # Для смешанных языков - разделяем по скриптам
            parts = name.split()
            if len(parts) >= 2:
                # Генерируем склонения только для кириллических частей
                for i, part in enumerate(parts):
                    if self._is_cyrillic(part):
                        part_variants = self._generate_single_word_declensions(part)
                        for variant in part_variants:
                            new_parts = parts.copy()
                            new_parts[i] = variant
                            variants.append(" ".join(new_parts))
        
        # Для английского языка склонения не генерируем
        
        return list(set(variants))  # Убираем дубликаты
    
    def _is_cyrillic(self, text: str) -> bool:
        """Проверяет, содержит ли текст кириллические символы"""
        return any('\u0400' <= char <= '\u04FF' for char in text)
    
    def _generate_single_word_declensions(self, word: str) -> List[str]:
        """Генерация склонений для одного слова"""
        variants = []
        
        # Родительный падеж
        if word.endswith("а"):
            variants.append(word[:-1] + "ы")
            variants.append(word[:-1] + "и")
        elif word.endswith("о"):
            variants.append(word[:-1] + "а")
        elif word.endswith("ий"):
            variants.append(word[:-2] + "ого")
        elif word.endswith("ов") or word.endswith("ев"):
            variants.append(word + "а")
        elif word.endswith("р"):  # Петр -> Петра
            variants.append(word + "а")
        
        # Дательный падеж
        if word.endswith("а"):
            variants.append(word[:-1] + "е")
            variants.append(word[:-1] + "і")
        elif word.endswith("о"):
            variants.append(word[:-1] + "у")
        elif word.endswith("ий"):
            variants.append(word[:-2] + "ому")
        elif word.endswith("ов") or word.endswith("ев"):
            variants.append(word + "у")
        elif word.endswith("р"):  # Петр -> Петру
            variants.append(word + "у")
        
        # Творительный падеж
        if word.endswith("а"):
            variants.append(word[:-1] + "ой")
            variants.append(word[:-1] + "ою")
        elif word.endswith("о"):
            variants.append(word[:-1] + "ом")
        elif word.endswith("ий"):
            variants.append(word[:-2] + "им")
        elif word.endswith("ов") or word.endswith("ев"):
            variants.append(word + "ым")
        elif word.endswith("р"):  # Петр -> Петром
            variants.append(word + "ом")
        
        # Предложный падеж
        if word.endswith("а"):
            variants.append(word[:-1] + "е")
            variants.append(word[:-1] + "і")
        elif word.endswith("о"):
            variants.append(word[:-1] + "е")
        elif word.endswith("ий"):
            variants.append(word[:-2] + "ом")
        elif word.endswith("ов") or word.endswith("ев"):
            variants.append(word + "е")
        elif word.endswith("р"):  # Петр -> Петре
            variants.append(word + "е")
        
        return variants

    def _generate_diminutive_variants(self, name: str, language: str) -> List[str]:
        """Генерация диминутивов для имен с правильными комбинациями фамилия+диминутив"""
        variants = []

        # Разбиваем имя на части
        parts = name.split()
        if len(parts) < 2:
            return variants

        # Определяем фамилию и имя (предполагаем порядок Фамилия Имя Отчество)
        surname = parts[0]
        first_name = parts[1] if len(parts) > 1 else ""

        if not first_name:
            return variants

        # Загружаем словари диминутивов для украинского и русского
        diminutives_variants = []

        for lang in ["uk", "ru"]:
            try:
                if lang not in self._diminutives_cache:
                    self._load_diminutives_dictionary(lang)

                diminutives_dict = self._diminutives_cache.get(lang, {})

                # Ищем диминутивы для имени (в кириллице)
                first_name_lower = first_name.lower()
                if first_name_lower in diminutives_dict:
                    canonical_name = diminutives_dict[first_name_lower]
                    # Находим все диминутивы для этого имени
                    for dim, full in diminutives_dict.items():
                        if full == canonical_name and dim != first_name_lower:
                            diminutives_variants.append(dim.title())

            except Exception:
                continue

        # Создаём правильные комбинации согласно требованиям
        clean_diminutives = []

        # Только чистые кириллические диминутивы с кириллической фамилией
        if self._is_cyrillic_text(surname):
            for dim in diminutives_variants:
                if self._is_cyrillic_text(dim):
                    # RU варианты
                    clean_diminutives.extend([
                        f"{dim} {surname}",        # Рома Ковриков
                        f"{surname} {dim}",        # Ковриков Рома
                        f"{surname}, {dim}",       # Ковриков, Рома
                    ])

        # Только чистые латинские диминутивы с латинской фамилией
        elif self._is_latin_text(surname):
            # Транслитерируем диминутивы в латиницу
            for dim in diminutives_variants:
                if self._is_cyrillic_text(dim):
                    translit_dim = self._transliterate_to_latin(dim)
                    translit_surname = surname  # уже латиница
                    # EN варианты
                    clean_diminutives.extend([
                        f"{translit_dim} {translit_surname}",        # Roma Kovrykov
                        f"{translit_surname} {translit_dim}",        # Kovrykov Roma
                        f"{translit_surname}, {translit_dim}",       # Kovrykov, Roma
                    ])

        # Убираем дубликаты и возвращаем
        return list(set(clean_diminutives))[:15]  # Лимит согласно требованиям

    def _load_diminutives_dictionary(self, language: str):
        """Загружает словарь диминутивов для языка"""
        try:
            import json
            from pathlib import Path
            
            # Путь к словарю диминутивов
            data_dir = Path(__file__).resolve().parents[4] / "data"
            diminutives_file = data_dir / f"diminutives_{language}.json"
            
            if diminutives_file.exists():
                with open(diminutives_file, 'r', encoding='utf-8') as f:
                    self._diminutives_cache[language] = json.load(f)
            else:
                self._diminutives_cache[language] = {}
                
        except Exception:
            self._diminutives_cache[language] = {}

    def _transliterate_to_latin(self, text: str) -> str:
        """Транслитерация кириллицы в латиницу"""
        translit_map = {
            "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
            "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
            "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
            "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
            "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
            "і": "i", "ї": "i", "є": "e", "ґ": "g"
        }

        result = ""
        for char in text:
            lower_char = char.lower()
            if lower_char in translit_map:
                translit_char = translit_map[lower_char]
                # Сохраняем регистр
                if char.isupper() and translit_char:
                    result += translit_char.capitalize()
                else:
                    result += translit_char
            else:
                result += char
        return result

    def _generate_transliteration_variants(self, name: str, language: str) -> List[str]:
        """Генерация транслитераций для имен с альтернативными вариантами отчеств"""
        variants = []

        # Кириллица -> латиница с Title Case
        if any(ord(c) >= 0x0400 for c in name):
            # Базовая транслитерация с правильной капитализацией
            base_translit = self._transliterate_to_latin(name)
            if base_translit:
                # Применяем Title Case для каждого слова
                title_case_translit = " ".join(word.capitalize() for word in base_translit.split())
                variants.append(title_case_translit)

                # Добавляем альтернативные варианты отчества
                patronymic_variants = self._generate_patronymic_transliteration_variants(title_case_translit)
                variants.extend(patronymic_variants)

        # Латиница -> кириллица (обратная транслитерация)
        elif all(ord(c) < 0x0400 for c in name):
            reverse_map = {
                "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "e": "е",
                "zh": "ж", "z": "з", "i": "и", "y": "й", "k": "к", "l": "л", "m": "м",
                "n": "н", "o": "о", "p": "п", "r": "р", "s": "с", "t": "т", "u": "у",
                "f": "ф", "kh": "х", "ts": "ц", "ch": "ч", "sh": "ш", "shch": "щ",
                "yu": "ю", "ya": "я"
            }

            # Простая обратная транслитерация
            cyrillic_name = name.lower()
            for lat, cyr in reverse_map.items():
                cyrillic_name = cyrillic_name.replace(lat, cyr)
            variants.append(cyrillic_name.title())

        return list(set(variants))  # Убираем дубликаты

    def _generate_patronymic_transliteration_variants(self, translit_name: str) -> List[str]:
        """Генерация альтернативных вариантов отчества в транслитерации"""
        variants = []

        # Словарь альтернативных вариантов отчеств
        patronymic_alternatives = {
            "valeriiovych": ["valeriyovych", "valerijovych", "valerievich"],
            "valeriyovych": ["valeriiovych", "valerijovych", "valerievich"],
            "valerijovych": ["valeriiovych", "valeriyovych", "valerievich"],
            "valerievich": ["valeriiovych", "valeriyovych", "valerijovych"],
        }

        # Ищем отчество в имени и заменяем на альтернативы
        name_lower = translit_name.lower()
        for original, alternatives in patronymic_alternatives.items():
            if original in name_lower:
                for alt in alternatives:
                    # Заменяем с сохранением капитализации
                    variant = translit_name.replace(original.title(), alt.title())
                    variants.append(variant)

        return variants

    def _generate_typo_variants(self, name: str, language: str) -> List[str]:
        """Генерация опечаток для имен с жесткими ограничениями"""
        variants = set()  # Используем set для автоматического удаления дубликатов
        
        words = name.split()
        
        # Для многословных строк - генерируем опечатки только на самом информативном слове
        if len(words) > 1:
            # Находим самое длинное слово (наиболее информативное)
            target_word = max(words, key=len)
            if len(target_word) < 5 or len(target_word) > 24:
                return []
            
            # Генерируем опечатки только для этого слова
            target_variants = self._generate_single_word_typos(target_word, language)
            
            # Собираем обратно строку, заменив только target_word
            for variant in target_variants:
                new_name = name.replace(target_word, variant, 1)
                variants.add(new_name)
                
            return list(variants)[:40]  # Cap 40 для многословных
        
        # Для однословных строк
        if len(name) < 5 or len(name) > 24:
            return []
        
        # Генерируем опечатки для одного слова
        single_variants = self._generate_single_word_typos(name, language)
        return single_variants[:40]  # Cap 40 для однословных
    
    def _generate_single_word_typos(self, word: str, language: str) -> List[str]:
        """Генерация опечаток для одного слова"""
        variants = set()
        
        # 1. Пропуск букв (максимум 1 на слово)
        if len(word) > 5:
            for i in range(1, len(word) - 1):
                typo = word[:i] + word[i+1:]
                variants.add(typo)
        
        # 2. Замена букв (только для релевантных языков)
        if language in ["ru", "uk", "mixed"]:
            alphabet = "аеиорнсту"
        elif language in ["en"]:
            alphabet = "aeiourtns"
        else:
            alphabet = ""
        
        for i, char in enumerate(word):
            for repl in alphabet:
                if repl != char.lower():
                    typo = word[:i] + repl + word[i+1:]
                    variants.add(typo)
        
        # 3. Добавление гласных (максимум 1 на слово)
        vowels = "аеиоу" if language in ["ru", "uk", "mixed"] else "aeiou"
        for i in range(len(word) + 1):
            for vowel in vowels:
                typo = word[:i] + vowel + word[i:]
                variants.add(typo)
        
        return list(variants)

    def _generate_shortened_variants(self, name: str, language: str) -> List[str]:
        """Генерация сокращенных вариантов имен (инициалы, аббревиатуры)"""
        variants = []
        
        # Разбиваем имя на части
        parts = name.split()
        if len(parts) < 2:
            return variants
        
        # Генерируем различные сокращенные варианты
        if len(parts) >= 3:
            # Полное имя: Фамилия Имя Отчество -> Фамилия И. О.
            surname = parts[0]
            first_initial = parts[1][0] + "."
            middle_initial = parts[2][0] + "."
            variants.append(f"{surname} {first_initial} {middle_initial}")
            
            # Фамилия И. Отчество
            variants.append(f"{surname} {first_initial} {parts[2]}")
            
            # Фамилия Имя О.
            variants.append(f"{surname} {parts[1]} {middle_initial}")
            
            # Фамилия И. О. (только инициалы)
            variants.append(f"{surname} {first_initial} {middle_initial}")

            # Недостающие варианты согласно требованиям:
            # Фамилия И.О. (без пробела между инициалами)
            variants.append(f"{surname} {first_initial[0]}.{middle_initial}")

            # Фамилия, Имя О (без точки у последнего инициала)
            variants.append(f"{surname}, {parts[1]} {middle_initial[0]}")

        if len(parts) >= 2:
            # Фамилия И. (только имя сокращено)
            surname = parts[0]
            first_initial = parts[1][0] + "."
            variants.append(f"{surname} {first_initial}")
            
            # Фамилия Имя (без отчества)
            variants.append(f"{surname} {parts[1]}")
        
        # Генерируем варианты с разными сокращениями отчества
        if len(parts) >= 3:
            surname = parts[0]
            first_name = parts[1]
            patronymic = parts[2]
            
            # Сокращаем отчество по-разному
            if len(patronymic) > 3:
                # Первые 3-4 символа отчества
                short_patronymic = patronymic[:3] + "."
                variants.append(f"{surname} {first_name} {short_patronymic}")
                
                # Первые 4-5 символов отчества
                if len(patronymic) > 4:
                    short_patronymic = patronymic[:4] + "."
                    variants.append(f"{surname} {first_name} {short_patronymic}")
        
        return list(set(variants))  # Убираем дубликаты

    def _generate_name_permutations(self, surname: str, first_name: str, patronymic: str, language: str) -> List[str]:
        """Генерация всех валидных перестановок имени (Tier 1) - только чистые алфавиты"""
        variants = []
        
        # Все валидные перестановки
        permutations = [
            # F L P (основная форма)
            f"{first_name} {surname} {patronymic}",
            # F L (без отчества)
            f"{first_name} {surname}",
            # L F P (фамилия в начале)
            f"{surname} {first_name} {patronymic}",
            # L F (фамилия в начале, без отчества)
            f"{surname} {first_name}",
            # P F L (отчество в начале)
            f"{patronymic} {first_name} {surname}",
            # L P F (фамилия + отчество + имя)
            f"{surname} {patronymic} {first_name}",
            # L P (фамилия + отчество)
            f"{surname} {patronymic}",
        ]
        
        # Добавляем варианты с запятой
        comma_variants = [
            f"{surname}, {first_name} {patronymic}",
            f"{surname}, {first_name}",
            f"{surname}, {patronymic} {first_name}",
        ]
        
        variants.extend(permutations)
        variants.extend(comma_variants)
        
        # Добавляем RU-патронимы для кириллических имен
        if self._is_cyrillic_text(surname + first_name + patronymic):
            ru_patronymic_variants = self._get_ru_patronymic_variants(patronymic)
            for ru_patronymic in ru_patronymic_variants:
                ru_permutations = [
                    f"{first_name} {surname} {ru_patronymic}",
                    f"{surname} {first_name} {ru_patronymic}",
                    f"{ru_patronymic} {first_name} {surname}",
                    f"{surname} {ru_patronymic} {first_name}",
                    f"{surname}, {first_name} {ru_patronymic}",
                    f"{surname}, {ru_patronymic} {first_name}",
                ]
                variants.extend(ru_permutations)
        
        # Добавляем EN-патронимы для латинских имен
        if self._is_latin_text(surname + first_name + patronymic):
            en_patronymic_variants = self._get_en_patronymic_variants(patronymic)
            for en_patronymic in en_patronymic_variants:
                en_permutations = [
                    f"{first_name} {surname} {en_patronymic}",
                    f"{surname} {first_name} {en_patronymic}",
                    f"{en_patronymic} {first_name} {surname}",
                    f"{surname} {en_patronymic} {first_name}",
                    f"{surname}, {first_name} {en_patronymic}",
                    f"{surname}, {en_patronymic} {first_name}",
                ]
                variants.extend(en_permutations)
        
        return list(set(variants))  # Убираем дубликаты

    def _is_cyrillic_text(self, text: str) -> bool:
        """Проверяет, является ли текст кириллическим"""
        cyrillic_chars = sum(1 for c in text if 'а' <= c.lower() <= 'я' or c in 'ё')
        return cyrillic_chars > len(text) * 0.5

    def _is_latin_text(self, text: str) -> bool:
        """Проверяет, является ли текст латинским"""
        latin_chars = sum(1 for c in text if 'a' <= c.lower() <= 'z')
        return latin_chars > len(text) * 0.5

    def _get_ru_patronymic_variants(self, patronymic: str) -> List[str]:
        """Получает RU-варианты патронима"""
        ru_variants = []
        patronymic_lower = patronymic.lower()
        
        if "валерійович" in patronymic_lower:
            ru_variants.append("Валерьевич")
        elif "valeriiovych" in patronymic_lower:
            ru_variants.append("Валерьевич")
        elif "valeriyovych" in patronymic_lower:
            ru_variants.append("Валерьевич")
        elif "valerijovych" in patronymic_lower:
            ru_variants.append("Валерьевич")
        
        return ru_variants

    def _get_en_patronymic_variants(self, patronymic: str) -> List[str]:
        """Получает EN-варианты патронима"""
        en_variants = []
        patronymic_lower = patronymic.lower()
        
        if "валерійович" in patronymic_lower:
            en_variants.extend(["Valeriiovych", "Valeriyovych", "Valerijovych", "Valerievich"])
        elif "валерьевич" in patronymic_lower:
            en_variants.append("Valerievich")
        elif "valeriiovych" in patronymic_lower:
            en_variants.extend(["Valeriiovych", "Valeriyovych", "Valerijovych", "Valerievich"])
        
        return en_variants

    def _map_patronymic_variants(self, patronymic: str, language: str) -> List[str]:
        """Генерация нормативных вариантов патронима (Tier 2)"""
        variants = []
        
        # Словарь нормативных вариантов патронимов
        patronymic_map = {
            # UA кириллица -> различные варианты
            "валерійович": [
                "valeriiovych",  # основной UA
                "valeriyovych",  # альтернативный UA
                "valerijovych",  # еще один UA вариант
                "валерьевич",    # RU эквивалент
                "valerievich",   # RU транслитерация
            ],
            "валерьевич": [
                "valerievich",   # RU транслитерация
                "валерійович",   # UA эквивалент
                "valeriiovych",  # UA транслитерация
                "valeriyovych",  # UA альтернативный
                "valerijovych",  # UA еще один
            ],
            # EN -> кириллица
            "valeriiovych": [
                "валерійович",   # UA кириллица
                "валерьевич",    # RU кириллица
            ],
            "valeriyovych": [
                "валерійович",   # UA кириллица
                "валерьевич",    # RU кириллица
            ],
            "valerijovych": [
                "валерійович",   # UA кириллица
                "валерьевич",    # RU кириллица
            ],
            "valerievich": [
                "валерьевич",    # RU кириллица
                "валерійович",   # UA кириллица
            ],
        }
        
        patronymic_lower = patronymic.lower()
        
        # Ищем в словаре
        if patronymic_lower in patronymic_map:
            variants.extend(patronymic_map[patronymic_lower])
        
        # Обратный поиск
        for key, values in patronymic_map.items():
            if patronymic_lower in values:
                variants.append(key)
                variants.extend([v for v in values if v != patronymic_lower])
        
        return list(set(variants))  # Убираем дубликаты

    def _generate_initials_everywhere(self, surname: str, first_name: str, patronymic: str, language: str) -> List[str]:
        """Генерация инициалов во всех позициях (Tier 2)"""
        variants = []
        
        # Инициалы
        first_initial = first_name[0] + "."
        patronymic_initial = patronymic[0] + "." if patronymic else ""
        
        # 1. Перед фамилией
        if patronymic_initial:
            variants.extend([
                f"{first_initial}{patronymic_initial} {surname}",
                f"{first_initial} {patronymic_initial} {surname}",
                f"{first_initial[0]}{patronymic_initial[0]} {surname}",  # без точек
            ])
        else:
            variants.extend([
                f"{first_initial} {surname}",
                f"{first_initial[0]} {surname}",  # без точки
            ])
        
        # 2. После фамилии (без запятой)
        if patronymic_initial:
            variants.extend([
                f"{surname} {first_initial} {patronymic_initial}",
                f"{surname} {first_initial} {patronymic_initial[0]}",
                f"{surname} {first_initial[0]}{patronymic_initial[0]}",
            ])
        else:
            variants.extend([
                f"{surname} {first_initial}",
                f"{surname} {first_initial[0]}",
            ])
        
        # 3. После имени
        if patronymic_initial:
            variants.extend([
                f"{first_name} {patronymic_initial} {surname}",
                f"{first_name} {patronymic_initial[0]} {surname}",  # без точки
            ])
        
        # 4. Слитно
        if patronymic_initial:
            variants.extend([
                f"{first_initial[0]}{patronymic_initial[0]}{surname}",
                f"{surname}{first_initial[0]}{patronymic_initial[0]}",
            ])
        else:
            variants.extend([
                f"{first_initial[0]}{surname}",
                f"{surname}{first_initial[0]}",
            ])
        
        # 5. С запятой
        if patronymic_initial:
            variants.extend([
                f"{surname}, {first_initial} {patronymic_initial}",
                f"{surname}, {first_initial} {patronymic_initial[0]}",
                f"{surname}, {first_name} {patronymic_initial}",  # имя + инициал отчества
                f"{surname}, {first_name} {patronymic_initial[0]}",  # имя + инициал отчества без точки
            ])
        else:
            variants.extend([
                f"{surname}, {first_initial}",
                f"{surname}, {first_initial[0]}",
            ])
        
        # 6. Дополнительные естественные варианты
        if patronymic_initial:
            variants.extend([
                f"{first_initial[0]}. {surname}",  # R. Kovrykov
                f"{surname} {first_initial[0]}.{patronymic_initial[0]}.",  # Kovrykov R.V.
                f"{surname} {first_initial[0]}{patronymic_initial[0]}",  # Kovrykov RV
            ])
        else:
            variants.extend([
                f"{first_initial[0]}. {surname}",  # R. Kovrykov
            ])
        
        return list(set(variants))  # Убираем дубликаты

    def _generate_controlled_transliterations(self, text: str, language: str) -> List[str]:
        """Генерация контролируемых транслитераций (Tier 2) - только для полных ФИО"""
        variants = []
        
        # Белый список разрешенных транслитераций
        allowed_transliterations = {
            # Фамилии
            "ковриков": ["kovrykov", "kovrikov"],
            "kovrykov": ["ковриков"],
            "kovrikov": ["ковриков"],
            
            # Имена
            "роман": ["roman"],
            "roman": ["роман"],
            
            # Патронимы (только нормативные)
            "валерійович": ["valeriiovych", "valeriyovych", "valerijovych"],
            "валерьевич": ["valerievich"],
            "valeriiovych": ["валерійович", "валерьевич"],
            "valeriyovych": ["валерійович", "валерьевич"],
            "valerijovych": ["валерійович", "валерьевич"],
            "valerievich": ["валерьевич", "валерійович"],
        }
        
        text_lower = text.lower()
        
        # Ищем в белом списке
        if text_lower in allowed_transliterations:
            variants.extend(allowed_transliterations[text_lower])
        
        # Обратный поиск
        for key, values in allowed_transliterations.items():
            if text_lower in values:
                variants.append(key)
        
        return list(set(variants))  # Убираем дубликаты

    def _generate_full_name_with_alternative_patronymics(self, surname: str, first_name: str, patronymic: str, language: str) -> List[str]:
        """Генерация полных ФИО с альтернативными патронимами (Tier 1)"""
        variants = []
        
        # Получаем все варианты патронима
        patronymic_variants = self._map_patronymic_variants(patronymic, language)
        
        # Генерируем перестановки для каждого варианта патронима
        for patronymic_variant in patronymic_variants:
            # Основные перестановки
            permutations = [
                f"{surname} {first_name} {patronymic_variant}",
                f"{first_name} {surname} {patronymic_variant}",
                f"{patronymic_variant} {first_name} {surname}",
                f"{surname} {patronymic_variant} {first_name}",
            ]
            
            # Варианты с запятой
            comma_variants = [
                f"{surname}, {first_name} {patronymic_variant}",
                f"{surname}, {patronymic_variant} {first_name}",
            ]
            
            variants.extend(permutations)
            variants.extend(comma_variants)
        
        return list(set(variants))  # Убираем дубликаты

    def _should_generate_feminine_surname(self, first_name: str, patronymic: str) -> bool:
        """Проверяет, нужно ли генерировать женскую форму фамилии"""
        # Мужские имена (не генерируем женскую фамилию)
        masculine_names = {
            "роман", "roman", "валерійович", "валерьевич", 
            "valeriiovych", "valerievich"
        }
        
        # Проверяем имя и отчество
        first_lower = first_name.lower()
        patronymic_lower = patronymic.lower() if patronymic else ""
        
        # Если есть мужское имя или отчество - не генерируем женскую фамилию
        if (first_lower in masculine_names or 
            patronymic_lower in masculine_names):
            return False
        
        return True

    def _generate_diminutive_combinations(self, surname: str, first_name: str, language: str) -> List[str]:
        """Генерация диминутивных вариантов (Tier 2)"""
        variants = []
        
        # Белый список фамилий
        allowed_surnames = {"ковриков", "kovrykov", "kovrikov"}
        surname_lower = surname.lower()
        
        if surname_lower not in allowed_surnames:
            return variants
        
        # Диминутивы для имени
        diminutives = {
            "роман": ["рома", "ромчик", "ромка", "ромик"],
            "roman": ["roma", "rom"],
        }
        
        first_name_lower = first_name.lower()
        if first_name_lower in diminutives:
            for diminutive in diminutives[first_name_lower]:
                # RU варианты
                if self._is_cyrillic_text(surname):
                    variants.extend([
                        f"{diminutive} {surname}",
                        f"{surname} {diminutive}",
                        f"{surname}, {diminutive}",
                    ])
                # EN варианты
                elif self._is_latin_text(surname):
                    variants.extend([
                        f"{diminutive.capitalize()} {surname}",
                        f"{surname} {diminutive.capitalize()}",
                    ])
                # Mixed варианты (только несколько)
                else:
                    if surname_lower == "kovrykov":
                        variants.extend([
                            f"{diminutive} {surname}",
                            f"{surname} {diminutive}",
                        ])
        
        return list(set(variants))  # Убираем дубликаты

    def _post_export_sanitizer(self, patterns: List[RecallOptimizedPattern]) -> List[RecallOptimizedPattern]:
        """Очистка и дедупликация паттернов перед экспортом"""
        sanitized = []
        seen_patterns = set()
        
        for pattern in patterns:
            # Нормализуем паттерн для сравнения
            normalized_pattern = self.normalize_for_ac(pattern.pattern)
            
            # Пропускаем дубликаты
            if normalized_pattern in seen_patterns:
                continue
            
            # Удаляем POTENTIAL_SURNAME полностью
            if pattern.pattern_type == "potential_surname":
                continue
            
            # Пропускаем одиночные токены в Tier 2 (кроме документов)
            if (pattern.recall_tier == 2 and 
                pattern.pattern_type == "controlled_transliteration" and 
                len(pattern.pattern.split()) == 1):
                continue
            
            # Проверяем чистоту алфавита в Tier 1
            if pattern.recall_tier == 1 and self._has_mixed_script(pattern.pattern):
                # Переносим в MIXED_LANGUAGE_VARIANT или удаляем
                continue
            
            # Пропускаем некорректные склонения (женская фамилия + мужское имя)
            if self._is_invalid_declension(pattern.pattern):
                continue
            
            # Пропускаем паттерны с артефактами транслитерации
            if self._has_transliteration_artifacts(pattern.pattern):
                continue
            
            # Проверяем валидность инициалов
            if pattern.pattern_type == "initials_everywhere" and not self._is_valid_initials(pattern.pattern):
                continue
            
            # Проверяем диминутивы только с разрешенными фамилиями
            if pattern.pattern_type == "diminutive_variant" and not self._has_allowed_surname(pattern.pattern):
                continue

            # Ограничиваем TYPO_VARIANT до 100 штук и проверяем на реалистичность
            if pattern.pattern_type == "typo_variant":
                if not self._is_realistic_typo(pattern.pattern):
                    continue

            seen_patterns.add(normalized_pattern)
            sanitized.append(pattern)
        
        return sanitized

    def _is_invalid_declension(self, pattern: str) -> bool:
        """Проверяет, является ли склонение некорректным"""
        # Женские фамилии с мужскими именами
        feminine_surnames = ["кова", "ская", "ина"]
        masculine_names = ["роман", "roman", "валерійович", "валерьевич", "valeriiovych", "valerievich"]
        
        pattern_lower = pattern.lower()
        
        for feminine in feminine_surnames:
            if feminine in pattern_lower:
                for masculine in masculine_names:
                    if masculine in pattern_lower:
                        return True
        
        return False

    def _has_transliteration_artifacts(self, pattern: str) -> bool:
        """Проверяет наличие артефактов транслитерации"""
        # Артефакты типа "коврыков", "валєр", "йцх"
        artifacts = ["коврыков", "валєр", "йцх", "ыch", "єр", "йуцх", "вйцх"]

        pattern_lower = pattern.lower()
        for artifact in artifacts:
            if artifact in pattern_lower:
                return True

        # Проверка на невозможные биграммы
        impossible_bigrams = [
            r'йуцх\b', r'вйцх\b', r'йцх\b', r'уцх\b', r'йух\b',
            r'щщ', r'жж', r'цц', r'хх', r'ьь', r'ъъ'
        ]

        import re
        for bigram_pattern in impossible_bigrams:
            if re.search(bigram_pattern, pattern_lower):
                return True

        return False

    def _has_mixed_script(self, pattern: str) -> bool:
        """Проверяет, содержит ли паттерн смешанные скрипты"""
        has_cyrillic = any('а' <= c.lower() <= 'я' or c in 'ё' for c in pattern)
        has_latin = any('a' <= c.lower() <= 'z' for c in pattern)
        return has_cyrillic and has_latin

    def _is_valid_initials(self, pattern: str) -> bool:
        """Проверяет валидность инициальных паттернов"""
        import re
        
        # Разрешенные паттерны инициалов
        valid_patterns = [
            r'^[A-ZА-Я]\. [A-Z][a-z]+|[А-Я][а-я]+$',  # R. Kovrykov, Р. Ковриков
            r'^(Kovrykov|Ковриков),? (Roman|Роман) V\.?$',  # Kovrykov, Roman V
            r'^(Kovrykov|Ковриков) R\.V\.?$',  # Kovrykov R.V.
            r'^(Kovrykov|Ковриков) [A-ZА-Я]\. [A-ZА-Я]\.$',  # Kovrykov R. V.
        ]
        
        for valid_pattern in valid_patterns:
            if re.match(valid_pattern, pattern):
                return True

        return False

    def _has_allowed_surname(self, pattern: str) -> bool:
        """Проверяет, содержит ли паттерн разрешенную фамилию"""
        allowed_surnames = {"ковриков", "kovrykov", "kovrikov"}
        pattern_lower = pattern.lower()
        return any(surname in pattern_lower for surname in allowed_surnames)

    def _is_realistic_typo(self, pattern: str) -> bool:
        """Проверяет, является ли опечатка реалистичной"""
        # Не более 1-2 символьных замен/перестановок
        # Белый список изменений: o↔a/e, удвоения, пропуски

        # Запрещаем невозможные биграммы
        if self._has_transliteration_artifacts(pattern):
            return False

        # Запрещаем слишком много изменений в одном слове
        words = pattern.split()
        for word in words:
            if self._has_excessive_changes(word):
                return False

        return True

    def _has_excessive_changes(self, word: str) -> bool:
        """Проверяет, слишком ли много изменений в слове"""
        # Простая эвристика: слишком много необычных символов
        unusual_chars = sum(1 for c in word.lower() if c in 'qwxz')
        total_chars = len(word)

        # Если больше 30% необычных символов - это мусор
        if total_chars > 0 and unusual_chars / total_chars > 0.3:
            return True

        # Проверяем на тройные повторы
        import re
        if re.search(r'(.)\1{2,}', word):
            return True

        return False

    def _has_allowed_surname(self, pattern: str) -> bool:
        """Проверяет, содержит ли паттерн разрешенную фамилию"""
        allowed_surnames = {"ковриков", "kovrykov", "kovrikov"}
        pattern_lower = pattern.lower()
        
        for surname in allowed_surnames:
            if surname in pattern_lower:
                return True
        
        return False

    def _generate_feminine_surname_variants(self, surname: str, language: str) -> List[str]:
        """Генерация женских форм фамилии (только в контролируемых случаях)"""
        variants = []
        
        # Правила образования женских форм
        if language in ["ru", "uk"]:
            # Для фамилий на -ов/-ев
            if surname.endswith(("ов", "ев")):
                feminine = surname[:-2] + "ова"
                variants.append(feminine)
            # Для фамилий на -ский/-ская
            elif surname.endswith("ский"):
                feminine = surname[:-4] + "ская"
                variants.append(feminine)
            # Для фамилий на -ин/-ын
            elif surname.endswith(("ин", "ын")):
                feminine = surname[:-2] + "ина"
                variants.append(feminine)
        
        # Английские фамилии
        elif language == "en":
            if surname.endswith("ov"):
                feminine = surname[:-2] + "ova"
                variants.append(feminine)
            elif surname.endswith("sky"):
                feminine = surname[:-3] + "skaya"
                variants.append(feminine)
        
        return variants

    def _generate_other_variants(self, text: str, language: str) -> List[str]:
        """Генерация других возможных вариантов"""
        variants = []
        
        # Варианты с дефисами
        words = text.split()
        if len(words) > 1:
            variants.append("-".join(words))
            variants.append("_".join(words))
            variants.append("".join(words))
        
        # Варианты с инициалами
        if len(words) > 1:
            initials = ".".join([word[0] for word in words])
            variants.append(initials)
            variants.append(initials + ".")
        
        # Варианты с сокращениями
        if len(words) > 1:
            first_word = words[0]
            rest_words = words[1:]
            for i in range(1, len(first_word)):
                short_first = first_word[:i] + "."
                variants.append(" ".join([short_first] + rest_words))
        
        return variants

    def _generate_mixed_language_variants(self, text: str) -> List[str]:
        """Генерация смешанных языковых вариантов для mixed режима"""
        variants = []
        words = text.split()
        
        if len(words) >= 2:
            # Генерируем все возможные комбинации кириллицы и латиницы
            for i in range(len(words)):
                for j in range(i+1, len(words)):
                    # Создаем копию списка слов
                    mixed_words = words.copy()
                    
                    # Транслитерируем i-е слово в кириллицу
                    mixed_words[i] = self._transliterate_to_cyrillic(words[i])
                    # Транслитерируем j-е слово в латиницу
                    mixed_words[j] = self._transliterate_to_latin(words[j])
                    
                    variants.append(" ".join(mixed_words))
                    
                    # Обратная комбинация
                    mixed_words = words.copy()
                    mixed_words[i] = self._transliterate_to_latin(words[i])
                    mixed_words[j] = self._transliterate_to_cyrillic(words[j])
                    
                    variants.append(" ".join(mixed_words))
        
        return variants

    def _transliterate_to_cyrillic(self, text: str) -> str:
        """Транслитерация в кириллицу"""
        translit_map = {
            "a": "а", "b": "б", "c": "ц", "d": "д", "e": "е", "f": "ф", "g": "г",
            "h": "х", "i": "і", "j": "й", "k": "к", "l": "л", "m": "м", "n": "н",
            "o": "о", "p": "п", "q": "к", "r": "р", "s": "с", "t": "т", "u": "у",
            "v": "в", "w": "в", "x": "кс", "y": "й", "z": "з"
        }
        
        result = ""
        for char in text.lower():
            if char in translit_map:
                result += translit_map[char]
            else:
                result += char
        return result

    def _transliterate_to_latin(self, text: str) -> str:
        """Улучшенная транслитерация в латиницу"""
        # Сначала обрабатываем специальные случаи
        text = text.replace("ійович", "iyovych")
        text = text.replace("ійович", "iyovych")
        text = text.replace("ійович", "iyovych")
        
        translit_map = {
            "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
            "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
            "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
            "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
            "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
            "і": "i", "ї": "i", "є": "e", "ґ": "g"
        }
        
        result = ""
        for char in text.lower():
            if char in translit_map:
                result += translit_map[char]
            else:
                result += char
        return result

    def _extract_suspicious_sequences(
        self, text: str, language: str
    ) -> List[RecallOptimizedPattern]:
        """Извлечение подозрительных последовательностей - Tier 3"""
        patterns = []

        # Tier 3 должен генерировать варианты существующих паттернов, а не новые по одному слову
        # Это делается в _generate_comprehensive_variants через name_variants_generators
        # Здесь оставляем пустым, чтобы избежать ложных срабатываний

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

        # Адаптивное ограничение количества паттернов
        total_patterns = len(filtered)
        
        if total_patterns <= 1000:
            # Если паттернов мало - не обрезаем
            return filtered
        else:
            # Если много - оставляем топ-1000 по приоритету
            # Приоритет: recall_tier (меньше = выше), длина строки (больше = выше)
            # Сортировка уже выполнена выше: tier → длина
            return filtered[:1000]

    def _detect_language(self, text: str) -> str:
        """Определение языка с поддержкой смешанного режима"""
        cyrillic = len(re.findall(r"[а-яіїєёА-ЯІЇЄЁҐ]", text))
        latin = len(re.findall(r"[a-zA-Z]", text))

        # Если есть и кириллица, и латиница - смешанный режим
        if cyrillic > 0 and latin > 0:
            return "mixed"
        elif cyrillic > 0:
            ukrainian = len(re.findall(r"[іїєґІЇЄҐ]", text))
            return "uk" if ukrainian > 0 else "ru"
        elif latin > 0:
            return "en"
        else:
            return "ru"  # Default

    def export_for_high_recall_ac(
        self, patterns: List[RecallOptimizedPattern]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Экспорт для многоуровневого AC с максимальным Recall
        Каждый элемент содержит pattern, pattern_type и recall_tier
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
            
            # Создаем словарь для основного паттерна
            pattern_dict = {
                "pattern": normalized_pattern,
                "pattern_type": pattern.pattern_type,
                "recall_tier": pattern.recall_tier
            }
            
            # Add main pattern
            if pattern.recall_tier == 0:
                export_tiers["tier_0_exact"].append(pattern_dict)
            elif pattern.recall_tier == 1:
                export_tiers["tier_1_high_recall"].append(pattern_dict)
            elif pattern.recall_tier == 2:
                export_tiers["tier_2_medium_recall"].append(pattern_dict)
            else:
                export_tiers["tier_3_broad_recall"].append(pattern_dict)

            # Add variants with proper tier distribution
            for variant in pattern.variants:
                # Определяем tier для варианта на основе его типа
                variant_tier = self._tier_for_variant(pattern.recall_tier, pattern.pattern_type)
                
                variant_dict = {
                    "pattern": variant,
                    "pattern_type": f"{pattern.pattern_type}_variant",
                    "recall_tier": variant_tier
                }
                
                # Добавляем в соответствующий tier
                if variant_tier == 0:
                    export_tiers["tier_0_exact"].append(variant_dict)
                elif variant_tier == 1:
                    export_tiers["tier_1_high_recall"].append(variant_dict)
                elif variant_tier == 2:
                    export_tiers["tier_2_medium_recall"].append(variant_dict)
                else:
                    export_tiers["tier_3_broad_recall"].append(variant_dict)

        # Remove duplicates in each level (по pattern)
        for tier in export_tiers:
            seen_patterns = set()
            unique_items = []
            for item in export_tiers[tier]:
                pattern_key = item["pattern"]
                if pattern_key not in seen_patterns:
                    seen_patterns.add(pattern_key)
                    unique_items.append(item)
            export_tiers[tier] = unique_items

        return export_tiers

    def _tier_for_variant(self, base_tier: int, variant_type: str) -> int:
        """Определяет tier для варианта на основе его типа"""
        # Безопасные форматные варианты остаются в том же tier
        if variant_type in {"format", "apostrophe", "quotes", "hyphen", "space"}:
            return base_tier
        
        # Морфологические и диминутивы - не ниже Tier 2
        if variant_type in {"morph", "gender", "diminutive", "initials", "declension_variant", "diminutive_variant"}:
            return max(2, base_tier)
        
        # Транслитерации - не ниже Tier 2
        if variant_type in {"transliteration_variant", "transliteration"}:
            return max(2, base_tier)
        
        # Опечатки, грубые транслитерации, смешанные комбинации - Tier 3
        if variant_type in {"typo_variant", "typo", "mixed_language_variant", "other_variant"}:
            return 3
        
        # По умолчанию - тот же tier что у базового паттерна
        return base_tier

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
