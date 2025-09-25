#!/usr/bin/env python3

"""
Отладка fuzzy search в продакшне - проверяем содержимое кандидатов.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_production_fuzzy_debug():
    """Детальная отладка fuzzy search в продакшне."""
    print("🔍 ОТЛАДКА PRODUCTION FUZZY SEARCH")
    print("=" * 60)

    try:
        from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader

        # Принудительно очищаем кеш
        loader = SanctionsDataLoader()
        await loader.clear_cache()
        print("🗑️ Кеш очищен")

        # Загружаем dataset
        dataset = await loader.load_dataset(force_reload=True)
        print(f"📊 Dataset загружен: {dataset.total_entries} entries")
        print(f"   Sources: {dataset.sources}")

        # Получаем fuzzy candidates
        fuzzy_candidates = await loader.get_fuzzy_candidates()
        print(f"🔍 Fuzzy candidates: {len(fuzzy_candidates)}")

        # Поиск Ковриков
        kovrykov_variants = [
            "ковриков", "kovrykov", "коврико", "kovryko",
            "роман", "roman", "валерійович", "valeriyovych"
        ]

        matches = []
        for variant in kovrykov_variants:
            variant_matches = [c for c in fuzzy_candidates if variant.lower() in c.lower()]
            if variant_matches:
                matches.extend(variant_matches)
                print(f"   '{variant}' matches: {len(variant_matches)}")
                for match in variant_matches[:3]:
                    print(f"     - {match}")

        # Убираем дубликаты
        unique_matches = list(set(matches))
        print(f"\n📋 Все уникальные совпадения: {len(unique_matches)}")
        for match in unique_matches:
            print(f"  - {match}")

        # Тестируем fuzzy напрямую
        print(f"\n🧪 Тест fuzzy алгоритма:")
        from ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig

        fuzzy_config = FuzzyConfig(
            min_score_threshold=0.5,
            high_confidence_threshold=0.80,
            partial_match_threshold=0.70,
            enable_name_fuzzy=True,
            name_boost_factor=1.2
        )

        fuzzy_service = FuzzySearchService(fuzzy_config)
        query = "Коврико Роман"

        # Тестируем с найденными кандидатами
        if unique_matches:
            print(f"   Testing with {len(unique_matches)} relevant candidates...")
            results = await fuzzy_service.search_async(
                query=query,
                candidates=unique_matches
            )
            print(f"   Results: {len(results)}")
            for result in results:
                print(f"     - {result.matched_text} (score: {result.score:.3f})")

        # Тестируем с sample кандидатами
        test_candidates = [
            "Ковриков Роман Валерійович",
            "Роман Ковриков",
            "Коврик Роман",
            "Ковриков Роман"
        ] + unique_matches[:5]

        print(f"\n   Testing with sample + found candidates ({len(test_candidates)})...")
        results = await fuzzy_service.search_async(
            query=query,
            candidates=test_candidates
        )
        print(f"   Results: {len(results)}")
        for result in results:
            print(f"     - {result.matched_text} (score: {result.score:.3f})")

        return len(results) > 0

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 PRODUCTION FUZZY DEBUG")
    print("=" * 50)

    success = await test_production_fuzzy_debug()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Fuzzy алгоритм нашел результаты!")
    else:
        print("❌ FAILURE: Fuzzy алгоритм не работает")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)