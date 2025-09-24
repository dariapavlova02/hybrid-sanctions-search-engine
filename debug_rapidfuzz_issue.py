#!/usr/bin/env python3
"""
Debug rapidfuzz issue
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_rapidfuzz_issue():
    """Debug rapidfuzz Candidate issue."""
    print("🔍 DEBUGGING RAPIDFUZZ CANDIDATE ISSUE")
    print("="*40)

    try:
        # Import necessary modules
        from rapidfuzz import process, fuzz
        from ai_service.layers.search.contracts import Candidate, SearchMode

        print("✅ rapidfuzz imported successfully")
        print("✅ Candidate imported successfully")

        # Test basic rapidfuzz functionality
        query = "Петр Порошенко"
        candidates = ["Петр Порошенко", "Петро Порошенко", "Иван Иванов"]

        print(f"\n🔍 Testing basic rapidfuzz with query: '{query}'")

        matches = process.extract(
            query,
            candidates,
            scorer=fuzz.token_sort_ratio,
            limit=5,
            score_cutoff=50
        )

        print(f"rapidfuzz matches: {matches}")

        # Test creating Candidate objects from matches
        print(f"\n🔍 Testing Candidate creation from matches:")

        for i, (match_text, score, index) in enumerate(matches):
            print(f"  Match {i+1}: text='{match_text}', score={score}, index={index}")

            try:
                # Create Candidate correctly
                candidate = Candidate(
                    doc_id=f"test_{i}",
                    score=score / 100.0,
                    text=match_text,
                    entity_type="person",
                    metadata={"source": "rapidfuzz_test"},
                    search_mode=SearchMode.FUZZY,
                    match_fields=["name"],
                    confidence=score / 100.0
                )
                print(f"    ✅ Candidate created successfully: {candidate.doc_id}")

            except Exception as e:
                print(f"    ❌ Error creating Candidate: {e}")

        # Test with different approach - see if we can reproduce the 'name' parameter error
        print(f"\n🔍 Testing problematic Candidate creation:")

        try:
            # This might cause the error if some code tries to pass 'name' parameter
            bad_candidate = Candidate(
                doc_id="test",
                score=0.5,
                text="Test Name",
                entity_type="person",
                metadata={},
                search_mode=SearchMode.FUZZY,
                match_fields=["name"],
                confidence=0.5,
                name="This should cause error"  # This parameter doesn't exist
            )
        except Exception as e:
            print(f"    ✅ Expected error with 'name' parameter: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_rapidfuzz_issue()