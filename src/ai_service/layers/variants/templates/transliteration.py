"""
Transliteration utilities for name variant generation.
"""

from typing import List


class Transliterator:
    """Handles Cyrillic-Latin transliteration for name variants."""

    def __init__(self):
        """Initialize transliteration mappings."""
        # Cyrillic to Latin mapping
        self.cyrillic_to_latin = {
            "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
            "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
            "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
            "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
            "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
            "і": "i", "ї": "i", "є": "e", "ґ": "g"
        }

        # Latin to Cyrillic (reverse mapping)
        self.latin_to_cyrillic = {
            "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "e": "е",
            "zh": "ж", "z": "з", "i": "и", "y": "й", "k": "к", "l": "л", "m": "м",
            "n": "н", "o": "о", "p": "п", "r": "р", "s": "с", "t": "т", "u": "у",
            "f": "ф", "kh": "х", "ts": "ц", "ch": "ч", "sh": "ш", "shch": "щ",
            "yu": "ю", "ya": "я"
        }

    def transliterate_to_latin(self, text: str) -> str:
        """Транслитерация кириллицы в латиницу."""
        if not text:
            return ""

        result = ""
        for char in text:
            lower_char = char.lower()
            if lower_char in self.cyrillic_to_latin:
                translit_char = self.cyrillic_to_latin[lower_char]
                # Сохраняем регистр
                if char.isupper() and translit_char:
                    result += translit_char.capitalize()
                else:
                    result += translit_char
            else:
                result += char
        return result

    def transliterate_to_cyrillic(self, text: str) -> str:
        """Транслитерация латиницы в кириллицу."""
        if not text:
            return ""

        # Process text to handle multi-character mappings first
        text_lower = text.lower()
        result = ""
        i = 0

        while i < len(text_lower):
            # Check for multi-character mappings first (longest first)
            matched = False
            for length in [4, 3, 2, 1]:  # Check 'shch', 'kh', 'zh', etc.
                if i + length <= len(text_lower):
                    substr = text_lower[i:i + length]
                    if substr in self.latin_to_cyrillic:
                        cyrillic_char = self.latin_to_cyrillic[substr]
                        # Preserve case from original
                        if text[i].isupper():
                            result += cyrillic_char.upper()
                        else:
                            result += cyrillic_char
                        i += length
                        matched = True
                        break

            if not matched:
                result += text[i]
                i += 1

        return result

    def generate_transliteration_variants(self, name: str, language: str) -> List[str]:
        """Генерация транслитераций для имен с альтернативными вариантами отчеств."""
        variants = []

        # Кириллица -> латиница с Title Case
        if any(ord(c) >= 0x0400 for c in name):
            # Базовая транслитерация с правильной капитализацией
            base_translit = self.transliterate_to_latin(name)
            if base_translit:
                # Применяем Title Case для каждого слова
                title_case_translit = " ".join(word.capitalize() for word in base_translit.split())
                variants.append(title_case_translit)

                # Добавляем альтернативные варианты отчества
                patronymic_variants = self._generate_patronymic_transliteration_variants(title_case_translit)
                variants.extend(patronymic_variants)

        # Латиница -> кириллица (обратная транслитерация)
        elif all(ord(c) < 0x0400 for c in name if c.isalpha()):
            cyrillic_variant = self.transliterate_to_cyrillic(name)
            if cyrillic_variant and cyrillic_variant != name:
                variants.append(cyrillic_variant)

        return list(set(variants))  # Remove duplicates

    def _generate_patronymic_transliteration_variants(self, translit_name: str) -> List[str]:
        """Генерация альтернативных вариантов отчества при транслитерации."""
        variants = []

        # Обрабатываем отчества с заменами
        patronymic_replacements = [
            ("ovich", "ovych"),
            ("evich", "evych"),
            ("ovna", "ivna"),
            ("evna", "ivna"),
        ]

        for old_suffix, new_suffix in patronymic_replacements:
            if old_suffix in translit_name.lower():
                variant = translit_name.lower().replace(old_suffix, new_suffix)
                # Восстанавливаем капитализацию
                variant_words = []
                original_words = translit_name.split()
                variant_word_parts = variant.split()

                for i, word in enumerate(variant_word_parts):
                    if i < len(original_words):
                        # Сохраняем исходную капитализацию
                        if original_words[i][0].isupper():
                            variant_words.append(word.capitalize())
                        else:
                            variant_words.append(word)
                    else:
                        variant_words.append(word.capitalize())

                variants.append(" ".join(variant_words))

        return variants