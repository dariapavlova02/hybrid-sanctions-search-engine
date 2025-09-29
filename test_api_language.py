#!/usr/bin/env python3
"""
Test API language detection for Ukrainian names.
"""

import requests
import json

def test_api_language():
    """Test API language detection."""
    print("🌐 API LANGUAGE DETECTION TEST")
    print("=" * 50)

    api_url = "http://95.217.84.234:8000/process"

    payload = {
        "text": "Петра Порошенка",
        "enable_search": False,
        "enable_decision": False
    }

    try:
        response = requests.post(api_url, json=payload, timeout=15)

        if response.status_code == 200:
            result = response.json()

            print(f"✅ Success: {result.get('success', False)}")
            print(f"🌍 Language: {result.get('language', 'unknown')}")
            print(f"📝 Normalized: '{result.get('normalized_text', '')}'")

            # Show trace for debugging
            tokens = result.get('tokens', [])
            print(f"🔍 Tokens: {tokens}")

            if 'trace' in result:
                for token in result['trace']:
                    if token.get('token') == 'Порошенка':
                        print(f"\n🎯 Порошенка trace:")
                        print(f"   Role: {token.get('role')}")
                        print(f"   Output: {token.get('output')}")
                        print(f"   Notes: {token.get('notes', '')[:150]}...")

        else:
            print(f"❌ HTTP Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_api_language()