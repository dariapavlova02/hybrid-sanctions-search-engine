#!/usr/bin/env python3

"""
Test fuzzy matching for one specific person.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_one_person():
    """Test fuzzy matching for Ковриков specifically."""
    print("🔍 TESTING ONE PERSON FUZZY MATCHING")
    print("=" * 50)

    try:
        from ai_service.layers.search.mock_search_service import MockSearchService, SearchOpts, SearchMode
        from ai_service.contracts.base_contracts import NormalizationResult

        # Create mock search service
        search_service = MockSearchService()

        # Find the Ковриков record
        kovrikovs = [p for p in search_service._test_persons if 'ковриков' in p.text.lower()]
        print(f"Found {len(kovrikovs)} Ковриков records")

        if kovrikovs:
            target_person = kovrikovs[0]
            print(f"Target person: {target_person.text}")

            # Create a mini search service with just this one person
            search_service._test_persons = [target_person]

            # Test query
            query = "Коврико Роман"
            print(f"Query: '{query}'")

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

            # Test with HYBRID mode
            opts = SearchOpts(search_mode=SearchMode.HYBRID, threshold=0.5, top_k=10)
            print(f"SearchOpts: mode={opts.search_mode}, threshold={opts.threshold}")

            candidates = await search_service.find_candidates(norm_result, query, opts)
            print(f"Found {len(candidates)} candidates")

            for candidate in candidates:
                print(f"  - {candidate.text} (score: {candidate.score:.3f})")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_one_person())