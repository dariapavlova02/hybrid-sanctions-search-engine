"""
Property-based tests for Unicode service to prevent test fitting.

These tests use hypothesis to generate random inputs and verify
invariant properties that should always hold, making it much harder
to "fit" tests to specific broken behavior.
"""

import pytest
from hypothesis import given, strategies as st, assume
import string
import unicodedata

from src.ai_service.layers.unicode.unicode_service import UnicodeService


class TestUnicodeServiceProperties:
    """Property-based tests for Unicode service invariants"""

    @pytest.fixture
    def unicode_service(self):
        return UnicodeService()

    @given(st.text(alphabet=string.ascii_letters + string.digits + " .-'", min_size=1, max_size=100))
    def test_ascii_text_preserved_structure(self, unicode_service, text):
        """Property: ASCII text should preserve basic structure"""
        assume(text.strip())  # Non-empty after stripping

        result = unicode_service.normalize_text(text)

        # ASCII text should not be changed dramatically
        assert isinstance(result, dict)
        assert "normalized" in result
        assert "original" in result
        assert result["original"] == text

        # Length should not change drastically for ASCII
        assert len(result["normalized"]) <= len(text) * 2
        assert len(result["normalized"]) >= len(text.strip()) // 2

    @given(st.text(alphabet="áéíóúàèìòùâêîôûäëïöüãñç", min_size=1, max_size=50))
    def test_diacritic_removal_completeness(self, unicode_service, text):
        """Property: All diacritics should be removed consistently"""
        assume(any(unicodedata.category(c) == 'Mn' or ord(c) > 127 for c in text))

        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # After normalization, no combining marks should remain
        combining_marks = [c for c in normalized if unicodedata.category(c) == 'Mn']
        assert len(combining_marks) == 0, f"Combining marks found: {combining_marks}"

        # Common diacritics should be removed
        forbidden_chars = "áéíóúàèìòùâêîôûäëïöüãñç"
        for char in forbidden_chars:
            assert char not in normalized, f"Diacritic {char} not normalized"

    @given(st.text(alphabet="АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ", min_size=1, max_size=50))
    def test_cyrillic_case_preservation(self, unicode_service, text):
        """Property: Cyrillic case should be preserved per CLAUDE.md P0.3"""
        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # Case preservation means uppercase letters should remain in some form
        original_has_upper = any(c.isupper() for c in text)
        if original_has_upper:
            # Either preserved as uppercase or documented case change
            assert any(c.isupper() for c in normalized) or len(result.get("changes", [])) > 0

    @given(st.text(min_size=0, max_size=1000))
    def test_normalization_stability(self, unicode_service, text):
        """Property: Normalizing twice should give same result"""
        result1 = unicode_service.normalize_text(text)
        result2 = unicode_service.normalize_text(result1["normalized"])

        # Second normalization should be stable
        assert result2["normalized"] == result1["normalized"]

    @given(st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя", min_size=1, max_size=50))
    def test_russian_morphology_requirements(self, unicode_service, text):
        """Property: Russian text should follow morphology rules"""
        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # ё should be normalized to е consistently
        if "ё" in text:
            assert "ё" not in normalized, "Russian ё should be normalized to е"
            assert normalized.count("е") >= text.count("ё"), "ё should become е"

    @given(st.integers(min_value=1, max_value=10))
    def test_batch_consistency(self, unicode_service, count):
        """Property: Batch normalization should be consistent with individual"""
        # Generate consistent test data
        texts = ["Café", "München", "José"] * count

        # Individual results
        individual_results = [unicode_service.normalize_text(text) for text in texts]

        # Batch results
        batch_results = unicode_service.normalize_batch(texts)

        # Should be identical
        assert len(batch_results) == len(individual_results)
        for i, (ind, batch) in enumerate(zip(individual_results, batch_results)):
            assert ind["normalized"] == batch["normalized"], f"Mismatch at index {i}"

    @given(st.text(alphabet=string.printable, min_size=1, max_size=100))
    def test_no_information_loss_on_important_chars(self, unicode_service, text):
        """Property: Important characters should not disappear completely"""
        # Filter to meaningful text
        meaningful_chars = [c for c in text if c.isalnum() or c in ".-' "]
        assume(len(meaningful_chars) >= 2)

        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # Should not lose all meaningful content
        normalized_meaningful = [c for c in normalized if c.isalnum() or c in ".-' "]
        assert len(normalized_meaningful) >= len(meaningful_chars) // 3, "Too much content lost"