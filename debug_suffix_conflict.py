#!/usr/bin/env python3
"""
Debug suffix conflicts between patronymic and surname suffixes.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_suffix_conflict():
    """Debug suffix conflicts."""
    print("Debugging suffix conflicts...")

    from ai_service.layers.normalization.processors.role_classifier import _PATRONYMIC_SUFFIXES, _DIM_SUFFIX_MAP

    ru_patronymic = set(_PATRONYMIC_SUFFIXES.get("ru", []))
    ru_surname = set(_DIM_SUFFIX_MAP.get("ru", []))

    print("Russian patronymic suffixes:")
    for suffix in sorted(ru_patronymic):
        print(f"  '{suffix}'")

    print("\nRussian surname suffixes:")
    for suffix in sorted(ru_surname):
        print(f"  '{suffix}'")

    # Check conflicts
    conflicts = ru_patronymic.intersection(ru_surname)
    print(f"\nConflicting suffixes: {conflicts}")

    # Test specific token
    test_token = "Юрьевной"
    token_lower = test_token.lower()

    print(f"\nTesting '{test_token}' ('{token_lower}'):")

    patronymic_matches = []
    for suffix in ru_patronymic:
        if token_lower.endswith(suffix):
            patronymic_matches.append(suffix)

    surname_matches = []
    for suffix in ru_surname:
        if token_lower.endswith(suffix):
            surname_matches.append(suffix)

    print(f"Patronymic matches: {patronymic_matches}")
    print(f"Surname matches: {surname_matches}")

    # Test the classifier methods directly
    try:
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier

        classifier = RoleClassifier({}, {})

        patronymic_result = classifier._classify_patronymic_role(test_token, "ru")
        surname_result = classifier._classify_surname_by_suffix(test_token, "ru")

        print(f"\nClassifier results:")
        print(f"  _classify_patronymic_role('{test_token}', 'ru') = '{patronymic_result}'")
        print(f"  _classify_surname_by_suffix('{test_token}', 'ru') = '{surname_result}'")

        # Step by step through _classify_personal_role
        print(f"\nStep-by-step _classify_personal_role:")
        print(f"1. Is initial? {classifier._is_initial(test_token)}")
        print(f"2. In given names? {test_token.lower() in classifier.given_names.get('ru', set())}")
        print(f"3. In surnames? {test_token.lower() in classifier.surnames.get('ru', set())}")
        print(f"4. In diminutives? {test_token.lower() in classifier.diminutives.get('ru', set())}")
        print(f"5. Patronymic classification: {patronymic_result}")
        print(f"6. Surname suffix classification: {surname_result}")

        final_result = classifier._classify_personal_role(test_token, "ru")
        print(f"\nFinal result: '{final_result}'")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_suffix_conflict()