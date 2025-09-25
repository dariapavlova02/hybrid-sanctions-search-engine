#!/usr/bin/env python3

"""
Тест эскалации в HybridSearchService для "Коврико Роман".
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_escalation_debug():
    """Проверка логики эскалации."""
    print("🔍 ТЕСТ ЛОГИКИ ЭСКАЛАЦИИ")
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

        query_text = "Коврико Роман"
        search_opts = SearchOpts(
            top_k=10,
            threshold=0.5,
            search_mode=SearchMode.HYBRID,
            enable_escalation=True,       # ⭐ ВАЖНО: включаем эскалацию
            escalation_threshold=0.8      # ⭐ ВАЖНО: устанавливаем порог
        )

        print(f"📊 SearchOpts:")
        print(f"   search_mode: {search_opts.search_mode}")
        print(f"   enable_escalation: {search_opts.enable_escalation}")
        print(f"   escalation_threshold: {search_opts.escalation_threshold}")
        print(f"   top_k: {search_opts.top_k}")

        # Тестируем полный find_candidates
        print(f"\n🔍 Тест полного find_candidates для: '{query_text}'")
        norm_result = MockNormResult(query_text, query_text.split())
        all_results = await search_service.find_candidates(
            normalized=norm_result,
            text=query_text,
            opts=search_opts
        )

        print(f"\n📊 РЕЗУЛЬТАТЫ:")
        print(f"   Всего результатов: {len(all_results)}")

        if all_results:
            print(f"   ТОП-5 результатов:")
            for i, result in enumerate(all_results[:5], 1):
                print(f"     {i}. {result.text}")
                print(f"        - score: {result.score:.3f}")
                print(f"        - search_mode: {result.search_mode}")
                print(f"        - confidence: {result.confidence:.3f}")
        else:
            print("   ❌ НЕТ РЕЗУЛЬТАТОВ")

        return len(all_results) > 0

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА ЭСКАЛАЦИИ")
    print("=" * 50)

    success = await test_escalation_debug()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Эскалация работает и находит результаты!")
    else:
        print("❌ FAILURE: Проблемы с эскалацией")
        print("\n🔧 ВОЗМОЖНЫЕ ПРИЧИНЫ:")
        print("   1. enable_escalation = False")
        print("   2. escalation_threshold слишком низкий")
        print("   3. AC search находит хорошие результаты")
        print("   4. Проблемы в _fuzzy_search")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)