#!/usr/bin/env python3

"""
Test homoglyph detection locally.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_homoglyph_detection():
    """Test homoglyph detection on mixed script names."""
    print("🔍 HOMOGLYPH DETECTION TEST")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.homoglyph_detector import HomoglyphDetector

        detector = HomoglyphDetector()

        test_cases = [
            {
                "name": "Clean Latin",
                "text": "Liudmila Ulianova",
                "expected": False
            },
            {
                "name": "Clean Cyrillic",
                "text": "Людмила Ульянова",
                "expected": False
            },
            {
                "name": "Mixed Script Attack",
                "text": "Liudмуlа Uliаnоvа",  # Mixed Latin/Cyrillic
                "expected": True
            },
            {
                "name": "Partial Mixed",
                "text": "Петро Poroshenko",  # Cyrillic + Latin
                "expected": True
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")
            print(f"   Expected homoglyph: {test_case['expected']}")

            try:
                result = detector.detect_homoglyphs(test_case['text'])
                detected = result.get('has_homoglyphs', False)
                confidence = result.get('confidence', 0.0)
                details = result.get('details', [])
                suspicious_chars = result.get('suspicious_chars', [])

                print(f"   🔍 Result: detected={detected}, confidence={confidence:.3f}")

                if suspicious_chars:
                    print(f"   📍 Suspicious chars: {len(suspicious_chars)}")
                    for char_info in suspicious_chars[:3]:  # Show first 3
                        print(f"     {char_info}")

                if detected == test_case['expected']:
                    print(f"   ✅ PASS")
                else:
                    print(f"   ❌ FAIL - Expected {test_case['expected']}, got {detected}")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")

    except Exception as e:
        print(f"❌ Failed to import HomoglyphDetector: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("HOMOGLYPH TEST COMPLETE")


if __name__ == "__main__":
    test_homoglyph_detection()