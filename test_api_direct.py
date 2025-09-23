#!/usr/bin/env python3
"""
Test API directly using curl/requests
"""
import requests
import json

def test_api_endpoint():
    """Test the process API endpoint"""
    print("🚀 Testing API endpoint directly...")

    # API endpoint
    api_url = "http://localhost:8080/process"

    # Test data
    test_data = {
        "text": "Ковриков Роман Валерійович",
        "options": {
            "enable_advanced_features": True,
            "generate_variants": False,
            "generate_embeddings": False,
            "enable_search": True
        }
    }

    print(f"Testing with: {test_data['text']}")

    try:
        response = requests.post(api_url, json=test_data, timeout=30)

        if response.status_code == 200:
            result = response.json()

            print(f"✅ API Response received")
            print(f"Success: {result.get('success', False)}")
            print(f"Normalized: {result.get('normalized_text', 'N/A')}")

            # Check search results
            search_results = result.get('search_results', {})
            if search_results:
                total_results = search_results.get('total_hits', 0)
                print(f"Search results: {total_results} hits")

                if total_results > 0:
                    print("✅ Search returning results!")
                    results = search_results.get('results', [])
                    if results:
                        top_result = results[0]
                        print(f"Top result: {top_result.get('entity_name', 'N/A')} (confidence: {top_result.get('confidence', 0):.3f})")
                    return True
                else:
                    print("❌ Search still returning 0 results")
                    return False
            else:
                print("⚠️  No search results in response")
                return False

        else:
            print(f"❌ API request failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False

    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server (not running?)")
        return False
    except Exception as e:
        print(f"❌ API test failed: {e}")
        return False

def test_with_curl():
    """Test using curl command as fallback"""
    print("\n🔧 Testing with curl command...")

    import subprocess

    curl_cmd = [
        'curl', '-X', 'POST',
        'http://localhost:8080/process',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "text": "Ковриков Роман Валерійович",
            "options": {
                "enable_advanced_features": True,
                "generate_variants": False,
                "generate_embeddings": False,
                "enable_search": True
            }
        }),
        '--connect-timeout', '5'
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)

        if result.returncode == 0:
            response = json.loads(result.stdout)
            print("✅ Curl request successful")

            search_results = response.get('search_results', {})
            if search_results and search_results.get('total_hits', 0) > 0:
                print(f"Search results: {search_results['total_hits']} hits")
                print("✅ System working end-to-end!")
                return True
            else:
                print("❌ Still no search results")
                return False
        else:
            print(f"❌ Curl failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"❌ Curl test failed: {e}")
        return False

def main():
    print("🎯 Final API functionality test")
    print("=" * 40)

    # Try requests first
    if test_api_endpoint():
        print("\n🎉 SUCCESS: API working perfectly!")
        return True

    # Fallback to curl
    if test_with_curl():
        print("\n🎉 SUCCESS: API working via curl!")
        return True

    print("\n❌ API tests failed - server may not be running")
    return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)