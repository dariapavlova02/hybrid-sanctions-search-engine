#!/usr/bin/env python3

import json
import subprocess
import time
import os

def test_search_via_api():
    """Test search functionality via HTTP API to bypass Python dependency issues"""

    print("🔍 Testing search functionality via HTTP API")
    print("This bypasses Python import issues by testing the deployed service directly")

    # Test data
    test_cases = [
        ("Порошенко Петро", "Ukrainian name with partial pattern"),
        ("Петро Порошенко", "Ukrainian name reversed order"),
        ("Poroshenko Petro", "Latin transliteration"),
        ("ПОРОШЕНКО", "Surname only uppercase"),
        ("порошенко", "Surname only lowercase"),
        ("John Smith", "English name (should find in general patterns)")
    ]

    print("\n📋 Testing these cases:")
    for text, description in test_cases:
        print(f"  - '{text}' ({description})")

    # First, check if the service is running
    print("\n🔍 Checking if AI service is running on localhost:8000...")

    try:
        result = subprocess.run([
            'curl', '-s', '--connect-timeout', '3',
            'http://localhost:8000/health'
        ], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            print("✅ AI service is responding")
        else:
            print("❌ AI service is not responding - need to start it first")
            print("   Run: ENABLE_SEARCH=true ENABLE_EMBEDDINGS=true uvicorn ai_service.main:app --host 0.0.0.0 --port 8000")
            return False
    except Exception as e:
        print(f"❌ Error checking service: {e}")
        return False

    print("\n🧪 Running search tests...")

    for text, description in test_cases:
        print(f"\n🔍 Testing: '{text}' ({description})")

        # Create test payload
        payload = {
            "text": text
        }

        # Write payload to temp file for curl
        with open('test_payload.json', 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)

        # Make API call with search enabled
        curl_cmd = [
            'curl', '-s', '-X', 'POST',
            'http://localhost:8000/process',
            '-H', 'Content-Type: application/json',
            '-H', 'X-Enable-Search: true',  # Custom header to enable search
            '-H', 'X-Enable-Embeddings: true',  # Custom header to enable embeddings
            '--data-binary', '@test_payload.json'
        ]

        try:
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)

            if result.returncode == 0:
                try:
                    response = json.loads(result.stdout)

                    print(f"  ✅ Response received")
                    print(f"  📝 Normalized: '{response.get('normalized_text', 'N/A')}'")

                    # Check search results
                    search_results = response.get('search_results')
                    if search_results:
                        total_hits = search_results.get('total_hits', 0)
                        search_type = search_results.get('search_type', 'unknown')
                        print(f"  🔍 Search: {total_hits} hits ({search_type})")

                        if total_hits > 0:
                            results = search_results.get('results', [])
                            print(f"  🎯 Top results:")
                            for i, hit in enumerate(results[:3]):
                                if isinstance(hit, dict):
                                    pattern = hit.get('pattern', hit.get('canonical', str(hit)))
                                    score = hit.get('score', hit.get('confidence', 'N/A'))
                                    print(f"    {i+1}. '{pattern}' (score: {score})")
                                else:
                                    print(f"    {i+1}. {hit}")
                    else:
                        print(f"  ⚠️ No search results field in response")

                    # Check embeddings
                    embedding = response.get('embedding')
                    if embedding:
                        print(f"  🔢 Embedding: Generated ({len(embedding)} dimensions)")
                    else:
                        print(f"  ⚠️ No embedding generated")

                    # Check decision
                    decision = response.get('decision')
                    if decision:
                        risk_level = decision.get('risk_level', 'unknown')
                        risk_score = decision.get('risk_score', 'N/A')
                        print(f"  🎯 Decision: {risk_level} (score: {risk_score})")

                except json.JSONDecodeError as e:
                    print(f"  ❌ Invalid JSON response: {e}")
                    print(f"  Raw response: {result.stdout[:200]}...")
                except Exception as e:
                    print(f"  ❌ Error parsing response: {e}")
            else:
                print(f"  ❌ API call failed: {result.stderr}")

        except subprocess.TimeoutExpired:
            print(f"  ❌ Request timed out")
        except Exception as e:
            print(f"  ❌ Error making request: {e}")

        # Clean up temp file
        if os.path.exists('test_payload.json'):
            os.remove('test_payload.json')

        time.sleep(0.5)  # Small delay between requests

    print("\n📊 Test Summary:")
    print("✅ API-based testing completed")
    print("💡 This approach bypasses Python dependency issues")
    print("🔧 If search is not working, check:")
    print("   1. Service started with ENABLE_SEARCH=true")
    print("   2. Elasticsearch is running and accessible")
    print("   3. Patterns are properly uploaded")

    return True

if __name__ == "__main__":
    test_search_via_api()