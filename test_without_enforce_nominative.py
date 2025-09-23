#!/usr/bin/env python3
"""
Тест без ENFORCE_NOMINATIVE чтобы избежать двойной морфологии.
"""

import os
import sys
from pathlib import Path

# Set production environment variables BUT disable ENFORCE_NOMINATIVE
os.environ.update({
    'PRESERVE_FEMININE_SURNAMES': 'true',
    'ENABLE_ENHANCED_GENDER_RULES': 'true',
    'PRESERVE_FEMININE_SUFFIX_UK': 'true',
    'ENABLE_FSM_TUNED_ROLES': 'true',
    'MORPHOLOGY_CUSTOM_RULES_FIRST': 'true',
    'ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_MORPHOLOGY': 'true',
    'ENFORCE_NOMINATIVE': 'false',  # ❌ ОТКЛЮЧАЕМ ДВОЙНУЮ МОРФОЛОГИЮ!
    'DEBUG_TRACING': 'true'
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_without_double_morphology():
    """Тест без двойной морфологии."""
    print("🔍 ТЕСТ БЕЗ ENFORCE_NOMINATIVE (без двойной морфологии)")
    print("="*70)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

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

                if result.normalized == expected:
                    print(f"   🎉 ИСПРАВЛЕНО! Двойная морфология была проблемой!")

            except Exception as e:
                print(f"   ❌ ОШИБКА: {e}")

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")

if __name__ == "__main__":
    test_without_double_morphology()