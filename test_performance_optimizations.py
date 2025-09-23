#!/usr/bin/env python3
"""
Быстрый тест производительности оптимизаций.
Сравнивает время обработки до и после оптимизации.
"""

import asyncio
import time
from typing import List, Dict

# Test cases с разной сложностью
TEST_CASES = [
    # Простые случаи (должны быть очень быстрыми с early returns)
    "Петров",
    "John",
    "Мария",
    "123",
    "",

    # Средней сложности (должны выиграть от ограничения паттернов)
    "Петров Иван Сергеевич",
    "John Smith",
    "Мария Александровна Петрова",

    # Сложные случаи (полный пайплайн, но с кэшированием)
    "ООО \"Ромашка\" Петров Иван Сергеевич дата рождения 01.01.1990 ИНН 1234567890",
    "LLC John Smith DOB 1990-01-01 SSN 123-45-6789",
    "Організація з обмеженою відповідальністю \"Соняшник\" Марія Олександрівна Петренко",
]

async def measure_processing_time(text: str, orchestrator) -> Dict[str, float]:
    """Измерить время обработки одного текста"""
    start_time = time.time()

    try:
        result = await orchestrator.process(text)
        end_time = time.time()

        return {
            "text": text,
            "processing_time": end_time - start_time,
            "success": result.success,
            "normalized_length": len(result.normalized_text),
            "token_count": len(result.tokens),
            "error_count": len(result.errors)
        }
    except Exception as e:
        end_time = time.time()
        return {
            "text": text,
            "processing_time": end_time - start_time,
            "success": False,
            "error": str(e)
        }

async def run_performance_test():
    """Запустить полный тест производительности"""
    print("🚀 Тестирование оптимизаций производительности...\n")

    try:
        # Динамически импортируем, чтобы не зависеть от среды
        from src.ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from src.ai_service.core.orchestrator_factory import OrchestratorFactory

        # Создаем оркестратор с оптимизациями
        factory = OrchestratorFactory()
        orchestrator = factory.create_orchestrator()

        print("✅ Оркестратор создан успешно")

    except ImportError as e:
        print(f"❌ Не удалось импортировать модули: {e}")
        return

    results = []
    total_start = time.time()

    # Тестируем каждый случай
    for i, test_case in enumerate(TEST_CASES, 1):
        print(f"📝 Тест {i}/{len(TEST_CASES)}: '{test_case[:50]}{'...' if len(test_case) > 50 else ''}'")

        result = await measure_processing_time(test_case, orchestrator)
        results.append(result)

        # Выводим результат
        if result['success']:
            print(f"   ✅ {result['processing_time']*1000:.1f}ms | "
                  f"tokens: {result['token_count']} | "
                  f"normalized: {result['normalized_length']} chars")
        else:
            print(f"   ❌ {result['processing_time']*1000:.1f}ms | "
                  f"error: {result.get('error', 'unknown')}")

        # Небольшая пауза между тестами
        await asyncio.sleep(0.1)

    total_time = time.time() - total_start

    # Анализ результатов
    print(f"\n📊 Результаты тестирования:")
    print(f"   Общее время: {total_time:.2f}s")
    print(f"   Всего тестов: {len(results)}")

    successful_results = [r for r in results if r['success']]
    failed_results = [r for r in results if not r['success']]

    print(f"   Успешных: {len(successful_results)}")
    print(f"   Неудачных: {len(failed_results)}")

    if successful_results:
        times = [r['processing_time'] for r in successful_results]
        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        print(f"\n⏱️  Статистика по времени:")
        print(f"   Среднее: {avg_time*1000:.1f}ms")
        print(f"   Минимальное: {min_time*1000:.1f}ms")
        print(f"   Максимальное: {max_time*1000:.1f}ms")

        # Проверка целевых метрик
        print(f"\n🎯 Проверка целевых метрик:")
        fast_cases = sum(1 for t in times if t < 0.1)  # < 100ms
        medium_cases = sum(1 for t in times if 0.1 <= t < 0.5)  # 100ms-500ms
        slow_cases = sum(1 for t in times if t >= 0.5)  # >= 500ms

        print(f"   Быстрые (<100ms): {fast_cases}/{len(times)} ({fast_cases/len(times)*100:.1f}%)")
        print(f"   Средние (100-500ms): {medium_cases}/{len(times)} ({medium_cases/len(times)*100:.1f}%)")
        print(f"   Медленные (>=500ms): {slow_cases}/{len(times)} ({slow_cases/len(times)*100:.1f}%)")

        if avg_time < 0.5:
            print(f"   ✅ Цель <500ms достигнута! (среднее: {avg_time*1000:.1f}ms)")
        else:
            print(f"   ⚠️  Цель <500ms не достигнута (среднее: {avg_time*1000:.1f}ms)")

    # Детальный отчет по неудачным тестам
    if failed_results:
        print(f"\n❌ Неудачные тесты:")
        for result in failed_results:
            print(f"   '{result['text'][:30]}...': {result.get('error', 'unknown error')}")

    print(f"\n🏁 Тестирование завершено!")

def run_sync_test():
    """Синхронная обертка для async теста"""
    try:
        asyncio.run(run_performance_test())
    except KeyboardInterrupt:
        print("\n⏹️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n💥 Ошибка во время тестирования: {e}")

if __name__ == "__main__":
    run_sync_test()