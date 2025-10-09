#!/usr/bin/env python
"""
Direct test of sanctioned INN cache lookup for debugging production issue.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.ai_service.layers.search.sanctioned_inn_cache import get_inn_cache, lookup_sanctioned_inn

def test_direct_cache_lookup():
    """Test direct lookup in the INN cache."""

    print("=" * 80)
    print("DIRECT INN CACHE LOOKUP TEST")
    print("=" * 80)

    # Test INN that should be sanctioned
    test_inn = "2839403975"

    # Method 1: Using global cache instance
    print(f"\n1. Testing with get_inn_cache().lookup('{test_inn}')...")
    cache = get_inn_cache()

    # Check if cache is loaded
    stats = cache.get_stats()
    print(f"   Cache stats: {stats['total_inns']} INNs loaded")
    print(f"   Persons: {stats['persons']}, Organizations: {stats['organizations']}")

    # Lookup the INN
    result = cache.lookup(test_inn)
    if result:
        print(f"   ✅ FOUND: {result}")
        print(f"   Name: {result.get('name')}")
        print(f"   Type: {result.get('type')}")
    else:
        print(f"   ❌ NOT FOUND in cache")

    # Method 2: Using convenience function
    print(f"\n2. Testing with lookup_sanctioned_inn('{test_inn}')...")
    result2 = lookup_sanctioned_inn(test_inn)
    if result2:
        print(f"   ✅ FOUND: {result2.get('name')}")
    else:
        print(f"   ❌ NOT FOUND")

    # Method 3: Check raw cache content
    print(f"\n3. Checking raw cache content...")
    if test_inn in cache.cache:
        print(f"   ✅ INN '{test_inn}' exists as key in cache")
        print(f"   Value: {cache.cache[test_inn]}")
    else:
        print(f"   ❌ INN '{test_inn}' NOT a key in cache")
        # Show first few keys to verify format
        print(f"   Sample cache keys: {list(cache.cache.keys())[:5]}")

    # Try normalized lookup
    print(f"\n4. Testing normalized lookup...")
    normalized = str(test_inn).strip()
    print(f"   Normalized INN: '{normalized}' (type: {type(normalized)})")
    if normalized in cache.cache:
        print(f"   ✅ Normalized INN found in cache")
    else:
        print(f"   ❌ Normalized INN not found")

    print("\n" + "=" * 80)

    # Return success/failure
    return result is not None

if __name__ == "__main__":
    success = test_direct_cache_lookup()
    sys.exit(0 if success else 1)