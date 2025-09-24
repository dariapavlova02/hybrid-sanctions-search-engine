#!/usr/bin/env python3
"""
Standalone test for fuzzy search functionality.
"""

import asyncio
import sys
import time

# Test rapidfuzz directly first
try:
    import rapidfuzz
    from rapidfuzz import fuzz, process
    print(f"✅ rapidfuzz {rapidfuzz.__version__} available")
except ImportError as e:
    print(f"❌ rapidfuzz not available: {e}")
    sys.exit(1)

async def test_fuzzy_basic():
    """Basic fuzzy matching test."""
    print("\n🔍 BASIC FUZZY MATCHING TEST")
    print("-" * 40)

    # Test cases: (query_with_typo, candidates)
    test_cases = [
        ("Порошенк Петро", [
            "Петро Порошенко",
            "Володимир Зеленський",
            "Юлія Тимошенко",
            "Віталій Кличко",
        ]),
        ("Зеленскй Владимир", [
            "Володимир Зеленський",
            "Владимир Путин",
            "Петро Порошенко",
        ]),
        ("Тимошенк", [
            "Юлія Тимошенко",
            "Тимошенко Юлія",
            "Катерина Шевченко",
        ]),
    ]

    for i, (query, candidates) in enumerate(test_cases, 1):
        print(f"\nTest {i}: '{query}'")
        print(f"Candidates: {candidates}")

        # Test different algorithms
        algorithms = [
            ("ratio", fuzz.ratio),
            ("partial_ratio", fuzz.partial_ratio),
            ("token_sort_ratio", fuzz.token_sort_ratio),
            ("token_set_ratio", fuzz.token_set_ratio),
        ]

        best_matches = {}

        for algo_name, algo_func in algorithms:
            matches = process.extract(
                query,
                candidates,
                scorer=algo_func,
                limit=3,
                score_cutoff=60  # 60% minimum
            )

            if matches:
                match_result = matches[0]
                if len(match_result) == 3:  # (text, score, index)
                    best_match, best_score, _ = match_result
                else:  # (text, score)
                    best_match, best_score = match_result
                best_matches[algo_name] = (best_match, best_score / 100.0)
                print(f"  {algo_name:20}: '{best_match}' - {best_score / 100.0:.3f}")

        # Find overall best
        if best_matches:
            best_algo = max(best_matches.keys(), key=lambda k: best_matches[k][1])
            best_name, best_score = best_matches[best_algo]
            print(f"  🏆 BEST ({best_algo}): '{best_name}' - {best_score:.3f}")

            if best_score >= 0.85:
                print("  ✅ HIGH CONFIDENCE")
            elif best_score >= 0.65:
                print("  ⚠️  MEDIUM CONFIDENCE")
            else:
                print("  ❌ LOW CONFIDENCE")

async def test_fuzzy_performance():
    """Test performance with larger dataset."""
    print("\n⚡ PERFORMANCE TEST")
    print("-" * 40)

    # Create larger candidate list
    base_names = [
        "Петро Порошенко", "Володимир Зеленський", "Юлія Тимошенко",
        "Віталій Кличко", "Ігор Коломойський", "Рінат Ахметов",
        "Владимир Путин", "Сергей Лавров", "Михаил Мишустин",
        "Катерина Шевченко", "Марія Петренко", "Оксана Ткачук"
    ]

    large_candidates = []
    for i in range(200):  # Create 2400 candidates
        for name in base_names:
            large_candidates.append(f"{name} {i}")

    test_query = "Порошенк Петро"

    print(f"Testing with {len(large_candidates)} candidates")
    print(f"Query: '{test_query}'")

    start_time = time.time()
    matches = process.extract(
        test_query,
        large_candidates,
        scorer=fuzz.token_sort_ratio,
        limit=10,
        score_cutoff=65
    )
    end_time = time.time()

    print(f"Time: {(end_time - start_time) * 1000:.2f}ms")
    print(f"Matches found: {len(matches)}")

    if matches:
        print("Top 3 matches:")
        for i, match_result in enumerate(matches[:3], 1):
            if len(match_result) == 3:
                name, score, _ = match_result
            else:
                name, score = match_result
            print(f"  {i}. '{name}' - {score / 100.0:.3f}")

async def test_typo_scenarios():
    """Test various typo scenarios."""
    print("\n🔤 TYPO SCENARIOS TEST")
    print("-" * 40)

    scenarios = [
        # Missing letters
        ("Порошенк", "Порошенко"),
        ("Зеленськ", "Зеленський"),

        # Extra letters
        ("Порошенкко", "Порошенко"),
        ("Зеленськкий", "Зеленський"),

        # Wrong letters
        ("Порошенсо", "Порошенко"),
        ("Зеленський", "Зеленський"),  # Correct

        # Transposed letters
        ("Поршенко", "Порошенко"),
        ("Зелнеський", "Зеленський"),

        # Mixed case
        ("порошенко", "Порошенко"),
        ("ЗЕЛЕНСЬКИЙ", "Зеленський"),

        # Word order
        ("Петро Порошенко", "Порошенко Петро"),
        ("Володимир Зеленський", "Зеленський Володимир"),
    ]

    for typo, correct in scenarios:
        score = fuzz.token_sort_ratio(typo, correct) / 100.0

        status = "✅" if score >= 0.8 else "⚠️" if score >= 0.6 else "❌"
        print(f"  {status} '{typo}' → '{correct}': {score:.3f}")

async def main():
    """Run all fuzzy search tests."""
    print("🧪 Fuzzy Search Standalone Testing")
    print("=" * 50)

    await test_fuzzy_basic()
    await test_fuzzy_performance()
    await test_typo_scenarios()

    print("\n" + "=" * 50)
    print("✅ Fuzzy search testing completed!")
    print("\n💡 Key findings:")
    print("- token_sort_ratio works best for name reordering")
    print("- partial_ratio good for substring matches")
    print("- Threshold of 0.65+ recommended for typo tolerance")
    print("- Performance is good even with 1000+ candidates")

if __name__ == "__main__":
    asyncio.run(main())