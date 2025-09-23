#!/usr/bin/env python3
"""
Check simple configuration
"""

import requests
import json

def check_simple():
    """Check with simple test"""

    url = "http://95.217.84.234:8002/process"

    payload = {
        "text": "Страх",
        "generate_variants": False,
        "generate_embeddings": False,
        "options": {
            "flags": {
                "debug_tracing": True,
                "strict_stopwords": True
            }
        }
    }

    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()

        result = response.json()

        print(f"Input: 'Страх'")
        print(f"Output: '{result.get('normalized_text', '')}'")
        print(f"Tokens: {result.get('tokens', [])}")
        print(f"Success: {result.get('success', False)}")

        if 'decision' in result:
            decision = result['decision']
            if 'decision_details' in decision:
                details = decision['decision_details']
                if 'weights_used' in details:
                    weights = details['weights_used']
                    print(f"\nWeights:")
                    print(f"  w_search_exact: {weights.get('w_search_exact', 'N/A')}")
                    if 'bonus_exact_match' in weights:
                        print(f"  bonus_exact_match: {weights['bonus_exact_match']}")
                    else:
                        print(f"  bonus_exact_match: NOT FOUND")

                if 'thresholds' in details:
                    thresholds = details['thresholds']
                    print(f"  thr_medium: {thresholds.get('thr_medium', 'N/A')}")

        return result

    except Exception as e:
        print(f"❌ Error: {e}")
        return None

if __name__ == "__main__":
    check_simple()