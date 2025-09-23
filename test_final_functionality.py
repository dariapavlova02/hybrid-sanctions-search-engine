#!/usr/bin/env python3
"""
Final test to verify the complete system works end-to-end
Testing:
1. SmartFilter with real ES AC patterns
2. Hybrid search with homoglyph-fixed patterns
3. Full normalization pipeline
"""
import sys
sys.path.insert(0, 'src')

import json
import time
from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService
from ai_service.layers.search.hybrid_search_service import HybridSearchService

def test_smartfilter():
    """Test SmartFilter with real ES AC patterns"""
    print("🔍 Testing SmartFilter with real ES AC patterns...")

    test_text = "Ковриков Роман Валерійович"

    # Initialize SmartFilter
    smart_filter = SmartFilterService(
        language_service=None,
        signal_service=None,
        enable_terrorism_detection=True,
        enable_aho_corasick=True
    )

    # Test should_process_text
    result = smart_filter.should_process_text(test_text)

    print(f"Text: {test_text}")
    print(f"Should process: {result.should_process}")
    print(f"Confidence: {result.confidence}")
    print(f"AC matches found: {result.signal_details.get('aho_corasick_matches', {}).get('total_matches', 0)}")

    if result.should_process and result.signal_details.get('aho_corasick_matches', {}).get('total_matches', 0) > 0:
        print("✅ SmartFilter working correctly!")
        return True
    else:
        print("❌ SmartFilter still has issues")
        return False

def test_hybrid_search():
    """Test hybrid search with homoglyph-fixed patterns"""
    print("\n🔍 Testing Hybrid Search...")

    try:
        # Initialize hybrid search service
        search_service = HybridSearchService()

        # Test search for known entity
        test_query = "Ковриков Роман Валерійович"

        results = search_service.search(
            query=test_query,
            search_type="hybrid",
            max_results=10
        )

        print(f"Query: {test_query}")
        print(f"Total results: {len(results)}")
        print(f"AC results: {sum(1 for r in results if r.get('search_type') == 'ac')}")
        print(f"Vector results: {sum(1 for r in results if r.get('search_type') == 'vector')}")

        if len(results) > 0:
            print("✅ Hybrid search working!")
            print(f"Top result: {results[0].get('entity_name', 'N/A')} (confidence: {results[0].get('confidence', 0):.3f})")
            return True
        else:
            print("❌ Hybrid search returning empty results")
            return False

    except Exception as e:
        print(f"❌ Hybrid search failed with error: {e}")
        return False

def test_ac_patterns_direct():
    """Test AC patterns directly via ES"""
    print("\n🔍 Testing AC patterns directly...")

    import requests
    from requests.auth import HTTPBasicAuth

    # ES connection
    ES_HOST = "95.217.84.234"
    ES_PORT = 9200
    ES_USER = "elastic"
    ES_PASSWORD = "AiServiceElastic2024!"
    ES_INDEX = "ai_service_ac_patterns"

    # Test search
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}/_search"
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

    search_query = {
        "query": {
            "wildcard": {
                "pattern": {
                    "value": "*ковриков*",
                    "case_insensitive": True
                }
            }
        },
        "size": 5
    }

    try:
        response = requests.post(url, json=search_query, auth=auth)
        if response.status_code == 200:
            result = response.json()
            total_hits = result["hits"]["total"]["value"]
            print(f"Direct ES search found {total_hits} patterns for 'ковриков'")

            if total_hits > 0:
                print("Sample patterns:")
                for hit in result["hits"]["hits"][:3]:
                    pattern = hit["_source"]
                    print(f"  - {pattern['pattern']} (tier {pattern['tier']}, {pattern['type']})")
                print("✅ AC patterns available in ES!")
                return True
            else:
                print("❌ No AC patterns found")
                return False
        else:
            print(f"❌ ES request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ES connection failed: {e}")
        return False

def main():
    print("🚀 Testing complete AI service functionality after fixes...")
    print("=" * 60)

    success_count = 0
    total_tests = 3

    # Test 1: SmartFilter
    if test_smartfilter():
        success_count += 1

    # Test 2: AC patterns direct
    if test_ac_patterns_direct():
        success_count += 1

    # Test 3: Hybrid search
    if test_hybrid_search():
        success_count += 1

    print(f"\n📊 Test Results: {success_count}/{total_tests} tests passed")

    if success_count == total_tests:
        print("🎉 All systems working correctly! The AI service is now operational.")
        return True
    else:
        print("⚠️  Some systems still need attention.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)