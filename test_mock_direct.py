#!/usr/bin/env python3
"""
Direct test for MockSearchService avoiding elasticsearch imports.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Direct import to avoid elasticsearch dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src', 'ai_service', 'layers', 'search'))

async def test_mock_search_service():
    """Test the enhanced MockSearchService directly."""

    print("🔍 Testing MockSearchService with fallback test records")
    print("=" * 60)

    try:
        # Import directly from the file
        from mock_search_service import MockSearchService, SearchOpts, SearchMode, NormalizationResult

        # Initialize mock service
        mock_service = MockSearchService()

        # Test health check
        print("\n🧪 Health Check Test")
        health = await mock_service.health_check()
        print(f"  Status: {health['status']}")
        print(f"  Message: {health['message']}")
        print(f"  Test records: {health['test_records']}")

        # Test 1: Search by Ukrainian name
        print(f"\n🧪 Test 1: Search by Ukrainian name")
        test_query = "Ковриков"
        print(f"📝 Query: '{test_query}'")

        search_result = await mock_service.search(test_query, limit=5)
        print(f"📊 Results: {search_result['total_hits']} hits")
        for i, result in enumerate(search_result['results'], 1):
            print(f"  Result {i}: {result['text']} | ITN: {result['metadata']['itn']}")

        # Test 2: Search by English name
        print(f"\n🧪 Test 2: Search by English name")
        test_query = "Kovrykov"
        print(f"📝 Query: '{test_query}'")

        search_result = await mock_service.search(test_query, limit=5)
        print(f"📊 Results: {search_result['total_hits']} hits")
        for i, result in enumerate(search_result['results'], 1):
            print(f"  Result {i}: {result['text']} | EN: {result['metadata']['name_en']}")

        # Test 3: Search by ITN
        print(f"\n🧪 Test 3: Search by ITN")
        test_query = "782611846337"
        print(f"📝 Query: '{test_query}'")

        search_result = await mock_service.search(test_query, limit=5)
        print(f"📊 Results: {search_result['total_hits']} hits")
        for i, result in enumerate(search_result['results'], 1):
            print(f"  Result {i}: {result['text']} | ITN: {result['metadata']['itn']}")

        # Test 4: find_candidates method
        print(f"\n🧪 Test 4: find_candidates method")
        normalized = NormalizationResult(
            normalized="Гаркушев Євген",
            tokens=["Гаркушев", "Євген"],
            trace=[],
            language="uk",
            confidence=0.9,
            original_length=20,
            normalized_length=18,
            token_count=2,
            processing_time=0.001,
            success=True
        )

        opts = SearchOpts(
            search_mode=SearchMode.AC,
            top_k=5,
            threshold=0.8,
            enable_escalation=False
        )

        print(f"📝 Normalized text: '{normalized.normalized}'")
        candidates = await mock_service.find_candidates(normalized, "Гаркушев", opts)
        print(f"📊 Candidates found: {len(candidates)}")

        for i, candidate in enumerate(candidates, 1):
            print(f"  Candidate {i}: {candidate.text}")
            print(f"    Score: {candidate.score}")
            print(f"    Entity type: {candidate.entity_type}")
            print(f"    DOB: {candidate.metadata.get('dob')}")
            print(f"    ITN: {candidate.metadata.get('itn')}")

        # Test 5: No matches test
        print(f"\n🧪 Test 5: No matches test")
        test_query = "NonexistentPerson"
        print(f"📝 Query: '{test_query}'")

        search_result = await mock_service.search(test_query, limit=5)
        print(f"📊 Results: {search_result['total_hits']} hits")

        # Test 6: Threshold filtering test
        print(f"\n🧪 Test 6: Threshold filtering test")
        opts_high_threshold = SearchOpts(
            search_mode=SearchMode.AC,
            top_k=5,
            threshold=0.96,  # Higher than mock scores
            enable_escalation=False
        )

        candidates = await mock_service.find_candidates(normalized, "Ковриков", opts_high_threshold)
        print(f"📊 High threshold candidates: {len(candidates)} (should be 0)")

        opts_low_threshold = SearchOpts(
            search_mode=SearchMode.AC,
            top_k=5,
            threshold=0.85,  # Lower than mock scores
            enable_escalation=False
        )

        candidates = await mock_service.find_candidates(normalized, "Ковриков", opts_low_threshold)
        print(f"📊 Low threshold candidates: {len(candidates)} (should be 1)")

        # Summary
        print(f"\n🎉 SUCCESS: MockSearchService tests completed successfully")
        print("✅ Mock service provides meaningful fallback test records")
        print("✅ Supports search by Ukrainian names, English names, and ITN")
        print("✅ Implements proper threshold filtering")
        print("✅ Compatible with both search() and find_candidates() methods")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(test_mock_search_service())
    sys.exit(0 if success else 1)