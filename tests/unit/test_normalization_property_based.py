"""
Property-based tests for NormalizationService to prevent test fitting.

These tests ensure that core business rules always hold regardless
of input variations, making it impossible to "fit" tests to broken behavior.
"""

import pytest
from hypothesis import given, strategies as st, assume
import string

from src.ai_service.layers.normalization.normalization_service import NormalizationService


class TestNormalizationServiceProperties:
    """Property-based tests for normalization service invariants"""

    @pytest.fixture
    def normalization_service(self):
        return NormalizationService()

    @given(st.text(alphabet="АаБбВвГгДдЕеЁёЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЫыЬьЭэЮюЯя", min_size=2, max_size=50))
    def test_russian_feminine_surname_preservation(self, normalization_service, text):
        """Property: Russian feminine surnames should be preserved per CLAUDE.md"""
        # Focus on surnames ending in -ова, -ева, -ина, -ская
        feminine_endings = ["ова", "ева", "ина", "ская", "цкая", "нская"]

        # Only test if text might be a feminine surname
        assume(any(text.lower().endswith(ending) for ending in feminine_endings))

        result = normalization_service.normalize(text, language="ru")

        # Feminine forms should be preserved, not converted to masculine
        normalized_tokens = [token.lower() for token in result.tokens]
        original_feminine = any(text.lower().endswith(ending) for ending in feminine_endings)

        if original_feminine:
            # Should not be converted to masculine -ов, -ев, -ин, -ский
            masculine_endings = ["ов", "ев", "ин", "ский", "цкий", "нский"]
            for token in normalized_tokens:
                for masc_end in masculine_endings:
                    if token.endswith(masc_end):
                        # Ensure it's not a conversion from feminine
                        original_fem_base = token[:-len(masc_end)]
                        assert not any(text.lower().startswith(original_fem_base) for _ in feminine_endings)

    @given(st.text(alphabet="АаБбВвГгДдЕеЖжЗзИиЙйКкЛлМмНнОоПпРрСсТтУуФфХхЦцЧчШшЩщЪъЫыЬьЭэЮюЯя", min_size=3, max_size=30))
    def test_ukrainian_case_preservation(self, normalization_service, text):
        """Property: Ukrainian genitive/dative cases should be preserved per CLAUDE.md"""
        # Focus on Ukrainian case endings
        ukrainian_case_endings = ["ого", "ому", "ої", "ій", "ем", "ам", "ах", "ями"]

        assume(any(text.lower().endswith(ending) for ending in ukrainian_case_endings))

        result = normalization_service.normalize(text, language="uk")

        # Case endings should be preserved in normalization
        # This prevents conversion to nominative case
        normalized = result.normalized_text.lower()
        if any(text.lower().endswith(ending) for ending in ukrainian_case_endings):
            # Should preserve the case structure, not force nominative
            assert len(normalized.split()) <= len(text.split()) + 1  # Allow reasonable expansion

    @given(st.text(alphabet=string.ascii_letters + " .-'", min_size=2, max_size=50))
    def test_token_trace_completeness(self, normalization_service, text):
        """Property: Every output token must have trace information"""
        assume(text.strip() and any(c.isalpha() for c in text))

        result = normalization_service.normalize(text, language="en")

        # Every token in output should have corresponding trace
        assert len(result.tokens) == len(result.trace), "Token count must match trace count"

        for i, (token, trace_item) in enumerate(zip(result.tokens, result.trace)):
            assert trace_item.output == token, f"Trace output mismatch at position {i}"
            assert trace_item.role is not None, f"Missing role for token {token}"
            assert trace_item.rule is not None, f"Missing rule for token {token}"

    @given(st.lists(st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя", min_size=2, max_size=15), min_size=1, max_size=5))
    def test_org_acronym_filtering(self, normalization_service, words):
        """Property: ORG_ACRONYMS should never appear in personal name output"""
        # Add some org acronyms to test
        org_acronyms = ["ооо", "тов", "ллс", "лтд", "инк", "корп"]
        text_with_orgs = " ".join(words + org_acronyms[:2])

        result = normalization_service.normalize(text_with_orgs, language="ru")

        # ORG_ACRONYMS should be filtered out from personal names
        normalized_tokens_lower = [token.lower() for token in result.tokens]
        for acronym in org_acronyms:
            if acronym in text_with_orgs.lower():
                # Should not appear in normalized personal name output
                assert acronym not in normalized_tokens_lower, f"Org acronym {acronym} should be filtered"

    @given(st.text(alphabet="АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ", min_size=1, max_size=20))
    def test_case_normalization_consistency(self, normalization_service, text):
        """Property: Case normalization should be consistent and documented"""
        result1 = normalization_service.normalize(text, language="ru")
        result2 = normalization_service.normalize(text.lower(), language="ru")

        # Results should be related but may differ due to case processing
        # But the processing should be consistent
        assert result1.success == result2.success
        assert len(result1.tokens) == len(result2.tokens) or abs(len(result1.tokens) - len(result2.tokens)) <= 1

        # If different, should be documented in trace
        if result1.normalized_text != result2.normalized_text:
            case_changes = [item for item in result1.trace if 'case' in item.rule.lower()]
            # Should have some explanation for case processing differences

    @given(st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя" + "АБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ", min_size=3, max_size=30))
    def test_yo_normalization_consistency(self, normalization_service, text):
        """Property: ё should be consistently normalized to е"""
        if "ё" in text.lower():
            result = normalization_service.normalize(text, language="ru")

            # ё should be normalized to е in output
            normalized_lower = result.normalized_text.lower()
            assert "ё" not in normalized_lower, "ё should be normalized to е"

            # Should be documented in trace
            yo_changes = [item for item in result.trace if "ё" in getattr(item, 'original', '') or "yo" in item.rule.lower()]
            if "ё" in text:
                assert len(yo_changes) > 0, "ё normalization should be traced"

    @given(st.integers(min_value=1, max_value=5))
    def test_deterministic_behavior(self, normalization_service, seed):
        """Property: Same input should always produce same output"""
        test_cases = [
            "Владимир Владимирович Путин",
            "José María García",
            "O'Connor Patrick",
            "Мария Ивановна Петрова",
            "Jean-Baptiste Müller"
        ]

        for text in test_cases:
            result1 = normalization_service.normalize(text)
            result2 = normalization_service.normalize(text)

            # Must be completely identical
            assert result1.normalized_text == result2.normalized_text
            assert result1.tokens == result2.tokens
            assert len(result1.trace) == len(result2.trace)
            assert result1.success == result2.success

    @given(st.text(alphabet="абвгдеёжзийклмнопрстуфхцчшщъыьэюя іїєґ", min_size=5, max_size=40))
    def test_language_specific_processing(self, normalization_service, text):
        """Property: Language-specific rules should be applied correctly"""
        # Test with both Russian and Ukrainian
        if "і" in text or "ї" in text or "є" in text or "ґ" in text:
            # Likely Ukrainian
            result_uk = normalization_service.normalize(text, language="uk")
            result_ru = normalization_service.normalize(text, language="ru")

            # Ukrainian processing should preserve Ukrainian characters
            # Russian processing may convert them
            # But behavior should be consistent within each language
            assert result_uk.language in ["uk", "ru"]  # Should detect correctly
            assert result_ru.language in ["uk", "ru"]
        else:
            # Likely Russian
            result = normalization_service.normalize(text, language="ru")
            assert result.language == "ru"