#!/usr/bin/env python3

"""
Test fuzzy search functionality on production server.
"""

import json
import requests
import time

def test_fuzzy_search_production():
    """Test fuzzy search on production server."""
    server_url = "http://95.217.84.234:8000"

    print("🔍 PRODUCTION FUZZY SEARCH TEST")
    print("=" * 60)

    test_cases = [
        # Test case 1: Exact match (should work via AC)
        {
            "name": "Exact match",
            "query": "Петро Порошенко",
            "expected": "Should find AC matches"
        },
        # Test case 2: Fuzzy match (should escalate to fuzzy)
        {
            "name": "Fuzzy truncated surname",
            "query": "Порошенк Петро",
            "expected": "Should find via fuzzy search"
        },
        # Test case 3: Fuzzy with typo
        {
            "name": "Fuzzy with typo",
            "query": "Петро Порошенко",  # Deliberate typo
            "expected": "Should find via fuzzy search"
        },
        # Test case 4: Different order
        {
            "name": "Different order",
            "query": "Порошенко Петро",
            "expected": "Should find via AC or fuzzy"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n{i}. TEST: {test_case['name']}")
        print(f"   Query: '{test_case['query']}'")
        print(f"   Expected: {test_case['expected']}")

        try:
            # Make request
            response = requests.post(
                f"{server_url}/process",
                headers={"Content-Type": "application/json"},
                json={"text": test_case["query"]},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                search_results = data.get("search_results", {})
                total_hits = search_results.get("total_hits", 0)
                search_type = search_results.get("search_type", "unknown")
                processing_time = search_results.get("processing_time_ms", 0)

                decision = data.get("decision", {})
                search_contribution = decision.get("decision_details", {}).get("score_breakdown", {}).get("search_contribution", 0.0)

                print(f"   ✅ Response: {response.status_code}")
                print(f"   Total hits: {total_hits}")
                print(f"   Search type: {search_type}")
                print(f"   Processing time: {processing_time}ms")
                print(f"   Search contribution to risk: {search_contribution}")

                if total_hits > 0:
                    print(f"   🎯 SUCCESS - Found {total_hits} matches!")
                    # Show first few matches
                    results = search_results.get("results", [])
                    for j, result in enumerate(results[:3]):
                        doc_id = result.get("doc_id", "")
                        score = result.get("score", 0)
                        search_mode = result.get("search_mode", "unknown")
                        print(f"     Match {j+1}: doc_id={doc_id[:12]}..., score={score:.2f}, mode={search_mode}")
                else:
                    print(f"   ❌ FAILED - No matches found")
                    print(f"   This suggests fuzzy search is not working properly")
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                print(f"   Response: {response.text[:200]}")

        except Exception as e:
            print(f"   ❌ Request failed: {e}")

        # Small delay between requests
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("PRODUCTION TEST COMPLETE")


if __name__ == "__main__":
    test_fuzzy_search_production()