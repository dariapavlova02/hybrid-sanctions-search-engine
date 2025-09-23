#!/usr/bin/env python3
"""
Debug search service initialization.
"""

import os
import sys
from pathlib import Path

# Set production environment variables
os.environ.update({
    'ENABLE_SEARCH': 'true',
    'ENABLE_HYBRID_SEARCH': 'true',
    'ES_HOSTS': 'localhost:9200',
    'ENABLE_FALLBACK': 'true',
    'DEBUG_TRACING': 'true'
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_search_initialization():
    """Test search service initialization."""
    print("🔍 SEARCH SERVICE INITIALIZATION TEST")
    print("="*60)

    try:
        from ai_service.core.orchestrator_factory import OrchestratorFactory

        print("📝 Creating production orchestrator...")
        orchestrator = await OrchestratorFactory.create_production_orchestrator()

        print(f"✅ Orchestrator created: {type(orchestrator).__name__}")

        # Check if search service is available
        print(f"\n🔍 Search service status:")
        print(f"  - hasattr(orchestrator, 'search_service'): {hasattr(orchestrator, 'search_service')}")

        if hasattr(orchestrator, 'search_service'):
            search_service = orchestrator.search_service
            print(f"  - search_service: {search_service}")
            print(f"  - search_service type: {type(search_service).__name__ if search_service else 'None'}")

            if search_service:
                print(f"  - search_service initialized: True")

                # Test health check
                try:
                    health = await search_service.health_check()
                    print(f"  - health check: {health}")
                except Exception as e:
                    print(f"  - health check failed: {e}")
            else:
                print(f"  - search_service initialized: False")
        else:
            print(f"  - search_service attribute: Not found")

        # Check orchestrator configuration
        print(f"\n⚙️ Orchestrator configuration:")
        print(f"  - enable_search: {getattr(orchestrator, 'enable_search', 'not found')}")

        # Test a simple search call
        print(f"\n🔍 Testing search functionality:")

        # First normalize a name to get something to search
        print("  - Testing normalization first...")
        try:
            result = await orchestrator.process(
                text="Иванов Иван Иванович",
                generate_variants=False,
                generate_embeddings=False,
                search_trace_enabled=True
            )
            print(f"    Normalized: '{result.normalized_text}'")
            print(f"    Success: {result.success}")

            # Check if search results are included
            if hasattr(result, 'search_results'):
                print(f"    Search results: {result.search_results}")
            else:
                print(f"    No search_results attribute found")

            # Check trace for search activity
            if hasattr(result, 'search_trace') and result.search_trace:
                print(f"    Search trace: {result.search_trace}")
            else:
                print(f"    No search trace found")

        except Exception as e:
            print(f"    Process failed: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_search_config():
    """Test search configuration."""
    print("\n\n⚙️ SEARCH CONFIGURATION TEST")
    print("="*40)

    try:
        from ai_service.config.settings import SEARCH_CONFIG

        print(f"📝 Search config:")
        print(f"  - es_hosts: {SEARCH_CONFIG.es_hosts}")
        print(f"  - enable_hybrid_search: {SEARCH_CONFIG.enable_hybrid_search}")
        print(f"  - enable_fallback: {SEARCH_CONFIG.enable_fallback}")
        print(f"  - enable_escalation: {SEARCH_CONFIG.enable_escalation}")

        # Test HybridSearchService direct initialization
        print(f"\n🔧 Direct HybridSearchService initialization:")
        try:
            from ai_service.layers.search.hybrid_search_service import HybridSearchService

            search_service = HybridSearchService(SEARCH_CONFIG)
            print(f"  - Created: {type(search_service).__name__}")

            search_service.initialize()
            print(f"  - Initialized: True")

            # Test health check
            try:
                health = await search_service.health_check()
                print(f"  - Health check: {health}")
            except Exception as e:
                print(f"  - Health check failed: {e}")

        except Exception as e:
            print(f"  - Direct initialization failed: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Config test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_search_initialization())
    asyncio.run(test_search_config())