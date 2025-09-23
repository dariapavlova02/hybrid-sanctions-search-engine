"""
Unified Pattern Service - consolidates PatternService and OptimizedACPatternGenerator
Provides optimized pattern generation with minimal false positives for Aho-Corasick
"""

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from ...utils.logging_config import get_logger


@dataclass
class UnifiedPattern:
    """Unified pattern for AC search with enhanced metadata"""

    pattern: str
    pattern_type: str
    context_required: bool = False  # Requires contextual confirmation
    min_match_length: int = 0  # Minimum length for triggering
    boost_score: float = 1.0  # Boost coefficient
    language: str = "auto"
    confidence: float = 0.8
    source: str = "unified"
    metadata: Dict = None
    created_at: str = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()
        if self.min_match_length == 0:
            self.min_match_length = len(self.pattern)


class UnifiedPatternService:
    """Unified Pattern Service combining best features from both services"""

    def __init__(self, max_patterns_per_name: int = 1000):
        self.logger = get_logger(__name__)
        self.max_patterns_per_name = max_patterns_per_name

        # Comprehensive language patterns
        self.name_patterns = {
            "en": {
                "full_name": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
                "initials_surname": r"\b[A-Z]\. [A-Z]\. [A-Z][a-z]+\b",
                "surname_initials": r"\b[A-Z][a-z]+ [A-Z]\. [A-Z]\.\b",
                "surname_only": r"\b[A-Z][a-z]{2,}\b",
                "name_only": r"\b[A-Z][a-z]{2,}\b",
                "compound_name": r"\b[A-Z][a-z]+-[A-Z][a-z]+\b",
            },
            "ru": {
                "full_name": r"\b[А-ЯІЇЄ][а-яіїє]+ [А-ЯІЇЄ][а-яіїє]+\b",
                "initials_surname": r"\b[А-ЯІЇЄ]\. [А-ЯІЇЄ]\. [А-ЯІЇЄ][а-яіїє]+\b",
                "surname_initials": r"\b[А-ЯІЇЄ][а-яіїє]+ [А-ЯІЇЄ]\. [А-ЯІЇЄ]\.\b",
                "surname_only": r"\b[А-ЯІЇЄ][а-яіїє]{2,}\b",
                "name_only": r"\b[А-ЯІЇЄ][а-яіїє]{2,}\b",
            },
            "uk": {
                "full_name": r"\b[А-ЯІЇЄҐ][а-яіїєґ]+ [А-ЯІЇЄҐ][а-яіїєґ]+\b",
                "initials_surname": r"\b[А-ЯІЇЄҐ]\. [А-ЯІЇЄҐ]\. [А-ЯІЇЄҐ][а-яіїєґ]+\b",
                "surname_initials": r"\b[А-ЯІЇЄҐ][а-яіїєґ]+ [А-ЯІЇЄҐ]\. [А-ЯІЇЄҐ]\.\b",
                "surname_only": r"\b[А-ЯІЇЄҐ][а-яіїєґ]{2,}\b",
                "name_only": r"\b[А-ЯІЇЄҐ][а-яіїєґ]{2,}\b",
            },
            "fr": {
                "full_name": r"\b[A-Z][a-z]+ [A-Z][a-z]+\b",
                "compound_name": r"\b[A-Z][a-z]+-[A-Z][a-z]+\b",
                "surname_only": r"\b[A-Z][a-z]{2,}\b",
                "name_only": r"\b[A-Z][a-z]{2,}\b",
            },
            "es": {
                "full_name": r"\b[A-Z][a-záéíóúñÁÉÍÓÚÑ]+ [A-Z][a-záéíóúñÁÉÍÓÚÑ]+\b",
                "surname_only": r"\b[A-Z][a-záéíóúñÁÉÍÓÚÑ]{2,}\b",
                "name_only": r"\b[A-Z][a-záéíóúñÁÉÍÓÚÑ]{2,}\b",
            },
        }

        # Context triggers for high-precision matching (frozenset for immutability and performance)
        self.context_triggers = {
            "ru": {
                "payment": frozenset(["платеж", "оплата", "перевод", "перечисление", "зачисление"]),
                "contract": frozenset(["договор", "контракт", "соглашение", "сделка"]),
                "recipient": frozenset(["получатель", "бенефициар", "в пользу", "на имя"]),
                "sender": frozenset(["отправитель", "плательщик", "от имени"]),
                "legal": frozenset(["ООО", "ЗАО", "ОАО", "ПАО", "ИП", "ФЛ"]),
            },
            "uk": {
                "payment": frozenset(["платіж", "оплата", "переказ", "перерахування"]),
                "contract": frozenset(["договір", "контракт", "угода", "домовленість"]),
                "recipient": frozenset(["одержувач", "бенефіціар", "на користь", "на ім'я"]),
                "sender": frozenset(["відправник", "платник", "від імені"]),
                "legal": frozenset(["ТОВ", "ПАТ", "АТ", "ПрАТ", "ФОП", "ФО"]),
            },
            "en": {
                "payment": frozenset(["payment", "transfer", "remittance", "wire", "funds"]),
                "contract": frozenset(["contract", "agreement", "deal", "arrangement"]),
                "recipient": frozenset(["beneficiary", "payee", "recipient", "to"]),
                "sender": frozenset(["payer", "sender", "from"]),
                "legal": frozenset(["LLC", "Inc", "Ltd", "Corp", "Co", "LP"]),
            },
        }

        # Stop words that should not be patterns by themselves (frozenset for immutability and performance)
        self.stop_patterns = {
            "ru": frozenset({"для", "или", "его", "этот", "один", "два", "три", "год", "день", "время"}),
            "uk": frozenset({"для", "або", "його", "цей", "один", "два", "три", "рік", "день", "час"}),
            "en": frozenset({"for", "or", "his", "this", "one", "two", "three", "year", "day", "time"}),
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
            "edrpou": [r"\b\d{8}\b", r"\b\d{6}\b"],  # EDRPOU formats
            "iban": [
                r"\bUA\d{2}[A-Z0-9]{25}\b",  # Ukrainian IBAN
                r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b",  # Generic IBAN
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

        # Payment context patterns (from original PatternService)
        self.payment_patterns = {
            "ru": [
                r"оплата\s+від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
                r"оплата\s+для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
                r"від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
                r"для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
            ],
            "uk": [
                r"оплата\s+від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
                r"оплата\s+для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
                r"від\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
                r"для\s+([А-ЯІЇЄ][а-яіїє]+(?:\s+[А-ЯІЇЄ][а-яіїє]+)*)",
            ],
        }

        # Name dictionaries for enhanced recognition
        self.name_dictionaries = {
            "ru": {
                "names": {"Иван", "Петр", "Сергей", "Володимир", "Дарья", "Анна", "Мария", "Олексій"},
                "surnames": {"Иванов", "Петров", "Сидоров", "Порошенко", "Акопджанів", "Ковриков", "Гаркушев"},
            },
            "uk": {
                "names": {"Іван", "Петро", "Сергій", "Володимир", "Дарʼя", "Анна", "Марія", "Олексій"},
                "surnames": {"Іванов", "Петренко", "Сидоренко", "Порошенко", "Акопджанів", "Ковриков", "Гаркушев"},
            },
            "en": {
                "names": {"John", "James", "Robert", "Michael", "William", "David", "Richard", "Charles"},
                "surnames": {"Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis"},
            },
        }

        self.logger.info("UnifiedPatternService initialized")

    def generate_patterns(
        self,
        text: str,
        language: str = "auto",
        entity_type: str = "auto",
        entity_metadata: Dict = None,
    ) -> List[UnifiedPattern]:
        """
        Main pattern generation method with unified approach
        """
        if not text or not text.strip():
            return []

        if language == "auto":
            language = self._detect_language(text)

        patterns = []
        entity_metadata = entity_metadata or {}

        # TIER-0: Document patterns (maximum accuracy)
        patterns.extend(self._extract_document_patterns(text))

        # TIER-1: Contextual patterns (high accuracy)
        patterns.extend(self._extract_contextual_patterns(text, language))

        # TIER-2: Structured patterns (medium accuracy)
        patterns.extend(self._extract_structured_patterns(text, language))

        # TIER-3: Company legal patterns (medium accuracy)
        patterns.extend(self._extract_company_patterns(text, language))

        # TIER-4: DOB-enhanced patterns
        patterns.extend(self._extract_dob_patterns(text, language))

        # TIER-5: Dictionary-based patterns
        patterns.extend(self._extract_dictionary_patterns(text, language))

        # TIER-6: Payment context patterns
        patterns.extend(self._extract_payment_patterns(text, language))

        # TIER-7: Basic name patterns
        patterns.extend(self._extract_basic_patterns(text, language))

        # TIER-8: Metadata-enriched patterns
        if entity_metadata:
            patterns.extend(self._extract_metadata_patterns(text, language, entity_metadata))

        # Optimize and deduplicate
        optimized_patterns = self._optimize_patterns(patterns)

        # Apply pattern limit to prevent combinatorial explosion
        if len(optimized_patterns) > self.max_patterns_per_name:
            self.logger.warning(f"Generated {len(optimized_patterns)} patterns, limiting to {self.max_patterns_per_name}")
            # Keep highest confidence patterns first
            optimized_patterns.sort(key=lambda p: p.confidence, reverse=True)
            optimized_patterns = optimized_patterns[:self.max_patterns_per_name]

        self.logger.info(f"Generated {len(optimized_patterns)} unified patterns for language: {language}")
        return optimized_patterns

    def _extract_document_patterns(self, text: str) -> List[UnifiedPattern]:
        """Extract document patterns (maximum accuracy)"""
        patterns = []

        for doc_type, regex_list in self.document_patterns.items():
            for regex in regex_list:
                matches = re.finditer(regex, text)
                for match in matches:
                    patterns.append(
                        UnifiedPattern(
                            pattern=match.group().strip(),
                            pattern_type=f"document_{doc_type}",
                            context_required=False,
                            boost_score=2.0,
                            language="universal",
                            confidence=0.98,
                            source="document_extractor",
                            metadata={"doc_type": doc_type},
                        )
                    )
        return patterns

    def _extract_contextual_patterns(self, text: str, language: str) -> List[UnifiedPattern]:
        """Extract names with contextual confirmation"""
        patterns = []

        if language not in self.context_triggers:
            return patterns

        triggers = self.context_triggers[language]
        all_triggers = []
        for category, words in triggers.items():
            all_triggers.extend(words)

        trigger_pattern = r"\b(?:" + "|".join(re.escape(w) for w in all_triggers) + r")\b"

        for match in re.finditer(trigger_pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 20)
            end = min(len(text), match.end() + 20)
            context_window = text[start:end]

            # Search for full names in context
            if language in ["ru", "uk"]:
                name_regex = r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}(?:\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,})?\b"
            else:
                name_regex = r"\b[A-Z][a-z\']{2,}\s+[A-Z][a-z\']{2,}(?:\s+[A-Z][a-z\']{2,})?\b"

            for name_match in re.finditer(name_regex, context_window):
                full_name = name_match.group().strip()
                if self._is_high_quality_name(full_name, language):
                    patterns.append(
                        UnifiedPattern(
                            pattern=full_name,
                            pattern_type="contextual_full_name",
                            context_required=False,
                            boost_score=1.8,
                            language=language,
                            confidence=0.92,
                            source="contextual_extractor",
                            metadata={"context_trigger": match.group()},
                        )
                    )
        return patterns

    def _extract_structured_patterns(self, text: str, language: str) -> List[UnifiedPattern]:
        """Extract structured names (Last F.M. or F.M. Last)"""
        patterns = []

        if language in ["ru", "uk"]:
            # Include all Cyrillic letters including Ukrainian specific ones
            # Remove word boundaries for Cyrillic patterns as they don't work well with Unicode
            cyrillic_upper = r"[А-ЯЁІЇЄҐ]"
            cyrillic_lower = r"[а-яёіїєґ]"
            structured_regex = rf"{cyrillic_upper}{cyrillic_lower}+\s+{cyrillic_upper}\.\s+{cyrillic_upper}\."
            reverse_regex = rf"{cyrillic_upper}\.\s+{cyrillic_upper}\.\s+{cyrillic_upper}{cyrillic_lower}+"
        else:
            structured_regex = r"\b[A-Z][a-z\']{2,}\s+[A-Z]\.\s+[A-Z]\.\b"
            reverse_regex = r"\b[A-Z]\.\s+[A-Z]\.\s+[A-Z][a-z\']{2,}\b"

        for regex in [structured_regex, reverse_regex]:
            for match in re.finditer(regex, text):
                name = match.group().strip()
                if self._is_valid_structured_name(name, language):
                    patterns.append(
                        UnifiedPattern(
                            pattern=name,
                            pattern_type="structured_name",
                            context_required=True,
                            boost_score=1.5,
                            language=language,
                            confidence=0.85,
                            source="structured_extractor",
                        )
                    )
        return patterns

    def _extract_company_patterns(self, text: str, language: str) -> List[UnifiedPattern]:
        """Extract companies with legal forms"""
        patterns = []

        if language not in self.context_triggers:
            return patterns

        legal_forms = self.context_triggers[language].get("legal", [])
        if not legal_forms:
            return patterns

        legal_pattern = r"\b(?:" + "|".join(re.escape(form) for form in legal_forms) + r")\b"

        for match in re.finditer(legal_pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 30)
            end = min(len(text), match.end() + 30)
            context = text[start:end]

            # Company name patterns
            if language in ["ru", "uk"]:
                company_regex = r'(?:[""«][^""»]{2,20}[""»]|(?:[А-ЯІЇЄҐ][а-яіїєґ0-9\-]{1,}\s*){1,4})'
            else:
                company_regex = r'(?:[""«][^""»]{2,20}[""»]|(?:[A-Z][a-z0-9\-]{1,}\s*){1,4})'

            for company_match in re.finditer(company_regex, context):
                company_name = company_match.group().strip()

                # Create full pattern: legal form + name
                if match.start() < company_match.start():
                    full_pattern = f"{match.group().strip()} {company_name}"
                else:
                    full_pattern = f"{company_name} {match.group().strip()}"

                if self._is_valid_company_name(company_name, language):
                    patterns.append(
                        UnifiedPattern(
                            pattern=full_pattern.strip(),
                            pattern_type="company_legal",
                            context_required=False,
                            boost_score=1.6,
                            language=language,
                            confidence=0.88,
                            source="company_extractor",
                            metadata={"legal_form": match.group().strip()},
                        )
                    )
        return patterns

    def _extract_dob_patterns(self, text: str, language: str) -> List[UnifiedPattern]:
        """Extract names near date of birth patterns"""
        patterns = []

        # DOB regex patterns
        dob_regex = r"\b(0?[1-9]|[12][0-9]|3[01])[./-](0?[1-9]|1[0-2])[./-]((19|20)\d{2})\b"

        for dmatch in re.finditer(dob_regex, text):
            start = max(0, dmatch.start() - 40)
            end = min(len(text), dmatch.end() + 40)
            ctx = text[start:end]

            # Search for names near DOB
            if language in ["ru", "uk"]:
                name_patterns = [
                    (r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\b", "structured_name"),
                    (r"\b[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b", "structured_name"),
                    (r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b", "contextual_full_name"),
                ]
            else:
                name_patterns = [
                    (r"\b[A-Z][a-z\']{2,}\s+[A-Z]\.\s*[A-Z]\.\b", "structured_name"),
                    (r"\b[A-Z]\.\s*[A-Z]\.\s+[A-Z][a-z\']{2,}\b", "structured_name"),
                    (r"\b[A-Z][a-z\']{2,}\s+[A-Z][a-z\']{2,}\b", "contextual_full_name"),
                ]

            for regex, ptype in name_patterns:
                for m in re.finditer(regex, ctx):
                    name = m.group().strip()
                    patterns.append(
                        UnifiedPattern(
                            pattern=name,
                            pattern_type=ptype,
                            context_required=False,
                            boost_score=1.85,
                            language=language,
                            confidence=0.9,
                            source="dob_extractor",
                            metadata={"dob_nearby": dmatch.group()},
                        )
                    )
        return patterns

    def _extract_dictionary_patterns(self, text: str, language: str) -> List[UnifiedPattern]:
        """Extract patterns from name dictionaries"""
        patterns = []

        if language not in self.name_dictionaries:
            return patterns

        words = re.findall(r"\b[A-ZА-ЯІЇЄ][a-zA-Zа-яіїє\'-]+\b", text)

        # Check names
        for word in words:
            if word in self.name_dictionaries[language]["names"]:
                patterns.append(
                    UnifiedPattern(
                        pattern=word,
                        pattern_type="dictionary_name",
                        context_required=True,
                        boost_score=1.2,
                        language=language,
                        confidence=0.95,
                        source="name_dictionary",
                    )
                )

            # Check surnames
            if word in self.name_dictionaries[language]["surnames"]:
                patterns.append(
                    UnifiedPattern(
                        pattern=word,
                        pattern_type="dictionary_surname",
                        context_required=True,
                        boost_score=1.2,
                        language=language,
                        confidence=0.95,
                        source="surname_dictionary",
                    )
                )

            # Handle compound names
            if "'" in word or "-" in word:
                clean_word = re.sub(r"[\'-]", "", word)
                if clean_word in self.name_dictionaries[language]["names"]:
                    patterns.append(
                        UnifiedPattern(
                            pattern=clean_word,
                            pattern_type="dictionary_name_clean",
                            context_required=True,
                            boost_score=1.1,
                            language=language,
                            confidence=0.9,
                            source="name_dictionary_clean",
                        )
                    )

        return patterns

    def _extract_payment_patterns(self, text: str, language: str) -> List[UnifiedPattern]:
        """Extract payment context patterns"""
        patterns = []

        if language not in self.payment_patterns:
            return patterns

        for regex in self.payment_patterns[language]:
            matches = re.finditer(regex, text, re.IGNORECASE)
            for match in matches:
                if match.group(1):
                    name_text = match.group(1).strip()
                    if self._looks_like_name(name_text, language):
                        patterns.append(
                            UnifiedPattern(
                                pattern=name_text,
                                pattern_type="payment_context",
                                context_required=False,
                                boost_score=1.7,
                                language=language,
                                confidence=0.9,
                                source="payment_extractor",
                            )
                        )
        return patterns

    def _extract_basic_patterns(self, text: str, language: str) -> List[UnifiedPattern]:
        """Extract basic name patterns"""
        patterns = []

        if language not in self.name_patterns:
            return patterns

        for pattern_type, regex in self.name_patterns[language].items():
            matches = re.finditer(regex, text, re.IGNORECASE)
            for match in matches:
                matched_text = match.group()
                if self._is_high_quality_name(matched_text, language):
                    # Original case
                    patterns.append(
                        UnifiedPattern(
                            pattern=matched_text,
                            pattern_type=pattern_type,
                            context_required=pattern_type in ["surname_only", "name_only"],
                            boost_score=1.0,
                            language=language,
                            confidence=0.8,
                            source="basic_extractor",
                        )
                    )

                    # Case variations for better coverage
                    for case_variant, conf_adjust in [
                        (matched_text.lower(), -0.1),
                        (matched_text.title(), -0.1),
                    ]:
                        if case_variant != matched_text:
                            patterns.append(
                                UnifiedPattern(
                                    pattern=case_variant,
                                    pattern_type=f"{pattern_type}_variant",
                                    context_required=pattern_type in ["surname_only", "name_only"],
                                    boost_score=0.9,
                                    language=language,
                                    confidence=0.8 + conf_adjust,
                                    source=f"basic_extractor_{case_variant.lower()}case",
                                )
                            )
        return patterns

    def _extract_metadata_patterns(
        self, text: str, language: str, metadata: Dict
    ) -> List[UnifiedPattern]:
        """Extract metadata-enriched patterns"""
        patterns = []

        # If DOB exists in metadata, search for names near dates
        if "date_of_birth" in metadata or "dob" in metadata:
            date_patterns = [
                r"\b\d{1,2}[./]\d{1,2}[./]\d{2,4}\b",
                r"\b\d{2,4}[./]\d{1,2}[./]\d{1,2}\b",
            ]

            for date_pattern in date_patterns:
                for date_match in re.finditer(date_pattern, text):
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
                                UnifiedPattern(
                                    pattern=name,
                                    pattern_type="metadata_enriched",
                                    context_required=False,
                                    boost_score=1.9,
                                    language=language,
                                    confidence=0.95,
                                    source="metadata_extractor",
                                    metadata={"near_dob": date_match.group()},
                                )
                            )

        return patterns

    def _optimize_patterns(self, patterns: List[UnifiedPattern]) -> List[UnifiedPattern]:
        """Optimize and filter patterns"""
        if not patterns:
            return []

        # Remove duplicates (keep highest confidence)
        unique_patterns = {}
        for pattern in patterns:
            key = (pattern.pattern.lower(), pattern.pattern_type, pattern.language)
            if key not in unique_patterns or pattern.confidence > unique_patterns[key].confidence:
                unique_patterns[key] = pattern

        patterns = list(unique_patterns.values())

        # Filter by minimum requirements
        filtered_patterns = []
        for pattern in patterns:
            pattern_type_base = pattern.pattern_type.split("_")[0]
            if pattern_type_base in self.min_requirements:
                req = self.min_requirements[pattern_type_base]
                if len(pattern.pattern) >= req["min_length"]:
                    if req["context_required"] and not pattern.context_required:
                        pattern.context_required = True
                    filtered_patterns.append(pattern)
            else:
                filtered_patterns.append(pattern)

        # Remove stop word patterns
        final_patterns = []
        for pattern in filtered_patterns:
            if not self._contains_stop_words(pattern.pattern, pattern.language):
                final_patterns.append(pattern)

        # Sort by priority (confidence * boost_score)
        final_patterns.sort(key=lambda x: x.confidence * x.boost_score, reverse=True)

        # Limit quantity (top-100 patterns per text)
        return final_patterns[:100]

    def _is_high_quality_name(self, name: str, language: str) -> bool:
        """Check if name is high quality"""
        if not name or len(name) < 4:
            return False

        # Check stop words
        if self._contains_stop_words(name, language):
            return False

        # Number of words
        words = name.split()
        if len(words) < 1 or len(words) > 4:
            return False

        # All words should start with capital letter, but not be all caps
        for word in words:
            if not word:
                continue
            if not word[0].isupper():
                return False
            # Reject all-caps words (except single letter words/initials)
            if len(word) > 1 and word.isupper():
                return False

        # Check for minimum word length
        if not all(len(word) >= 2 for word in words):
            return False

        return True

    def _is_valid_structured_name(self, name: str, language: str) -> bool:
        """Check if structured name is valid"""
        if not name or "." not in name:
            return False

        parts = name.split()
        initials = sum(1 for part in parts if re.match(r"^[А-ЯІЇЄҐA-Z]\.?$", part))
        full_words = sum(1 for part in parts if re.match(r"^[А-ЯІЇЄҐA-Z][а-яіїєґa-z\']{2,}$", part))

        return initials == 2 and full_words == 1

    def _is_valid_company_name(self, name: str, language: str) -> bool:
        """Check if company name is valid"""
        if not name or len(name) < 3:
            return False

        clean_name = re.sub(r'^[""«»\']\s*|\s*[""«»\']$', "", name).strip()
        if len(clean_name) < 3:
            return False

        return not self._contains_stop_words(clean_name, language)

    def _contains_stop_words(self, text: str, language: str) -> bool:
        """Check if text contains stop words"""
        if language in self.stop_patterns:
            words = text.lower().split()
            return any(word in self.stop_patterns[language] for word in words)
        return False

    def _looks_like_name(self, word: str, language: str) -> bool:
        """Check if word looks like a name"""
        if not word or len(word) < 2:
            return False

        if language in ["ru", "uk"]:
            return bool(re.match(r"^[А-ЯІЇЄҐ][а-яіїєґ]+$", word))
        else:
            return bool(re.match(r"^[A-Z][a-z]+$", word))

    def _detect_language(self, text: str) -> str:
        """Detect language from text"""
        cyrillic_chars = len(re.findall(r"[а-яіїєёА-ЯІЇЄЁҐ]", text))
        latin_chars = len(re.findall(r"[a-zA-Z]", text))

        if cyrillic_chars > 0:
            ukrainian_specific = len(re.findall(r"[іїєґІЇЄҐ]", text))
            return "uk" if ukrainian_specific > 0 else "ru"
        elif latin_chars > 0:
            return "en"
        else:
            return "en"

    def export_for_aho_corasick(self, patterns: List[UnifiedPattern]) -> Dict[str, List[str]]:
        """Export patterns for Aho-Corasick with tiered confidence"""
        result = {
            "tier_0_exact": [],  # Documents, IDs - immediate triggering
            "tier_1_high_confidence": [],  # Contextual names - high triggering
            "tier_2_medium_confidence": [],  # Structured names - requires context
            "tier_3_low_confidence": [],  # Others - requires additional verification
        }

        # Filter out case variants since AC matching will be case-insensitive
        seen_patterns = set()

        for pattern in patterns:
            # Skip case variants (lower/title case) since AC will handle case insensitivity
            pattern_key = pattern.pattern.lower()
            if pattern_key in seen_patterns:
                continue
            seen_patterns.add(pattern_key)

            if pattern.pattern_type.startswith("document_"):
                result["tier_0_exact"].append(pattern.pattern)
            elif pattern.boost_score >= 1.8:
                result["tier_1_high_confidence"].append(pattern.pattern)
            elif pattern.boost_score >= 1.5:
                result["tier_2_medium_confidence"].append(pattern.pattern)
            else:
                result["tier_3_low_confidence"].append(pattern.pattern)

        return result

    def get_pattern_statistics(self, patterns: List[UnifiedPattern]) -> Dict[str, Any]:
        """Get comprehensive pattern statistics"""
        if not patterns:
            return {
                "total_patterns": 0,
                "by_type": {},
                "by_language": {},
                "by_source": {},
                "by_confidence": {"high": 0, "medium": 0, "low": 0},
                "context_required": 0,
                "average_confidence": 0.0,
                "average_boost": 0.0,
            }

        stats = {
            "total_patterns": len(patterns),
            "by_type": {},
            "by_language": {},
            "by_source": {},
            "by_confidence": {"high": 0, "medium": 0, "low": 0},
            "context_required": 0,
            "average_confidence": sum(p.confidence for p in patterns) / len(patterns),
            "average_boost": sum(p.boost_score for p in patterns) / len(patterns),
        }

        for pattern in patterns:
            # By type
            stats["by_type"][pattern.pattern_type] = stats["by_type"].get(pattern.pattern_type, 0) + 1

            # By language
            stats["by_language"][pattern.language] = stats["by_language"].get(pattern.language, 0) + 1

            # By source
            stats["by_source"][pattern.source] = stats["by_source"].get(pattern.source, 0) + 1

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

    # Legacy compatibility methods for existing code
    def generate_high_precision_patterns(
        self, text: str, language: str = "auto", entity_metadata: Dict = None
    ) -> List[UnifiedPattern]:
        """Legacy compatibility method"""
        return self.generate_patterns(text, language, "auto", entity_metadata)

    def _remove_duplicate_patterns(self, patterns: List[UnifiedPattern]) -> List[UnifiedPattern]:
        """Legacy compatibility method"""
        return self._optimize_patterns(patterns)