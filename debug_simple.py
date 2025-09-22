#!/usr/bin/env python3
"""Simple debug script for specific issue."""

import json

def check_diminutives():
    """Check diminutives dictionaries."""

    print("🔍 Checking diminutives dictionaries\n")

    # Load Russian diminutives
    with open("data/diminutives_ru.json", "r", encoding="utf-8") as f:
        ru_diminutives = json.load(f)

    print(f"Russian diminutives count: {len(ru_diminutives)}")

    # Test specific cases
    test_cases = [
        "даша", "даши", "дашка", "дашенька", "дашуля",
        "павел", "павлик", "паша", "пашка", "павловой"
    ]

    print("\n📋 Test cases:")
    for case in test_cases:
        if case in ru_diminutives:
            print(f"✅ {case} → {ru_diminutives[case]}")
        else:
            print(f"❌ {case} not found")

    # Show all Даша variations
    print("\n📝 All Даша variations:")
    for dim, full in ru_diminutives.items():
        if "даш" in dim.lower():
            print(f"  {dim} → {full}")

def check_suffixes():
    """Check suffix patterns."""

    print("\n🔧 Checking suffix patterns\n")

    test_words = ["Павловой", "Юрьевной", "Даши", "Павлова"]

    # Russian surname suffixes
    surname_suffixes = ["ов", "ев", "ин", "ын", "ова", "ева", "ина", "ына", "ой", "ей"]

    # Patronymic suffixes
    patronymic_suffixes = ["ович", "евич", "йович", "ич", "овна", "евна", "ична", "овны", "евны", "ичны"]

    for word in test_words:
        word_lower = word.lower()

        print(f"Word: '{word}'")

        # Check surname suffixes
        surname_matches = [s for s in surname_suffixes if word_lower.endswith(s)]
        print(f"  Surname suffixes: {surname_matches}")

        # Check patronymic suffixes
        patronymic_matches = [s for s in patronymic_suffixes if word_lower.endswith(s)]
        print(f"  Patronymic suffixes: {patronymic_matches}")

        print()

if __name__ == "__main__":
    check_diminutives()
    check_suffixes()