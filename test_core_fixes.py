#!/usr/bin/env python3
"""
Test core fixes without heavy dependencies
"""
import sys
sys.path.insert(0, 'src')

import requests
from requests.auth import HTTPBasicAuth

def test_es_ac_patterns():
    """Test AC patterns are available in ES"""
    print("🔍 Testing AC patterns in Elasticsearch...")

    # ES connection
    ES_HOST = "95.217.84.234"
    ES_PORT = 9200
    ES_USER = "elastic"
    ES_PASSWORD = "AiServiceElastic2024!"
    ES_INDEX = "ai_service_ac_patterns"

    # Test count
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}/_count"
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

    try:
        response = requests.get(url, auth=auth)
        if response.status_code == 200:
            count = response.json()["count"]
            print(f"Total AC patterns in ES: {count:,}")

            if count > 900000:  # Should be ~942K
                print("✅ AC patterns successfully uploaded!")
            else:
                print(f"⚠️  Lower pattern count than expected: {count}")

        else:
            print(f"❌ ES count request failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ES connection failed: {e}")
        return False

    # Test specific search for our test entity
    search_url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}/_search"

    search_query = {
        "query": {
            "wildcard": {
                "pattern": {
                    "value": "*ковриков*",
                    "case_insensitive": True
                }
            }
        },
        "size": 10
    }

    try:
        response = requests.post(search_url, json=search_query, auth=auth)
        if response.status_code == 200:
            result = response.json()
            total_hits = result["hits"]["total"]["value"]
            print(f"Found {total_hits} patterns for 'ковриков'")

            if total_hits > 0:
                print("Sample patterns:")
                for hit in result["hits"]["hits"][:3]:
                    pattern = hit["_source"]
                    print(f"  - '{pattern['pattern']}' (tier {pattern['tier']}, {pattern['type']})")
                print("✅ Specific entity patterns found!")
                return True
            else:
                print("❌ No patterns found for test entity")
                return False
        else:
            print(f"❌ ES search failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ ES search failed: {e}")
        return False

def test_smartfilter_integration():
    """Test SmartFilter integration with ES"""
    print("\n🔍 Testing SmartFilter AC integration...")

    try:
        # Test the SmartFilter AC search method directly
        from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService

        smart_filter = SmartFilterService(
            language_service=None,
            signal_service=None,
            enable_terrorism_detection=True,
            enable_aho_corasick=True
        )

        # Test AC search
        test_text = "Ковриков Роман Валерійович"
        ac_result = smart_filter.search_aho_corasick(test_text)

        print(f"AC search for '{test_text}':")
        print(f"  Total matches: {ac_result.get('total_matches', 0)}")
        print(f"  Query time: {ac_result.get('query_time_ms', 0)}ms")

        if ac_result.get('total_matches', 0) > 0:
            print("✅ SmartFilter AC integration working!")
            return True
        else:
            print("❌ SmartFilter AC integration failed")
            return False

    except Exception as e:
        print(f"❌ SmartFilter test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_homoglyph_normalization():
    """Test homoglyph normalization fix"""
    print("\n🔍 Testing homoglyph normalization...")

    try:
        from ai_service.layers.patterns.high_recall_ac_generator import TextCanonicalizer

        test_text = "Ковриков Роман Валерійович"
        normalized = TextCanonicalizer.normalize_for_ac(test_text)

        print(f"Original: {test_text}")
        print(f"Normalized: {normalized}")

        # Check if normalization preserves Cyrillic
        if all(ord(char) >= 0x0400 and ord(char) <= 0x04FF or char.isspace() for char in normalized if char.isalpha()):
            print("✅ Homoglyph normalization working correctly!")
            return True
        else:
            print("❌ Normalization still has issues")
            return False

    except Exception as e:
        print(f"❌ Normalization test failed: {e}")
        return False

def main():
    print("🚀 Testing core AI service fixes...")
    print("=" * 50)

    tests = [
        ("AC Patterns in ES", test_es_ac_patterns),
        ("Homoglyph Normalization", test_homoglyph_normalization),
        ("SmartFilter Integration", test_smartfilter_integration)
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        if test_func():
            passed += 1

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All core fixes working! System should be operational.")
        return True
    else:
        print("⚠️  Some issues remain.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)