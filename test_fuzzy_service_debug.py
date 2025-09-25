#!/usr/bin/env python3

"""
Тест состояния FuzzySearchService в HybridSearchService для выяснения
почему fuzzy search не работает.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_fuzzy_service_state():
    """Проверка состояния FuzzySearchService."""
    print("🔍 ТЕСТ СОСТОЯНИЯ FUZZYSEARCHSERVICE")
    print("=" * 60)

    try:
        # Проверяем rapidfuzz
        print("1. Проверка rapidfuzz...")
        try:
            import rapidfuzz
            from rapidfuzz import fuzz, process
            print("   ✅ rapidfuzz доступен")
            print(f"   Версия: {rapidfuzz.__version__ if hasattr(rapidfuzz, '__version__') else 'неизвестно'}")
        except ImportError as e:
            print(f"   ❌ rapidfuzz НЕ доступен: {e}")
            return False

        # Создаем HybridSearchService
        print("\n2. Создание HybridSearchService...")
        from ai_service.layers.search.config import HybridSearchConfig
        from ai_service.layers.search.hybrid_search_service import HybridSearchService

        search_config = HybridSearchConfig.from_env()
        search_service = HybridSearchService(search_config)
        search_service.initialize()

        print("   ✅ HybridSearchService создан")

        # Проверяем FuzzySearchService
        print("\n3. Проверка FuzzySearchService...")
        fuzzy_service = search_service._fuzzy_service
        print(f"   fuzzy_service type: {type(fuzzy_service).__name__}")
        print(f"   fuzzy_service.enabled: {fuzzy_service.enabled}")

        if not fuzzy_service.enabled:
            print("   ❌ FuzzySearchService отключен!")
            return False

        print("   ✅ FuzzySearchService включен")

        # Тестируем direct fuzzy search
        print("\n4. Тест direct fuzzy search...")
        candidates = ["Ковриков Роман Валерійович", "Петров Иван", "Сидоров Василий"]
        query = "Коврико Роман"

        fuzzy_results = await fuzzy_service.search_async(
            query=query,
            candidates=candidates
        )

        print(f"   Query: '{query}'")
        print(f"   Candidates: {len(candidates)}")
        print(f"   Results: {len(fuzzy_results)}")

        for result in fuzzy_results:
            print(f"     - {result.matched_text} (score: {result.score:.3f}, algo: {result.algorithm})")

        return len(fuzzy_results) > 0

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА FUZZYSEARCHSERVICE")
    print("=" * 50)

    success = await test_fuzzy_service_state()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: FuzzySearchService работает!")
    else:
        print("❌ FAILURE: Проблемы с FuzzySearchService")
        print("\n🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("   1. rapidfuzz не установлен")
        print("   2. FuzzySearchService.enabled = False")
        print("   3. Проблемы в алгоритме поиска")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)