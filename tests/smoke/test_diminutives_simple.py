"""
Simple test for diminutives functionality.
"""

import asyncio
import pytest
from src.ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from src.ai_service.utils.feature_flags import FeatureFlags


@pytest.mark.asyncio
async def test_russian_diminutive_simple():
    """Test Russian diminutive resolution."""
    factory = NormalizationFactory()
    flags = FeatureFlags()
    flags.use_diminutives_dictionary_only = True
    
    config = NormalizationConfig(
        language='ru',
        enable_advanced_features=True,
        enable_morphology=True
    )
    
    result = await factory.normalize_text('Сашка Пушкин', config, flags)
    
    # Verify the result
    assert result.normalized == "Александр Пушкин"
    assert result.success is True


@pytest.mark.asyncio
async def test_ukrainian_diminutive_simple():
    """Test Ukrainian diminutive resolution."""
    factory = NormalizationFactory()
    flags = FeatureFlags()
    flags.use_diminutives_dictionary_only = True
    
    config = NormalizationConfig(
        language='uk',
        enable_advanced_features=True,
        enable_morphology=True
    )
    
    result = await factory.normalize_text('Сашко Коваль', config, flags)
    
    # Verify the result
    assert result.normalized == "Олександр Коваль"
    assert result.success is True


@pytest.mark.asyncio
async def test_diminutives_disabled():
    """Test that diminutives are not resolved when flag is disabled."""
    factory = NormalizationFactory()
    flags = FeatureFlags()
    flags.use_diminutives_dictionary_only = False  # Disabled
    
    config = NormalizationConfig(
        language='ru',
        enable_advanced_features=True,
        enable_morphology=True
    )
    
    result = await factory.normalize_text('Сашка Пушкин', config, flags)
    
    # Should not resolve diminutive when flag is disabled
    assert "Сашка" in result.normalized or "сашка" in result.normalized.lower()
    assert "Александр" not in result.normalized
