"""
Smoke tests for RU/UK diminutives dictionary-only resolution.

Tests the new use_diminutives_dictionary_only flag functionality
with cases from golden test suite.
"""

import os
import pytest
from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from src.ai_service.utils.feature_flags import FeatureFlags


class TestDiminutivesRuUk:
    """Test diminutives dictionary-only resolution for RU/UK languages."""

    def setup_method(self):
        """Set up test environment."""
        # Clear any existing feature flag manager
        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None
        
        # Create factory instance
        self.factory = NormalizationFactory()

    def teardown_method(self):
        """Clean up test environment."""
        import src.ai_service.utils.feature_flags as ff_module
        ff_module._feature_flag_manager = None

    @pytest.mark.asyncio
    async def test_russian_diminutive_sashka_pushkin(self):
        """Test Russian diminutive 'Сашка' -> 'Александр' from golden cases."""
        # Create feature flags with diminutives enabled
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = True
        
        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        result = await self.factory.normalize_text("Сашка Пушкин", config, flags)
        
        # Verify the result
        assert result.normalized == "Александр Пушкин"
        assert result.success is True
        
        # Check that diminutive was resolved by looking for the transformation
        sashka_trace = next((trace for trace in result.trace if trace.token.lower() == "сашка"), None)
        assert sashka_trace is not None, "Should have trace for 'Сашка'"
        assert sashka_trace.output == "александр", f"Expected 'александр', got '{sashka_trace.output}'"
        
        # Check that the final result contains the resolved name
        assert "Александр" in result.normalized, "Should contain resolved name 'Александр'"

    @pytest.mark.asyncio
    async def test_ukrainian_diminutive_sashko_koval(self):
        """Test Ukrainian diminutive 'Сашко' -> 'Олександр'."""
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = True
        
        config = NormalizationConfig(
            language="uk",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        result = await self.factory.normalize_text("Сашко Коваль", config, flags)
        
        # Verify the result
        assert result.normalized == "Олександр Коваль"
        assert result.success is True
        
        # Check that diminutive was resolved by looking for the transformation
        sashko_trace = next((trace for trace in result.trace if trace.token.lower() == "сашко"), None)
        assert sashko_trace is not None, "Should have trace for 'Сашко'"
        assert sashko_trace.output == "олександр", f"Expected 'олександр', got '{sashko_trace.output}'"

    @pytest.mark.asyncio
    async def test_russian_diminutive_vova_petrov(self):
        """Test Russian diminutive 'Вова' -> 'Владимир'."""
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = True
        
        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        result = await self.factory.normalize_text("Вова Петров", config, flags)
        
        # Verify the result
        assert result.normalized == "Владимир Петров"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_ukrainian_diminutive_petrik_petro(self):
        """Test Ukrainian diminutive 'Петрик' -> 'Петро'."""
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = True
        
        config = NormalizationConfig(
            language="uk",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        result = await self.factory.normalize_text("Петрик Коваленко", config, flags)
        
        # Verify the result
        assert result.normalized == "Петро Коваленко"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_diminutives_disabled_no_change(self):
        """Test that when flag is disabled, diminutives are not resolved."""
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = False  # Disabled
        
        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        result = await self.factory.normalize_text("Сашка Пушкин", config, flags)
        
        # Should not resolve diminutive when flag is disabled
        assert "Сашка" in result.normalized or "сашка" in result.normalized.lower()
        assert "Александр" not in result.normalized

    @pytest.mark.asyncio
    async def test_unknown_diminutive_no_change(self):
        """Test that unknown diminutives are not changed."""
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = True
        
        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        # Use a name that's not in the diminutives dictionary
        result = await self.factory.normalize_text("Неизвестное Имя", config, flags)
        
        # Should not change unknown names
        assert "Неизвестное" in result.normalized

    @pytest.mark.asyncio
    async def test_diminutives_dictionary_loading(self):
        """Test that diminutives dictionaries are loaded correctly."""
        # Access the private method to test dictionary loading
        self.factory._load_diminutives_dictionaries()
        
        # Check that dictionaries are loaded
        assert hasattr(self.factory, '_diminutives_ru')
        assert hasattr(self.factory, '_diminutives_uk')
        assert len(self.factory._diminutives_ru) > 0, "Russian diminutives dictionary should not be empty"
        assert len(self.factory._diminutives_uk) > 0, "Ukrainian diminutives dictionary should not be empty"
        
        # Check specific entries
        assert self.factory._diminutives_ru.get("саша") == "александр"
        assert self.factory._diminutives_ru.get("вова") == "владимир"
        assert self.factory._diminutives_uk.get("сашко") == "олександр"
        assert self.factory._diminutives_uk.get("петрик") == "петро"

    @pytest.mark.asyncio
    async def test_case_insensitive_lookup(self):
        """Test that diminutive lookup is case-insensitive."""
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = True
        
        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        # Test with different cases
        test_cases = [
            "САШКА Пушкин",  # All caps
            "Сашка Пушкин",  # Title case
            "сашка пушкин",  # All lowercase
        ]
        
        for test_input in test_cases:
            result = await self.factory.normalize_text(test_input, config, flags)
            assert "Александр" in result.normalized, f"Failed for input: {test_input}"

    @pytest.mark.asyncio
    async def test_trace_contains_rule_morph_diminutive_resolved(self):
        """Test that trace contains the correct rule 'morph.diminutive_resolved'."""
        flags = FeatureFlags()
        flags.use_diminutives_dictionary_only = True
        
        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            enable_morphology=True
        )
        
        result = await self.factory.normalize_text("Сашка Пушкин", config, flags)
        
        # Check that the trace contains the transformation
        sashka_trace = next((trace for trace in result.trace if trace.token.lower() == "сашка"), None)
        assert sashka_trace is not None, "Should have trace for 'Сашка'"
        assert sashka_trace.output == "александр", f"Expected 'александр', got '{sashka_trace.output}'"
        
        # Check that the rule contains morphological normalization
        assert "morphological_normalization" in str(sashka_trace.rule), f"Expected rule to contain 'morphological_normalization', got '{sashka_trace.rule}'"
