#!/usr/bin/env python3
"""Debug role classification and diminutives issues."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.layers.normalization.processors.role_classifier import RoleClassifier
from ai_service.data.dicts.diminutives_extra import get_diminutives_dicts

def debug_role_classification():
    """Debug the role classification logic."""

    # Initialize role classifier
    classifier = RoleClassifier()

    # Test cases
    test_cases = [
        ("Павловой", "ru"),
        ("Даши", "ru"),
        ("павловой", "ru"),
        ("даши", "ru"),
        ("Павлова", "ru"),
        ("Дарья", "ru"),
    ]

    print("🔍 Debug Role Classification\n")

    for token, lang in test_cases:
        print(f"Token: '{token}' (language: {lang})")

        # Check in different dictionaries
        given_names = classifier.given_names.get(lang, set())
        surnames = classifier.surnames.get(lang, set())
        diminutives = classifier.diminutives.get(lang, set())

        print(f"  In given_names: {token.lower() in given_names}")
        print(f"  In surnames: {token.lower() in surnames}")
        print(f"  In diminutives: {token.lower() in diminutives}")

        # Check suffix classifications
        patronymic_role = classifier._classify_patronymic_role(token, lang)
        surname_by_suffix = classifier._classify_surname_by_suffix(token, lang)

        print(f"  Patronymic check: {patronymic_role}")
        print(f"  Surname by suffix: {surname_by_suffix}")

        # Get final classification
        final_role = classifier._classify_personal_role(token, lang)
        print(f"  ✅ Final role: {final_role}")

        # Check diminutive expansion
        if token.lower() in diminutives:
            expanded = classifier._normalize_diminutive_to_full(token, lang)
            print(f"  📝 Diminutive expansion: {token} → {expanded}")

        print()

def debug_diminutives_dictionary():
    """Debug the diminutives dictionary."""

    print("📚 Debug Diminutives Dictionary\n")

    # Get diminutives
    dim_dicts = get_diminutives_dicts()
    ru_diminutives = dim_dicts.get("ru", {})

    # Test specific cases
    test_cases = ["даша", "даши", "павел", "павлик", "павловой"]

    for case in test_cases:
        if case in ru_diminutives:
            full_form = ru_diminutives[case]
            print(f"✅ {case} → {full_form}")
        else:
            print(f"❌ {case} not found")

    # Show some Дашa variations
    print("\n🔍 All Дашa variations:")
    for dim, full in ru_diminutives.items():
        if "даш" in dim.lower():
            print(f"  {dim} → {full}")

def debug_suffix_logic():
    """Debug the suffix classification logic."""

    print("🔧 Debug Suffix Logic\n")

    from ai_service.layers.normalization.processors.role_classifier import _DIM_SUFFIX_MAP, _PATRONYMIC_SUFFIXES

    ru_surname_suffixes = _DIM_SUFFIX_MAP.get("ru", [])
    ru_patronymic_suffixes = _PATRONYMIC_SUFFIXES.get("ru", [])

    print("Russian surname suffixes:")
    for suffix in ru_surname_suffixes:
        print(f"  -{suffix}")

    print("\nRussian patronymic suffixes:")
    for suffix in ru_patronymic_suffixes:
        print(f"  -{suffix}")

    # Test specific cases
    test_cases = ["Павловой", "Юрьевной", "Даши"]

    print("\n🧪 Suffix matching tests:")
    for case in test_cases:
        case_lower = case.lower()

        matching_surname_suffixes = [s for s in ru_surname_suffixes if case_lower.endswith(s)]
        matching_patronymic_suffixes = [s for s in ru_patronymic_suffixes if case_lower.endswith(s)]

        print(f"  '{case}':")
        print(f"    Surname suffixes: {matching_surname_suffixes}")
        print(f"    Patronymic suffixes: {matching_patronymic_suffixes}")

if __name__ == "__main__":
    debug_role_classification()
    debug_diminutives_dictionary()
    debug_suffix_logic()