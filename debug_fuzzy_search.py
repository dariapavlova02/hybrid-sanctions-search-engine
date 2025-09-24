#!/usr/bin/env python3
"""
Debug why fuzzy search doesn't work for Poroshenko typo
"""

import sys
import json
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_fuzzy_search():
    """Debug fuzzy search functionality."""
    print("🔍 DEBUGGING FUZZY SEARCH")
    print("="*50)

    try:
        # Test search service directly
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.config import HybridSearchConfig

        print("📊 Search Service Test:")

        # Try to initialize search service
        try:
            config = HybridSearchConfig()
            search_service = HybridSearchService(config=config)
            print("  ✅ Search service initialized")

            # Test search
            test_queries = [
                "Порошенк Петро",        # With typo
                "Порошенко Петро",       # Correct
                "Порошенко",             # Just surname
            ]

            for query in test_queries:
                print(f"\n  🔍 Searching for: '{query}'")

                try:
                    # Try different search modes
                    for mode in ["fuzzy", "hybrid", "exact"]:
                        result = search_service.search(
                            query=query,
                            search_mode=mode,
                            max_results=5
                        )
                        print(f"    Mode '{mode}': {result.total_hits} hits")
                        if result.results:
                            for hit in result.results[:2]:  # Show first 2 results
                                print(f"      - {hit.get('name', 'N/A')} (score: {hit.get('score', 0):.3f})")

                except Exception as e:
                    print(f"    ❌ Search failed: {e}")

        except Exception as e:
            print(f"  ❌ Search service initialization failed: {e}")

        # Check if there's test data with Poroshenko
        print(f"\n📂 Checking test data:")

        try:
            from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader
            loader = SanctionsDataLoader()

            # Try to find any Poroshenko entries
            print("  Looking for 'Poroshenko' or similar entries...")

            # This might not work if data isn't loaded, but let's try

        except Exception as e:
            print(f"  ❌ Cannot check test data: {e}")

        # Check configuration
        print(f"\n⚙️ Configuration Check:")

        try:
            from ai_service.config.settings import get_settings
            settings = get_settings()

            # Check if search is enabled
            search_enabled = getattr(settings, 'ENABLE_SEARCH', False)
            print(f"  ENABLE_SEARCH: {search_enabled}")

            # Check fuzzy search settings
            fuzzy_enabled = getattr(settings, 'ENABLE_FUZZY_SEARCH', False)
            print(f"  ENABLE_FUZZY_SEARCH: {fuzzy_enabled}")

            # Check Elasticsearch settings
            es_url = getattr(settings, 'ELASTICSEARCH_URL', None)
            print(f"  ELASTICSEARCH_URL: {es_url}")

        except Exception as e:
            print(f"  ❌ Cannot check configuration: {e}")

        # Check if search is called from orchestrator
        print(f"\n🎯 Orchestrator Search Integration:")

        try:
            from ai_service.core.unified_orchestrator import UnifiedOrchestrator
            print("  ✅ UnifiedOrchestrator available")

            # Check if it has search functionality
            # This is tricky without initializing full orchestrator...

        except Exception as e:
            print(f"  ❌ Cannot check orchestrator: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_fuzzy_search()