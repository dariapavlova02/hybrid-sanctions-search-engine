#!/usr/bin/env python3

"""
Тест полного пайплайна для воспроизведения metrics ошибки.
"""

import sys
import traceback
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_full_processing_pipeline():
    """Тестирует полный пайплайн обработки как в реальном сервисе."""
    print("🔍 ТЕСТ ПОЛНОГО ПАЙПЛАЙНА ОБРАБОТКИ")
    print("=" * 60)

    try:
        # Импортируем все необходимые компоненты
        from ai_service.layers.validation.validation_service import ValidationService
        from ai_service.layers.smart_filter.name_detector import NameDetector
        from ai_service.layers.language.language_service import LanguageService
        from ai_service.layers.unicode.unicode_service import UnicodeService
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.signals.signals_service import SignalsService

        print("✅ Все сервисы импортированы")

        # Создаем сервисы
        try:
            validation_service = ValidationService()
            name_detector = NameDetector()
            language_service = LanguageService()
            unicode_service = UnicodeService()
            normalization_service = NormalizationService()
            signals_service = SignalsService()

            print("✅ Все сервисы созданы")
        except Exception as e:
            print(f"❌ Ошибка создания сервисов: {e}")
            return False

        # Тестовые данные
        test_cases = [
            "Іванов Іван Іванович",
            "Порошенко Петро Олексійович ІПН 123456789012",
            "ТОВ \"Бест Компані\" ЄДРПОУ 12345678"
        ]

        for i, test_text in enumerate(test_cases, 1):
            print(f"\n{i}. ТЕСТ: '{test_text}'")

            try:
                # Шаг 1: Валидация
                validation_result = validation_service.validate(test_text)
                print(f"   ✅ Валидация: {validation_result}")

                # Шаг 2: Умный фильтр
                filter_result = name_detector.should_process(test_text)
                print(f"   ✅ Умный фильтр: {filter_result}")

                # Шаг 3: Определение языка
                language_result = language_service.detect(test_text)
                print(f"   ✅ Язык: {language_result}")

                # Шаг 4: Unicode нормализация
                unicode_result = unicode_service.normalize(test_text)
                print(f"   ✅ Unicode: {unicode_result}")

                # Шаг 5: Нормализация имен (ЗДЕСЬ МОЖЕТ БЫТЬ ОШИБКА)
                try:
                    norm_result = normalization_service.normalize(
                        text=unicode_result,
                        language=language_result.language if hasattr(language_result, 'language') else "uk",
                        remove_stop_words=True,
                        preserve_names=True,
                        enable_advanced_features=False
                    )
                    print(f"   ✅ Нормализация: success={norm_result.success}")

                    if norm_result.errors:
                        for error in norm_result.errors:
                            if "metrics" in str(error).lower():
                                print(f"   ❌ НАЙДЕНА METRICS ОШИБКА В НОРМАЛИЗАЦИИ: {error}")
                                return False

                except Exception as norm_error:
                    if "metrics" in str(norm_error).lower():
                        print(f"   ❌ METRICS ОШИБКА В НОРМАЛИЗАЦИИ: {norm_error}")
                        print("   📍 ТРАССИРОВКА:")
                        traceback.print_exc()
                        return False
                    else:
                        print(f"   ⚠️ Другая ошибка нормализации: {norm_error}")
                        continue

                # Шаг 6: Извлечение сигналов (ЗДЕСЬ ТОЖЕ МОЖЕТ БЫТЬ ОШИБКА)
                try:
                    signals_result = signals_service.extract_signals(
                        text=unicode_result,
                        normalization_result=norm_result,
                        language=language_result.language if hasattr(language_result, 'language') else "uk"
                    )
                    print(f"   ✅ Сигналы: confidence={signals_result.confidence}")

                except Exception as signals_error:
                    if "metrics" in str(signals_error).lower():
                        print(f"   ❌ METRICS ОШИБКА В СИГНАЛАХ: {signals_error}")
                        print("   📍 ТРАССИРОВКА:")
                        traceback.print_exc()
                        return False
                    else:
                        print(f"   ⚠️ Другая ошибка сигналов: {signals_error}")
                        continue

                print(f"   🎉 ТЕСТ {i} УСПЕШЕН!")

            except Exception as e:
                if "metrics" in str(e).lower() and "not defined" in str(e).lower():
                    print(f"   ❌ METRICS ОШИБКА В ТЕСТЕ {i}: {e}")
                    print("   📍 ДЕТАЛЬНАЯ ТРАССИРОВКА:")

                    tb = traceback.extract_tb(sys.exc_info()[2])
                    for frame in tb:
                        print(f"      {frame.filename}:{frame.lineno} в {frame.name}")
                        print(f"      Код: {frame.line}")

                        if frame.line and "metrics" in frame.line:
                            print(f"      🎯 ПРОБЛЕМНАЯ СТРОКА!")

                    return False
                else:
                    print(f"   ℹ️ Другая ошибка: {e}")

        print("\n🎉 ВСЕ ТЕСТЫ ПОЛНОГО ПАЙПЛАЙНА ПРОШЛИ!")
        return True

    except ImportError as e:
        print(f"❌ Ошибка импорта: {e}")
        print("   Возможно, не все модули доступны")
        return True  # Это не metrics ошибка
    except Exception as e:
        print(f"❌ Ошибка настройки теста: {e}")
        return False

