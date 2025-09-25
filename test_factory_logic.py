#!/usr/bin/env python3

"""
Точная копия логики из orchestrator_factory для диагностики fallback.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_factory_logic():
    """Тест логики создания search service из orchestrator_factory."""
    print("🔍 ТЕСТ ЛОГИКИ ORCHESTRATOR FACTORY")
    print("=" * 60)

    # Точная копия кода из orchestrator_factory
    enable_search = True
    search_service = None

    if enable_search and search_service is None:
        try:
            print("1. Попытка создания HybridSearchService...")
            from ai_service.layers.search.config import HybridSearchConfig
            from ai_service.layers.search.hybrid_search_service import HybridSearchService

            search_config = HybridSearchConfig.from_env()
            search_service = HybridSearchService(search_config)
            search_service.initialize()  # Not async
            print("✅ Search service initialized")

            print(f"   Search service type: {type(search_service).__name__}")

        except Exception as e:
            print(f"❌ Failed to initialize HybridSearchService: {e}")
            print(f"   Error type: {type(e).__name__}")
            print("ℹ️ Falling back to MockSearchService for development/testing")

            # Force use MockSearchService when Elasticsearch is not available
            try:
                from ai_service.layers.search.mock_search_service import MockSearchService
                search_service = MockSearchService()
                search_service.initialize()
                print("✅ MockSearchService initialized successfully - search escalation available")

                print(f"   Search service type: {type(search_service).__name__}")

            except Exception as mock_e:
                print(f"❌ Critical: Failed to initialize MockSearchService: {mock_e}")
                search_service = None
                enable_search = False

    print(f"\n📊 FINAL RESULT:")
    print(f"   enable_search: {enable_search}")
    print(f"   search_service: {type(search_service).__name__ if search_service else None}")

    return search_service

def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА FACTORY LOGIC")
    print("=" * 50)

    search_service = test_factory_logic()

    print("\n" + "=" * 50)
    if search_service and type(search_service).__name__ == "HybridSearchService":
        print("🎉 SUCCESS: Factory использует HybridSearchService!")
    elif search_service and type(search_service).__name__ == "MockSearchService":
        print("⚠️ FALLBACK: Factory использует MockSearchService")
        print("   Причина: HybridSearchService.initialize() failed")
    else:
        print("❌ FAILURE: Никакой search service не создан")

    return search_service is not None

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)