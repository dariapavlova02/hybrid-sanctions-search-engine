#!/usr/bin/env python3
"""
Find Ulianova patterns with correct field names
"""

import requests
import json

def find_ulianova_patterns():
    """Find Ulianova patterns using correct field names"""

    print("🔍 FINDING ULIANOVA PATTERNS WITH CORRECT FIELDS")
    print("=" * 60)

    es_host = "http://95.217.84.234:9200"
    query_text = "Liudmyla Ulianova"

    indices = [
        ("ac_patterns", "text", "keyword"),  # pattern field is text with .keyword subfield
        ("ai_service_ac_patterns", "keyword", None)  # pattern field is keyword
    ]

    for index_name, pattern_type, keyword_suffix in indices:
        print(f"\n📋 INDEX: {index_name} (pattern type: {pattern_type})")

        try:
            # Build appropriate query based on field type
            if pattern_type == "text":
                # For text field with keyword subfield
                search_query = {
                    "query": {
                        "bool": {
                            "should": [
                                {"term": {"pattern.keyword": query_text}},
                                {"term": {"pattern.keyword": query_text.lower()}},
                                {"term": {"pattern.keyword": query_text.upper()}},
                                {"match": {"pattern": query_text}},
                                {"wildcard": {"pattern.keyword": f"*{query_text.lower()}*"}},
                                {"wildcard": {"pattern.keyword": f"*{query_text}*"}}
                            ]
                        }
                    },
                    "size": 20,
                    "_source": ["pattern", "tier", "pattern_type", "canonical", "entity_id"]
                }
            else:
                # For keyword field
                search_query = {
                    "query": {
                        "bool": {
                            "should": [
                                {"term": {"pattern": query_text}},
                                {"term": {"pattern": query_text.lower()}},
                                {"term": {"pattern": query_text.upper()}},
                                {"wildcard": {"pattern": f"*{query_text.lower()}*"}},
                                {"wildcard": {"pattern": f"*{query_text}*"}}
                            ]
                        }
                    },
                    "size": 20,
                    "_source": ["pattern", "tier", "pattern_type", "canonical", "entity_id"]
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

                print(f"   🎯 Found {len(hits)} patterns")

                exact_matches = []
                partial_matches = []

                for hit in hits:
                    source = hit.get('_source', {})
                    pattern = source.get('pattern', '')
                    tier = source.get('tier', 'unknown')
                    pattern_type = source.get('pattern_type', 'unknown')
                    canonical = source.get('canonical', '')
                    entity_id = source.get('entity_id', '')
                    score = hit.get('_score', 0)

                    if pattern.lower() == query_text.lower():
                        exact_matches.append((pattern, tier, pattern_type, canonical, entity_id, score))
                    elif query_text.lower() in pattern.lower():
                        partial_matches.append((pattern, tier, pattern_type, canonical, entity_id, score))

                if exact_matches:
                    print(f"   ✅ EXACT MATCHES ({len(exact_matches)}):")
                    for pattern, tier, ptype, canonical, eid, score in exact_matches:
                        print(f"      '{pattern}' (tier: {tier}, type: {ptype}, canonical: '{canonical}', id: {eid}, score: {score})")
                else:
                    print(f"   ❌ No exact matches")

                if partial_matches:
                    print(f"   📝 PARTIAL MATCHES ({len(partial_matches)}):")
                    for pattern, tier, ptype, canonical, eid, score in partial_matches[:10]:
                        print(f"      '{pattern}' (tier: {tier}, type: {ptype}, canonical: '{canonical}', id: {eid}, score: {score})")

            else:
                print(f"   ❌ Search failed: {response.status_code}")
                print(f"      Response: {response.text}")

        except Exception as e:
            print(f"   ❌ Error: {e}")

def test_ac_search_query_format():
    """Test the exact query format used by AC adapter"""

    print(f"\n🔌 TESTING AC ADAPTER QUERY FORMAT")
    print("=" * 60)

    es_host = "http://95.217.84.234:9200"
    query = "Liudmyla Ulianova"

    # This is the exact query format from ElasticsearchACAdapter._build_ac_pattern_queries
    ac_query = {
        "query": {
            "bool": {
                "should": [
                    # Exact pattern match (T0/T1) - highest priority
                    {
                        "term": {
                            "pattern": {
                                "value": query,
                                "boost": 3.0
                            }
                        }
                    }
                ]
            }
        },
        "size": 10,
        "_source": ["pattern", "tier", "pattern_type", "canonical", "entity_id"]
    }

    # Test on both indices
    for index in ["ac_patterns", "ai_service_ac_patterns"]:
        print(f"\n   Testing {index}:")
        try:
            response = requests.post(
                f"{es_host}/{index}/_search",
                json=ac_query,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('hits', [])
                print(f"      Results: {len(hits)}")

                for hit in hits:
                    source = hit.get('_source', {})
                    pattern = source.get('pattern', '')
                    score = hit.get('_score', 0)
                    print(f"         '{pattern}' (score: {score})")
            else:
                print(f"      Error: {response.status_code}")

        except Exception as e:
            print(f"      Error: {e}")

def main():
    find_ulianova_patterns()
    test_ac_search_query_format()

if __name__ == "__main__":
    main()