#!/usr/bin/env python3
"""
Test if homoglyph normalization fix works
"""
import sys
sys.path.insert(0, 'src')

from ai_service.layers.patterns.high_recall_ac_generator import TextCanonicalizer

def test_normalization():
    # Test original problematic text
    test_text = "Ковриков Роман Валерійович"

    print("=== Testing AC Pattern Normalization Fix ===")
    print(f"Original: {test_text}")

    # Test new normalization
    normalized = TextCanonicalizer.normalize_for_ac(test_text)
    print(f"Normalized: {normalized}")

    # Check character codes
    print("\nCharacter analysis:")
    for i, char in enumerate(normalized):
        print(f"  {i}: '{char}' -> U+{ord(char):04X}")

    # Test if it matches API normalization result
    expected = "Ковриков Роман Валерійович"  # From API test
    if normalized == expected:
        print("✅ SUCCESS: Normalization now matches API result!")
        return True
    else:
        print("❌ MISMATCH: Normalization still differs from API")
        print(f"   Expected: {expected}")
        print(f"   Got:      {normalized}")
        return False

if __name__ == "__main__":
    success = test_normalization()
    sys.exit(0 if success else 1)