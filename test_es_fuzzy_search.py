#!/usr/bin/env python3

"""
Тест ES-based fuzzy search implementation.
"""

import sys
import time
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_es_fuzzy_search():
    """Test ES-based fuzzy search with production Elasticsearch."""
    print("🔍 ТЕСТ ES-BASED FUZZY SEARCH")
    print("=" * 60)

    try:
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.elasticsearch_adapters import ElasticsearchACAdapter
        from ai_service.layers.search.contracts import SearchOpts

        # Create ES adapter pointing to production server
        es_adapter = ElasticsearchACAdapter(
            hosts=["http://95.217.84.234:9200"],
            index_name="ai_service_ac_patterns"
        )

        # Create hybrid search service
        search_service = HybridSearchService(ac_adapter=es_adapter)

        # Test query
        query = "Коврико Роман"
        search_opts = SearchOpts(
            enable_fuzzy=True,
            enable_vector=False,
            fuzzy_threshold=0.5,
            max_results=10
        )

        print(f"🧪 Testing ES fuzzy search for: '{query}'")
        start_time = time.time()

        # Test ES fuzzy search directly
        results = await search_service._elasticsearch_fuzzy_search(query, search_opts)

        elapsed_time = time.time() - start_time
        print(f"   Время поиска: {elapsed_time:.3f}s")
        print(f"   Найдено результатов: {len(results)}")

        for i, result in enumerate(results[:5], 1):
            print(f"   {i}. {result.matched_text} (score: {result.score:.3f})")
            if hasattr(result, 'canonical_name'):
                print(f"      → {result.canonical_name}")

        # Test fallback to in-memory fuzzy search
        print(f"\n🧪 Testing fallback in-memory fuzzy search...")
        start_time = time.time()

        fallback_results = await search_service._in_memory_fuzzy_search(query, search_opts)

        elapsed_time = time.time() - start_time
        print(f"   Время поиска: {elapsed_time:.3f}s")
        print(f"   Найдено результатов: {len(fallback_results)}")

        for i, result in enumerate(fallback_results[:3], 1):
            print(f"   {i}. {result.matched_text} (score: {result.score:.3f})")

        # Test full hybrid search with ES fuzzy enabled
        print(f"\n🧪 Testing full hybrid search with ES fuzzy...")
        start_time = time.time()

        hybrid_results = await search_service._fuzzy_search(query, search_opts)

        elapsed_time = time.time() - start_time
        print(f"   Время поиска: {elapsed_time:.3f}s")
        print(f"   Найдено результатов: {len(hybrid_results)}")

        for i, result in enumerate(hybrid_results[:5], 1):
            print(f"   {i}. {result.matched_text} (score: {result.score:.3f})")

        # Check if we found Ковриков
        found_kovrykov = any("ковриков" in r.matched_text.lower() for r in hybrid_results)
        print(f"\n🎯 'Ковриков' найден в результатах: {found_kovrykov}")

        return len(hybrid_results) > 0 and found_kovrykov

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    print("🎯 ES-BASED FUZZY SEARCH TEST")
    print("=" * 50)

    success = await test_es_fuzzy_search()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: ES-based fuzzy search работает!")
    else:
        print("❌ FAILURE: Проблемы с ES-based fuzzy search")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)