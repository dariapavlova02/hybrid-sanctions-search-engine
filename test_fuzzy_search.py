#!/usr/bin/env python3
"""
Test script for fuzzy search functionality.
"""

import asyncio
import json
import time
from src.ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig, fuzzy_match_names

async def test_fuzzy_search():
    """Test fuzzy search for typos and misspellings."""
    print("🔍 Testing Fuzzy Search for Typo Tolerance")
    print("="*60)

    # Test data with typos
    test_cases = [
        ("Порошенк Петро", ["Петро Порошенко", "Володимир Зеленський", "Юлія Тимошенко"]),
        ("Зеленскй Владимир", ["Володимир Зеленський", "Петро Порошенко", "Владимир Путин"]),
        ("Тимошенк Юлия", ["Юлія Тимошенко", "Юлия Тимошенко", "Катерина Шевченко"]),
        ("Катрина", ["Катерина", "Катерина Шевченко", "Екатерина Иванова"]),
        ("Навалный", ["Алексей Навальный", "Михаил Навальный", "Игорь Петров"]),
    ]

    # Initialize fuzzy search service
    config = FuzzyConfig(
        min_score_threshold=0.6,
        high_confidence_threshold=0.85,
        enable_name_fuzzy=True,
        name_boost_factor=1.2
    )

    fuzzy_service = FuzzySearchService(config)

    if not fuzzy_service.enabled:
        print("❌ Fuzzy search not available - install rapidfuzz:")
        print("   pip install rapidfuzz")
        return

    print(f"✅ Fuzzy search service initialized")
    print(f"   Min score threshold: {config.min_score_threshold}")
    print(f"   High confidence threshold: {config.high_confidence_threshold}")
    print("")

    for i, (query, candidates) in enumerate(test_cases, 1):
        print(f"TEST CASE {i}: '{query}'")
        print("-" * 40)

        # Test async fuzzy search
        start_time = time.time()
        results = await fuzzy_service.search_async(query, candidates)
        search_time = (time.time() - start_time) * 1000

        print(f"Query: '{query}'")
        print(f"Candidates: {candidates}")
        print(f"Results ({len(results)} found in {search_time:.2f}ms):")

        if results:
            for j, result in enumerate(results[:3], 1):  # Show top 3
                print(f"  {j}. '{result.matched_text}' - Score: {result.score:.3f} (Algorithm: {result.algorithm})")

            best_match = results[0]
            if best_match.score >= config.high_confidence_threshold:
                print(f"  ✅ HIGH CONFIDENCE match: '{best_match.matched_text}' ({best_match.score:.3f})")
            elif best_match.score >= config.min_score_threshold:
                print(f"  ⚠️  MEDIUM match: '{best_match.matched_text}' ({best_match.score:.3f})")
            else:
                print(f"  ❌ LOW confidence: '{best_match.matched_text}' ({best_match.score:.3f})")
        else:
            print("  ❌ No matches found")

        print("")

    # Test quick fuzzy matching function
    print("TESTING QUICK FUZZY FUNCTION")
    print("-" * 40)

    quick_candidates = [
        "Петро Порошенко", "Володимир Зеленський", "Юлія Тимошенко",
        "Віталій Кличко", "Ігор Коломойський", "Алексей Навальный"
    ]

    quick_query = "Порошенк"
    quick_results = fuzzy_match_names(quick_query, quick_candidates, threshold=0.6, limit=5)

    print(f"Quick search for '{quick_query}':")
    for name, score in quick_results:
        print(f"  '{name}' - {score:.3f}")

    print("")

    # Performance test
    print("PERFORMANCE TEST")
    print("-" * 40)

    large_candidates = []
    for i in range(1000):
        large_candidates.extend([
            f"Іван Петров {i}",
            f"Марія Іванова {i}",
            f"Олександр Коваленко {i}",
            f"Катерина Шевченко {i}",
        ])

    perf_query = "Іван Петров 500"
    start_time = time.time()
    perf_results = await fuzzy_service.search_async(perf_query, large_candidates[:5000])  # Limit for test
    perf_time = (time.time() - start_time) * 1000

    print(f"Performance test: {len(large_candidates[:5000])} candidates")
    print(f"Query: '{perf_query}'")
    print(f"Time: {perf_time:.2f}ms")
    print(f"Results: {len(perf_results)}")
    if perf_results:
        print(f"Best match: '{perf_results[0].matched_text}' - {perf_results[0].score:.3f}")

    print("")

    # Algorithm comparison test
    print("ALGORITHM COMPARISON TEST")
    print("-" * 40)

    try:
        import rapidfuzz
        from rapidfuzz import fuzz

        test_query = "Порошенк Петро"
        test_candidate = "Петро Порошенко"

        algorithms = [
            ("ratio", fuzz.ratio),
            ("partial_ratio", fuzz.partial_ratio),
            ("token_sort_ratio", fuzz.token_sort_ratio),
            ("token_set_ratio", fuzz.token_set_ratio),
        ]

        print(f"Comparing algorithms for '{test_query}' vs '{test_candidate}':")
        for name, algo in algorithms:
            score = algo(test_query, test_candidate) / 100.0
            print(f"  {name:20}: {score:.3f}")

    except ImportError:
        print("rapidfuzz not available for algorithm comparison")

    # Test statistics
    print("")
    print("FUZZY SERVICE STATISTICS")
    print("-" * 40)
    stats = fuzzy_service.get_stats()
    print(json.dumps(stats, indent=2))

if __name__ == "__main__":
    print("🧪 Fuzzy Search Testing Suite")
    print("==============================")
    asyncio.run(test_fuzzy_search())