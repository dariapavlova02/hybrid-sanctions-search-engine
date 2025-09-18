"""
Property-based tests for normalization idempotency.

This test ensures that normalization is idempotent: applying normalization
twice to the same input should yield the same result.

norm(norm(x)) == norm(x)
"""

import pytest
from hypothesis import given, strategies as st, assume, settings, HealthCheck
from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from src.ai_service.utils.feature_flags import FeatureFlags


class TestNormalizationIdempotency:
    """Test normalization idempotency properties."""

    @pytest.fixture
    def factory(self):
        """Get normalization factory instance for testing."""
        return NormalizationFactory()

    @pytest.fixture
    def config_ru(self):
        """Get Russian normalization config."""
        return NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True,
            remove_stop_words=True,
            preserve_names=True
        )

    @pytest.fixture
    def config_uk(self):
        """Get Ukrainian normalization config."""
        return NormalizationConfig(
            language="uk",
            enable_advanced_features=True,
            enable_morphology=True,
            remove_stop_words=True,
            preserve_names=True
        )

    @pytest.fixture
    def feature_flags(self):
        """Get feature flags with nominative enforcement enabled."""
        return FeatureFlags(
            enforce_nominative=True,
            preserve_feminine_surnames=True
        )

    # Generate Russian names using Cyrillic characters
    @given(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), whitelist_characters=' .-'),
        min_size=1,
        max_size=50
    ).filter(lambda x: any(ord(c) >= 0x400 and ord(c) <= 0x04FF for c in x if c.isalpha())))
    @settings(max_examples=50, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    async def test_russian_normalization_idempotency(self, text):
        """Test that Russian normalization is idempotent."""
        # Create instances inside the test to avoid function-scoped fixture issues
        factory = NormalizationFactory()
        config_ru = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True,
            remove_stop_words=True,
            preserve_names=True
        )
        feature_flags = FeatureFlags(
            enforce_nominative=True,
            preserve_feminine_surnames=True
        )

        # Skip empty or whitespace-only strings
        assume(text and text.strip())

        # Skip strings that are too short or too long
        assume(2 <= len(text.strip()) <= 50)

        # First normalization
        result1 = await factory.normalize_text(text, config_ru, feature_flags)

        # Skip if first normalization failed
        assume(result1.success)
        assume(result1.normalized)

        # Second normalization on the result
        result2 = await factory.normalize_text(result1.normalized, config_ru, feature_flags)

        # Idempotency check: norm(norm(x)) == norm(x)
        assert result2.success, f"Second normalization failed for '{result1.normalized}'"
        assert result1.normalized == result2.normalized, \
            f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    # Generate Ukrainian names using Cyrillic characters
    @given(st.text(
        alphabet=st.characters(whitelist_categories=('Lu', 'Ll'), whitelist_characters=' .-'),
        min_size=1,
        max_size=50
    ).filter(lambda x: any(ord(c) >= 0x400 and ord(c) <= 0x04FF for c in x if c.isalpha())))
    @settings(max_examples=50, deadline=5000, suppress_health_check=[HealthCheck.function_scoped_fixture, HealthCheck.filter_too_much])
    async def test_ukrainian_normalization_idempotency(self, text):
        """Test that Ukrainian normalization is idempotent."""
        # Create instances inside the test to avoid function-scoped fixture issues
        factory = NormalizationFactory()
        config_uk = NormalizationConfig(
            language="uk",
            enable_advanced_features=True,
            enable_morphology=True,
            remove_stop_words=True,
            preserve_names=True
        )
        feature_flags = FeatureFlags(
            enforce_nominative=True,
            preserve_feminine_surnames=True
        )

        # Skip empty or whitespace-only strings
        assume(text and text.strip())

        # Skip strings that are too short or too long
        assume(2 <= len(text.strip()) <= 50)

        # First normalization
        result1 = await factory.normalize_text(text, config_uk, feature_flags)

        # Skip if first normalization failed
        assume(result1.success)
        assume(result1.normalized)

        # Second normalization on the result
        result2 = await factory.normalize_text(result1.normalized, config_uk, feature_flags)

        # Idempotency check: norm(norm(x)) == norm(x)
        assert result2.success, f"Second normalization failed for '{result1.normalized}'"
        assert result1.normalized == result2.normalized, \
            f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    @pytest.mark.asyncio
    async def test_known_cases_idempotency(self, factory, config_ru, feature_flags):
        """Test idempotency for known test cases."""
        test_cases = [
            "Иван Иванович Иванов",
            "Мария Петровна Сидорова",
            "Петров Иван Сергеевич",
            "Анна Владимировна Козлова",
            "И. И. Петров",
            "Иванов И.И.",
            "Петров-Водкин Кузьма Сергеевич",
            "О'Коннор Шон",
        ]

        for text in test_cases:
            # First normalization
            result1 = await factory.normalize_text(text, config_ru, feature_flags)
            assert result1.success, f"First normalization failed for '{text}'"

            # Second normalization
            result2 = await factory.normalize_text(result1.normalized, config_ru, feature_flags)
            assert result2.success, f"Second normalization failed for '{result1.normalized}'"

            # Idempotency check
            assert result1.normalized == result2.normalized, \
                f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    @pytest.mark.asyncio
    async def test_declining_forms_idempotency(self, factory, config_ru, feature_flags):
        """Test idempotency for names in various declining forms."""
        declining_forms = [
            # Genitive forms that should become nominative
            "Иванова",    # Genitive/Accusative -> should become "Иванов" (if masculine intended)
            "Петрову",    # Dative -> should become "Петров"
            "Сидоровым",  # Instrumental -> should become "Сидоров"
            "Марии",      # Genitive -> should become "Мария"
            "Анне",       # Dative -> should become "Анна"

            # Feminine forms that should be preserved
            "Ивановой",   # Feminine genitive -> should become "Иванова"
            "Петровой",   # Feminine instrumental -> should become "Петрова"
        ]

        for text in declining_forms:
            # First normalization (should convert to nominative)
            result1 = await factory.normalize_text(text, config_ru, feature_flags)
            assert result1.success, f"First normalization failed for '{text}'"

            # Second normalization (should be idempotent)
            result2 = await factory.normalize_text(result1.normalized, config_ru, feature_flags)
            assert result2.success, f"Second normalization failed for '{result1.normalized}'"

            # Idempotency check
            assert result1.normalized == result2.normalized, \
                f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    @pytest.mark.asyncio
    async def test_initials_idempotency(self, factory, config_ru, feature_flags):
        """Test idempotency for various initial formats."""
        initial_forms = [
            "И.",
            "И. И.",
            "И.И.",
            "И.. И..",  # Double dots that should be collapsed
            "И . И .",  # Spaced initials
            "П.И.",
            "А.В.",
        ]

        for text in initial_forms:
            # First normalization
            result1 = await factory.normalize_text(text, config_ru, feature_flags)
            assert result1.success, f"First normalization failed for '{text}'"

            # Second normalization
            result2 = await factory.normalize_text(result1.normalized, config_ru, feature_flags)
            assert result2.success, f"Second normalization failed for '{result1.normalized}'"

            # Idempotency check
            assert result1.normalized == result2.normalized, \
                f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    @pytest.mark.asyncio
    async def test_hyphenated_names_idempotency(self, factory, config_ru, feature_flags):
        """Test idempotency for hyphenated names."""
        hyphenated_names = [
            "Петрова-Сидорова",
            "иванов-петров",      # Lowercase that should be title-cased
            "КОЗЛОВ-СМИРНОВ",     # Uppercase that should be title-cased
            "О'Коннор",
            "Ван-дер-Ваальс",
        ]

        for text in hyphenated_names:
            # First normalization
            result1 = await factory.normalize_text(text, config_ru, feature_flags)
            assert result1.success, f"First normalization failed for '{text}'"

            # Second normalization
            result2 = await factory.normalize_text(result1.normalized, config_ru, feature_flags)
            assert result2.success, f"Second normalization failed for '{result1.normalized}'"

            # Idempotency check
            assert result1.normalized == result2.normalized, \
                f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    @pytest.mark.asyncio
    async def test_mixed_case_idempotency(self, factory, config_ru, feature_flags):
        """Test idempotency for mixed case inputs."""
        mixed_case_names = [
            "иВАН иВАНОВИЧ иВАНОВ",     # Mixed case
            "мария петровна сидорова",  # All lowercase
            "ПЕТР СЕРГЕЕВИЧ КОЗЛОВ",    # All uppercase
            "аНнА вЛаДиМиРоВнА",       # Alternating case
        ]

        for text in mixed_case_names:
            # First normalization
            result1 = await factory.normalize_text(text, config_ru, feature_flags)
            assert result1.success, f"First normalization failed for '{text}'"

            # Second normalization
            result2 = await factory.normalize_text(result1.normalized, config_ru, feature_flags)
            assert result2.success, f"Second normalization failed for '{result1.normalized}'"

            # Idempotency check
            assert result1.normalized == result2.normalized, \
                f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    @pytest.mark.asyncio
    async def test_empty_and_edge_cases_idempotency(self, factory, config_ru, feature_flags):
        """Test idempotency for edge cases."""
        edge_cases = [
            "А",           # Single letter
            "И.",          # Single initial
            "Х-ы",         # Very short hyphenated
        ]

        for text in edge_cases:
            # First normalization
            result1 = await factory.normalize_text(text, config_ru, feature_flags)
            # Don't assert success for edge cases, but if it succeeds, check idempotency
            if result1.success and result1.normalized:
                # Second normalization
                result2 = await factory.normalize_text(result1.normalized, config_ru, feature_flags)
                if result2.success:
                    # Idempotency check
                    assert result1.normalized == result2.normalized, \
                        f"Idempotency violation: '{text}' -> '{result1.normalized}' -> '{result2.normalized}'"

    @pytest.mark.asyncio
    async def test_feature_flag_consistency_idempotency(self, factory, config_ru):
        """Test that normalization is idempotent across different feature flag settings."""
        test_text = "Иванова Мария Петровна"

        # Test with different flag combinations
        flag_combinations = [
            FeatureFlags(enforce_nominative=True, preserve_feminine_surnames=True),
            FeatureFlags(enforce_nominative=True, preserve_feminine_surnames=False),
            FeatureFlags(enforce_nominative=False, preserve_feminine_surnames=True),
            FeatureFlags(enforce_nominative=False, preserve_feminine_surnames=False),
        ]

        for flags in flag_combinations:
            # First normalization
            result1 = await factory.normalize_text(test_text, config_ru, flags)
            assert result1.success, f"First normalization failed for flags {flags.to_dict()}"

            # Second normalization with same flags
            result2 = await factory.normalize_text(result1.normalized, config_ru, flags)
            assert result2.success, f"Second normalization failed for flags {flags.to_dict()}"

            # Idempotency check
            assert result1.normalized == result2.normalized, \
                f"Idempotency violation with flags {flags.to_dict()}: '{test_text}' -> '{result1.normalized}' -> '{result2.normalized}'"