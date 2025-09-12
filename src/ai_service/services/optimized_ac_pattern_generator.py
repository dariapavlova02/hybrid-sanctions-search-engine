"""
Оптимизированный генератор паттернов для Aho-Corasick с минимизацией false positives
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from ..utils import get_logger


@dataclass
class OptimizedPattern:
    """Оптимизированный паттерн для AC поиска"""

    pattern: str
    pattern_type: str
    context_required: bool  # Requires contextual confirmation
    min_match_length: int  # Minimum length for triggering
    boost_score: float  # Boost coefficient
    language: str
    confidence: float
    metadata: Dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class OptimizedACPatternGenerator:
    """Оптимизированный генератор паттернов для поиска с минимальными FP"""

    def __init__(self):
        self.logger = get_logger(__name__)

        # Critical context words for different languages
        self.context_triggers = {
            "ru": {
                "payment": [
                    "платеж",
                    "оплата",
                    "перевод",
                    "перечисление",
                    "зачисление",
                ],
                "contract": ["договор", "контракт", "соглашение", "сделка"],
                "recipient": ["получатель", "бенефициар", "в пользу", "на имя"],
                "sender": ["отправитель", "плательщик", "от имени"],
                "legal": ["ООО", "ЗАО", "ОАО", "ПАО", "ИП", "ФЛ"],
            },
            "uk": {
                "payment": ["платіж", "оплата", "переказ", "перерахування"],
                "contract": ["договір", "контракт", "угода", "домовленість"],
                "recipient": ["одержувач", "бенефіціар", "на користь", "на ім'я"],
                "sender": ["відправник", "платник", "від імені"],
                "legal": ["ТОВ", "ПАТ", "АТ", "ПрАТ", "ФОП", "ФО"],
            },
            "en": {
                "payment": ["payment", "transfer", "remittance", "wire", "funds"],
                "contract": ["contract", "agreement", "deal", "arrangement"],
                "recipient": ["beneficiary", "payee", "recipient", "to"],
                "sender": ["payer", "sender", "from"],
                "legal": ["LLC", "Inc", "Ltd", "Corp", "Co", "LP"],
            },
        }

        # Stop words that should not be patterns by themselves
        self.stop_patterns = {
            "ru": {
                "для",
                "или",
                "его",
                "этот",
                "один",
                "два",
                "три",
                "год",
                "день",
                "время",
            },
            "uk": {
                "для",
                "або",
                "його",
                "цей",
                "один",
                "два",
                "три",
                "рік",
                "день",
                "час",
            },
            "en": {
                "for",
                "or",
                "his",
                "this",
                "one",
                "two",
                "three",
                "year",
                "day",
                "time",
            },
        }

        # Document patterns (high accuracy)
        self.document_patterns = {
            "passport": [
                r"\b[A-Z]{2}\d{6}\b",  # Foreign passport
                r"\b\d{2}\s?\d{2}\s?\d{6}\b",  # Ukrainian passport
                r"\b[А-Я]{2}\d{6}\b",  # Cyrillic passport
            ],
            "tax_id": [
                r"\b\d{10}\b",  # Ukrainian tax ID
                r"\b\d{12}\b",  # Individual tax number
            ],
            "edrpou": [r"\b\d{8}\b", r"\b\d{6}\b"],  # EDRPOU  # Old EDRPOU format
            "iban": [
                r"\bUA\d{2}[A-Z0-9]{25}\b",  # Ukrainian IBAN (29 chars total)
                # Generic IBAN: 2 letters + 2 digits + 11-30 alphanum (total length 15-34)
                r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",
            ],
        }

        # Minimum requirements for triggers
        self.min_requirements = {
            "surname_only": {"min_length": 4, "context_required": True},
            "name_only": {"min_length": 3, "context_required": True},
            "full_name": {"min_length": 6, "context_required": False},
            "company_name": {"min_length": 5, "context_required": False},
            "document": {"min_length": 6, "context_required": False},
        }

        self.logger.info("OptimizedACPatternGenerator initialized")

    def generate_patterns(
        self,
        text: str,
        entity_type: str = "auto",
        language: str = "auto",
        entity_metadata: Dict = None,
    ) -> List[OptimizedPattern]:
        """
        Main pattern generation method (compatibility wrapper)
        """
        return self.generate_high_precision_patterns(text, language, entity_metadata)

    def generate_high_precision_patterns(
        self, text: str, language: str = "auto", entity_metadata: Dict = None
    ) -> List[OptimizedPattern]:
        """
        Генерация высокоточных паттернов с минимальными FP
        """
        if not text or not text.strip():
            return []

        if language == "auto":
            language = self._detect_language(text)

        patterns = []
        entity_metadata = entity_metadata or {}

        # 1. TIER-0: Exact documents and IDs (maximum accuracy)
        doc_patterns = self._extract_document_patterns(text)
        patterns.extend(doc_patterns)

        # 2. TIER-1: Full names with context (high accuracy)
        contextual_patterns = self._extract_contextual_name_patterns(text, language)
        patterns.extend(contextual_patterns)

        # 3. TIER-2: Structured names (Last F.M.) (medium accuracy)
        structured_patterns = self._extract_structured_name_patterns(text, language)
        patterns.extend(structured_patterns)

        # 4. TIER-3: Companies with legal forms (medium accuracy)
        company_patterns = self._extract_company_legal_patterns(text, language)
        patterns.extend(company_patterns)

        # 5. DOB-context: if birth date present in text — boost nearby names
        patterns.extend(self._extract_dob_name_patterns(text, language))

        # 6. TIER-4: Enriched patterns with metadata (if available)
        if entity_metadata:
            enriched_patterns = self._extract_metadata_enriched_patterns(
                text, language, entity_metadata
            )
            patterns.extend(enriched_patterns)

        # Filtering and optimization
        optimized_patterns = self._optimize_patterns(patterns)

        self.logger.info(f"Generated {len(optimized_patterns)} high-precision patterns")
        return optimized_patterns

    def _extract_document_patterns(self, text: str) -> List[OptimizedPattern]:
        """Извлечение паттернов документов (максимальная точность)"""
        patterns = []

        for doc_type, regex_list in self.document_patterns.items():
            for regex in regex_list:
                matches = re.finditer(regex, text)
                for match in matches:
                    patterns.append(
                        OptimizedPattern(
                            pattern=match.group().strip(),
                            pattern_type=f"document_{doc_type}",
                            context_required=False,
                            min_match_length=len(match.group().strip()),
                            boost_score=2.0,  # Very high boost
                            language="universal",
                            confidence=0.98,
                            metadata={"doc_type": doc_type},
                        )
                    )

        return patterns

    def _extract_dob_name_patterns(
        self, text: str, language: str
    ) -> List[OptimizedPattern]:
        """Извлекаем имена рядом с датой рождения из самого текста (без metadata)."""
        patterns: List[OptimizedPattern] = []
        # dd.mm.yyyy, dd/mm/yyyy, dd-mm-yyyy (allow leading zeros)
        dob_regex = (
            r"\b(0?[1-9]|[12][0-9]|3[01])[./-](0?[1-9]|1[0-2])[./-]((19|20)\d{2})\b"
        )
        for dmatch in re.finditer(dob_regex, text):
            start = max(0, dmatch.start() - 40)
            end = min(len(text), dmatch.end() + 40)
            ctx = text[start:end]
            # Search for structured forms or full names
            if language in ["ru", "uk"]:
                struct = r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\b"
                reverse = r"\b[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b"
                full = r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b"
            else:
                struct = r"\b[A-Z][a-z\']{2,}\s+[A-Z]\.\s*[A-Z]\.\b"
                reverse = r"\b[A-Z]\.\s*[A-Z]\.\s+[A-Z][a-z\']{2,}\b"
                full = r"\b[A-Z][a-z\']{2,}\s+[A-Z][a-z\']{2,}\b"
            found = False
            for rx, ptype in (
                (struct, "structured_name"),
                (reverse, "structured_name"),
                (full, "contextual_full_name"),
            ):
                for m in re.finditer(rx, ctx):
                    name = m.group().strip()
                    patterns.append(
                        OptimizedPattern(
                            pattern=name,
                            pattern_type=ptype,
                            context_required=False,
                            min_match_length=len(name),
                            boost_score=1.85,
                            language=language,
                            confidence=0.9,
                            metadata={"dob_nearby": dmatch.group()},
                        )
                    )
                    found = True
            # if nothing found, skip
        return patterns

    def _extract_contextual_name_patterns(
        self, text: str, language: str
    ) -> List[OptimizedPattern]:
        """Извлечение имен с обязательным контекстом"""
        patterns = []

        if language not in self.context_triggers:
            return patterns

        triggers = self.context_triggers[language]

        # Combine all triggers into one big regex
        all_triggers = []
        for category, words in triggers.items():
            all_triggers.extend(words)

        trigger_pattern = (
            r"\b(?:" + "|".join(re.escape(w) for w in all_triggers) + r")\b"
        )

        # Search for names in trigger context (within 20 characters)
        for match in re.finditer(trigger_pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context_window = text[start:end]

            # In this window search for full names
            if language in ["ru", "uk"]:
                name_regex = r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}(?:\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,})?\b"
            else:
                name_regex = (
                    r"\b[A-Z][a-z\']{2,}\s+[A-Z][a-z\']{2,}(?:\s+[A-Z][a-z\']{2,})?\b"
                )

            for name_match in re.finditer(name_regex, context_window):
                full_name = name_match.group().strip()

                # Quality check
                if self._is_high_quality_name(full_name, language):
                    patterns.append(
                        OptimizedPattern(
                            pattern=full_name,
                            pattern_type="contextual_full_name",
                            context_required=False,  # Context already checked
                            min_match_length=len(full_name),
                            boost_score=1.8,
                            language=language,
                            confidence=0.92,
                            metadata={"context_trigger": match.group()},
                        )
                    )

        return patterns

    def _extract_structured_name_patterns(
        self, text: str, language: str
    ) -> List[OptimizedPattern]:
        """Извлечение структурированных имен (Фамилия И.О.)"""
        patterns = []

        if language in ["ru", "uk"]:
            # Last F.M.
            structured_regex = (
                r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\b"
            )
            # F.M. Last
            reverse_regex = r"\b[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b"
        else:
            structured_regex = r"\b[A-Z][a-z\']{2,}\s+[A-Z]\.\s*[A-Z]\.\b"
            reverse_regex = r"\b[A-Z]\.\s*[A-Z]\.\s+[A-Z][a-z\']{2,}\b"

        for regex in [structured_regex, reverse_regex]:
            for match in re.finditer(regex, text):
                name = match.group().strip()
                if self._is_valid_structured_name(name, language):
                    patterns.append(
                        OptimizedPattern(
                            pattern=name,
                            pattern_type="structured_name",
                            context_required=True,  # Requires additional context
                            min_match_length=len(name),
                            boost_score=1.5,
                            language=language,
                            confidence=0.85,
                        )
                    )

        return patterns

    def _extract_company_legal_patterns(
        self, text: str, language: str
    ) -> List[OptimizedPattern]:
        """Извлечение компаний с юридическими формами"""
        patterns = []

        if language not in self.context_triggers:
            return patterns

        legal_forms = self.context_triggers[language].get("legal", [])
        if not legal_forms:
            return patterns

        legal_pattern = (
            r"\b(?:" + "|".join(re.escape(form) for form in legal_forms) + r")\b"
        )

        # Search for companies with legal forms
        for match in re.finditer(legal_pattern, text, re.IGNORECASE):
            # Search for company name nearby (before or after legal form)
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]

            # Company name: words with capital letters or in quotes
            if language in ["ru", "uk"]:
                company_regex = r'(?:[""«][^""»]{2,20}[""»]|(?:[А-ЯІЇЄҐ][а-яіїєґ0-9\-]{1,}\s*){1,4})'
            else:
                company_regex = (
                    r'(?:[""«][^""»]{2,20}[""»]|(?:[A-Z][a-z0-9\-]{1,}\s*){1,4})'
                )

            for company_match in re.finditer(company_regex, context):
                company_name = company_match.group().strip()

                # Create full pattern: legal form + name
                if match.start() < company_match.start():  # legal form before name
                    full_pattern = f"{match.group().strip()} {company_name}"
                else:  # name before legal form
                    full_pattern = f"{company_name} {match.group().strip()}"

                if self._is_valid_company_name(company_name, language):
                    patterns.append(
                        OptimizedPattern(
                            pattern=full_pattern.strip(),
                            pattern_type="company_legal",
                            context_required=False,
                            min_match_length=len(full_pattern.strip()),
                            boost_score=1.6,
                            language=language,
                            confidence=0.88,
                            metadata={"legal_form": match.group().strip()},
                        )
                    )

        return patterns

    def _extract_metadata_enriched_patterns(
        self, text: str, language: str, metadata: Dict
    ) -> List[OptimizedPattern]:
        """Обогащенные паттерны с метаданными"""
        patterns = []

        # If DOB exists, search for names near dates
        if "date_of_birth" in metadata or "dob" in metadata:
            date_patterns = [
                r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b",
                r"\b\d{2,4}[./]\d{1,2}[./]\d{1,2}\b",
            ]

            for date_pattern in date_patterns:
                for date_match in re.finditer(date_pattern, text):
                    # Search for names near dates
                    start = max(0, date_match.start() - 25)
                    end = min(len(text), date_match.end() + 25)
                    context = text[start:end]

                    if language in ["ru", "uk"]:
                        name_regex = r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}(?:\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,})*\b"
                    else:
                        name_regex = r"\b[A-Z][a-z\']{2,}(?:\s+[A-Z][a-z\']{2,})*\b"

                    for name_match in re.finditer(name_regex, context):
                        name = name_match.group().strip()
                        if self._is_high_quality_name(name, language):
                            patterns.append(
                                OptimizedPattern(
                                    pattern=name,
                                    pattern_type="metadata_enriched",
                                    context_required=False,
                                    min_match_length=len(name),
                                    boost_score=1.9,  # Very high boost with DOB
                                    language=language,
                                    confidence=0.95,
                                    metadata={"near_dob": date_match.group()},
                                )
                            )

        return patterns

    def _is_high_quality_name(self, name: str, language: str) -> bool:
        """Проверка качества имени"""
        if not name or len(name) < 4:
            return False

        # Check stop words
        if language in self.stop_patterns:
            words = name.lower().split()
            if any(word in self.stop_patterns[language] for word in words):
                return False

        # Number of words
        words = name.split()
        if len(words) < 1 or len(words) > 4:
            return False

        # All words should start with capital letter
        if not all(word[0].isupper() for word in words if word):
            return False

        # Check for minimum word length
        if not all(len(word) >= 2 for word in words):
            return False

        return True

    def _is_valid_structured_name(self, name: str, language: str) -> bool:
        """Проверка корректности структурированного имени"""
        if not name:
            return False

        # Should contain dots for initials
        if "." not in name:
            return False

        # Count initials and full words
        parts = name.split()
        initials = sum(1 for part in parts if re.match(r"^[А-ЯІЇЄҐA-Z]\.?$", part))
        full_words = sum(
            1 for part in parts if re.match(r"^[А-ЯІЇЄҐA-Z][а-яіїєґa-z\']{2,}$", part)
        )

        # Should be 2 initials and 1 full word, or vice versa
        return initials == 2 and full_words == 1

    def _is_valid_company_name(self, name: str, language: str) -> bool:
        """Проверка корректности названия компании"""
        if not name or len(name) < 3:
            return False

        # Remove quotes for checking
        clean_name = re.sub(r'^[""«»\']\s*|\s*[""«»\']$', "", name).strip()

        if len(clean_name) < 3:
            return False

        # Should not consist only of stop words
        if language in self.stop_patterns:
            words = clean_name.lower().split()
            if all(word in self.stop_patterns[language] for word in words):
                return False

        return True

    def _optimize_patterns(
        self, patterns: List[OptimizedPattern]
    ) -> List[OptimizedPattern]:
        """Оптимизация и фильтрация паттернов"""
        if not patterns:
            return []

        # 1. Remove duplicates
        unique_patterns = {}
        for pattern in patterns:
            key = (pattern.pattern.lower(), pattern.pattern_type, pattern.language)
            if (
                key not in unique_patterns
                or pattern.confidence > unique_patterns[key].confidence
            ):
                unique_patterns[key] = pattern

        patterns = list(unique_patterns.values())

        # 2. Filter by minimum requirements
        filtered_patterns = []
        for pattern in patterns:
            pattern_type_base = pattern.pattern_type.split("_")[0]
            if pattern_type_base in self.min_requirements:
                req = self.min_requirements[pattern_type_base]
                if len(pattern.pattern) >= req["min_length"]:
                    # Update context_required if needed
                    if req["context_required"] and not pattern.context_required:
                        pattern.context_required = True
                    filtered_patterns.append(pattern)
            else:
                # If no special requirements, add pattern
                filtered_patterns.append(pattern)

        # 3. Sort by priority (confidence * boost_score)
        filtered_patterns.sort(key=lambda x: x.confidence * x.boost_score, reverse=True)

        # 4. Limit quantity (top-100 patterns per text)
        final_patterns = filtered_patterns[:100]

        return final_patterns

    # Methods for test compatibility
    def _generate_basic_patterns(self, text: str) -> List[str]:
        """Generate basic patterns (compatibility method for tests)"""
        if not text or not text.strip():
            return []
        patterns = self.generate_high_precision_patterns(text)
        return [p.pattern for p in patterns]

    def _generate_advanced_patterns(self, text: str) -> List[str]:
        """Generate advanced patterns (compatibility method for tests)"""
        return self._generate_basic_patterns(text)

    def _generate_phonetic_patterns(self, text: str) -> List[str]:
        """Generate phonetic patterns (compatibility method for tests)"""
        return self._generate_basic_patterns(text)

    def optimize_patterns(self, patterns: List[str]) -> List[str]:
        """Optimize patterns (compatibility method for tests)"""
        if not patterns:
            return []
        # Convert strings to OptimizedPattern objects, optimize, then back to strings
        opt_patterns = []
        for pattern in patterns:
            opt_patterns.append(
                OptimizedPattern(
                    pattern=pattern,
                    pattern_type="basic",
                    context_required=False,
                    min_match_length=len(pattern),
                    boost_score=1.0,
                    language="auto",
                    confidence=0.8,
                )
            )
        optimized = self._optimize_patterns(opt_patterns)
        return [p.pattern for p in optimized]

    def _remove_duplicates(self, patterns: List[str]) -> List[str]:
        """Remove duplicate patterns (compatibility method for tests)"""
        if not patterns:
            return []
        return list(set(patterns))

    def _detect_language(self, text: str) -> str:
        """Простое определение языка"""
        cyrillic_chars = len(re.findall(r"[а-яіїєёА-ЯІЇЄЁҐ]", text))
        latin_chars = len(re.findall(r"[a-zA-Z]", text))

        if cyrillic_chars > 0:
            ukrainian_specific = len(re.findall(r"[іїєґІЇЄҐ]", text))
            if ukrainian_specific > 0:
                return "uk"
            else:
                return "ru"
        elif latin_chars > 0:
            return "en"
        else:
            return "en"

    def export_for_aho_corasick(
        self, patterns: List[OptimizedPattern]
    ) -> Dict[str, List[str]]:
        """Экспорт для AC с разделением по уровням точности"""
        result = {
            "tier_0_exact": [],  # Documents, IDs - immediate triggering
            "tier_1_high_confidence": [],  # Contextual names - high triggering
            "tier_2_medium_confidence": [],  # Structured names - requires context
            "tier_3_low_confidence": [],  # Others - requires additional verification
        }

        for pattern in patterns:
            if pattern.pattern_type.startswith("document_"):
                result["tier_0_exact"].append(pattern.pattern)
            elif pattern.boost_score >= 1.8:
                result["tier_1_high_confidence"].append(pattern.pattern)
            elif pattern.boost_score >= 1.5:
                result["tier_2_medium_confidence"].append(pattern.pattern)
            else:
                result["tier_3_low_confidence"].append(pattern.pattern)

        return result

    def get_pattern_statistics(self, patterns: List[OptimizedPattern]) -> Dict:
        """Статистика паттернов"""
        if not patterns:
            return {}

        stats = {
            "total_patterns": len(patterns),
            "by_type": {},
            "by_language": {},
            "by_confidence": {"high": 0, "medium": 0, "low": 0},
            "context_required": 0,
            "average_confidence": sum(p.confidence for p in patterns) / len(patterns),
            "average_boost": sum(p.boost_score for p in patterns) / len(patterns),
        }

        for pattern in patterns:
            # By types
            stats["by_type"][pattern.pattern_type] = (
                stats["by_type"].get(pattern.pattern_type, 0) + 1
            )

            # By languages
            stats["by_language"][pattern.language] = (
                stats["by_language"].get(pattern.language, 0) + 1
            )

            # By confidence level
            if pattern.confidence >= 0.9:
                stats["by_confidence"]["high"] += 1
            elif pattern.confidence >= 0.7:
                stats["by_confidence"]["medium"] += 1
            else:
                stats["by_confidence"]["low"] += 1

            # Context requirements
            if pattern.context_required:
                stats["context_required"] += 1

        return stats
