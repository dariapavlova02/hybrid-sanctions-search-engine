#!/usr/bin/env python3
"""
Отладка смешанного контента с латинскими символами и J.
"""

import os
import sys
from pathlib import Path

# Set production environment variables
os.environ.update({
    'PRESERVE_FEMININE_SURNAMES': 'true',
    'ENABLE_ENHANCED_GENDER_RULES': 'true',
    'PRESERVE_FEMININE_SUFFIX_UK': 'true',
    'ENABLE_FSM_TUNED_ROLES': 'true',
    'MORPHOLOGY_CUSTOM_RULES_FIRST': 'true',
    'ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_MORPHOLOGY': 'true',
    'ENFORCE_NOMINATIVE': 'false',
    'DEBUG_TRACING': 'true'
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def analyze_text_characters(text):
    """Анализ символов в тексте."""
    print(f"\n🔍 АНАЛИЗ СИМВОЛОВ В ТЕКСТЕ: '{text}'")
    for i, char in enumerate(text):
        print(f"  [{i}] '{char}' -> U+{ord(char):04X} ({char.encode('unicode_escape').decode()})")

def test_mixed_content():
    """Тест смешанного контента."""
    print("🔍 ТЕСТ СМЕШАННОГО КОНТЕНТА")
    print("="*60)

    # Проблемный текст из запроса
    text = "Оплaтa Пepoшeнкa Oт J Пeтpa"
    analyze_text_characters(text)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        print(f"\n📝 Тест: '{text}'")

        result = service.normalize_sync(
            text=text,
            language=None,  # Автоопределение языка
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n✅ Результат: '{result.normalized}'")
        print(f"✅ Язык: '{result.language}'")
        print(f"✅ Токены: {result.tokens}")

        print(f"\n🔍 TRACE АНАЛИЗ:")
        for i, trace in enumerate(result.trace):
            if hasattr(trace, 'token'):
                print(f"  {i:2d}: '{trace.token}' → {trace.role} → '{trace.output}'")
                if trace.notes:
                    notes = trace.notes[:100] + "..." if len(trace.notes) > 100 else trace.notes
                    print(f"      notes: {notes}")
            else:
                print(f"  {i:2d}: {trace}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

def test_clean_version():
    """Тест с очищенной версией."""
    print("\n🔍 ТЕСТ ОЧИЩЕННОЙ ВЕРСИИ")
    print("="*40)

    # Очищенная версия с правильными кириллическими символами
    clean_text = "Оплата Порошенка От J Петра"
    analyze_text_characters(clean_text)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        print(f"\n📝 Тест: '{clean_text}'")

        result = service.normalize_sync(
            text=clean_text,
            language="uk",  # Принудительно украинский
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n✅ Результат: '{result.normalized}'")
        print(f"✅ Язык: '{result.language}'")
        print(f"✅ Токены: {result.tokens}")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    test_mixed_content()
    test_clean_version()