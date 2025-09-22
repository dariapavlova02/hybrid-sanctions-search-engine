#!/usr/bin/env python3
"""Fix diminutives dictionary by adding case forms."""

import json
from typing import Dict, Set

def generate_case_forms(name: str) -> Set[str]:
    """Generate case forms for Russian diminutive names."""

    forms = {name}  # nominative

    if name.endswith('а'):
        base = name[:-1]
        forms.update({
            base + 'и',    # genitive: Даша → Даши
            base + 'е',    # dative: Даша → Даше
            base + 'у',    # accusative: Даша → Дашу
            base + 'ой',   # instrumental: Даша → Дашой
            base + 'е',    # prepositional: Даша → Даше
        })
    elif name.endswith('я'):
        base = name[:-1]
        forms.update({
            base + 'и',    # genitive: Таня → Тани
            base + 'е',    # dative: Таня → Тане
            base + 'ю',    # accusative: Таня → Таню
            base + 'ей',   # instrumental: Таня → Таней
            base + 'е',    # prepositional: Таня → Тане
        })
    elif name.endswith('ь'):
        base = name[:-1]
        forms.update({
            base + 'и',    # genitive: Игорь → Игори (редко, но бывает)
            base + 'ю',    # accusative: Игорь → Игорю
            base + 'ем',   # instrumental: Игорь → Игорем
            base + 'е',    # prepositional: Игорь → Игоре
        })
    else:
        # Мужские имена на согласный
        forms.update({
            name + 'а',    # genitive: Коля → Коли
            name + 'е',    # dative: Коля → Коле
            name + 'у',    # accusative: Коля → Колю
            name + 'ой',   # instrumental: Коля → Колей
            name + 'е',    # prepositional: Коля → Коле
        })

    return forms

def add_case_forms_to_diminutives():
    """Add case forms to diminutives dictionary."""

    print("📝 Adding case forms to diminutives dictionary...")

    # Load existing dictionary
    with open("data/diminutives_ru.json", "r", encoding="utf-8") as f:
        diminutives = json.load(f)

    original_count = len(diminutives)
    print(f"Original entries: {original_count}")

    # Get base diminutives (only those that map to different full names)
    base_diminutives = {}
    for dim, full in diminutives.items():
        if dim != full:  # Only real diminutives, not full names
            base_diminutives[dim] = full

    print(f"Base diminutives: {len(base_diminutives)}")

    # Generate case forms for each diminutive
    added_count = 0
    for diminutive, full_name in base_diminutives.items():
        case_forms = generate_case_forms(diminutive)

        for case_form in case_forms:
            if case_form != diminutive and case_form not in diminutives:
                diminutives[case_form] = full_name
                added_count += 1

    print(f"Added {added_count} case forms")
    print(f"Total entries: {len(diminutives)}")

    # Save updated dictionary
    with open("data/diminutives_ru.json", "w", encoding="utf-8") as f:
        json.dump(diminutives, f, ensure_ascii=False, indent=2, sort_keys=True)

    print("✅ Updated diminutives dictionary saved")

    # Test our specific cases
    test_cases = ["даши", "дашу", "даше", "дашой"]
    print(f"\n🧪 Testing specific cases:")
    for case in test_cases:
        if case in diminutives:
            print(f"✅ {case} → {diminutives[case]}")
        else:
            print(f"❌ {case} not found")

if __name__ == "__main__":
    add_case_forms_to_diminutives()