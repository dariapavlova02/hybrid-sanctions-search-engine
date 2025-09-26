#!/usr/bin/env python3
"""
Check AC patterns in production Elasticsearch
"""

import requests
import json

def check_production_ac_patterns():
    """Check what AC patterns are stored in production Elasticsearch"""

    print("🔍 CHECKING PRODUCTION AC PATTERNS")
    print("=" * 60)

    # Production Elasticsearch (assumption based on typical setup)
    es_host = "http://95.217.84.234:9200"  # Common ES port

    # Try different possible index names
    possible_indices = [
        "ac_patterns",
        "ai_service_ac_patterns",
        "watchlist_ac_patterns",
        "patterns"
    ]

    for index_name in possible_indices:
        print(f"\n📋 CHECKING INDEX: {index_name}")
        try:
            # Check if index exists
            response = requests.get(f"{es_host}/{index_name}", timeout=10)

            if response.status_code == 200:
                print(f"   ✅ Index exists: {index_name}")

                # Search for patterns containing Ulianova
                search_query = {
                    "query": {
                        "bool": {
                            "should": [
                                {"wildcard": {"pattern": "*ulianova*"}},
                                {"wildcard": {"pattern": "*Ulianova*"}},
                                {"wildcard": {"pattern": "*liudmyla*"}},
                                {"wildcard": {"pattern": "*Liudmyla*"}}
                            ]
                        }
                    },
                    "size": 50
                }

                search_response = requests.post(
                    f"{es_host}/{index_name}/_search",
                    json=search_query,
                    headers={"Content-Type": "application/json"},
                    timeout=10
                )

                if search_response.status_code == 200:
                    search_result = search_response.json()
                    hits = search_result.get('hits', {}).get('hits', [])

                    print(f"   🎯 Found {len(hits)} matching patterns:")

                    ulianova_patterns = []
                    liudmyla_patterns = []

                    for hit in hits:
                        source = hit.get('_source', {})
                        pattern = source.get('pattern', '')

                        if 'liudmyla' in pattern.lower() and 'ulianova' in pattern.lower():
                            print(f"      🎯 TARGET: '{pattern}'")
                        elif 'ulianova' in pattern.lower():
                            ulianova_patterns.append(pattern)
                        elif 'liudmyla' in pattern.lower():
                            liudmyla_patterns.append(pattern)

                    if ulianova_patterns:
                        print(f"   📝 Ulianova patterns ({len(ulianova_patterns)}):")
                        for pattern in ulianova_patterns[:10]:
                            print(f"      - '{pattern}'")

                    if liudmyla_patterns:
                        print(f"   📝 Liudmyla patterns ({len(liudmyla_patterns)}):")
                        for pattern in liudmyla_patterns[:10]:
                            print(f"      - '{pattern}'")

                    # Check total patterns
                    total_response = requests.get(f"{es_host}/{index_name}/_count", timeout=10)
                    if total_response.status_code == 200:
                        total_count = total_response.json().get('count', 0)
                        print(f"   📊 Total patterns in index: {total_count:,}")

                else:
                    print(f"   ❌ Search failed: {search_response.status_code}")

            elif response.status_code == 404:
                print(f"   ❌ Index not found: {index_name}")
            else:
                print(f"   ❌ Error checking index: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Connection error: {e}")

def main():
    check_production_ac_patterns()

    print(f"\n🎯 NEXT STEPS:")
    print("   1. If no 'Liudmyla Ulianova' patterns found - this confirms the bug")
    print("   2. Need to regenerate AC patterns with Title Case support")
    print("   3. Redeploy updated patterns to Elasticsearch")

if __name__ == "__main__":
    main()