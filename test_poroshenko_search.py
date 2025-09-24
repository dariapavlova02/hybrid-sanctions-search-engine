#!/usr/bin/env python3
"""
Test for Poroshenko search escalation.

Tests that "Порошенк Петро" (with typo) triggers vector search escalation.
"""

import sys
import os
import asyncio

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_poroshenko_search():
    """Test search escalation for Poroshenko with typo."""

    print("🔍 Testing Poroshenko Search Escalation")
    print("=" * 60)

    try:
        # Enable search for testing
        os.environ['ENABLE_SEARCH'] = 'true'

        from ai_service.core.unified_orchestrator import UnifiedOrchestrator

        orchestrator = UnifiedOrchestrator()

        # Test cases with variations
        test_cases = [
            ("Порошенко Петро Олексійович", "Correct spelling"),
            ("Порошенк Петро", "Typo in surname"),
            ("Парошенко Петро", "Different typo"),
            ("Poroshenko Petro", "Latin script"),
        ]

        for text, description in test_cases:
            print(f"\n🧪 Test: {description}")
            print(f"📝 Input: '{text}'")

            result = await orchestrator.process_async(
                text=text,
                language='uk',
                enable_search=True,
                enable_variants=True,
                enable_embeddings=False
            )

            print(f"\n📊 Results:")
            print(f"  Normalized: {result.normalization.normalized}")

            # Check search results
            if hasattr(result, 'search') and result.search:
                print(f"  Search hits: {result.search.get('total_hits', 0)}")
                print(f"  Search type: {result.search.get('search_type', 'unknown')}")

                # Check if escalation happened
                if 'escalation' in result.search.get('meta', {}):
                    print(f"  ✅ Escalation triggered: {result.search['meta']['escalation']}")
                else:
                    print(f"  ⚠️ No escalation info")

                # Check vector search
                if result.search.get('vector_results'):
                    print(f"  Vector hits: {len(result.search['vector_results'])}")

            else:
                print(f"  ❌ No search results")

            # Check decision
            if hasattr(result, 'decision') and result.decision:
                print(f"  Risk score: {result.decision.get('risk_score', 0):.3f}")
                print(f"  Risk level: {result.decision.get('risk_level', 'unknown')}")

            # Check specific search components
            print(f"\n  Search Details:")

            # Try to get search trace
            if hasattr(result, 'traces') and 'search' in result.traces:
                search_trace = result.traces['search']
                print(f"    AC search: {search_trace.get('ac_hits', 0)} hits")
                print(f"    Vector search: {search_trace.get('vector_hits', 0)} hits")
                print(f"    Escalated: {search_trace.get('escalated', False)}")

        # Now test with MockSearchService directly
        print(f"\n" + "=" * 60)
        print("🧪 Testing MockSearchService directly")

        # Import directly to test
        sys.path.insert(0, 'src/ai_service/layers/search')
        from mock_search_service import MockSearchService, SearchOpts, SearchMode, NormalizationResult

        mock_service = MockSearchService()

        norm_result = NormalizationResult(
            normalized="Порошенк Петро",
            tokens=["Порошенк", "Петро"],
            trace=[],
            language="uk",
            confidence=0.9,
            original_length=20,
            normalized_length=18,
            token_count=2,
            processing_time=0.001,
            success=True
        )

        # Test with different search modes
        for mode in [SearchMode.AC, SearchMode.VECTOR, SearchMode.HYBRID]:
            opts = SearchOpts(
                search_mode=mode,
                top_k=10,
                threshold=0.3,  # Low threshold to catch fuzzy matches
                enable_escalation=True
            )

            print(f"\n  Mode: {mode.value}")
            candidates = await mock_service.find_candidates(norm_result, "Порошенк Петро", opts)
            print(f"    Candidates: {len(candidates)}")

            if candidates:
                for c in candidates:
                    print(f"      - {c.text} (score: {c.score:.3f})")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_poroshenko_search())
    sys.exit(0 if success else 1)