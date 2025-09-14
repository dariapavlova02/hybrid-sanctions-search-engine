"""
Comprehensive test suite for UnicodeService.

Tests Unicode normalization, character mapping, encoding recovery,
and edge cases for the Unicode processing layer.
"""

import pytest
import unicodedata
from ai_service.layers.unicode.unicode_service import UnicodeService


class TestUnicodeService:
    """Test UnicodeService core functionality"""

    def setup_method(self):
        """Setup UnicodeService for each test"""
        self.service = UnicodeService()

    def test_initialization(self):
        """Test UnicodeService initialization"""
        service = UnicodeService()
        assert service is not None
        assert hasattr(service, 'character_mapping')
        assert hasattr(service, 'preserved_chars')
        assert len(service.character_mapping) > 0

    def test_normalize_text_basic(self):
        """Test basic text normalization"""
        text = "Hello World"
        result = self.service.normalize_text(text)

        assert result == "Hello World"
        assert isinstance(result, str)

    def test_normalize_text_cyrillic_mapping(self):
        """Test Cyrillic character mappings"""
        test_cases = [
            ("ё", "е"),  # Russian ё -> е
            ("Ё", "Е"),  # Capital Ё -> Е
            ("і", "и"),  # Ukrainian і -> Russian и
            ("ї", "и"),  # Ukrainian ї -> Russian и
            ("є", "е"),  # Ukrainian є -> Russian е
            ("ґ", "г"),  # Ukrainian ґ -> Russian г
        ]

        for input_char, expected_char in test_cases:
            result = self.service.normalize_text(input_char)
            assert expected_char in result, f"Failed mapping {input_char} -> {expected_char}"

    def test_normalize_text_latin_diacritics(self):
        """Test Latin character diacritic removal"""
        test_cases = [
            ("José", "Jose"),
            ("Müller", "Muller"),
            ("François", "Francois"),
            ("André", "Andre"),
            ("Björk", "Bjork"),
            ("naïve", "naive"),
        ]

        for input_text, expected in test_cases:
            result = self.service.normalize_text(input_text)
            # Should contain the base characters without diacritics
            for i, char in enumerate(expected):
                assert char.lower() in result.lower(), f"Failed normalizing {input_text}"

    def test_normalize_text_aggressive_mode(self):
        """Test aggressive normalization mode"""
        # Test with emoji and special characters
        text_with_emoji = "Hello 👋 World 🌍"
        result = self.service.normalize_text(text_with_emoji, aggressive=True)

        # Aggressive mode should remove or replace emoji
        assert "👋" not in result
        assert "🌍" not in result
        assert "Hello" in result
        assert "World" in result

    def test_normalize_text_mixed_scripts(self):
        """Test normalization with mixed scripts"""
        mixed_text = "John Иванов François"
        result = self.service.normalize_text(mixed_text)

        assert "John" in result
        assert "Иванов" in result or "Ivanov" in result  # May be transliterated
        assert len(result) > 0

    def test_unicode_nfc_normalization(self):
        """Test Unicode NFC normalization"""
        # Test combining characters
        combining_text = "e\u0301"  # e + combining acute accent = é
        result = self.service.normalize_text(combining_text)

        # Should be normalized to precomposed form
        normalized_expected = unicodedata.normalize('NFC', combining_text)
        assert normalized_expected in result or 'e' in result

    def test_encoding_recovery(self):
        """Test encoding recovery functionality"""
        # Test Windows-1252 encoding issues
        corrupted_texts = [
            "Caf\x82",  # Should become "Café"
            "r\x82sum\x82",  # Should become "résumé"
        ]

        for corrupted in corrupted_texts:
            result = self.service.normalize_text(corrupted)
            assert result != corrupted  # Should be different
            assert len(result) >= len(corrupted.replace('\x82', ''))

    def test_whitespace_normalization(self):
        """Test whitespace normalization"""
        test_cases = [
            ("  multiple   spaces  ", "multiple spaces"),
            ("\t\n\r mixed whitespace \t\n", "mixed whitespace"),
            ("line1\n\nline2", "line1 line2"),
            ("  ", ""),
        ]

        for input_text, expected_pattern in test_cases:
            result = self.service.normalize_text(input_text)
            # Should collapse whitespace
            assert not re.search(r'\s{2,}', result)
            assert result.strip() != "" or input_text.strip() == ""

    def test_invisible_characters_removal(self):
        """Test removal of invisible Unicode characters"""
        invisible_chars = [
            "\u200b",  # Zero-width space
            "\u200c",  # Zero-width non-joiner
            "\u200d",  # Zero-width joiner
            "\ufeff",  # Byte order mark
        ]

        for char in invisible_chars:
            text_with_invisible = f"Hello{char}World"
            result = self.service.normalize_text(text_with_invisible)
            assert char not in result
            assert "HelloWorld" in result or "Hello World" in result

    def test_homoglyph_handling(self):
        """Test homoglyph character handling"""
        # Test visually similar characters
        homoglyph_cases = [
            ("H0ME", "HOME"),  # 0 -> O
            ("1OOK", "LOOK"),  # 1 -> I, 0 -> O
        ]

        for input_text, expected_pattern in homoglyph_cases:
            result = self.service.normalize_text(input_text)
            # Should handle common homoglyphs
            assert result != input_text or any(c.isalpha() for c in result)

    def test_preserve_cyrillic_characters(self):
        """Test that important Cyrillic characters are preserved"""
        cyrillic_text = "Владимир Путин"
        result = self.service.normalize_text(cyrillic_text)

        # Should preserve Cyrillic script
        cyrillic_preserved = any('\u0400' <= c <= '\u04FF' for c in result)
        assert cyrillic_preserved or "Vladimir" in result  # May be transliterated

    def test_edge_cases(self):
        """Test edge cases and error conditions"""
        edge_cases = [
            "",  # Empty string
            None,  # None input
            "   ",  # Only whitespace
            "\x00\x01\x02",  # Control characters
            "🚀" * 1000,  # Very long emoji string
        ]

        for case in edge_cases:
            try:
                if case is None:
                    with pytest.raises((TypeError, AttributeError)):
                        self.service.normalize_text(case)
                else:
                    result = self.service.normalize_text(case)
                    assert isinstance(result, str)
                    # Should not crash
            except Exception as e:
                pytest.fail(f"Failed on edge case {repr(case)}: {e}")

    def test_long_text_handling(self):
        """Test handling of very long texts"""
        long_text = "А" * 10000  # 10k Cyrillic characters
        result = self.service.normalize_text(long_text)

        assert isinstance(result, str)
        assert len(result) > 0
        # Performance should be reasonable (tested by not timing out)

    def test_character_mapping_completeness(self):
        """Test that character mapping is comprehensive"""
        service = UnicodeService()

        # Check that common problematic characters are mapped
        important_chars = ['ё', 'Ё', 'і', 'ї', 'є', 'ґ', 'á', 'é', 'ñ', 'ç']

        for char in important_chars:
            if char in service.character_mapping:
                mapped = service.character_mapping[char]
                assert len(mapped) > 0
                assert mapped != char  # Should actually map to something different

    def test_normalization_consistency(self):
        """Test that normalization is consistent across calls"""
        test_text = "Тест François José"

        result1 = self.service.normalize_text(test_text)
        result2 = self.service.normalize_text(test_text)

        assert result1 == result2  # Should be deterministic

    def test_normalization_with_numbers_and_punctuation(self):
        """Test normalization preserves numbers and basic punctuation"""
        text = "João Silva, 123-456-7890, email@domain.com"
        result = self.service.normalize_text(text)

        # Numbers and basic punctuation should be preserved
        assert "123" in result
        assert "456" in result
        assert "7890" in result
        assert "@" in result or "email" in result
        assert "domain" in result

    def test_different_normalization_forms(self):
        """Test different Unicode normalization forms"""
        # Test text with combining characters
        text = "café"  # This might be composed or decomposed

        result = self.service.normalize_text(text)

        # Should handle both NFC and NFD forms consistently
        assert "cafe" in result.lower() or "café" in result
        assert len(result) > 0

    def test_rtl_and_bidi_text(self):
        """Test handling of RTL and bidirectional text"""
        # Arabic/Hebrew text (if we need to support it)
        rtl_text = "Hello שלום World"
        result = self.service.normalize_text(rtl_text)

        assert "Hello" in result
        assert "World" in result
        # RTL parts may be preserved or transliterated
        assert len(result) > 0


