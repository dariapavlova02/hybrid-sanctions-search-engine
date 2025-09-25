#!/usr/bin/env python3

"""
Test MockSearchService directly.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_mock_search():
    """Test MockSearchService fuzzy matching directly."""
    print("🔍 TESTING MOCK SEARCH")
    print("=" * 50)

    try:
        from ai_service.layers.search.mock_search_service import MockSearchService
        from ai_service.contracts.base_contracts import NormalizationResult

        # Create mock search service
        search_service = MockSearchService()
        search_service.initialize()

        print("✅ Successfully initialized MockSearchService")

        # Test simple search method first
        print("\n1. Testing simple search method:")
        query = "Коврико Роман"
        result = await search_service.search(query, limit=10)
        print(f"Query: '{query}'")
        print(f"Results: {result}")

        # Test find_candidates method with different opts
        print("\n2. Testing find_candidates method:")

        # Create a minimal NormalizationResult
        norm_result = NormalizationResult(
            normalized="коврико роман",
            tokens=["коврико", "роман"],
            trace=[],
            language="uk",
            confidence=0.8,
            original_length=len(query),
            normalized_length=len("коврико роман"),
            token_count=2,
            processing_time=0.001,
            success=True
        )

        # Import SearchOpts
        try:
            from ai_service.layers.search.mock_search_service import SearchOpts, SearchMode
        except ImportError:
            # Create minimal SearchOpts
            from dataclasses import dataclass
            from enum import Enum

            class SearchMode(Enum):
                AC = "ac"
                VECTOR = "vector"
                HYBRID = "hybrid"

            @dataclass
            class SearchOpts:
                search_mode: SearchMode = SearchMode.HYBRID
                top_k: int = 10
                threshold: float = 0.5  # Lower threshold for testing

        # Test with different search modes and thresholds
        test_cases = [
            ("AC mode, threshold 0.7", SearchOpts(search_mode=SearchMode.AC, threshold=0.7)),
            ("HYBRID mode, threshold 0.7", SearchOpts(search_mode=SearchMode.HYBRID, threshold=0.7)),
            ("HYBRID mode, threshold 0.5", SearchOpts(search_mode=SearchMode.HYBRID, threshold=0.5)),
            ("HYBRID mode, threshold 0.65", SearchOpts(search_mode=SearchMode.HYBRID, threshold=0.65)),
            ("VECTOR mode, threshold 0.5", SearchOpts(search_mode=SearchMode.VECTOR, threshold=0.5)),
        ]

        for desc, opts in test_cases:
            print(f"\n  Testing {desc}:")
            print(f"    SearchOpts: mode={opts.search_mode}, threshold={opts.threshold}, top_k={opts.top_k}")

            candidates = await search_service.find_candidates(norm_result, query, opts)
            print(f"    Found {len(candidates)} candidates")

            for i, candidate in enumerate(candidates):
                print(f"      {i+1}. {candidate.text} (score: {candidate.score:.3f}, mode: {candidate.search_mode})")

        # Also test exact match
        print("\n3. Testing exact match:")
        exact_query = "Ковриков Роман Валерійович"
        exact_result = await search_service.search(exact_query, limit=10)
        print(f"Query: '{exact_query}'")
        print(f"Results count: {exact_result.get('total_hits', 0)}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_mock_search())