#!/usr/bin/env python3
"""
Simple test of search integration without elasticsearch.
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

async def test_mock_search():
    """Test mock search service directly."""
    print("🔍 MOCK SEARCH SERVICE TEST")
    print("="*50)

    try:
        from ai_service.layers.search.mock_search_service import MockSearchService

        # Create mock service
        mock_service = MockSearchService()
        mock_service.initialize()

        print("✅ Mock search service created")

        # Test health check
        health = await mock_service.health_check()
        print(f"Health: {health}")

        # Test search
        search_result = await mock_service.search_similar(
            normalized_text="Иванов Иван",
            limit=10,
            threshold=0.7
        )

        print(f"Search result: {search_result}")

        # Verify structure
        assert 'query' in search_result
        assert 'results' in search_result
        assert 'total_hits' in search_result
        assert search_result['total_hits'] == 0
        print("✅ Mock search structure is correct")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

async def test_integration():
    """Test integration through a simple process call."""
    print("\n🔍 INTEGRATION TEST")
    print("="*30)

    try:
        # Direct normalization test
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()
        result = service.normalize_sync(
            text="Иванов Иван Иванович",
            language=None,
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"✅ Normalization works: '{result.normalized}'")
        print(f"  Tokens: {result.tokens}")
        print(f"  Language: {result.language}")
        print(f"  Success: {result.success}")

        return True

    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio

    asyncio.run(test_mock_search())
    asyncio.run(test_integration())