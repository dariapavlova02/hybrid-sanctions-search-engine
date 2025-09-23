#!/usr/bin/env python3
"""
Диагностика production runtime - проверить что именно не работает в морфологии и флагах.
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_production_config():
    """Проверить конфигурацию флагов."""
    print("=== ПРОВЕРКА ПЕРЕМЕННЫХ ОКРУЖЕНИЯ ===")

    # Критичные флаги для украинских имен
    critical_flags = [
        'PRESERVE_FEMININE_SURNAMES',
        'ENABLE_ENHANCED_GENDER_RULES',
        'PRESERVE_FEMININE_SUFFIX_UK',
        'ENABLE_FSM_TUNED_ROLES',
        'MORPHOLOGY_CUSTOM_RULES_FIRST',
        'ENABLE_ADVANCED_FEATURES'
    ]

    for flag in critical_flags:
        value = os.getenv(flag, 'MISSING')
        print(f"{flag}={value}")

    print("\n=== ПРОВЕРКА SMART FILTER ФЛАГОВ ===")
    filter_flags = [
        'ENABLE_SMART_FILTER',
        'ALLOW_SMART_FILTER_SKIP',
        'ENABLE_AHO_CORASICK',
        'ENABLE_VECTOR_FALLBACK'
    ]

    for flag in filter_flags:
        value = os.getenv(flag, 'MISSING')
        print(f"{flag}={value}")

def test_morphology_adapter():
    """Прямая проверка морфологии."""
    print("\n=== ТЕСТ МОРФОЛОГИИ АДАПТЕРА ===")

    try:
        from ai_service.layers.normalization.morphology_adapter import MorphologyAdapter

        adapter = MorphologyAdapter()
        print("✅ MorphologyAdapter инициализирован")

        # Тест украинских проблемных случаев
        test_cases = [
            ("Павлової", "uk", "Павлова"),  # женская фамилия
            ("Порошенка", "uk", "Порошенко"),  # мужская фамилия
            ("Дарʼї", "uk", "Дарʼя"),  # имя с апострофом
            ("Юріївни", "uk", "Юріївна")  # отчество женское
        ]

        for word, lang, expected in test_cases:
            try:
                result = adapter.to_nominative(word, lang)
                status = "✅" if result == expected else "❌"
                print(f"{status} {word} ({lang}) → {result} (ожидали: {expected})")
            except Exception as e:
                print(f"❌ {word} ({lang}) → ERROR: {e}")

    except ImportError as e:
        print(f"❌ Не удалось импортировать MorphologyAdapter: {e}")
    except Exception as e:
        print(f"❌ Ошибка инициализации: {e}")

def test_normalization_flags():
    """Проверить поведение флагов в нормализации."""
    print("\n=== ТЕСТ ФЛАГОВ НОРМАЛИЗАЦИИ ===")

    try:
        from ai_service.layers.normalization.flags import FeatureFlags

        flags = FeatureFlags()
        print("✅ FeatureFlags инициализированы")

        # Проверить ключевые флаги
        key_flags = [
            'preserve_feminine_surnames',
            'enable_enhanced_gender_rules',
            'preserve_feminine_suffix_uk',
            'enable_advanced_features'
        ]

        for flag_name in key_flags:
            value = getattr(flags, flag_name, 'MISSING')
            print(f"{flag_name}: {value}")

    except ImportError as e:
        print(f"❌ Не удалось импортировать FeatureFlags: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def test_full_normalization():
    """Тест полного пайплайна нормализации."""
    print("\n=== ТЕСТ ПОЛНОЙ НОРМАЛИЗАЦИИ ===")

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()
        print("✅ NormalizationService инициализирован")

        # Тест проблемных случаев из продакшена
        test_cases = [
            "Порошенка Петенька",
            "Павлової Дарʼї Юріївни"
        ]

        for text in test_cases:
            try:
                result = service.normalize_sync(
                    text=text,
                    language="uk",
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )

                print(f"\n📝 Текст: '{text}'")
                print(f"   Результат: '{result.normalized}'")
                print(f"   Токены: {result.tokens}")
                print(f"   Трейс:")
                for i, trace in enumerate(result.trace[:3]):  # первые 3
                    print(f"     {i}: {trace.get('token', 'N/A')} → {trace.get('role', 'N/A')} → {trace.get('output', 'N/A')}")

            except Exception as e:
                print(f"❌ Ошибка нормализации '{text}': {e}")

    except ImportError as e:
        print(f"❌ Не удалось импортировать NormalizationService: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def test_smart_filter():
    """Проверить SmartFilter конфигурацию."""
    print("\n=== ТЕСТ SMART FILTER ===")

    try:
        from ai_service.layers.smart_filter.name_detector import NameDetector

        detector = NameDetector()
        print("✅ NameDetector инициализирован")

        # Тест обработки украинских имен
        test_cases = [
            "Порошенка Петенька",
            "Павлової Дарʼї Юріївни"
        ]

        for text in test_cases:
            try:
                result = detector.detect_name_signals(text)
                print(f"\n📝 Текст: '{text}'")
                print(f"   Confidence: {result.get('confidence', 'N/A')}")
                print(f"   Should process: {result.get('should_process', 'N/A')}")
                print(f"   Signals: {result.get('detected_signals', [])}")

            except Exception as e:
                print(f"❌ Ошибка детекции '{text}': {e}")

    except ImportError as e:
        print(f"❌ Не удалось импортировать NameDetector: {e}")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

if __name__ == "__main__":
    print("🔍 ДИАГНОСТИКА PRODUCTION RUNTIME")
    print("="*50)

    test_production_config()
    test_morphology_adapter()
    test_normalization_flags()
    test_full_normalization()
    test_smart_filter()

    print("\n" + "="*50)
    print("✅ Диагностика завершена")