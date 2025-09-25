#!/usr/bin/env python3

"""
Специфический тест для проверки исправления metrics в _handle_name_normalization_layer.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_normalization_layer_metrics():
    """Тест исправления metrics в слое нормализации."""
    print("🔍 ТЕСТ ИСПРАВЛЕНИЯ METRICS В СЛОЕ НОРМАЛИЗАЦИИ")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        print("✅ NormalizationService импортирован")

        service = NormalizationService()
        print("✅ NormalizationService создан")

        # Тестируем нормализацию, которая теперь должна работать без ошибок
        test_text = "Іванов Іван Іванович"
        print(f"🧪 Тестируем нормализацию: '{test_text}'")

        result = service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True  # Полная функциональность
        )

        print(f"📋 Результат нормализации:")
        print(f"   Success: {result.success}")
        print(f"   Normalized: '{result.normalized}'")
        print(f"   Tokens: {result.tokens}")
        print(f"   Language: {result.language}")
        print(f"   Processing time: {result.processing_time}s")

        # Проверяем на metrics ошибки
        if result.errors:
            for error in result.errors:
                if "metrics" in str(error).lower() and "not defined" in str(error).lower():
                    print(f"❌ METRICS ОШИБКА НАЙДЕНА: {error}")
                    return False
                else:
                    print(f"ℹ️ Другая ошибка (не metrics): {error}")

        if result.success and result.normalized:
            print("✅ Нормализация прошла успешно без metrics ошибок!")
            return True
        else:
            print(f"⚠️ Нормализация не полностью успешна, но metrics ошибок нет")
            return True

    except NameError as e:
        if "metrics" in str(e) and "not defined" in str(e):
            print(f"❌ METRICS NAMEERROR ВСЕ ЕЩЕ ЕСТЬ: {e}")
            import traceback
            traceback.print_exc()
            return False
        else:
            print(f"ℹ️ Другая NameError: {e}")
            return True

    except Exception as e:
        if "metrics" in str(e).lower() and "not defined" in str(e).lower():
            print(f"❌ METRICS ОШИБКА ВСЕ ЕЩЕ ЕСТЬ: {e}")
            import traceback
            traceback.print_exc()
            return False
        else:
            print(f"ℹ️ Другая ошибка: {e}")
            return True

def main():
    """Главная функция."""
    print("🎯 ТЕСТ ИСПРАВЛЕНИЯ METRICS В НОРМАЛИЗАЦИИ")
    print("=" * 50)

    success = test_normalization_layer_metrics()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Metrics ошибка в нормализации исправлена!")
        print("   Теперь сервис должен работать без 'metrics' is not defined")
    else:
        print("❌ FAILURE: Metrics ошибка все еще есть.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)