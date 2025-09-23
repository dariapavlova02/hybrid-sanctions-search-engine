#!/usr/bin/env python3
"""
Отладка потери морфологических результатов в пайплайне.
"""

import os
import sys
from pathlib import Path

# Set production environment variables + extra logging
os.environ.update({
    'PRESERVE_FEMININE_SURNAMES': 'true',
    'ENABLE_ENHANCED_GENDER_RULES': 'true',
    'PRESERVE_FEMININE_SUFFIX_UK': 'true',
    'ENABLE_FSM_TUNED_ROLES': 'true',
    'MORPHOLOGY_CUSTOM_RULES_FIRST': 'true',
    'ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_MORPHOLOGY': 'true',
    'DEBUG_TRACING': 'true'
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def patch_factory_with_logging():
    """Патчим NormalizationFactory для добавления логирования."""
    from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory

    original_normalize = NormalizationFactory.normalize_async

    async def debug_normalize(self, text, config):
        print(f"\n🔍 НАЧАЛО НОРМАЛИЗАЦИИ: '{text}'")

        # Call original method but intercept intermediate results
        result = await original_normalize(text, config)

        print(f"🔍 ФИНАЛЬНЫЙ РЕЗУЛЬТАТ:")
        print(f"   normalized: '{result.normalized}'")
        print(f"   tokens: {result.tokens}")

        return result

    # Monkey patch
    NormalizationFactory.normalize_async = debug_normalize

    # Also patch morphology method to track intermediate results
    original_normalize_morphology = NormalizationFactory._normalize_morphology

    async def debug_normalize_morphology(self, tokens, roles, config, skip_indices=None, effective_flags=None):
        print(f"\n🔍 ВХОД В МОРФОЛОГИЮ:")
        print(f"   input tokens: {tokens}")
        print(f"   input roles: {roles}")

        normalized_tokens, morph_traces = await original_normalize_morphology(tokens, roles, config, skip_indices, effective_flags)

        print(f"🔍 ВЫХОД ИЗ МОРФОЛОГИИ:")
        print(f"   output tokens: {normalized_tokens}")
        print(f"   morph traces: {morph_traces[:3]}")  # First 3 traces

        return normalized_tokens, morph_traces

    NormalizationFactory._normalize_morphology = debug_normalize_morphology

def test_morphology_tracing():
    """Тест с отслеживанием морфологии."""
    print("🔍 ОТСЛЕЖИВАНИЕ ПОТЕРИ МОРФОЛОГИЧЕСКИХ РЕЗУЛЬТАТОВ")
    print("="*70)

    try:
        # Patch factory first
        patch_factory_with_logging()

        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        text = "Порошенка Петенька"
        print(f"📝 Тест: '{text}'")

        result = service.normalize_sync(
            text=text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n✅ ИТОГОВЫЙ РЕЗУЛЬТАТ:")
        print(f"   Normalized: '{result.normalized}'")
        print(f"   Tokens: {result.tokens}")

        if result.normalized != "Порошенко Петро":
            print(f"❌ ОШИБКА! Ожидали: 'Порошенко Петро'")
        else:
            print(f"✅ УСПЕХ! Результат правильный")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_morphology_tracing()