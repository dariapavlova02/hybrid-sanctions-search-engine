#!/usr/bin/env python3
"""
Test API with fixed settings
"""

import requests
import json

def test_insurance_payment():
    """Test the insurance payment example"""

    url = "http://95.217.84.234:8002/process"

    test_text = "Страх. платіж по договору TRAVEL 68ccdc4cd19cabdee2eaa56c TV0015628 від 20.09.2025 Holoborodko Liudmyla д.р. 12.11.1968 іпн 2515321244 GM293232 OKPO 30929821 7sichey"

    payload = {
        "text": test_text,
        "generate_variants": True,
        "generate_embeddings": False,
        "cache_result": True,
        "options": {
            "flags": {
                "normalization_implementation": "factory",
                "factory_rollout_percentage": 100,
                "strict_stopwords": True,
                "debug_tracing": True,
                "preserve_hyphenated_case": True,
                "fix_initials_double_dot": True,
            }
        }
    }

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    try:
        print(f"Testing: {test_text}")
        print("=" * 80)

        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()

        result = response.json()

        print(f"✅ SUCCESS")
        print(f"Normalized: {result.get('normalized_text', '')}")
        print(f"Tokens: {result.get('tokens', [])}")
        print(f"Language: {result.get('language', '')}")

        # Check decision info
        if 'decision' in result:
            decision = result['decision']
            print(f"Risk level: {decision.get('risk_level', '')}")
            print(f"Risk score: {decision.get('risk_score', 0):.3f}")

            # Check weight improvements
            if 'decision_details' in decision and 'weights_used' in decision['decision_details']:
                weights = decision['decision_details']['weights_used']
                print(f"w_search_exact: {weights.get('w_search_exact', 'N/A')}")

            if 'decision_details' in decision and 'thresholds' in decision['decision_details']:
                thresholds = decision['decision_details']['thresholds']
                print(f"thr_medium: {thresholds.get('thr_medium', 'N/A')}")

        # Expected: should only extract "Holoborodko Liudmyla"
        expected_clean = ["Holoborodko", "Liudmyla"]
        actual_tokens = result.get('tokens', [])

        print(f"\n📊 ANALYSIS:")
        print(f"Expected clean tokens: {expected_clean}")
        print(f"Actual tokens: {actual_tokens}")

        # Check if garbage terms are filtered
        garbage_terms = ["Страх", "TRAVEL", "TV0015628", "GM293232", "OKPO"]
        found_garbage = [token for token in actual_tokens if any(garbage.lower() in token.lower() for garbage in garbage_terms)]

        if found_garbage:
            print(f"❌ Found garbage terms: {found_garbage}")
        else:
            print(f"✅ No garbage terms found")

        return result

    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Error: {e}")
        return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def test_simple_cases():
    """Test simple cases to verify basic functionality"""

    simple_cases = [
        "Прийом оплат клієнтів",
        "Перевезення товарів",
        "Іван Петров",
        "Кухарук В. Р."
    ]

    url = "http://95.217.84.234:8002/process"

    for text in simple_cases:
        payload = {
            "text": text,
            "generate_variants": False,
            "generate_embeddings": False,
            "options": {
                "flags": {
                    "strict_stopwords": True,
                    "debug_tracing": True
                }
            }
        }

        headers = {
            'accept': 'application/json',
            'Content-Type': 'application/json'
        }

        try:
            print(f"\n🧪 Testing: '{text}'")
            response = requests.post(url, headers=headers, json=payload, timeout=15)
            response.raise_for_status()

            result = response.json()
            normalized = result.get('normalized_text', '').strip()
            tokens = result.get('tokens', [])

            print(f"   Normalized: '{normalized}'")
            print(f"   Tokens: {tokens}")

            if not normalized:
                print(f"   ✅ Correctly filtered out")
            else:
                print(f"   ⚠️  Still processed")

        except Exception as e:
            print(f"   ❌ Error: {e}")

if __name__ == "__main__":
    print("🔧 Testing API fixes for garbage terms filtering")
    print("=" * 80)

    # Test weight improvements and main insurance case
    result = test_insurance_payment()

    # Test simple cases
    test_simple_cases()

    print("\n✅ Testing completed!")