#!/usr/bin/env python3
"""
Debug search issue for IP 95.217.84.234 - why known person is not found
"""

import sys
import json
import asyncio
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def debug_search_issue():
    """Debug search service and index issues."""
    print("🔍 DEBUGGING SEARCH ISSUE FOR IP 95.217.84.234")
    print("="*60)

    try:
        # First check if we can access search components
        print("📊 SEARCH COMPONENTS CHECK:")

        try:
            from ai_service.layers.search.hybrid_search_service import HybridSearchService
            from ai_service.layers.search.config import HybridSearchConfig
            print("  ✅ HybridSearchService imported")
        except Exception as e:
            print(f"  ❌ Cannot import HybridSearchService: {e}")
            return

        try:
            from ai_service.layers.search.elasticsearch_client import ElasticsearchClient
            print("  ✅ ElasticsearchClient imported")
        except Exception as e:
            print(f"  ❌ Cannot import ElasticsearchClient: {e}")

        # Check if data loader is available
        try:
            from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader
            loader = SanctionsDataLoader()
            print("  ✅ SanctionsDataLoader available")
        except Exception as e:
            print(f"  ❌ Cannot import SanctionsDataLoader: {e}")

        # Check configuration
        print(f"\n⚙️ CONFIGURATION CHECK:")
        try:
            from ai_service.config.settings import SERVICE_CONFIG
            print(f"  enable_search: {SERVICE_CONFIG.enable_search}")
            print(f"  elasticsearch_url: {getattr(SERVICE_CONFIG, 'elasticsearch_url', 'Not set')}")
        except Exception as e:
            print(f"  ❌ Cannot check SERVICE_CONFIG: {e}")

        # Try to initialize search service
        print(f"\n🔧 SEARCH SERVICE INITIALIZATION:")
        try:
            config = HybridSearchConfig()
            search_service = HybridSearchService(config=config)
            print("  ✅ Search service created")

            # Check if it initializes properly
            try:
                search_service.initialize()
                print("  ✅ Search service initialized")
            except Exception as e:
                print(f"  ⚠️  Search service initialization warning: {e}")

        except Exception as e:
            print(f"  ❌ Search service creation failed: {e}")
            return

        # Check Elasticsearch connection
        print(f"\n🔌 ELASTICSEARCH CONNECTION CHECK:")
        try:
            # Try to create Elasticsearch client directly
            from ai_service.layers.search.elasticsearch_client import ElasticsearchClient
            es_config = config.elasticsearch
            client = ElasticsearchClient(es_config)

            # Try to get cluster health
            health = await client.cluster_health()
            print(f"  ✅ Elasticsearch health: {health.get('status', 'unknown')}")

            # Check if indices exist
            indices = await client.list_indices()
            print(f"  📁 Available indices: {list(indices.keys()) if indices else 'None'}")

            # Check if watchlist index has data
            if 'watchlist' in indices:
                count = await client.count_documents('watchlist')
                print(f"  📊 Documents in 'watchlist': {count}")

            if 'watchlist_ac' in indices:
                count = await client.count_documents('watchlist_ac')
                print(f"  📊 Documents in 'watchlist_ac': {count}")

        except Exception as e:
            print(f"  ❌ Elasticsearch connection failed: {e}")
            print(f"     This explains why search returns 0 results!")

        # Test search directly if possible
        print(f"\n🔍 DIRECT SEARCH TEST:")
        try:
            from ai_service.layers.normalization.normalization_service import NormalizationService
            from ai_service.layers.search.contracts import SearchOpts
            from ai_service.layers.search.contracts import SearchMode

            # Create test query
            norm_service = NormalizationService()
            norm_result = norm_service.normalize_sync("Порошенк Петро", language="uk")

            # Create search options
            search_opts = SearchOpts(
                search_mode=SearchMode.FUZZY,
                top_k=10,
                threshold=0.5,
                client_id="debug_test"
            )

            print(f"  Query: 'Порошенк Петро'")
            print(f"  Normalized: '{norm_result.normalized}'")
            print(f"  Search mode: {search_opts.search_mode}")

            # Try to search
            candidates = await search_service.find_candidates(
                normalized=norm_result,
                text="Порошенк Петро",
                opts=search_opts
            )

            print(f"  🎯 Search results: {len(candidates)} candidates found")
            for i, candidate in enumerate(candidates[:3]):  # Show first 3
                print(f"    {i+1}. Score: {candidate.score:.3f}, Name: {getattr(candidate, 'name', 'N/A')}")

        except Exception as e:
            print(f"  ❌ Direct search test failed: {e}")
            import traceback
            traceback.print_exc()

        # Check if there are any fallback services
        print(f"\n🔄 FALLBACK SERVICES CHECK:")
        try:
            # Check if local indexes exist
            import os
            fallback_paths = [
                'data/watchlist_index.pkl',
                'data/vector_index.pkl',
                'watchlist_index.pkl',
                'vector_index.pkl'
            ]

            for path in fallback_paths:
                if os.path.exists(path):
                    size = os.path.getsize(path)
                    print(f"  ✅ Fallback index found: {path} ({size} bytes)")
                else:
                    print(f"  ❌ No fallback index: {path}")

        except Exception as e:
            print(f"  ❌ Cannot check fallback services: {e}")

        # Check orchestrator configuration
        print(f"\n🎯 ORCHESTRATOR CONFIGURATION:")
        try:
            from ai_service.core.unified_orchestrator import UnifiedOrchestrator

            # Check if orchestrator has search enabled
            print("  Checking how UnifiedOrchestrator is typically initialized...")

            # This would show us what search_service is passed
            print("  Note: search_service is None by default in UnifiedOrchestrator constructor")
            print("  This is likely the root cause - no search service is provided!")

        except Exception as e:
            print(f"  ❌ Cannot check orchestrator: {e}")

        print(f"\n💡 LIKELY ROOT CAUSES:")
        print(f"  1. search_service=None in UnifiedOrchestrator initialization")
        print(f"  2. Elasticsearch is not running or not accessible")
        print(f"  3. Sanctions data not loaded into indices")
        print(f"  4. enable_search=False in configuration")

    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_search_issue())