#!/usr/bin/env python3

"""
Тест поиска в продакшне для "Коврико Роман" → "Ковриков Роман".
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_production_search():
    """Проверка fuzzy search в продакшне."""
    print("🔍 ТЕСТ ПРОДАКШН ПОИСКА")
    print("=" * 60)

    try:
        # Создаем HybridSearchService с продакшн конфигом
        from ai_service.layers.search.config import HybridSearchConfig
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.contracts import SearchOpts, SearchMode

        search_config = HybridSearchConfig.from_env()
        print(f"📊 Elasticsearch hosts: {search_config.elasticsearch.hosts}")

        search_service = HybridSearchService(search_config)
        search_service.initialize()

        print("✅ HybridSearchService инициализирован")

        # Проверяем fuzzy candidates
        print("\n1. Проверка fuzzy candidates...")
        fuzzy_candidates = await search_service._get_fuzzy_candidates()
        print(f"   Загружено кандидатов: {len(fuzzy_candidates)}")

        # Поиск Ковриков в кандидатах
        kovrykov_candidates = [c for c in fuzzy_candidates if "ковриков" in c.lower()]
        print(f"   'Ковриков' кандидатов: {len(kovrykov_candidates)}")
        for candidate in kovrykov_candidates[:3]:
            print(f"     - {candidate}")

        # Поиск всех вариантов "Роман"
        roman_candidates = [c for c in fuzzy_candidates
                          if "роман" in c.lower() and "ковр" in c.lower()]
        print(f"   'Роман + Ковр*' кандидатов: {len(roman_candidates)}")
        for candidate in roman_candidates[:3]:
            print(f"     - {candidate}")

        # Тестируем fuzzy search
        print("\n2. Тест fuzzy search...")
        query_text = "Коврико Роман"
        search_opts = SearchOpts(
            top_k=10,
            threshold=0.4,  # Понижаем порог
            search_mode=SearchMode.HYBRID,
            enable_escalation=True,
            escalation_threshold=0.8
        )

        # Прямой fuzzy search
        fuzzy_results = await search_service._fuzzy_search(
            query_text=query_text,
            opts=search_opts,
            search_trace=None
        )
        print(f"   Fuzzy результаты: {len(fuzzy_results)}")
        for result in fuzzy_results[:5]:
            print(f"     - {result.text} (score: {result.score:.3f})")

        # Если fuzzy не работает, попробуем разные варианты запроса
        if not fuzzy_results:
            print("\n3. Тест разных вариантов запроса...")
            test_queries = [
                "Ковриков Роман",
                "Роман Ковриков",
                "Ковриков",
                "Роман Валерійович",
                "Roman Kovrykov"
            ]

            for test_query in test_queries:
                print(f"\n   Тест: '{test_query}'")
                fuzzy_results = await search_service._fuzzy_search(
                    query_text=test_query,
                    opts=search_opts,
                    search_trace=None
                )
                print(f"     Результаты: {len(fuzzy_results)}")
                if fuzzy_results:
                    for result in fuzzy_results[:3]:
                        print(f"       - {result.text} (score: {result.score:.3f})")

        return len(fuzzy_results) > 0

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА ПРОДАКШН ПОИСКА")
    print("=" * 50)

    success = await test_production_search()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Продакшн поиск работает!")
    else:
        print("❌ FAILURE: Проблемы с продакшн поиском")
        print("\n🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("   1. 'Ковриков Роман' нет в sanctions data")
        print("   2. Fuzzy threshold слишком высокий")
        print("   3. Имя в другом формате в базе")
        print("   4. Проблемы с Elasticsearch в продакшне")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)