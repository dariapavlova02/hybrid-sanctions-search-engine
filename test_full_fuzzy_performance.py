#!/usr/bin/env python3

"""
Тест производительности fuzzy search с полным набором 20,000 кандидатов
как в продакшне.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_full_fuzzy_performance():
    """Тест fuzzy search с полными данными как в продакшне."""
    print("🔍 ТЕСТ ПРОИЗВОДИТЕЛЬНОСТИ FUZZY SEARCH")
    print("=" * 60)

    try:
        from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader
        from ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig

        # Загружаем полный dataset
        loader = SanctionsDataLoader()
        await loader.clear_cache()

        fuzzy_candidates = await loader.get_fuzzy_candidates()
        print(f"📊 Loaded {len(fuzzy_candidates)} fuzzy candidates")

        # Ограничиваем до 20,000 как в продакшне
        limited_candidates = fuzzy_candidates[:20000]
        print(f"🔒 Limited to {len(limited_candidates)} candidates (like production)")

        # Создаем fuzzy service с production настройками
        fuzzy_config = FuzzyConfig(
            min_score_threshold=0.5,   # Production threshold
            high_confidence_threshold=0.80,
            partial_match_threshold=0.70,
            enable_name_fuzzy=True,
            name_boost_factor=1.2,
            max_candidates=1000,  # Важно! Ограничиваем для производительности
            max_results=50
        )

        fuzzy_service = FuzzySearchService(fuzzy_config)
        query = "Коврико Роман"

        # Тест 1: Полный поиск по всем 20,000
        print(f"\n🧪 Тест 1: Поиск по всем {len(limited_candidates)} кандидатам...")
        start_time = time.time()

        results = await fuzzy_service.search_async(
            query=query,
            candidates=limited_candidates
        )

        elapsed_time = time.time() - start_time
        print(f"   Время поиска: {elapsed_time:.2f}s")
        print(f"   Результаты: {len(results)}")
        for result in results[:5]:
            print(f"     - {result.matched_text} (score: {result.score:.3f})")

        # Тест 2: Поиск с оптимизированными настройками
        print(f"\n🧪 Тест 2: Оптимизированный поиск...")
        optimized_config = FuzzyConfig(
            min_score_threshold=0.4,   # Еще ниже порог
            high_confidence_threshold=0.75,
            partial_match_threshold=0.65,
            enable_name_fuzzy=True,
            name_boost_factor=1.3,
            max_candidates=2000,  # Увеличиваем лимит candidates
            max_results=100,
            enable_preprocessing=True
        )

        optimized_service = FuzzySearchService(optimized_config)
        start_time = time.time()

        results_opt = await optimized_service.search_async(
            query=query,
            candidates=limited_candidates
        )

        elapsed_time = time.time() - start_time
        print(f"   Время поиска: {elapsed_time:.2f}s")
        print(f"   Результаты: {len(results_opt)}")
        for result in results_opt[:5]:
            print(f"     - {result.matched_text} (score: {result.score:.3f})")

        # Проверяем, есть ли Ковриков в результатах
        kovrykov_found = any("ковриков" in r.matched_text.lower() for r in results_opt)
        print(f"\n🎯 'Ковриков' найден в результатах: {kovrykov_found}")

        return len(results_opt) > 0

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 PRODUCTION FUZZY PERFORMANCE TEST")
    print("=" * 50)

    success = await test_full_fuzzy_performance()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Fuzzy search работает с полными данными!")
    else:
        print("❌ FAILURE: Проблемы с fuzzy search на полных данных")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)