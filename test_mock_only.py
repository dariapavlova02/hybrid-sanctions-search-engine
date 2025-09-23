#!/usr/bin/env python3
"""
Test only mock search service without other imports.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_mock_only():
    """Test mock search service directly."""
    print("🔍 DIRECT MOCK SEARCH TEST")
    print("="*40)

    try:
        # Import mock directly
        sys.path.insert(0, str(Path(__file__).parent / "src" / "ai_service" / "layers" / "search"))
        from mock_search_service import MockSearchService

        # Create mock service
        mock_service = MockSearchService()
        mock_service.initialize()

        print("✅ Mock search service created and initialized")

        # Test health check
        health = await mock_service.health_check()
        print(f"Health check: {health}")

        # Test search
        search_result = await mock_service.search_similar(
            normalized_text="Иванов Иван Иванович",
            limit=10,
            threshold=0.7
        )

        print(f"Search result: {search_result}")

        # Verify structure
        assert 'query' in search_result
        assert 'results' in search_result
        assert 'total_hits' in search_result
        assert search_result['total_hits'] == 0
        assert search_result['query'] == "Иванов Иван Иванович"
        print("✅ Mock search structure is correct")

        return search_result

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    import asyncio
    result = asyncio.run(test_mock_only())
    if result:
        print(f"\n🎉 SUCCESS: Mock search working correctly!")
        print(f"Search result structure: {list(result.keys())}")