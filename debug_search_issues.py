#!/usr/bin/env python3
"""
Debug search issues
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def check_homoglyph_detection():
    """Check homoglyph detection for mixed script names."""
    print("🔍 HOMOGLYPH DETECTION TEST")
    print("="*40)

    test_name = "Liudмуlа Uliаnоvа"  # Mixed Latin/Cyrillic

    print(f"Testing: '{test_name}'")

    # Check each character
    for i, char in enumerate(test_name):
        ord_val = ord(char)
        is_latin = ord_val <= 127
        is_cyrillic = 0x0400 <= ord_val <= 0x04FF

        if char != ' ':
            print(f"  [{i}] '{char}' -> ord={ord_val} {'(Latin)' if is_latin else '(Cyrillic)' if is_cyrillic else '(Other)'}")

    # Check ASCII/Unicode mix
    has_ascii = any(ord(c) <= 127 for c in test_name if c != ' ')
    has_unicode = any(ord(c) > 127 for c in test_name if c != ' ')

    print(f"\n📊 Analysis:")
    print(f"  Has ASCII: {has_ascii}")
    print(f"  Has Unicode: {has_unicode}")
    print(f"  Mixed script: {has_ascii and has_unicode}")

    if has_ascii and has_unicode:
        print("  🚨 HOMOGLYPH ATTACK DETECTED!")

        # Try to normalize
        normalized_parts = []
        for word in test_name.split():
            # Simple normalization attempt
            normalized = ""
            for char in word:
                if ord(char) <= 127:  # ASCII
                    normalized += char
                elif char in "мул":  # Common Cyrillic that might be confused
                    if char == "м":
                        normalized += "m"
                    elif char == "у":
                        normalized += "y"
                    elif char == "л":
                        normalized += "l"
                    else:
                        normalized += char
                else:
                    normalized += char
            normalized_parts.append(normalized)

        suggested_normal = " ".join(normalized_parts)
        print(f"  💡 Suggested normalization: '{suggested_normal}'")

async def check_sanctions_data():
    """Check what's actually in sanctions data."""
    print(f"\n🔍 SANCTIONS DATA CHECK")
    print("="*40)

    try:
        from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader

        loader = SanctionsDataLoader()
        dataset = await loader.load_dataset(force_reload=False)

        print(f"📊 Dataset stats:")
        print(f"  Total entries: {dataset.total_entries}")
        print(f"  Unique names: {len(dataset.all_names)}")

        # Search for similar names
        search_terms = [
            "Людмила",
            "Ульянова",
            "Людмила Ульянова",
            "Шевченко",
            "Анатолійович",
            "Анатолий",
            "Andriy"
        ]

        print(f"\n🔍 Searching for similar names:")
        for term in search_terms:
            found_names = [name for name in dataset.all_names if term.lower() in name.lower()]
            if found_names:
                print(f"  '{term}' -> Found {len(found_names)} matches:")
                for name in found_names[:5]:  # Show first 5
                    print(f"    - {name}")
                if len(found_names) > 5:
                    print(f"    ... and {len(found_names) - 5} more")
            else:
                print(f"  '{term}' -> No matches")

    except Exception as e:
        print(f"❌ Failed to check sanctions data: {e}")

def check_normalization_issue():
    """Check the strange normalization issue."""
    print(f"\n🔍 NORMALIZATION ISSUE")
    print("="*40)

    # This shows what went wrong with the second case
    problem_trace = [
        "ШЕВЧЕНКО -> surname",
        "АНДРІЙ -> unknown",
        "АНАТОЛІЙОВИЧ -> patronymic",
        "Шевченко -> surname (duplicate?)",
        "Анатолійович -> patronymic (duplicate?)"
    ]

    print("Problem trace shows duplicated tokens:")
    for trace in problem_trace:
        print(f"  {trace}")

    print("\n💡 Issues:")
    print("  1. АНДРІЙ marked as 'unknown' - should be 'given'")
    print("  2. Duplicated Шевченко/Анатолійович processing")
    print("  3. Mixed case output in signals")

    expected_result = "Шевченко Андрій Анатолійович"
    actual_signals = "ШЕВЧЕНКО андрій Анатолійович ШЕВЧЕНКО Анатолійович"

    print(f"\n  Expected: '{expected_result}'")
    print(f"  Actual signals: '{actual_signals}'")

if __name__ == "__main__":
    import asyncio

    check_homoglyph_detection()
    asyncio.run(check_sanctions_data())
    check_normalization_issue()