#!/usr/bin/env python3

"""
Тест создания orchestrator'а чтобы понять где происходит fallback на MockSearchService.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_orchestrator_creation():
    """Тест создания production orchestrator."""
    print("🔍 ТЕСТ СОЗДАНИЯ PRODUCTION ORCHESTRATOR")
    print("=" * 60)

    try:
        from ai_service.core.orchestrator_factory import OrchestratorFactory

        print("1. Создание production orchestrator...")

        # Имитируем создание production orchestrator
        orchestrator = await OrchestratorFactory.create_production_orchestrator()

        print("✅ Production orchestrator создан!")

        # Проверим какой search service используется
        search_service = orchestrator.search_service
        print(f"   Search service type: {type(search_service)}")
        print(f"   Search service class: {search_service.__class__.__name__}")

        if hasattr(search_service, 'config'):
            config = search_service.config
            print(f"   Config type: {type(config)}")
            if hasattr(config, 'elasticsearch'):
                print(f"   ES hosts: {config.elasticsearch.hosts}")

        # Попробуем простой поиск, чтобы понять где ломается
        print("\n2. Тестирование поиска...")

        # Создаем фиктивный NormalizationResult
        class MockNormResult:
            def __init__(self, normalized, tokens):
                self.normalized = normalized
                self.normalized_text = normalized  # HybridSearchService ожидает это поле
                self.tokens = tokens
                self.trace = []
                self.language = "uk"
                self.confidence = 0.8
                self.success = True

        try:
            # Импортируем SearchOpts
            from ai_service.layers.search.contracts import SearchOpts

            norm_result = MockNormResult("Коврико Роман", ["Коврико", "Роман"])
            search_opts = SearchOpts(top_k=5, threshold=0.7)

            print("   Выполняем find_candidates...")
            candidates = await search_service.find_candidates(
                normalized=norm_result,
                text="Коврико Роман",
                opts=search_opts
            )

            print(f"   ✅ Поиск выполнен! Найдено кандидатов: {len(candidates)}")
            for candidate in candidates[:3]:  # Показать первых 3
                print(f"     - {candidate.text} (score: {candidate.score:.3f})")

        except Exception as search_error:
            print(f"   ❌ Ошибка поиска: {search_error}")
            print(f"   Тип ошибки: {type(search_error)}")
            import traceback
            traceback.print_exc()

        return True

    except Exception as e:
        print(f"❌ Ошибка создания orchestrator: {e}")
        print(f"   Тип ошибки: {type(e)}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА СОЗДАНИЯ ORCHESTRATOR")
    print("=" * 50)

    success = await test_orchestrator_creation()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Orchestrator создается с HybridSearchService!")
    else:
        print("❌ FAILURE: Orchestrator fallback на MockSearchService.")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)