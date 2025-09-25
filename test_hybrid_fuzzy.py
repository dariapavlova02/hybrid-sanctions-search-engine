#!/usr/bin/env python3

"""
Тест fuzzy search в HybridSearchService для понимания почему он не находит результаты.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_hybrid_fuzzy_search():
    """Тест fuzzy search в HybridSearchService."""
    print("🔍 ТЕСТ FUZZY SEARCH В HYBRIDSEARCHSERVICE")
    print("=" * 60)

    try:
        # Создаем HybridSearchService
        from ai_service.layers.search.config import HybridSearchConfig
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.contracts import SearchOpts, SearchMode

        search_config = HybridSearchConfig.from_env()
        search_service = HybridSearchService(search_config)
        search_service.initialize()

        print("✅ HybridSearchService инициализирован")

        # Создаем mock NormalizationResult
        class MockNormResult:
            def __init__(self, normalized, tokens):
                self.normalized = normalized
                self.normalized_text = normalized
                self.tokens = tokens
                self.trace = []
                self.language = "uk"
                self.confidence = 0.8
                self.success = True

        # Тестируем fuzzy search напрямую
        print("\n1. Тест прямого fuzzy search...")

        query_text = "Коврико Роман"
        search_opts = SearchOpts(
            top_k=10,
            threshold=0.5,
            search_mode=SearchMode.HYBRID
        )

        try:
            # Проверяем fuzzy candidates
            print("   Загрузка fuzzy candidates...")
            fuzzy_candidates = await search_service._get_fuzzy_candidates()
            print(f"   Загружено кандидатов: {len(fuzzy_candidates)}")

            # Поиск Ковриков в кандидатах
            kovrykov_candidates = [c for c in fuzzy_candidates if "ковриков" in c.lower()]
            print(f"   'Ковриков' кандидатов: {len(kovrykov_candidates)}")
            for candidate in kovrykov_candidates[:3]:
                print(f"     - {candidate}")

        except Exception as e:
            print(f"   ❌ Ошибка загрузки candidates: {e}")

        # Тестируем fuzzy search
        print("\n2. Тест fuzzy search через _fuzzy_search...")
        try:
            fuzzy_results = await search_service._fuzzy_search(
                query_text=query_text,
                opts=search_opts,
                search_trace=None
            )
            print(f"   Fuzzy результаты: {len(fuzzy_results)}")
            for result in fuzzy_results[:5]:
                print(f"     - {result.text} (score: {result.score:.3f})")

        except Exception as e:
            print(f"   ❌ Ошибка fuzzy search: {e}")
            import traceback
            traceback.print_exc()

        # Тестируем полный find_candidates
        print("\n3. Тест полного find_candidates...")
        try:
            norm_result = MockNormResult(query_text, query_text.split())
            all_results = await search_service.find_candidates(
                normalized=norm_result,
                text=query_text,
                opts=search_opts
            )
            print(f"   Всего результатов: {len(all_results)}")
            for result in all_results[:5]:
                print(f"     - {result.text} (score: {result.score:.3f}, mode: {result.search_mode})")

        except Exception as e:
            print(f"   ❌ Ошибка find_candidates: {e}")

        return True

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА FUZZY SEARCH В HYBRIDSEARCHSERVICE")
    print("=" * 50)

    success = await test_hybrid_fuzzy_search()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Fuzzy search диагностика завершена")
    else:
        print("❌ FAILURE: Проблемы с fuzzy search")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)