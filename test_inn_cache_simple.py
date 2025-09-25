#!/usr/bin/env python3

"""
Simple test for sanctioned INN cache.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_inn_cache():
    """Test sanctioned INN cache directly."""
    print("🔍 TESTING INN CACHE")
    print("=" * 50)

    try:
        from ai_service.layers.search.sanctioned_inn_cache import get_inn_cache, lookup_sanctioned_inn

        print("✅ Successfully imported INN cache")

        # Initialize cache
        cache = get_inn_cache()
        print(f"📊 Cache loaded: {cache.stats}")

        # Test our specific INN
        test_inn = "782611846337"
        print(f"\n🎯 Testing INN: {test_inn}")

        result = lookup_sanctioned_inn(test_inn)
        if result:
            print(f"✅ FOUND: {result}")
        else:
            print(f"❌ NOT FOUND")

        # Check a few more common INNs from our extraction
        test_inns = ["782611846337", "123456789012", "999999999999"]
        print(f"\n🔍 Testing multiple INNs:")

        for inn in test_inns:
            result = lookup_sanctioned_inn(inn)
            if result:
                print(f"  ✅ {inn}: {result.get('name', 'Unknown')} ({result.get('type', 'unknown')})")
            else:
                print(f"  ❌ {inn}: NOT FOUND")

        print(f"\n📊 Final stats: {cache.get_stats()}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_inn_cache()