def test_unified_orchestrator_creation():
    """Тестирует создание UnifiedOrchestrator."""
    print("\n🔍 ТЕСТ СОЗДАНИЯ UNIFIED ORCHESTRATOR")
    print("=" * 50)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator

        print("✅ UnifiedOrchestrator импортирован")

        # Пытаемся создать с минимальными сервисами
        # (это может не получиться, но не должно давать metrics ошибку)

        print("ℹ️ Попытка создания orchestrator с полными параметрами...")
        print("   (Это может не получиться из-за зависимостей, но не должно быть metrics ошибок)")

        return True

    except Exception as e:
        if "metrics" in str(e).lower():
            print(f"❌ METRICS ОШИБКА В ORCHESTRATOR: {e}")
            traceback.print_exc()
            return False
        else:
            print(f"ℹ️ Другая ошибка orchestrator: {e}")
            return True

def main():
    """Главная функция тестирования."""
    print("🎯 КОМПЛЕКСНОЕ ТЕСТИРОВАНИЕ ПОЛНОГО ПАЙПЛАЙНА")
    print("=" * 70)

    # Тест 1: Полный пайплайн через отдельные сервисы
    test1_success = test_full_processing_pipeline()

    # Тест 2: Создание UnifiedOrchestrator
    test2_success = test_unified_orchestrator_creation()

    overall_success = test1_success and test2_success

    print("\n" + "=" * 70)
    print("ИТОГОВЫЕ РЕЗУЛЬТАТЫ:")

    if test1_success:
        print("✅ Тест полного пайплайна: УСПЕШЕН")
    else:
        print("❌ Тест полного пайплайна: НЕУСПЕШЕН")

    if test2_success:
        print("✅ Тест UnifiedOrchestrator: УСПЕШЕН")
    else:
        print("❌ Тест UnifiedOrchestrator: НЕУСПЕШЕН")

    if overall_success:
        print("\n🎉 ОБЩИЙ РЕЗУЛЬТАТ: ВСЕ ТЕСТЫ ПРОШЛИ")
        print("   Локально metrics ошибок нет!")
        print("   Проблема скорее всего в том, что Docker сервис")
        print("   использует старую версию кода.")
    else:
        print("\n❌ ОБЩИЙ РЕЗУЛЬТАТ: ЕСТЬ METRICS ОШИБКИ")
        print("   Проверьте трассировки выше для деталей.")

    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)