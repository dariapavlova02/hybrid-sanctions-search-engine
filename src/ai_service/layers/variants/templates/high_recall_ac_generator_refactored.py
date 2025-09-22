"""
Refactored High-Recall AC Pattern Generator для санкционного скрининга
ПРИОРИТЕТ: Максимальный Recall (не пропускать санкционных лиц)
Стратегия: Лучше 10 ложных срабатываний, чем 1 пропущенное санкционное лицо

This is a refactored version of the original high_recall_ac_generator.py
breaking down the large monolithic class into smaller, more manageable modules.
"""

import re
from typing import Any, Dict, List, Set

from .pattern_types import RecallOptimizedPattern
from .text_normalization import TextNormalizer
from .transliteration import Transliterator


class HighRecallACGeneratorRefactored:
    """
    Генератор паттернов с максимальным Recall для санкционного скрининга
    Философия: "Catch everything, filter later"

    Refactored version with improved modularity and maintainability.
    """

    def __init__(self):
        """Initialize the generator with required components."""
        # Initialize component services
        try:
            from ...unicode.unicode_service import UnicodeService
            unicode_service = UnicodeService()
        except ImportError:
            unicode_service = None

        self.text_normalizer = TextNormalizer(unicode_service)
        self.transliterator = Transliterator()

        # Stop words that should NEVER be patterns
        self.absolute_stop_words = {
            "ru": {
                "и", "в", "на", "с", "по", "для", "от", "до", "из",
                "год", "лет", "рублей", "долларов", "евро", "тысяч",
                "миллионов", "процентов", "штук", "человек", "дней"
            },
            "uk": {
                "і", "в", "на", "з", "по", "для", "від", "до", "із",
                "рік", "років", "гривень", "доларів", "євро", "тисяч",
                "мільйонів", "відсотків", "штук", "людей", "днів"
            },
            "en": {
                "and", "in", "on", "with", "by", "for", "from", "to", "of",
                "year", "years", "dollars", "euros", "thousands",
                "millions", "percent", "pieces", "people", "days"
            }
        }

        # Initialize caches
        self._diminutives_cache = {}
        self._nicknames_cache = {}

    def normalize_for_ac(self, text: str) -> str:
        """Normalize text for Aho-Corasick pattern matching."""
        return self.text_normalizer.normalize_for_ac(text)

    def generate_high_recall_patterns_from_sanctions_data(
        self,
        sanctions_record: Dict[str, Any]
    ) -> List[RecallOptimizedPattern]:
        """Генерация паттернов из данных санкций с использованием всех доступных вариантов имен."""
        patterns = []

        # TIER 0: Автоматическое извлечение документов и кодов
        tier_0_patterns = self._extract_document_codes_from_sanctions(sanctions_record)
        patterns.extend(tier_0_patterns)

        # TIER 1: Exact name matches (highest precision)
        exact_patterns = self._generate_exact_name_patterns(sanctions_record)
        patterns.extend(exact_patterns)

        # TIER 2: High recall variants (transliteration, declension)
        high_recall_patterns = self._generate_high_recall_variants(sanctions_record)
        patterns.extend(high_recall_patterns)

        # TIER 3: Broad recall variants (diminutives, nicknames)
        broad_recall_patterns = self._generate_broad_recall_variants(sanctions_record)
        patterns.extend(broad_recall_patterns)

        # Filter out stop words and invalid patterns
        filtered_patterns = self._filter_invalid_patterns(patterns)

        return filtered_patterns

    def generate_high_recall_patterns(
        self,
        name_variants: List[str],
        language: str = "auto",
        include_transliterations: bool = True,
        include_declensions: bool = True,
        include_diminutives: bool = True,
        aggressive_variants: bool = False
    ) -> List[RecallOptimizedPattern]:
        """
        Генерация паттернов высокого recall из списка вариантов имен

        Args:
            name_variants: Список исходных вариантов имен
            language: Язык для анализа ('ru', 'uk', 'en', 'auto')
            include_transliterations: Включать транслитерации
            include_declensions: Включать склонения
            include_diminutives: Включать уменьшительные формы
            aggressive_variants: Агрессивные варианты (больше false positives)
        """
        all_patterns = []

        for name_variant in name_variants:
            if not name_variant or len(name_variant.strip()) < 2:
                continue

            # Определяем язык если auto
            detected_lang = language
            if language == "auto":
                detected_lang = self.text_normalizer.detect_language(name_variant)

            # Генерируем паттерны для этого варианта
            variant_patterns = self._generate_patterns_for_single_name(
                name_variant,
                detected_lang,
                include_transliterations,
                include_declensions,
                include_diminutives,
                aggressive_variants
            )

            all_patterns.extend(variant_patterns)

        # Дедупликация и сортировка по приоритету
        return self._deduplicate_and_prioritize_patterns(all_patterns)

    def _generate_exact_name_patterns(self, sanctions_record: Dict[str, Any]) -> List[RecallOptimizedPattern]:
        """Generate exact name match patterns."""
        patterns = []

        # Extract all name fields from sanctions record
        name_fields = ['name', 'full_name', 'first_name', 'last_name', 'alias', 'aliases']

        for field in name_fields:
            if field in sanctions_record and sanctions_record[field]:
                value = sanctions_record[field]
                if isinstance(value, str):
                    pattern = self._create_pattern(
                        value,
                        "exact_name",
                        recall_tier=0,
                        precision_hint=0.95
                    )
                    patterns.append(pattern)
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            pattern = self._create_pattern(
                                item,
                                "exact_name",
                                recall_tier=0,
                                precision_hint=0.95
                            )
                            patterns.append(pattern)

        return patterns

    def _generate_high_recall_variants(self, sanctions_record: Dict[str, Any]) -> List[RecallOptimizedPattern]:
        """Generate high recall variants with transliteration and declension."""
        patterns = []

        # Get base names
        base_names = self._extract_base_names(sanctions_record)

        for name in base_names:
            language = self.text_normalizer.detect_language(name)

            # Transliteration variants
            translit_variants = self.transliterator.generate_transliteration_variants(name, language)
            for variant in translit_variants:
                pattern = self._create_pattern(
                    variant,
                    "transliteration",
                    recall_tier=1,
                    precision_hint=0.8
                )
                patterns.append(pattern)

            # Declension variants (for Cyrillic languages)
            if language in ["ru", "uk"]:
                declension_variants = self._generate_declension_variants(name, language)
                for variant in declension_variants:
                    pattern = self._create_pattern(
                        variant,
                        "declension",
                        recall_tier=1,
                        precision_hint=0.85
                    )
                    patterns.append(pattern)

        return patterns

    def _generate_broad_recall_variants(self, sanctions_record: Dict[str, Any]) -> List[RecallOptimizedPattern]:
        """Generate broad recall variants with diminutives and nicknames."""
        patterns = []

        # Get given names for diminutive generation
        given_names = self._extract_given_names(sanctions_record)

        for name in given_names:
            language = self.text_normalizer.detect_language(name)

            # Diminutive variants
            diminutive_variants = self._generate_diminutive_variants(name, language)
            for variant in diminutive_variants:
                pattern = self._create_pattern(
                    variant,
                    "diminutive",
                    recall_tier=2,
                    precision_hint=0.6
                )
                patterns.append(pattern)

        return patterns

    def _create_pattern(
        self,
        text: str,
        pattern_type: str,
        recall_tier: int,
        precision_hint: float
    ) -> RecallOptimizedPattern:
        """Create a pattern with normalized text and metadata."""
        normalized = self.normalize_for_ac(text)
        language = self.text_normalizer.detect_language(text)

        return RecallOptimizedPattern(
            pattern=normalized,
            pattern_type=pattern_type,
            recall_tier=recall_tier,
            precision_hint=precision_hint,
            variants=[text] if text != normalized else [],
            language=language,
            source_confidence=1.0
        )

    def _extract_document_codes_from_sanctions(self, sanctions_record: Dict[str, Any]) -> List[RecallOptimizedPattern]:
        """Extract document codes and identifiers from sanctions record."""
        # This is a simplified implementation
        # In the full version, this would extract passport numbers,
        # tax IDs, and other identifying documents
        patterns = []

        document_fields = ['passport', 'tax_id', 'registration_number', 'document_id']

        for field in document_fields:
            if field in sanctions_record and sanctions_record[field]:
                value = str(sanctions_record[field])
                if len(value) >= 4:  # Minimum length for meaningful document codes
                    pattern = self._create_pattern(
                        value,
                        "document_code",
                        recall_tier=0,
                        precision_hint=0.99
                    )
                    patterns.append(pattern)

        return patterns

    def _extract_base_names(self, sanctions_record: Dict[str, Any]) -> List[str]:
        """Extract base names from sanctions record."""
        names = []
        name_fields = ['name', 'full_name', 'first_name', 'last_name']

        for field in name_fields:
            if field in sanctions_record and sanctions_record[field]:
                value = sanctions_record[field]
                if isinstance(value, str):
                    names.append(value)
                elif isinstance(value, list):
                    names.extend(str(item) for item in value if item)

        return [name for name in names if len(name.strip()) >= 2]

    def _extract_given_names(self, sanctions_record: Dict[str, Any]) -> List[str]:
        """Extract given names for diminutive generation."""
        given_names = []

        if 'first_name' in sanctions_record:
            given_names.append(str(sanctions_record['first_name']))

        # Parse full names to extract first component
        full_names = self._extract_base_names(sanctions_record)
        for full_name in full_names:
            parts = full_name.split()
            if parts:
                given_names.append(parts[0])

        return [name for name in given_names if len(name.strip()) >= 2]

    def _generate_patterns_for_single_name(
        self,
        name: str,
        language: str,
        include_transliterations: bool,
        include_declensions: bool,
        include_diminutives: bool,
        aggressive_variants: bool
    ) -> List[RecallOptimizedPattern]:
        """Generate all pattern variants for a single name."""
        patterns = []

        # Exact pattern
        exact_pattern = self._create_pattern(name, "exact", 0, 0.95)
        patterns.append(exact_pattern)

        # Transliteration
        if include_transliterations:
            translit_variants = self.transliterator.generate_transliteration_variants(name, language)
            for variant in translit_variants:
                pattern = self._create_pattern(variant, "transliteration", 1, 0.8)
                patterns.append(pattern)

        # Add other variant types here...

        return patterns

    def _generate_declension_variants(self, name: str, language: str) -> List[str]:
        """Generate declension variants for Cyrillic names."""
        # Simplified implementation - in full version would use morphological analysis
        variants = []

        if language == "ru":
            # Simple Russian declension patterns
            if name.endswith('ов'):
                variants.extend([name + 'а', name + 'у', name + 'ым', name + 'е'])
            elif name.endswith('ин'):
                variants.extend([name + 'а', name + 'у', name + 'ым', name + 'е'])

        return variants

    def _generate_diminutive_variants(self, name: str, language: str) -> List[str]:
        """Generate diminutive variants for given names."""
        # Simplified implementation - in full version would use comprehensive dictionaries
        variants = []

        common_diminutives = {
            "ru": {
                "Александр": ["Саша", "Шура", "Алекс"],
                "Владимир": ["Вова", "Володя", "Влад"],
                "Екатерина": ["Катя", "Катюша", "Кейт"],
            },
            "en": {
                "Alexander": ["Alex", "Sasha", "Xander"],
                "Vladimir": ["Vlad", "Vova"],
                "Katherine": ["Kate", "Katie", "Kathy"],
            }
        }

        if language in common_diminutives and name in common_diminutives[language]:
            variants.extend(common_diminutives[language][name])

        return variants

    def _filter_invalid_patterns(self, patterns: List[RecallOptimizedPattern]) -> List[RecallOptimizedPattern]:
        """Filter out invalid patterns (stop words, too short, etc.)."""
        filtered = []

        for pattern in patterns:
            # Skip empty or too short patterns
            if not pattern.pattern or len(pattern.pattern.strip()) < 2:
                continue

            # Skip patterns that are stop words
            if self._is_stop_word(pattern.pattern, pattern.language):
                continue

            # Skip patterns that are purely numeric (unless document codes)
            if pattern.pattern.isdigit() and pattern.pattern_type != "document_code":
                continue

            filtered.append(pattern)

        return filtered

    def _is_stop_word(self, text: str, language: str) -> bool:
        """Check if text is a stop word that should not be a pattern."""
        if not text:
            return True

        text_lower = text.lower().strip()

        # Check against absolute stop words
        if language in self.absolute_stop_words:
            return text_lower in self.absolute_stop_words[language]

        # Check against all language stop words if language unknown
        for lang_stop_words in self.absolute_stop_words.values():
            if text_lower in lang_stop_words:
                return True

        return False

    def _deduplicate_and_prioritize_patterns(
        self,
        patterns: List[RecallOptimizedPattern]
    ) -> List[RecallOptimizedPattern]:
        """Remove duplicates and sort by recall tier and precision."""
        # Deduplicate by pattern text
        seen_patterns = set()
        unique_patterns = []

        for pattern in patterns:
            if pattern.pattern not in seen_patterns:
                seen_patterns.add(pattern.pattern)
                unique_patterns.append(pattern)

        # Sort by recall tier (lower = higher priority) then by precision hint (higher = higher priority)
        unique_patterns.sort(key=lambda p: (p.recall_tier, -p.precision_hint))

        return unique_patterns