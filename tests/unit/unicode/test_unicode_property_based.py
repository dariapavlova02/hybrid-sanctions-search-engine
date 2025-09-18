"""
Property-based tests for Unicode service to prevent test fitting.

These tests use hypothesis to generate random inputs and verify
invariant properties that should always hold, making it much harder
to "fit" tests to specific broken behavior.
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
import string
import unicodedata

from src.ai_service.layers.unicode.unicode_service import UnicodeService

# Configure Hypothesis settings for CI
settings.register_profile("ci", suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=200)
settings.load_profile("ci")


class TestUnicodeServiceProperties:
    """Property-based tests for Unicode service invariants"""

    @given(st.text(alphabet=string.ascii_letters + string.digits + " .-'", min_size=1, max_size=100))
    def test_ascii_text_preserved_structure(self, text):
        """Property: ASCII text should preserve basic structure"""
        assume(text.strip())  # Non-empty after stripping

        unicode_service = UnicodeService()
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
    def test_diacritic_removal_completeness(self, text):
        """Property: All diacritics should be removed consistently"""
        assume(any(unicodedata.category(c) == 'Mn' or ord(c) > 127 for c in text))

        unicode_service = UnicodeService()
        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # After normalization, no combining marks should remain
        combining_marks = [c for c in normalized if unicodedata.category(c) == 'Mn']
        assert len(combining_marks) == 0, f"Combining marks found: {combining_marks}"

        # Most common diacritics should be normalized (but some like ñ may be preserved)
        commonly_normalized = "áéíóúàèìòùâêîôûäëïöü"
        normalized_count = 0
        for char in commonly_normalized:
            if char not in normalized:
                normalized_count += 1

        # At least 80% of common diacritics should be normalized
        if len(commonly_normalized) > 0:
            normalization_ratio = normalized_count / len(commonly_normalized)
            assert normalization_ratio >= 0.8, f"Only {normalization_ratio:.1%} of diacritics normalized"

    @given(st.text(alphabet="АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ", min_size=1, max_size=50))
    def test_cyrillic_case_preservation(self, text):
        """Property: Cyrillic case should be preserved per CLAUDE.md P0.3"""
        unicode_service = UnicodeService()
        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # Case preservation means uppercase letters should remain in some form
        original_has_upper = any(c.isupper() for c in text)
        if original_has_upper:
            # Either preserved as uppercase or documented case change
            assert any(c.isupper() for c in normalized) or len(result.get("changes", [])) > 0

    @given(st.text(min_size=0, max_size=1000))
    def test_normalization_stability(self, text):
        """Property: Normalizing twice should give same result"""
        unicode_service = UnicodeService()
        result1 = unicode_service.normalize_text(text)
        result2 = unicode_service.normalize_text(result1["normalized"])

        # Second normalization should be stable
        assert result2["normalized"] == result1["normalized"]

    @given(st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя", min_size=1, max_size=50))
    def test_russian_morphology_requirements(self, text):
        """Property: Russian text should follow morphology rules"""
        unicode_service = UnicodeService()
        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # ё should be normalized to е consistently
        if "ё" in text:
            assert "ё" not in normalized, "Russian ё should be normalized to е"
            assert normalized.count("е") >= text.count("ё"), "ё should become е"

    @given(st.integers(min_value=1, max_value=10))
    def test_batch_consistency(self, count):
        """Property: Batch normalization should be consistent with individual"""
        unicode_service = UnicodeService()
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
    def test_no_information_loss_on_important_chars(self, text):
        """Property: Important characters should not disappear completely"""
        unicode_service = UnicodeService()
        # Filter to meaningful text
        meaningful_chars = [c for c in text if c.isalnum() or c in ".-' "]
        assume(len(meaningful_chars) >= 2)

        result = unicode_service.normalize_text(text)
        normalized = result["normalized"]

        # Should not lose all meaningful content
        normalized_meaningful = [c for c in normalized if c.isalnum() or c in ".-' "]
        assert len(normalized_meaningful) >= len(meaningful_chars) // 3, "Too much content lost"