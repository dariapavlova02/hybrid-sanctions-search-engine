#!/usr/bin/env python3
"""
Test name declension via API after fixing orchestrator to use factory.
"""

import requests
import json

def test_declension_api():
    """Test name declension through full API."""
    print("🧪 TESTING NAME DECLENSION VIA API")
    print("=" * 50)

    api_url = "http://95.217.84.234:8000/process"

    test_cases = [
        "Павловой Дарьи",    # Should become "Дарья Павлова"
        "Иванова Петра",     # Should become "Петр Иванов"
        "Дарья Павлова",     # Should stay the same
    ]

    for test_text in test_cases:
        print(f"\n🔍 Testing: '{test_text}'")

        payload = {
            "text": test_text,
            "enable_search": False,  # Focus only on normalization
            "enable_decision": False
        }

        try:
            response = requests.post(api_url, json=payload, timeout=15)

            if response.status_code == 200:
                result = response.json()

                normalized = result.get('normalized_text', '')
                language = result.get('language', 'unknown')
                success = result.get('success', False)

                print(f"✅ Success: {success}")
                print(f"🌍 Language: {language}")
                print(f"📝 Normalized: '{normalized}'")

                # Check if declension worked
                if test_text == "Павловой Дарьи" and normalized == "Дарья Павлова":
                    print("🎉 DECLENSION FIXED!")
                elif test_text == normalized:
                    print("✅ No change needed")
                else:
                    print(f"⚠️  Change detected: '{test_text}' -> '{normalized}'")

            else:
                print(f"❌ HTTP Error {response.status_code}")
                print(f"Response: {response.text}")

        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_declension_api()