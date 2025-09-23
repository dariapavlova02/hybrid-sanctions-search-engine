#!/usr/bin/env python3
"""
Тест нормализации с production переменными окружения.
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
    'NORMALIZATION_PRESERVE_NAMES': 'true',
    'NORMALIZATION_REMOVE_STOP_WORDS': 'true',
    'ENABLE_SMART_FILTER': 'true',
    'ALLOW_SMART_FILTER_SKIP': 'false',
    'ENABLE_AHO_CORASICK': 'true',
    'ENABLE_VECTOR_FALLBACK': 'true'
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_critical_cases():
    """Тест критичных случаев с production настройками."""
    print("🔍 ТЕСТ С PRODUCTION ПЕРЕМЕННЫМИ ОКРУЖЕНИЯ")
    print("="*60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()
        print("✅ NormalizationService инициализирован с production flags")

        # Критичные случаи из продакшена
        test_cases = [
            {
                "text": "Порошенка Петенька",
                "expected": "Порошенко Петро"
            },
            {
                "text": "Павлової Дарʼї Юріївни",
                "expected": "Павлова Дарʼя Юріївна"
            }
        ]

        for case in test_cases:
            text = case["text"]
            expected = case["expected"]

            print(f"\n📝 Тест: '{text}'")
            print(f"   Ожидаем: '{expected}'")

            try:
                result = service.normalize_sync(
                    text=text,
                    language="uk",
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )

                print(f"   ✅ Получили: '{result.normalized}'")

                status = "✅ PASS" if result.normalized == expected else "❌ FAIL"
                print(f"   {status}")

                if result.normalized != expected:
                    print(f"   🔍 Токены: {result.tokens}")
                    print(f"   🔍 Trace (first 3):")
                    for i, trace in enumerate(result.trace[:3]):
                        if hasattr(trace, 'token'):
                            print(f"      {i}: {trace.token} → {trace.role} → {trace.output}")
                        else:
                            print(f"      {i}: {trace}")

            except Exception as e:
                print(f"   ❌ ОШИБКА: {e}")

    except ImportError as e:
        print(f"❌ Не удалось импортировать: {e}")
    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

def test_morphology_direct():
    """Прямой тест морфологии."""
    print("\n🔍 ТЕСТ МОРФОЛОГИИ НАПРЯМУЮ")
    print("="*40)

    try:
        from ai_service.layers.normalization.morphology_adapter import MorphologyAdapter

        adapter = MorphologyAdapter()

        test_cases = [
            ("Павлової", "uk"),
            ("Порошенка", "uk"),
            ("Дарʼї", "uk"),
            ("Юріївни", "uk")
        ]

        for word, lang in test_cases:
            result = adapter.to_nominative(word, lang)
            print(f"   {word} ({lang}) → {result}")

    except Exception as e:
        print(f"❌ Ошибка морфологии: {e}")

if __name__ == "__main__":
    test_morphology_direct()
    test_critical_cases()
    print("\n" + "="*60)
    print("✅ Тест завершен")