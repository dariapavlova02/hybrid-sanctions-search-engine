#!/usr/bin/env python3
"""
Check current configuration
"""

import requests
import json

def check_current_config():
    """Check the current decision configuration"""

    url = "http://95.217.84.234:8002/process"

    # Simple test to get current config from response
    payload = {
        "text": "test",
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
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        response.raise_for_status()

        result = response.json()

        # Check decision details for current config
        if 'decision' in result and 'decision_details' in result['decision']:
            details = result['decision_details']

            print("🔧 CURRENT CONFIGURATION:")
            print("=" * 50)

            if 'weights_used' in details:
                weights = details['weights_used']
                print(f"w_search_exact: {weights.get('w_search_exact', 'N/A')}")
                print(f"w_person: {weights.get('w_person', 'N/A')}")
                print(f"w_org: {weights.get('w_org', 'N/A')}")
                print(f"bonus_exact_match: {weights.get('bonus_exact_match', 'NOT FOUND')}")

            if 'thresholds' in details:
                thresholds = details['thresholds']
                print(f"thr_medium: {thresholds.get('thr_medium', 'N/A')}")
                print(f"thr_high: {thresholds.get('thr_high', 'N/A')}")

            print("\n📊 SERVICE STATUS:")
            print(f"Normalized result: '{result.get('normalized_text', '')}'")
            print(f"Processing time: {result.get('processing_time', 0):.3f}s")

        return result

    except Exception as e:
        print(f"❌ Error checking config: {e}")
        return None

if __name__ == "__main__":
    check_current_config()