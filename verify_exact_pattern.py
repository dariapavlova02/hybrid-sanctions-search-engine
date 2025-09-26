#!/usr/bin/env python3
"""
Verify if exact pattern exists using different search methods
"""

import requests
import json

def verify_exact_pattern():
    """Verify exact pattern existence"""

    print("🔍 VERIFYING EXACT PATTERN EXISTENCE")
    print("=" * 60)

    es_host = "http://95.217.84.234:9200"
    target_patterns = [
        "Liudmyla Ulianova",
        "Ulianova Liudmyla",
        "liudmyla ulianova",
        "ulianova liudmyla",
        "LIUDMYLA ULIANOVA",
        "ULIANOVA LIUDMYLA"
    ]

    for index in ["ac_patterns", "ai_service_ac_patterns"]:
        print(f"\n📋 INDEX: {index}")

        for pattern in target_patterns:
            print(f"\n   🎯 Searching for: '{pattern}'")

            # Method 1: Wildcard search
            try:
                wildcard_query = {
                    "query": {
                        "wildcard": {
                            "pattern.keyword" if index == "ac_patterns" else "pattern": pattern
                        }
                    },
                    "size": 5,
                    "_source": ["pattern", "canonical", "entity_id", "tier"]
                }

                response = requests.post(
                    f"{es_host}/{index}/_search",
                    json=wildcard_query,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    hits = result.get('hits', {}).get('hits', [])

                    if hits:
                        print(f"      ✅ WILDCARD: Found {len(hits)} matches")
                        for hit in hits:
                            source = hit.get('_source', {})
                            found_pattern = source.get('pattern', '')
                            canonical = source.get('canonical', '')
                            entity_id = source.get('entity_id', '')
                            print(f"         '{found_pattern}' -> '{canonical}' (id: {entity_id})")
                    else:
                        print(f"      ❌ WILDCARD: No matches")

            except Exception as e:
                print(f"      ❌ WILDCARD ERROR: {e}")

            # Method 2: Match query
            try:
                match_query = {
                    "query": {
                        "match": {
                            "pattern": {
                                "query": pattern,
                                "operator": "and"
                            }
                        }
                    },
                    "size": 5,
                    "_source": ["pattern", "canonical", "entity_id", "tier"]
                }

                response = requests.post(
                    f"{es_host}/{index}/_search",
                    json=match_query,
                    timeout=10
                )

                if response.status_code == 200:
                    result = response.json()
                    hits = result.get('hits', {}).get('hits', [])

                    if hits:
                        print(f"      ✅ MATCH: Found {len(hits)} matches")
                        for hit in hits:
                            source = hit.get('_source', {})
                            found_pattern = source.get('pattern', '')
                            if found_pattern.lower() == pattern.lower():
                                print(f"         🎯 EXACT: '{found_pattern}'")
                            else:
                                print(f"         📝 PARTIAL: '{found_pattern}'")
                    else:
                        print(f"      ❌ MATCH: No matches")

            except Exception as e:
                print(f"      ❌ MATCH ERROR: {e}")

def check_sample_ulianova_docs():
    """Check what Ulianova documents actually exist"""

    print(f"\n🔍 CHECKING SAMPLE ULIANOVA DOCUMENTS")
    print("=" * 60)

    es_host = "http://95.217.84.234:9200"

    for index in ["ac_patterns", "ai_service_ac_patterns"]:
        print(f"\n📋 INDEX: {index}")

        # Search for any documents containing both "ulianova" and "liudmyla"
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"wildcard": {"pattern": "*ulianova*"}},
                        {"wildcard": {"pattern": "*liudmyla*"}}
                    ]
                }
            },
            "size": 10,
            "_source": ["pattern", "canonical", "entity_id", "tier", "pattern_type"]
        }

        try:
            response = requests.post(
                f"{es_host}/{index}/_search",
                json=query,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                hits = result.get('hits', {}).get('hits', [])

                print(f"   📊 Found {len(hits)} documents with both names:")
                for hit in hits:
                    source = hit.get('_source', {})
                    pattern = source.get('pattern', '')
                    canonical = source.get('canonical', '')
                    entity_id = source.get('entity_id', '')
                    tier = source.get('tier', '')
                    pattern_type = source.get('pattern_type', '')

                    print(f"      Pattern: '{pattern}'")
                    print(f"         Canonical: '{canonical}'")
                    print(f"         ID: {entity_id}, Tier: {tier}, Type: {pattern_type}")
                    print()

        except Exception as e:
            print(f"   ❌ Error: {e}")

def main():
    verify_exact_pattern()
    check_sample_ulianova_docs()

    print(f"\n🎯 CONCLUSION:")
    print("   If no exact patterns found, but we saw them earlier,")
    print("   there might be encoding/normalization differences")

if __name__ == "__main__":
    main()