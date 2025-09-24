#!/usr/bin/env python3

"""
Debug script to test Elasticsearch connection and configuration.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.layers.search.config import HybridSearchConfig, ElasticsearchConfig
from ai_service.layers.search.elasticsearch_client import ElasticsearchClientFactory
from ai_service.layers.search.hybrid_search_service import HybridSearchService
from ai_service.utils.logging_config import get_logger


async def test_elasticsearch_connection():
    """Test Elasticsearch connection and configuration."""
    logger = get_logger(__name__)

    print("🔍 ELASTICSEARCH CONNECTION DEBUG")
    print("=" * 60)

    # 1. Check environment variables
    print("\n1. ENVIRONMENT VARIABLES:")
    es_vars = [
        'ES_HOSTS', 'ELASTICSEARCH_HOSTS', 'ES_USERNAME', 'ES_PASSWORD',
        'ES_API_KEY', 'ES_TIMEOUT', 'ES_MAX_RETRIES', 'ES_VERIFY_CERTS',
        'ES_AC_INDEX', 'ES_VECTOR_INDEX', 'ENABLE_SEARCH'
    ]

    for var in es_vars:
        value = os.getenv(var)
        if value:
            # Mask passwords
            display_value = value if 'PASS' not in var else '***'
            print(f"  {var} = {display_value}")
        else:
            print(f"  {var} = <not set>")

    # 2. Load configuration
    print("\n2. CONFIGURATION LOADING:")
    try:
        config = HybridSearchConfig.from_env()
        print(f"  Service name: {config.service_name}")
        print(f"  Enable search: ENABLE_SEARCH should be checked in settings.py")
        print(f"  Default mode: {config.default_mode}")
        print(f"  Enable fallback: {config.enable_fallback}")

        es_config = config.elasticsearch
        print(f"  ES Hosts: {es_config.hosts}")
        print(f"  ES Normalized hosts: {es_config.normalized_hosts()}")
        print(f"  ES Timeout: {es_config.timeout}s")
        print(f"  ES Max retries: {es_config.max_retries}")
        print(f"  ES Verify certs: {es_config.verify_certs}")
        print(f"  ES AC Index: {es_config.ac_index}")
        print(f"  ES Vector Index: {es_config.vector_index}")

    except Exception as e:
        print(f"  ❌ Failed to load config: {e}")
        return

    # 3. Test client factory
    print("\n3. CLIENT FACTORY TEST:")
    try:
        client_factory = ElasticsearchClientFactory(config)
        print(f"  ✅ Created client factory")
        print(f"  Configured hosts: {client_factory.get_hosts()}")

        # Test health check
        print("\n4. ELASTICSEARCH HEALTH CHECK:")
        health = await client_factory.health_check()
        print(f"  Overall status: {health['status']}")

        for host_result in health['hosts']:
            host = host_result['host']
            status = host_result['status']
            elapsed = host_result.get('elapsed_ms', 'N/A')
            error = host_result.get('error', '')

            if status == 'healthy':
                print(f"  ✅ {host} - {status} ({elapsed}ms)")
            else:
                print(f"  ❌ {host} - {status}")
                if error:
                    print(f"     Error: {error}")

        # Test smoke test
        print("\n5. SMOKE TEST:")
        smoke_result = await client_factory.smoke_test()
        print(f"  Smoke test: {'✅ PASS' if smoke_result else '❌ FAIL'}")

        await client_factory.close()

    except Exception as e:
        print(f"  ❌ Client factory failed: {e}")
        import traceback
        traceback.print_exc()
        return

    # 4. Test hybrid search service
    print("\n6. HYBRID SEARCH SERVICE TEST:")
    try:
        search_service = HybridSearchService(config)
        print(f"  ✅ Created search service")

        # Try to initialize
        try:
            search_service.initialize()
            print(f"  ✅ Search service initialized successfully")

            # Test health check
            health = await search_service.health_check()
            print(f"  Service status: {health.get('status', 'unknown')}")

            if health.get('ac_adapter'):
                ac_status = health['ac_adapter'].get('status', 'unknown')
                print(f"  AC Adapter: {ac_status}")

            if health.get('vector_adapter'):
                vector_status = health['vector_adapter'].get('status', 'unknown')
                print(f"  Vector Adapter: {vector_status}")

        except Exception as e:
            print(f"  ❌ Search service initialization failed: {e}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        print(f"  ❌ Search service creation failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")


if __name__ == "__main__":
    asyncio.run(test_elasticsearch_connection())