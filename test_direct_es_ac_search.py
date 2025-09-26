#!/usr/bin/env python3
"""
Test direct Elasticsearch AC search to see if it works
"""

import requests
import json

def test_direct_es_ac_search():
    """Test direct AC pattern search in Elasticsearch"""

    print("🔍 DIRECT ELASTICSEARCH AC PATTERN SEARCH")
    print("=" * 60)

    es_host = "http://95.217.84.234:9200"
    query_text = "Liudmyla Ulianova"

    # Test both indices
    indices_to_test = ["ac_patterns", "ai_service_ac_patterns"]

    for index_name in indices_to_test:
        print(f"\n📋 TESTING INDEX: {index_name}")

        try:
            # Direct AC pattern search query
            search_query = {
                "query": {
                    "bool": {
                        "should": [
                            # Exact pattern match
                            {"term": {"pattern": query_text}},
                            {"term": {"pattern.keyword": query_text}},
                            # Case variants
                            {"term": {"pattern": query_text.lower()}},
                            {"term": {"pattern": query_text.upper()}},
                            # Wildcard search
                            {"wildcard": {"pattern": f"*{query_text.lower()}*"}},
                            {"wildcard": {"pattern": f"*{query_text}*"}}
                        ]
                    }
                },
                "size": 20,
                "_source": ["pattern", "tier", "pattern_type"]
            }

            response = requests.post(
                f"{es_host}/{index_name}/_search",
                json=search_query,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('hits', [])

                print(f"   🎯 Found {len(hits)} matching patterns:")

                exact_matches = []
                for hit in hits:
                    source = hit.get('_source', {})
                    pattern = source.get('pattern', '')
                    pattern_type = source.get('pattern_type', 'unknown')
                    score = hit.get('_score', 0)

                    if pattern.lower() == query_text.lower():
                        exact_matches.append((pattern, pattern_type, score))
                        print(f"      ✅ EXACT: '{pattern}' (type: {pattern_type}, score: {score})")
                    else:
                        print(f"      📝 PARTIAL: '{pattern}' (type: {pattern_type}, score: {score})")

                if exact_matches:
                    print(f"   🎯 {len(exact_matches)} EXACT MATCHES - AC search should work!")
                else:
                    print(f"   ❌ No exact matches found")

            else:
                print(f"   ❌ Search failed: {response.status_code}")
                print(f"      Response: {response.text}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_ac_search_api():
    """Test AC search via AI service API"""

    print(f"\n🔌 TESTING AC SEARCH VIA AI SERVICE API")
    print("=" * 60)

    try:
        # Test with the actual AI service
        response = requests.post(
            "http://95.217.84.234:8000/process",
            json={
                "text": "Liudmyla Ulianova"  # Direct normalized query
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            print(f"   Status: SUCCESS")
            print(f"   Risk Level: {result.get('risk_level', 'Unknown')}")

            # Check search trace
            search_results = result.get('search_results', {})
            trace = search_results.get('trace', {})
            steps = trace.get('steps', [])

            print(f"   Search Steps: {len(steps)}")
            for step in steps:
                stage = step.get('stage', 'unknown')
                step_type = step.get('step_type', 'unknown')
                results = step.get('results_count', 0)
                print(f"      {stage}: {step_type} -> {results} results")

            candidates = search_results.get('results', [])
            print(f"   Total Candidates: {len(candidates)}")

            if candidates:
                top = candidates[0]
                print(f"   Top Result: {top.get('name', 'N/A')} (score: {top.get('score', 'N/A')})")

        else:
            print(f"   ❌ API Error: {response.status_code}")

    except Exception as e:
        print(f"   ❌ API Error: {e}")

def main():
    test_direct_es_ac_search()
    test_ac_search_api()

    print(f"\n🎯 ANALYSIS:")
    print("   If ES has exact patterns but API returns 0 results:")
    print("   1. AC search might be disabled in config")
    print("   2. Wrong index being used")
    print("   3. AC search query format issue")

if __name__ == "__main__":
    main()