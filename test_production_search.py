#!/usr/bin/env python3
"""
Test search fix against production API.
"""

import requests
import json

def test_production_search():
    """Test the production API to verify search is working."""
    print("🌐 PRODUCTION API TEST - SEARCH FIX")
    print("=" * 50)

    # Production API endpoint (adjust if needed)
    api_url = "http://95.217.84.234:8000/process"

    test_cases = [
        "Одін Марін Інкорпорейтед",  # Target sanctioned organization
        "Дарья Павлова",             # Regular person
    ]

    for test_text in test_cases:
        print(f"\n🔍 Testing: '{test_text}'")

        payload = {
            "text": test_text,
            "enable_search": True,
            "enable_decision": True
        }

        try:
            response = requests.post(api_url, json=payload, timeout=30)

            if response.status_code == 200:
                result = response.json()

                print(f"✅ Success: {result.get('success', False)}")
                print(f"Normalized: '{result.get('normalized_text', '')}'")

                # Check organizations
                signals = result.get('signals', {})
                organizations = signals.get('organizations', [])
                print(f"Organizations: {len(organizations)}")

                # Check search results
                search_results = result.get('search_results')
                if search_results:
                    total_matches = search_results.get('total_matches', 0)
                    print(f"Search matches: {total_matches}")

                    if total_matches > 0:
                        candidates = search_results.get('candidates', [])
                        print(f"Top candidates:")
                        for i, candidate in enumerate(candidates[:3]):
                            name = candidate.get('name', 'Unknown')
                            score = candidate.get('score', 0)
                            print(f"  {i+1}. {name} (score: {score:.3f})")
                else:
                    print("No search results found")

                # Check decision
                decision = result.get('decision')
                if decision:
                    risk_level = decision.get('risk_level', 'unknown')
                    risk_score = decision.get('risk_score', 0)
                    print(f"Risk: {risk_level.upper()} (score: {risk_score:.3f})")

                    # Check if this is the target organization
                    if "Одін Марін" in test_text:
                        if risk_level.upper() == "HIGH":
                            print("🎉 SUCCESS: Sanctioned organization found with HIGH risk!")
                        else:
                            print(f"⚠️ Organization detected but risk level is {risk_level}, not HIGH")
                            if total_matches == 0:
                                print("   Likely reason: Not found in sanctions database")
                            else:
                                print("   Found matches but confidence may be low")
                else:
                    print("No decision available")

            else:
                print(f"❌ HTTP Error {response.status_code}: {response.text}")

        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    test_production_search()
