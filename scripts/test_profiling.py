#!/usr/bin/env python3
"""
Тестовый скрипт для проверки работы системы профилирования.

Этот скрипт проверяет, что все компоненты профилирования работают корректно
без необходимости полного запуска профилирования.
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.utils.profiling import (
    profile_time, profile_memory, profile_function, 
    get_profiling_stats, print_profiling_report, clear_profiling_stats
)


async def test_profiling_integration():
    """Тест интеграции профилирования в сервис."""
    print("Тестирование интеграции профилирования...")
    
    # Очищаем статистики
    clear_profiling_stats()
    
    # Создаём сервис
    service = NormalizationService()
    
    # Тестовые фразы
    test_phrases = [
        "Іван Петров",
        "ООО 'Ромашка' Иван И.",
        "John Smith"
    ]
    
    # Профилируем несколько фраз
    for phrase in test_phrases:
        print(f"Обработка: '{phrase}'")
        
        with profile_time("test.normalize_phrase"):
            result = await service.normalize_async(
                phrase,
                language="auto",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
        
        print(f"  Результат: '{result.normalized}'")
        print(f"  Успех: {result.success}")
        print(f"  Время: {result.processing_time:.4f}s")
    
    # Получаем статистики
    stats = get_profiling_stats()
    print(f"\nСтатистики профилирования:")
    print(f"  Счётчиков: {len(stats.get('counters', {}))}")
    print(f"  Трекеров памяти: {len(stats.get('memory_trackers', {}))}")
    
    # Выводим отчёт
    print_profiling_report()
    
    return True


def test_profiling_utilities():
    """Тест утилит профилирования."""
    print("Тестирование утилит профилирования...")
    
    # Очищаем статистики
    clear_profiling_stats()
    
    # Тест контекстного менеджера времени
    with profile_time("test.context_manager") as counter:
        import time
        time.sleep(0.01)  # 10ms
    
    # Тест декоратора
    @profile_function("test.decorator")
    def test_function(x: int) -> int:
        return x * 2
    
    result = test_function(5)
    print(f"  Результат test_function(5): {result}")
    
    # Тест контекстного менеджера памяти
    with profile_memory("test.memory") as tracker:
        # Создаём некоторую нагрузку на память
        data = [i for i in range(1000)]
        _ = sum(data)
    
    # Получаем статистики
    stats = get_profiling_stats()
    
    # Проверяем, что статистики собраны
    counters = stats.get('counters', {})
    memory_trackers = stats.get('memory_trackers', {})
    
    print(f"  Счётчиков времени: {len(counters)}")
    print(f"  Трекеров памяти: {len(memory_trackers)}")
    
    # Проверяем конкретные счётчики
    if 'test.context_manager' in counters:
        counter_stats = counters['test.context_manager']
        print(f"  context_manager: {counter_stats['calls']} вызовов, {counter_stats['total_time']:.4f}s")
    
    if 'test.decorator' in counters:
        counter_stats = counters['test.decorator']
        print(f"  decorator: {counter_stats['calls']} вызовов, {counter_stats['total_time']:.4f}s")
    
    if 'test.memory' in memory_trackers:
        memory_stats = memory_trackers['test.memory']
        print(f"  memory: {memory_stats['snapshots']} снимков, {memory_stats['peak_memory']} байт")
    
    return True


def test_imports():
    """Тест импортов всех компонентов."""
    print("Тестирование импортов...")
    
    try:
        # Тест основных компонентов
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory
        from ai_service.layers.normalization.processors.token_processor import TokenProcessor
        from ai_service.layers.normalization.processors.morphology_processor import MorphologyProcessor
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier
        
        print("  ✓ Основные компоненты импортированы")
        
        # Тест утилит профилирования
        from ai_service.utils.profiling import (
            PerformanceCounter, MemoryTracker, ProfilingManager,
            profile_time, profile_memory, profile_function
        )
        
        print("  ✓ Утилиты профилирования импортированы")
        
        # Тест опциональных зависимостей
        try:
            import pyinstrument
            print("  ✓ pyinstrument доступен")
        except ImportError:
            print("  ⚠ pyinstrument не установлен (опционально)")
        
        return True
        
    except ImportError as e:
        print(f"  ✗ Ошибка импорта: {e}")
        return False


async def main():
    """Главная функция тестирования."""
    print("Тестирование системы профилирования AI Service")
    print("=" * 50)
    
    success = True
    
    # Тест импортов
    if not test_imports():
        success = False
    
    print()
    
    # Тест утилит профилирования
    if not test_profiling_utilities():
        success = False
    
    print()
    
    # Тест интеграции
    try:
        if not await test_profiling_integration():
            success = False
    except Exception as e:
        print(f"  ✗ Ошибка интеграции: {e}")
        success = False
    
    print()
    print("=" * 50)
    
    if success:
        print("✅ Все тесты прошли успешно!")
        print("\nСистема профилирования готова к использованию.")
        print("Запустите 'make -f Makefile.profile profile-quick' для полного профилирования.")
    else:
        print("❌ Некоторые тесты не прошли.")
        print("Проверьте зависимости и конфигурацию.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
