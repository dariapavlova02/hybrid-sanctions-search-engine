#!/usr/bin/env python3
"""
Демонстрация системы профилирования AI Service.

Этот скрипт демонстрирует работу всех компонентов системы профилирования
на небольшом наборе тестовых данных.
"""

import asyncio
import sys
import time
from pathlib import Path

# Добавляем путь к проекту
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.utils.profiling import (
    profile_time, profile_memory, profile_function, 
    get_profiling_stats, print_profiling_report, clear_profiling_stats
)


# Демонстрационные фразы
DEMO_PHRASES = [
    "Іван Петров",
    "ООО 'Ромашка' Иван И.",
    "Петро Порошенко",
    "John Smith",
    "Анна Сергеевна Иванова"
]


@profile_function("demo.process_phrase")
async def process_phrase(service: NormalizationService, phrase: str) -> dict:
    """Обработка одной фразы с профилированием."""
    start_time = time.time()
    
    with profile_time("demo.normalize_async"):
        result = await service.normalize_async(
            phrase,
            language="auto",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
    
    processing_time = time.time() - start_time
    
    return {
        'phrase': phrase,
        'normalized': result.normalized,
        'success': result.success,
        'processing_time': processing_time,
        'tokens': result.tokens,
        'errors': result.errors
    }


async def demo_basic_profiling():
    """Демонстрация базового профилирования."""
    print("🔍 Демонстрация базового профилирования")
    print("-" * 50)
    
    # Очищаем статистики
    clear_profiling_stats()
    
    # Создаём сервис
    service = NormalizationService()
    
    # Обрабатываем фразы
    results = []
    for phrase in DEMO_PHRASES:
        print(f"Обработка: '{phrase}'")
        
        with profile_time("demo.phrase_processing"):
            result = await process_phrase(service, phrase)
            results.append(result)
        
        print(f"  → '{result['normalized']}' ({result['processing_time']:.4f}s)")
    
    # Выводим статистики
    print("\n📊 Статистики профилирования:")
    print_profiling_report()
    
    return results


async def demo_memory_profiling():
    """Демонстрация профилирования памяти."""
    print("\n🧠 Демонстрация профилирования памяти")
    print("-" * 50)
    
    service = NormalizationService()
    
    # Профилируем память для каждой фразы
    for phrase in DEMO_PHRASES:
        print(f"Профилирование памяти для: '{phrase}'")
        
        with profile_memory("demo.memory_processing"):
            result = await service.normalize_async(
                phrase,
                language="auto",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )
        
        print(f"  → '{result.normalized}'")
    
    # Выводим статистики памяти
    stats = get_profiling_stats()
    memory_trackers = stats.get('memory_trackers', {})
    
    if memory_trackers:
        print("\n📈 Статистики памяти:")
        for name, tracker_stats in memory_trackers.items():
            print(f"  {name}:")
            print(f"    Снимков: {tracker_stats['snapshots']}")
            print(f"    Пик памяти: {tracker_stats['peak_memory']} байт")
            print(f"    Средняя память: {tracker_stats['avg_memory']:.0f} байт")


def demo_performance_comparison():
    """Демонстрация сравнения производительности."""
    print("\n⚡ Сравнение производительности")
    print("-" * 50)
    
    service = NormalizationService()
    
    # Тестируем разные конфигурации
    configurations = [
        ("Базовые функции", True, True, True),
        ("Без морфологии", True, True, False),
        ("Без стоп-слов", False, True, True),
        ("Минимальная обработка", False, False, False)
    ]
    
    for config_name, remove_stop_words, preserve_names, enable_advanced in configurations:
        print(f"\n{config_name}:")
        
        total_time = 0
        for phrase in DEMO_PHRASES:
            start_time = time.time()
            
            # Синхронный вызов для точного измерения
            result = service.normalize_sync(
                phrase,
                language="auto",
                remove_stop_words=remove_stop_words,
                preserve_names=preserve_names,
                enable_advanced_features=enable_advanced
            )
            
            processing_time = time.time() - start_time
            total_time += processing_time
            
            print(f"  '{phrase}' → '{result.normalized}' ({processing_time:.4f}s)")
        
        avg_time = total_time / len(DEMO_PHRASES)
        print(f"  Среднее время: {avg_time:.4f}s")


async def demo_error_handling():
    """Демонстрация обработки ошибок."""
    print("\n🚨 Демонстрация обработки ошибок")
    print("-" * 50)
    
    service = NormalizationService()
    
    # Тестовые случаи с ошибками
    error_cases = [
        "",  # Пустая строка
        "   ",  # Только пробелы
        "a" * 10001,  # Слишком длинная строка
        None,  # None (будет преобразован в строку)
    ]
    
    for case in error_cases:
        print(f"Тестирование: {repr(case)}")
        
        try:
            with profile_time("demo.error_handling"):
                result = await service.normalize_async(
                    str(case) if case is not None else "",
                    language="auto",
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )
            
            print(f"  → Успех: {result.success}")
            if result.errors:
                print(f"  → Ошибки: {result.errors}")
            print(f"  → Время: {result.processing_time:.4f}s")
            
        except Exception as e:
            print(f"  → Исключение: {e}")


def demo_statistics_analysis():
    """Демонстрация анализа статистик."""
    print("\n📈 Анализ статистик")
    print("-" * 50)
    
    stats = get_profiling_stats()
    
    # Анализ счётчиков времени
    counters = stats.get('counters', {})
    if counters:
        print("Счётчики времени:")
        
        # Сортируем по общему времени
        sorted_counters = sorted(
            counters.items(),
            key=lambda x: x[1]['total_time'],
            reverse=True
        )
        
        for name, counter_stats in sorted_counters:
            print(f"  {name}:")
            print(f"    Вызовов: {counter_stats['calls']}")
            print(f"    Общее время: {counter_stats['total_time']:.4f}s")
            print(f"    Среднее время: {counter_stats['avg_time']:.6f}s")
            print(f"    P50: {counter_stats['p50_time']:.6f}s")
            print(f"    P95: {counter_stats['p95_time']:.6f}s")
            print()
    
    # Анализ трекеров памяти
    memory_trackers = stats.get('memory_trackers', {})
    if memory_trackers:
        print("Трекеры памяти:")
        
        for name, tracker_stats in memory_trackers.items():
            print(f"  {name}:")
            print(f"    Снимков: {tracker_stats['snapshots']}")
            print(f"    Пик памяти: {tracker_stats['peak_memory']} байт")
            print(f"    Средняя память: {tracker_stats['avg_memory']:.0f} байт")
            print()


async def main():
    """Главная функция демонстрации."""
    print("🚀 Демонстрация системы профилирования AI Service")
    print("=" * 60)
    
    try:
        # Базовое профилирование
        await demo_basic_profiling()
        
        # Профилирование памяти
        await demo_memory_profiling()
        
        # Сравнение производительности
        demo_performance_comparison()
        
        # Обработка ошибок
        await demo_error_handling()
        
        # Анализ статистик
        demo_statistics_analysis()
        
        print("\n✅ Демонстрация завершена успешно!")
        print("\nДля полного профилирования запустите:")
        print("  make -f Makefile.profile profile-quick")
        print("\nДля просмотра результатов:")
        print("  make -f Makefile.profile show-profile")
        
    except Exception as e:
        print(f"\n❌ Ошибка демонстрации: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