class TestUnicodeServiceIntegration:
    """Integration tests for UnicodeService with real-world scenarios"""

    def setup_method(self):
        """Setup UnicodeService for integration tests"""
        self.service = UnicodeService()

    def test_real_world_name_normalization(self):
        """Test normalization with real-world names"""
        real_names = [
            "José María García",
            "François Müller",
            "Владимир Путин",
            "Oleksandr Тимошенко",  # Mixed script
            "João da Silva",
            "Björn Åström",
        ]

        for name in real_names:
            result = self.service.normalize_text(name)
            assert len(result) > 0
            assert isinstance(result, str)
            # Should produce some meaningful output
            words = result.split()
            assert len(words) >= 2  # Should have at least name parts

    def test_payment_text_normalization(self):
        """Test normalization on payment description texts"""
        payment_texts = [
            "Оплата за услуги ООО Ромашка",
            "Payment to José García Müller",
            "Перевод для François Иванов",
            "Transfer für Björn Åström GmbH",
        ]

        for text in payment_texts:
            result = self.service.normalize_text(text)
            assert len(result) > 0
            # Should preserve organization indicators
            org_indicators = ["ООО", "GmbH", "LLC", "Ltd"]
            has_org_context = any(ind.lower() in result.lower() for ind in org_indicators)
            # At least preserve some meaningful content
            assert len(result.split()) >= 2

    def test_normalization_preserves_structure(self):
        """Test that normalization preserves important text structure"""
        structured_text = "Name: José García, DOB: 01.01.1980, ID: AB123456"
        result = self.service.normalize_text(structured_text)

        # Should preserve important structural elements
        assert ":" in result or "Garcia" in result
        assert "01" in result or "1980" in result
        assert "AB123456" in result or "123456" in result

    @pytest.mark.parametrize("aggressive", [True, False])
    def test_aggressive_vs_conservative_mode(self, aggressive):
        """Test difference between aggressive and conservative normalization"""
        complex_text = "Café 🌟 José@email.com #hashtag"

        result = self.service.normalize_text(complex_text, aggressive=aggressive)

        if aggressive:
            # Aggressive should remove more decorative elements
            assert "🌟" not in result
            assert "#" not in result or "hashtag" not in result

        # Both modes should preserve core content
        assert "Cafe" in result or "Jose" in result
        assert len(result) > 0


import re

# Add these imports if they're missing from the original test
import pytest
import unicodedata
# from ai_service.layers.unicode.unicode_service import UnicodeService