#!/usr/bin/env python3

"""
Test HybridSearchService initialization.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_hybrid_service_init():
    """Test HybridSearchService initialization."""
    print("🔍 TESTING HYBRID SERVICE INITIALIZATION")
    print("=" * 60)

    try:
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.config import HybridSearchConfig
        from ai_service.config.settings import SERVICE_CONFIG

        print(f"✅ Successfully imported HybridSearchService")
        print(f"📊 SERVICE_CONFIG.enable_search: {SERVICE_CONFIG.enable_search}")

        # Try to create config
        try:
            search_config = HybridSearchConfig.from_env()
            print(f"✅ Successfully created HybridSearchConfig")
            print(f"📋 Config hosts: {search_config.elasticsearch.hosts}")
            print(f"📋 Config enable_fallback: {search_config.enable_fallback}")
        except Exception as config_e:
            print(f"❌ Failed to create HybridSearchConfig: {config_e}")
            return

        # Try to create service
        try:
            search_service = HybridSearchService(config=search_config)
            print(f"✅ Successfully created HybridSearchService")
        except Exception as service_e:
            print(f"❌ Failed to create HybridSearchService: {service_e}")
            return

        # Try to initialize service
        try:
            search_service.initialize()
            print(f"✅ Successfully initialized HybridSearchService")
            print(f"📊 Service type: {type(search_service).__name__}")

            # Check health (skip for now - async method)
            print(f"🏥 Health check skipped (async method)")

        except Exception as init_e:
            print(f"❌ Failed to initialize HybridSearchService: {init_e}")
            print(f"📋 Error details: {type(init_e).__name__}: {init_e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"❌ Import/setup error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hybrid_service_init()