#!/usr/bin/env python3

import sys
sys.path.append("src")

from ai_service.layers.normalization.processors.role_classifier import RoleClassifier

# Test Ukrainian names loading
try:
    from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES
    print(f"UKRAINIAN_NAMES loaded with {len(UKRAINIAN_NAMES)} entries")

    # Check if Владислав is in the dictionary
    if "Владислав" in UKRAINIAN_NAMES:
        print("✓ 'Владислав' found in UKRAINIAN_NAMES")
        print(f"Data: {UKRAINIAN_NAMES['Владислав']}")
    else:
        print("✗ 'Владислав' NOT found in UKRAINIAN_NAMES")

    # Build name dictionaries like normalization_service does
    dictionaries = {}
    given_names = set()

    for name, props in UKRAINIAN_NAMES.items():
        given_names.add(name)
        if 'variants' in props:
            given_names.update(props['variants'])
        if 'declensions' in props:
            given_names.update(props['declensions'])

    dictionaries['given_names_uk'] = given_names
    print(f"Built given_names_uk with {len(given_names)} names")

    # Check if владислав (lowercase) is in the set
    if "владислав" in {n.lower() for n in given_names}:
        print("✓ 'владислав' (lowercase) found in given_names_uk")
    else:
        print("✗ 'владислав' (lowercase) NOT found in given_names_uk")

    # Test RoleClassifier
    role_classifier = RoleClassifier(dictionaries, {})

    print(f"RoleClassifier given_names: {role_classifier.given_names}")

    # Test classification
    result = role_classifier._classify_personal_role("Владислав", "uk")
    print(f"Classification result for 'Владислав' in 'uk': {result}")

    result = role_classifier._classify_personal_role("владислав", "uk")
    print(f"Classification result for 'владислав' in 'uk': {result}")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()