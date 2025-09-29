#!/usr/bin/env python3
"""
Check if specific company exists in sanctions database.
"""

import requests
import json

def check_sanctions_db():
    """Check what's in the sanctions database."""
    print("🔍 CHECKING SANCTIONS DATABASE")
    print("=" * 50)

    api_url = "http://95.217.84.234:8000/process"

    # Test known patterns that might be in database
    test_cases = [
        # Ukraine-related searches
        "Одін Марін",
        "Марін",
        "Інкорпорейтед", 
        "Odin Marin",
        "Marin",
        "Incorporated",
        
        # Common Russian/Ukrainian patterns
        "Иванов",
        "Петров", 
        "ООО",
        "Газпром",
        
        # Try some partial matches
        "Putin",
        "Путин",
    ]

    for test_text in test_cases:
        print(f"\n🔍 Testing: '{test_text}'")

        payload = {
            "text": test_text,
            "enable_search": True,
            "enable_decision": True
        }

        try:
            response = requests.post(api_url, json=payload, timeout=15)

            if response.status_code == 200:
                result = response.json()

                # Check search results
                search_results = result.get('search_results')
                if search_results:
                    total_matches = search_results.get('total_matches', 0)
                    if total_matches > 0:
                        print(f"✅ Found {total_matches} matches!")
                        candidates = search_results.get('candidates', [])
                        for i, candidate in enumerate(candidates[:3]):
                            name = candidate.get('name', 'Unknown')
                            score = candidate.get('score', 0)
                            print(f"  {i+1}. {name} (score: {score:.3f})")
                        
                        # Check decision
                        decision = result.get('decision')
                        if decision:
                            risk_level = decision.get('risk_level', 'unknown')
                            risk_score = decision.get('risk_score', 0)
                            print(f"     Risk: {risk_level.upper()} (score: {risk_score:.3f})")
                    else:
                        print("❌ No matches found")
                else:
                    print("❌ No search results")

            else:
                print(f"❌ HTTP Error {response.status_code}")

        except Exception as e:
            print(f"❌ Request failed: {e}")

if __name__ == "__main__":
    check_sanctions_db()
