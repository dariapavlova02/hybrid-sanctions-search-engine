#!/usr/bin/env python3
"""
Test the suffix logic directly.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_suffix_logic():
    """Test the suffix logic manually."""
    print("Testing suffix logic...")

    # Import the suffix map directly
    from ai_service.layers.normalization.processors.role_classifier import _DIM_SUFFIX_MAP

    print("Russian surname suffixes:")
    ru_suffixes = _DIM_SUFFIX_MAP.get("ru", [])
    for suffix in ru_suffixes:
        print(f"  '{suffix}'")

    # Test token
    test_token = "Павловой"
    token_lower = test_token.lower()

    print(f"\nTesting token: '{test_token}' (lowercase: '{token_lower}')")

    matches = []
    for suffix in ru_suffixes:
        if token_lower.endswith(suffix):
            matches.append(suffix)
            print(f"  ✅ Matches suffix: '{suffix}'")

    if matches:
        print(f"\n✅ SUCCESS: '{test_token}' should be classified as surname (matches: {matches})")
    else:
        print(f"\n❌ FAIL: '{test_token}' doesn't match any surname suffixes")
        print("Checking individual character match:")
        for suffix in ru_suffixes:
            if len(suffix) <= len(token_lower):
                actual_suffix = token_lower[-len(suffix):]
                print(f"  '{suffix}' vs '{actual_suffix}' -> {suffix == actual_suffix}")

    # Test other examples
    test_cases = [
        "Дарья",     # Should NOT match surname suffixes
        "Юрьевна",   # Should match patronymic suffixes
        "Иванов",    # Should match surname suffixes
    ]

    print(f"\nTesting other examples:")
    for test_case in test_cases:
        case_lower = test_case.lower()
        matches = []
        for suffix in ru_suffixes:
            if case_lower.endswith(suffix):
                matches.append(suffix)

        if matches:
            print(f"  '{test_case}' -> surname (matches: {matches})")
        else:
            print(f"  '{test_case}' -> not surname")

if __name__ == "__main__":
    test_suffix_logic()