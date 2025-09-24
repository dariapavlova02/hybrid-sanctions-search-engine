#!/usr/bin/env python3
"""
Test fuzzy search integration through API.
"""

import requests
import json
import time

def test_api_with_fuzzy():
    """Test API search with potential fuzzy matching."""
    print("🔍 Testing Fuzzy Search Integration via API")
    print("=" * 60)

    # Test cases with typos that should be caught by fuzzy search
    test_cases = [
        {
            "query": "Порошенк Петро",
            "expected": "Порошенко",
            "description": "Missing letter in surname"
        },
        {
            "query": "Зеленскй Владимир",
            "expected": "Зеленський",
            "description": "Missing letter + wrong first name"
        },
        {
            "query": "Тимошенк Юлия",
            "expected": "Тимошенко",
            "description": "Missing letter in surname"
        },
        {
            "query": "Катрина",  # Typo of Катерина
            "expected": "Катерина",
            "description": "Typo in given name"
        }
    ]

    api_url = "http://localhost:8000/process"

    # Check if server is running
    try:
        health_response = requests.get("http://localhost:8000/health/detailed", timeout=5)
        if health_response.status_code == 200:
            health_data = health_response.json()
            print(f"✅ Server is running - Status: {health_data.get('status', 'unknown')}")
        else:
            print(f"⚠️  Server returned status {health_response.status_code}")
    except Exception as e:
        print(f"❌ Cannot connect to server: {e}")
        print("Please start the server with: uvicorn src.ai_service.main:app --reload")
        return

    print()

    for i, test_case in enumerate(test_cases, 1):
        query = test_case["query"]
        expected = test_case["expected"]
        description = test_case["description"]

        print(f"TEST CASE {i}: {description}")
        print(f"Query: '{query}' (expecting match with '{expected}')")
        print("-" * 50)

        try:
            start_time = time.time()

            # Send request to API
            response = requests.post(
                api_url,
                json={
                    "text": query,
                    "language": "uk",
                    "enable_search": True,
                    "enable_variants": False,
                    "enable_embeddings": False
                },
                timeout=30
            )

            response_time = (time.time() - start_time) * 1000

            if response.status_code == 200:
                result = response.json()

                # Extract search results
                search_results = result.get("search_results", {})
                total_hits = search_results.get("total_hits", 0)
                search_type = search_results.get("search_type", "unknown")
                processing_time = search_results.get("processing_time_ms", 0)

                print(f"✅ Response received in {response_time:.2f}ms")
                print(f"   Search type: {search_type}")
                print(f"   Processing time: {processing_time}ms")
                print(f"   Total hits: {total_hits}")

                if search_results.get("results"):
                    print(f"   Top results:")
                    for j, hit in enumerate(search_results["results"][:3], 1):
                        name = hit.get("name", "Unknown")
                        score = hit.get("score", 0)
                        match_type = hit.get("match_type", "unknown")
                        print(f"     {j}. {name} (score: {score:.3f}, type: {match_type})")

                        # Check if expected name is found
                        if expected.lower() in name.lower():
                            print(f"     🎯 FOUND EXPECTED MATCH: '{expected}' in '{name}'!")

                    # Check if fuzzy search was used
                    best_result = search_results["results"][0]
                    if best_result.get("match_type") == "fuzzy" or "fuzzy" in str(best_result.get("metadata", {})):
                        print(f"   ✅ FUZZY SEARCH USED!")
                    elif total_hits > 0:
                        print(f"   ℹ️  Match found via other method ({search_type})")
                    else:
                        print(f"   ❌ NO MATCHES - Fuzzy search may not be working")
                else:
                    print(f"   ❌ No search results found")

                # Check decision
                decision = result.get("decision", {})
                risk_level = decision.get("risk_level", "unknown")
                risk_score = decision.get("risk_score", 0)
                print(f"   Decision: {risk_level} risk (score: {risk_score:.3f})")

            else:
                print(f"❌ API returned status {response.status_code}")
                print(f"   Response: {response.text}")

        except Exception as e:
            print(f"❌ Request failed: {e}")

        print()

    print("=" * 60)
    print("🎯 FUZZY SEARCH INTEGRATION SUMMARY")
    print("=" * 60)
    print("Expected behavior:")
    print("1. AC search fails to find exact matches")
    print("2. System escalates to fuzzy search")
    print("3. Fuzzy search finds typo matches")
    print("4. Results returned with fuzzy metadata")
    print()
    print("If fuzzy search is working correctly, you should see:")
    print("✅ Expected matches found in results")
    print("✅ 'FUZZY SEARCH USED!' messages")
    print("✅ Match types indicating fuzzy matching")

if __name__ == "__main__":
    test_api_with_fuzzy()