#!/usr/bin/env python3

"""
Debug script to test fuzzy search functionality.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_rapidfuzz():
    """Test rapidfuzz availability."""
    print("🔍 FUZZY SEARCH DEBUG")
    print("=" * 60)

    print("\n1. RAPIDFUZZ AVAILABILITY:")
    try:
        import rapidfuzz
        from rapidfuzz import fuzz, process
        print(f"  ✅ rapidfuzz available: version {rapidfuzz.__version__}")

        # Test basic functionality
        test_query = "Порошенк Петро"
        test_candidates = ["Петро Порошенко", "Володимир Зеленський", "Юлія Тимошенко"]

        print(f"\n2. TEST BASIC FUZZY MATCHING:")
        print(f"  Query: '{test_query}'")
        print(f"  Candidates: {test_candidates}")

        for candidate in test_candidates:
            ratio = fuzz.ratio(test_query, candidate)
            partial = fuzz.partial_ratio(test_query, candidate)
            token_sort = fuzz.token_sort_ratio(test_query, candidate)
            token_set = fuzz.token_set_ratio(test_query, candidate)

            print(f"  '{candidate}':")
            print(f"    ratio: {ratio}, partial: {partial}, token_sort: {token_sort}, token_set: {token_set}")

        print(f"\n3. PROCESS EXTRACTION:")
        matches = process.extract(test_query, test_candidates, limit=3, score_cutoff=50)
        print(f"  Best matches: {matches}")

    except ImportError as e:
        print(f"  ❌ rapidfuzz not available: {e}")
        return False

    # Test FuzzySearchService
    print(f"\n4. FUZZYSEARCHSERVICE TEST:")
    try:
        from ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig

        config = FuzzyConfig(
            min_score_threshold=0.65,
            high_confidence_threshold=0.85,
            partial_match_threshold=0.75,
            enable_name_fuzzy=True,
            name_boost_factor=1.2
        )

        fuzzy_service = FuzzySearchService(config)
        print(f"  ✅ FuzzySearchService created")
        print(f"  Enabled: {fuzzy_service.enabled}")

        if fuzzy_service.enabled:
            print(f"  Config: min_threshold={config.min_score_threshold}, high_threshold={config.high_confidence_threshold}")
        else:
            print(f"  ❌ FuzzySearchService disabled")

    except Exception as e:
        print(f"  ❌ FuzzySearchService failed: {e}")
        import traceback
        traceback.print_exc()

    # Test HybridSearchService fuzzy component
    print(f"\n5. HYBRIDSEARCHSERVICE FUZZY TEST:")
    try:
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.config import HybridSearchConfig

        config = HybridSearchConfig.from_env()
        search_service = HybridSearchService(config)

        print(f"  ✅ HybridSearchService created")
        print(f"  Fuzzy service enabled: {search_service._fuzzy_service.enabled}")

        if hasattr(search_service, '_sanctions_loader'):
            print(f"  Sanctions loader available: {search_service._sanctions_loader is not None}")

    except Exception as e:
        print(f"  ❌ HybridSearchService fuzzy test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("DEBUG COMPLETE")
    return True


if __name__ == "__main__":
    test_rapidfuzz()