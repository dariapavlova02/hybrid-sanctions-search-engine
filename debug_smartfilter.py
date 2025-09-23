#!/usr/bin/env python3
"""
Debug SmartFilter confidence for simple names
"""

import requests
import json

def test_smartfilter_confidence():
    """Test SmartFilter confidence calculation"""

    url = "http://95.217.84.234:8002/process"

    test_cases = [
        "Дарья Павлова",
        "Кухарук Вікторія",
        "Іван Петров",
        "John Smith",
        "Прийом оплат",  # Should be filtered
        "Перевезення товарів",  # Should be filtered
    ]

    for text in test_cases:
        payload = {
            "text": text,
            "generate_variants": False,
            "generate_embeddings": False,
            "options": {
                "flags": {
                    "debug_tracing": True
                }
            }
        }

        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }

        try:
            print(f"\n🔍 Testing: '{text}'")
            print("=" * 60)

            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()

            result = response.json()

            # Check main results
            normalized = result.get('normalized_text', '').strip()
            tokens = result.get('tokens', [])
            success = result.get('success', False)

            print(f"✅ Normalized: '{normalized}'")
            print(f"🔤 Tokens: {tokens}")
            print(f"📊 Success: {success}")

            # Check decision info
            if 'decision' in result:
                decision = result['decision']
                risk_level = decision.get('risk_level', 'unknown')
                reasons = decision.get('decision_reasons', [])

                print(f"🎯 Risk level: {risk_level}")
                print(f"📝 Reasons: {reasons}")

                # Check SmartFilter details
                if 'decision_details' in decision:
                    details = decision['decision_details']
                    if 'smartfilter' in details:
                        sf = details['smartfilter']
                        print(f"🧠 SmartFilter:")
                        print(f"   should_process: {sf.get('should_process', 'N/A')}")
                        print(f"   confidence: {sf.get('confidence', 'N/A')}")
                        print(f"   complexity: {sf.get('estimated_complexity', 'N/A')}")

                    # If we have smartfilter_should_process directly
                    should_process = details.get('smartfilter_should_process')
                    if should_process is not None:
                        print(f"🧠 SmartFilter should_process: {should_process}")

            # Check if it's a skip
            if risk_level == "skip":
                print("❌ RESULT: SKIPPED by SmartFilter")
            else:
                print("✅ RESULT: PROCESSED")

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Debugging SmartFilter confidence for simple names")
    print("=" * 80)
    test_smartfilter_confidence()
    print("\n✅ Debug completed!")