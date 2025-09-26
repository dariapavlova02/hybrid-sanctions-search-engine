#!/usr/bin/env python3
"""
Test homoglyph detection on production server
"""

import requests
import json

def test_production_homoglyph_detection():
    """Test homoglyph attack on production server"""

    print("🔍 TESTING PRODUCTION HOMOGLYPH DETECTION")
    print("=" * 60)

    # Production server
    server_url = "http://95.217.84.234:8000"

    # Test case: homoglyph attack
    homoglyph_query = "Liudмуla Ulianova"  # Contains Cyrillic м,у

    print(f"🎯 Testing homoglyph query: '{homoglyph_query}'")
    print("   (Contains Cyrillic characters in 'Liudмуla')")

    try:
        # Test with the production API
        response = requests.post(
            f"{server_url}/process",
            json={"text": homoglyph_query},
            headers={"Content-Type": "application/json"},
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            print(f"\n📊 RESPONSE:")
            print(f"   Status: SUCCESS")
            print(f"   Risk Level: {result.get('risk_level', 'Unknown')}")

            # Check homoglyph detection
            homoglyph_detected = result.get('homoglyph_detected', False)
            print(f"   Homoglyph Detected: {homoglyph_detected}")

            # Check search results
            search_results = result.get('search_results', {})
            candidates = search_results.get('candidates', [])
            print(f"   Candidates Found: {len(candidates)}")

            if candidates:
                print(f"   Top Candidate:")
                top = candidates[0]
                print(f"     Name: {top.get('name', 'N/A')}")
                print(f"     Score: {top.get('score', 'N/A')}")
                print(f"     Type: {top.get('match_type', 'N/A')}")

                # Check if it's the expected Ulianova record
                expected_name = "Ulianova Liudmyla Oleksandrivna"
                if expected_name.lower() in top.get('name', '').lower():
                    print(f"   ✅ EXPECTED TARGET FOUND: {expected_name}")
                    if result.get('risk_level') == 'HIGH':
                        print(f"   ✅ RISK LEVEL IS HIGH - Homoglyph attack detected correctly!")
                        return True
                    else:
                        print(f"   ❌ RISK LEVEL IS {result.get('risk_level')} - Should be HIGH")
                        return False
                else:
                    print(f"   ❌ Expected target not found in top candidate")
            else:
                print(f"   ❌ No candidates found")

            print(f"\n📋 Full response:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")

        return False

    except Exception as e:
        print(f"❌ Error testing production server: {e}")
        return False

def main():
    success = test_production_homoglyph_detection()

    print(f"\n🎯 RESULT:")
    if success:
        print("✅ HOMOGLYPH DETECTION WORKING - HIGH risk detected correctly")
        print("   Our AC generator fix appears to be working!")
    else:
        print("❌ HOMOGLYPH DETECTION FAILED - Risk level not HIGH")
        print("   Need to investigate further or deploy the fix")

if __name__ == "__main__":
    main()