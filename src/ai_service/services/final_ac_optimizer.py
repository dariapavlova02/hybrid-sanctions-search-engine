"""
Финальная оптимизированная версия генератора AC паттернов
Исправлены проблемы с распознаванием полных имен и структурированных форм
"""

import re
from dataclasses import dataclass
from typing import Dict, List, Set, Tuple


@dataclass
class ACPattern:
    """Оптимизированный паттерн для AC с метриками качества"""

    pattern: str
    pattern_type: str
    confidence: float
    specificity_score: float  # How specific the pattern is (1.0 = very specific)
    context_boost: float  # Boost from context
    language: str
    requires_confirmation: bool = False  # Requires additional confirmation


class FinalACOptimizer:
    """
    Финальная версия оптимизатора AC паттернов с максимальной точностью
    Основан на принципах из архитектурного плана НБУ
    """

    def __init__(self):
        # Context words for each language with weights
        self.context_weights = {
            "ru": {
                "high": ["договор", "контракт", "паспорт", "получатель", "плательщик"],
                "medium": ["платеж", "оплата", "перевод", "от", "для"],
                "low": ["имя", "лицо"],
            },
            "uk": {
                "high": ["договір", "контракт", "паспорт", "одержувач", "платник"],
                "medium": ["платіж", "оплата", "переказ", "від", "для"],
                "low": ["ім'я", "особа"],
            },
            "en": {
                "high": ["contract", "agreement", "passport", "beneficiary", "payer"],
                "medium": ["payment", "transfer", "from", "to", "for"],
                "low": ["name", "person"],
            },
        }

        # Exact document patterns
        self.document_patterns = {
            "passport_foreign": r"\b[A-Z]{2}\d{6}\b",
            "passport_ua": r"\b[А-Я]{2}\d{6}\b",
            "inn_ua": r"\b\d{10}\b",
            "edrpou": r"\b\d{8}\b",
            "iban": r"\bUA\d{2}[A-Z0-9]{25}\b",
        }

        # Legal forms (for companies)
        self.legal_forms = {
            "ru": ["ООО", "ЗАО", "ОАО", "ПАО", "ИП", "АО"],
            "uk": ["ТОВ", "ПАТ", "АТ", "ПрАТ", "ФОП"],
            "en": ["LLC", "Inc", "Ltd", "Corp", "Co", "LP"],
        }

        # Minimum lengths for different pattern types
        self.min_lengths = {
            "single_name": 3,
            "full_name": 6,
            "company": 5,
            "document": 6,
        }

    def generate_optimal_patterns(
        self, text: str, language: str = "auto"
    ) -> List[ACPattern]:
        """
        Генерация оптимальных паттернов для AC поиска
        Максимальная специфичность, минимальные false positives
        """
        if language == "auto":
            language = self._detect_language(text)

        patterns = []

        # LEVEL 0: Documents (maximum accuracy)
        doc_patterns = self._extract_documents(text)
        patterns.extend(doc_patterns)

        # LEVEL 1: Full names with strong context
        contextual_patterns = self._extract_contextual_full_names(text, language)
        patterns.extend(contextual_patterns)

        # LEVEL 2: Structured names (F.M. Last)
        structured_patterns = self._extract_structured_names(text, language)
        patterns.extend(structured_patterns)

        # LEVEL 3: Companies with legal forms
        company_patterns = self._extract_companies_with_legal_forms(text, language)
        patterns.extend(company_patterns)

        # Final filtering and ranking
        optimized_patterns = self._finalize_patterns(patterns, language)

        return optimized_patterns

    def _extract_documents(self, text: str) -> List[ACPattern]:
        """Извлечение документов - абсолютная точность"""
        patterns = []

        for doc_type, pattern_regex in self.document_patterns.items():
            for match in re.finditer(pattern_regex, text):
                doc_number = match.group().strip()

                patterns.append(
                    ACPattern(
                        pattern=doc_number,
                        pattern_type=f"document_{doc_type}",
                        confidence=0.99,
                        specificity_score=1.0,  # Maximum specificity
                        context_boost=0.0,  # No context needed
                        language="universal",
                        requires_confirmation=False,
                    )
                )

        return patterns

    def _extract_contextual_full_names(
        self, text: str, language: str
    ) -> List[ACPattern]:
        """
        Извлечение полных имен с обязательным контекстом
        Исправлена логика для захвата всего полного имени
        """
        patterns = []

        if language not in self.context_weights:
            return patterns

        # Combine all context words
        all_contexts = []
        for level, words in self.context_weights[language].items():
            all_contexts.extend(words)

        # Create regex for context search
        context_pattern = (
            r"\b(?:" + "|".join(re.escape(word) for word in all_contexts) + r")\b"
        )

        # Search for context words
        for context_match in re.finditer(context_pattern, text, re.IGNORECASE):
            # Determine context weight
            context_word = context_match.group().lower()
            context_boost = 0.3  # default

            for level, words in self.context_weights[language].items():
                if context_word in [w.lower() for w in words]:
                    if level == "high":
                        context_boost = 0.5
                    elif level == "medium":
                        context_boost = 0.3
                    else:
                        context_boost = 0.1
                    break

            # Expand search window for full names
            start = max(0, context_match.start() - 30)
            end = min(len(text), context_match.end() + 30)
            search_window = text[start:end]

            # Patterns for full names depending on language
            if language in ["ru", "uk"]:
                # For Cyrillic: 2-3 words, each starting with capital letter
                name_pattern = (
                    r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}(?:\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}){1,2}\b"
                )
            else:
                # For Latin: 2-3 words
                name_pattern = r"\b[A-Z][a-z\']{2,}(?:\s+[A-Z][a-z\']{2,}){1,2}\b"

            for name_match in re.finditer(name_pattern, search_window):
                full_name = name_match.group().strip()

                # Check quality of full name
                if self._is_high_quality_full_name(full_name, language):
                    patterns.append(
                        ACPattern(
                            pattern=full_name,
                            pattern_type="contextual_full_name",
                            confidence=0.90 + context_boost,
                            specificity_score=0.8,
                            context_boost=context_boost,
                            language=language,
                            requires_confirmation=False,
                        )
                    )

        return patterns

    def _extract_structured_names(self, text: str, language: str) -> List[ACPattern]:
        """
        Извлечение структурированных имен (Фамилия И.О. или И.О. Фамилия)
        Улучшенная версия с лучшим распознаванием
        """
        patterns = []

        if language in ["ru", "uk"]:
            # Last F.M.
            pattern1 = r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\s+[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\b"
            # F.M. Last
            pattern2 = r"\b[А-ЯІЇЄҐ]\.\s*[А-ЯІЇЄҐ]\.\s+[А-ЯІЇЄҐ][а-яіїєґ\']{2,}\b"
            # Last F. (abbreviated form)
            pattern3 = r"\b[А-ЯІЇЄҐ][а-яіїєґ\']{3,}\s+[А-ЯІЇЄҐ]\.\b"
        else:
            # English equivalents
            pattern1 = r"\b[A-Z][a-z\']{2,}\s+[A-Z]\.\s*[A-Z]\.\b"
            pattern2 = r"\b[A-Z]\.\s*[A-Z]\.\s+[A-Z][a-z\']{2,}\b"
            pattern3 = r"\b[A-Z][a-z\']{3,}\s+[A-Z]\.\b"

        for pattern_regex in [pattern1, pattern2, pattern3]:
            for match in re.finditer(pattern_regex, text):
                structured_name = match.group().strip()

                if self._is_valid_structured_name(structured_name, language):
                    patterns.append(
                        ACPattern(
                            pattern=structured_name,
                            pattern_type="structured_name",
                            confidence=0.85,
                            specificity_score=0.7,
                            context_boost=0.0,
                            language=language,
                            requires_confirmation=True,  # Requires additional verification
                        )
                    )

        return patterns

    def _extract_companies_with_legal_forms(
        self, text: str, language: str
    ) -> List[ACPattern]:
        """Извлечение компаний с юридическими формами"""
        patterns = []

        if language not in self.legal_forms:
            return patterns

        legal_forms = self.legal_forms[language]
        legal_pattern = (
            r"\b(?:" + "|".join(re.escape(form) for form in legal_forms) + r")\b"
        )

        for legal_match in re.finditer(legal_pattern, text, re.IGNORECASE):
            # Search for company name near legal form
            start = max(0, legal_match.start() - 25)
            end = min(len(text), legal_match.end() + 25)
            company_window = text[start:end]

            # Pattern for company name
            if language in ["ru", "uk"]:
                company_pattern = (
                    r'(?:[""«][^""»]{3,25}[""»]|(?:[А-ЯІЇЄҐ][а-яіїєґ0-9\-]*\s*){1,3})'
                )
            else:
                company_pattern = (
                    r'(?:[""«][^""»]{3,25}[""»]|(?:[A-Z][a-z0-9\-]*\s*){1,3})'
                )

            for company_match in re.finditer(company_pattern, company_window):
                company_name = company_match.group().strip()

                # Create full pattern
                legal_form = legal_match.group().strip()

                # Determine order: form before name or after
                if legal_match.start() < company_match.start():
                    full_pattern = f"{legal_form} {company_name}"
                else:
                    full_pattern = f"{company_name} {legal_form}"

                if self._is_valid_company_name(company_name, language):
                    patterns.append(
                        ACPattern(
                            pattern=full_pattern.strip(),
                            pattern_type="company_legal",
                            confidence=0.88,
                            specificity_score=0.75,
                            context_boost=0.1,
                            language=language,
                            requires_confirmation=False,
                        )
                    )

        return patterns

    def _is_high_quality_full_name(self, name: str, language: str) -> bool:
        """Проверка качества полного имени"""
        if len(name) < self.min_lengths["full_name"]:
            return False

        words = name.split()
        if len(words) < 2 or len(words) > 3:
            return False

        # All words should be long enough and start with capital letter
        for word in words:
            if len(word) < 2 or not word[0].isupper():
                return False

            # Exclude obvious non-names
            if word.lower() in [
                "для",
                "или",
                "год",
                "день",
                "for",
                "or",
                "year",
                "day",
            ]:
                return False

        return True

    def _is_valid_structured_name(self, name: str, language: str) -> bool:
        """Проверка корректности структурированного имени"""
        if not name or len(name) < 5:
            return False

        # Should contain dots
        if "." not in name:
            return False

        # Count components
        parts = name.split()
        initials = sum(1 for part in parts if re.match(r"^[А-ЯІЇЄҐA-Z]\.?$", part))
        full_words = sum(1 for part in parts if len(part) > 2 and part[0].isupper())

        # Should have at least 1 full word and 1-2 initials
        return initials >= 1 and full_words >= 1 and (initials + full_words) <= 3

    def _is_valid_company_name(self, name: str, language: str) -> bool:
        """Проверка названия компании"""
        if len(name) < self.min_lengths["company"]:
            return False

        # Remove quotes for checking
        clean_name = re.sub(r'^[""«»\']\s*|\s*[""«»\']$', "", name).strip()

        if len(clean_name) < 3:
            return False

        # Should not be only service words
        service_words = [
            "и",
            "в",
            "на",
            "с",
            "для",
            "от",
            "and",
            "in",
            "on",
            "with",
            "for",
            "from",
        ]
        words = clean_name.lower().split()

        if all(word in service_words for word in words):
            return False

        return True

    def _finalize_patterns(
        self, patterns: List[ACPattern], language: str
    ) -> List[ACPattern]:
        """Финальная обработка и ранжирование паттернов"""
        if not patterns:
            return []

        # 1. Remove duplicates (keep best by metrics)
        unique_patterns = {}
        for pattern in patterns:
            key = pattern.pattern.lower()

            if key not in unique_patterns:
                unique_patterns[key] = pattern
            else:
                # Compare by total score
                existing_score = (
                    unique_patterns[key].confidence
                    * unique_patterns[key].specificity_score
                )
                new_score = pattern.confidence * pattern.specificity_score

                if new_score > existing_score:
                    unique_patterns[key] = pattern

        filtered_patterns = list(unique_patterns.values())

        # 2. Sort by priority
        filtered_patterns.sort(
            key=lambda x: (
                x.confidence * x.specificity_score + x.context_boost,
                len(x.pattern),  # With equal score prefer longer ones
            ),
            reverse=True,
        )

        # 3. Limit quantity (top-30 for efficiency)
        return filtered_patterns[:30]

    def _detect_language(self, text: str) -> str:
        """Определение языка текста"""
        cyrillic = len(re.findall(r"[а-яіїєёА-ЯІЇЄЁҐ]", text))
        latin = len(re.findall(r"[a-zA-Z]", text))

        if cyrillic > 0:
            ukrainian_chars = len(re.findall(r"[іїєґІЇЄҐ]", text))
            return "uk" if ukrainian_chars > 0 else "ru"
        elif latin > 0:
            return "en"
        else:
            return "en"

    def export_for_tier_based_ac(
        self, patterns: List[ACPattern]
    ) -> Dict[str, List[str]]:
        """
        Экспорт для многоуровневого AC поиска по архитектуре НБУ
        """
        tiers = {
            "tier_0_exact": [],  # Documents - instant auto-hit
            "tier_1_high": [],  # Contextual names - high priority
            "tier_2_medium": [],  # Structured - requires verification
            "tier_3_low": [],  # Others - minimal priority
        }

        for pattern in patterns:
            if pattern.pattern_type.startswith("document_"):
                tiers["tier_0_exact"].append(pattern.pattern)
            elif (
                pattern.pattern_type == "contextual_full_name"
                and pattern.confidence >= 0.9
            ):
                tiers["tier_1_high"].append(pattern.pattern)
            elif pattern.requires_confirmation or pattern.specificity_score < 0.8:
                tiers["tier_2_medium"].append(pattern.pattern)
            else:
                tiers["tier_3_low"].append(pattern.pattern)

        return tiers

    def get_optimization_stats(self, patterns: List[ACPattern]) -> Dict:
        """Статистика оптимизации"""
        if not patterns:
            return {}

        return {
            "total_patterns": len(patterns),
            "by_type": {
                "documents": len(
                    [p for p in patterns if p.pattern_type.startswith("document_")]
                ),
                "contextual_names": len(
                    [p for p in patterns if p.pattern_type == "contextual_full_name"]
                ),
                "structured_names": len(
                    [p for p in patterns if p.pattern_type == "structured_name"]
                ),
                "companies": len(
                    [p for p in patterns if p.pattern_type == "company_legal"]
                ),
            },
            "confidence_distribution": {
                "very_high": len([p for p in patterns if p.confidence >= 0.95]),
                "high": len([p for p in patterns if 0.9 <= p.confidence < 0.95]),
                "medium": len([p for p in patterns if 0.8 <= p.confidence < 0.9]),
                "low": len([p for p in patterns if p.confidence < 0.8]),
            },
            "requires_confirmation": len(
                [p for p in patterns if p.requires_confirmation]
            ),
            "average_confidence": sum(p.confidence for p in patterns) / len(patterns),
            "average_specificity": sum(p.specificity_score for p in patterns)
            / len(patterns),
        }
