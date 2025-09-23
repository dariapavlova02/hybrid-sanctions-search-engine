#!/usr/bin/env python3
"""
Test patronymic classification.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_patronymic_classification():
    """Test patronymic classification directly."""
    print("Testing patronymic classification...")

    # Import the suffix map directly
    from ai_service.layers.normalization.processors.role_classifier import _PATRONYMIC_SUFFIXES

    print("Russian patronymic suffixes:")
    ru_suffixes = _PATRONYMIC_SUFFIXES.get("ru", [])
    for suffix in ru_suffixes:
        print(f"  '{suffix}'")

    # Test token
    test_token = "Юрьевна"
    token_lower = test_token.lower()

    print(f"\nTesting token: '{test_token}' (lowercase: '{token_lower}')")

    matches = []
    for suffix in ru_suffixes:
        if token_lower.endswith(suffix):
            matches.append(suffix)
            print(f"  ✅ Matches patronymic suffix: '{suffix}'")

    if matches:
        print(f"\n✅ SUCCESS: '{test_token}' should be classified as patronymic (matches: {matches})")
    else:
        print(f"\n❌ FAIL: '{test_token}' doesn't match any patronymic suffixes")

    # Test the role classifier directly
    print("\n" + "="*50)
    print("Testing role classifier directly...")

    try:
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier

        # Create a minimal role classifier instance
        classifier = RoleClassifier({}, {})

        # Test patronymic classification
        result = classifier._classify_patronymic_role("Юрьевна", "ru")
        print(f"_classify_patronymic_role('Юрьевна', 'ru') = '{result}'")

        # Test full personal role classification
        full_result = classifier._classify_personal_role("Юрьевна", "ru")
        print(f"_classify_personal_role('Юрьевна', 'ru') = '{full_result}'")

        if result == "patronymic":
            print("✅ Patronymic classification working correctly")
        else:
            print("❌ Patronymic classification failed")

        if full_result == "patronymic":
            print("✅ Full role classification working correctly")
        else:
            print("❌ Full role classification failed")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

    # Test other patronymics
    print("\n" + "="*30)
    print("Testing other patronymics:")

    test_cases = [
        "Сергеевна",   # Should be patronymic
        "Михайловна",  # Should be patronymic
        "Андреевна",   # Should be patronymic
        "Ивановна",    # Should be patronymic
        "Юрьевной",    # Genitive case - should be patronymic
    ]

    if 'classifier' in locals():
        for test_case in test_cases:
            result = classifier._classify_personal_role(test_case, "ru")
            print(f"  '{test_case}' -> {result}")

if __name__ == "__main__":
    test_patronymic_classification()