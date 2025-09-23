#!/usr/bin/env python3
"""Test search with different name orders"""

import requests
import json

# Test cases with different word orders
test_cases = [
    "Петро Порошенко",  # firstname lastname (input)
    "Порошенко Петро",  # lastname firstname (what we generated)
    "петро порошенко",  # lowercase version
    "порошенко петро",  # lowercase reverse
]

for test_text in test_cases:
    print(f"\n=== Testing: '{test_text}' ===")

    # Test direct ES search
    print(f"🔍 Direct ES search for: '{test_text}'")
    es_query = {
        "query": {
            "bool": {
                "should": [
                    {"match": {"pattern": {"query": test_text.lower(), "fuzziness": "AUTO"}}},
                    {"wildcard": {"pattern": {"value": f"*{test_text.lower()}*", "case_insensitive": True}}},
                    {"term": {"pattern": test_text.lower()}}
                ],
                "minimum_should_match": 1
            }
        },
        "size": 3
    }

    try:
        response = requests.post(
            "http://95.217.84.234:9200/ai_service_ac_patterns/_search",
            headers={"Content-Type": "application/json"},
            json=es_query,
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])
            print(f"   📊 Direct ES hits: {len(hits)}")
            for hit in hits[:2]:
                source = hit["_source"]
                print(f"   ✅ Found: '{source['pattern']}' -> '{source['canonical']}' (type: {source.get('pattern_type', 'unknown')})")
        else:
            print(f"   ❌ ES error: {response.status_code}")
    except Exception as e:
        print(f"   ❌ ES connection error: {e}")

    # Test AI service
    print(f"🤖 AI Service test for: '{test_text}'")
    try:
        ai_response = requests.post(
            "http://95.217.84.234:8002/process",
            headers={"Content-Type": "application/json"},
            json={"text": test_text},
            timeout=15
        )

        if ai_response.status_code == 200:
            ai_data = ai_response.json()
            search_results = ai_data.get("search_results", {})
            hits = search_results.get("total_hits", 0)
            normalized = ai_data.get("normalized_text", "")
            print(f"   📊 AI Service hits: {hits}")
            print(f"   🔤 Normalized: '{normalized}'")

            if hits > 0:
                for result in search_results.get("results", [])[:2]:
                    print(f"   ✅ Found: '{result.get('pattern', '')}' (confidence: {result.get('confidence', 0)})")
        else:
            print(f"   ❌ AI Service error: {ai_response.status_code}")
    except Exception as e:
        print(f"   ❌ AI Service connection error: {e}")

print("\n=== Summary ===")
print("If direct ES finds patterns but AI service doesn't, there's a search integration issue.")
print("If both find nothing, we need to check pattern generation and upload.")