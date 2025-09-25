#!/usr/bin/env python3

"""
Тест fuzzy алгоритма для понимания почему "Коврико Роман"
не находит "Ковриков Роман Валерійович".
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_fuzzy_algorithm():
    """Тест fuzzy алгоритма."""
    print("🔍 ТЕСТ FUZZY АЛГОРИТМА")
    print("=" * 60)

    try:
        # Проверяем rapidfuzz напрямую
        import rapidfuzz
        from rapidfuzz import fuzz

        query = "Коврико Роман"
        candidates = [
            "Ковриков Роман Валерійович",
            "Морозко Ольга Романівна",
            "Роман Ковриков",
            "Коврик Роман",
            "Ковриков Роман"
        ]

        print(f"Query: '{query}'\n")

        algorithms = [
            ("ratio", fuzz.ratio),
            ("partial_ratio", fuzz.partial_ratio),
            ("token_sort_ratio", fuzz.token_sort_ratio),
            ("token_set_ratio", fuzz.token_set_ratio)
        ]

        for candidate in candidates:
            print(f"Candidate: '{candidate}'")
            for algo_name, algo_func in algorithms:
                score = algo_func(query, candidate) / 100.0  # Convert to 0-1
                print(f"  {algo_name:15}: {score:.3f}")
            print()

        # Теперь тестируем FuzzySearchService
        print("=" * 40)
        print("ТЕСТ FUZZYSEARCHSERVICE")

        from ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig

        fuzzy_config = FuzzyConfig(
            min_score_threshold=0.4,   # Еще ниже для тестирования
            high_confidence_threshold=0.80,
            partial_match_threshold=0.70,
            enable_name_fuzzy=True,
            name_boost_factor=1.2
        )

        fuzzy_service = FuzzySearchService(fuzzy_config)
        print(f"FuzzySearchService enabled: {fuzzy_service.enabled}")
        print(f"Min threshold: {fuzzy_service.config.min_score_threshold}")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_fuzzy_service_direct():
    """Тест FuzzySearchService напрямую."""
    print("\n" + "=" * 40)
    print("ТЕСТ FUZZYSEARCHSERVICE ASYNC")

    try:
        from ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig

        fuzzy_config = FuzzyConfig(
            min_score_threshold=0.4,
            high_confidence_threshold=0.80,
            partial_match_threshold=0.70,
            enable_name_fuzzy=True,
            name_boost_factor=1.2
        )

        fuzzy_service = FuzzySearchService(fuzzy_config)

        query = "Коврико Роман"
        candidates = [
            "Ковриков Роман Валерійович",
            "Морозко Ольга Романівна",
            "Роман Ковриков",
            "Коврик Роман",
            "Ковриков Роман"
        ]

        print(f"\nQuery: '{query}'")
        print(f"Candidates: {len(candidates)}")

        results = await fuzzy_service.search_async(
            query=query,
            candidates=candidates
        )

        print(f"Results: {len(results)}")
        for result in results:
            print(f"  - {result.matched_text} (score: {result.score:.3f}, algo: {result.algorithm})")

        return len(results) > 0

    except Exception as e:
        print(f"❌ Ошибка async: {e}")
        return False

async def main():
    """Главная функция."""
    print("🎯 АНАЛИЗ FUZZY АЛГОРИТМА")
    print("=" * 50)

    sync_success = test_fuzzy_algorithm()
    async_success = await test_fuzzy_service_direct()

    print("\n" + "=" * 50)
    if sync_success and async_success:
        print("🎉 SUCCESS: Fuzzy алгоритм работает!")
    else:
        print("❌ FAILURE: Проблемы с fuzzy алгоритмом")

    return sync_success and async_success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)