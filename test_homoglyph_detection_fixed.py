#!/usr/bin/env python3
"""
Test homoglyph detection after AC pattern fix
"""

import sys
import os
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

from ai_service.layers.normalization.homoglyph_detector import HomoglyphDetector

def test_homoglyph_detection_fixed():
    """Test homoglyph detection with the AC pattern fix"""

    print("🔍 TESTING HOMOGLYPH DETECTION AFTER AC FIX")
    print("=" * 60)

    detector = HomoglyphDetector()

    # Test cases
    test_cases = [
        {
            "name": "Homoglyph attack on Ulianova",
            "input": "Liudмуla Ulianova",  # м (Cyrillic) instead of m, у (Cyrillic) instead of u
            "expected_normalized": "Liudmyla Ulianova",
            "expected_risk": "HIGH",
            "description": "Should detect homoglyphs and normalize to match AC pattern"
        },
        {
            "name": "Clean Ulianova query",
            "input": "Liudmyla Ulianova",  # Clean Latin
            "expected_normalized": "Liudmyla Ulianova",
            "expected_risk": "HIGH",
            "description": "Should match AC pattern directly"
        },
        {
            "name": "Original surname-first format",
            "input": "Ulianova Liudmyla",
            "expected_normalized": "Ulianova Liudmyla",
            "expected_risk": "HIGH",
            "description": "Should match existing AC pattern"
        }
    ]

    print(f"🧪 Running {len(test_cases)} test cases...")

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n--- Test {i}: {test_case['name']} ---")
        print(f"📝 Input: '{test_case['input']}'")
        print(f"📋 Description: {test_case['description']}")

        # Test normalization
        normalized_text, detection_info = detector.secure_normalize(test_case['input'])

        print(f"🔄 Normalized: '{normalized_text}'")
        print(f"📊 Detection info: {detection_info}")

        # Determine risk based on detection
        is_attack = detector.is_likely_attack(test_case['input'])
        risk_level = "HIGH" if is_attack else "LOW"

        print(f"🚨 Risk Level: {risk_level}")
        print(f"🔍 Is likely attack: {is_attack}")

        # Check expectations
        normalized_match = normalized_text == test_case['expected_normalized']
        risk_match = risk_level == test_case['expected_risk']

        if normalized_match and risk_match:
            print("✅ PASS - All expectations met")
        else:
            print("❌ FAIL - Expectations not met")
            if not normalized_match:
                print(f"   Expected normalized: '{test_case['expected_normalized']}'")
                print(f"   Actual normalized: '{normalized_text}'")
            if not risk_match:
                print(f"   Expected risk: {test_case['expected_risk']}")
                print(f"   Actual risk: {risk_level}")

    print(f"\n🏁 Testing complete!")

def main():
    test_homoglyph_detection_fixed()

if __name__ == "__main__":
    main()