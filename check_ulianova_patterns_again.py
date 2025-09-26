#!/usr/bin/env python3
"""
Check if Liudmyla Ulianova pattern was generated in the new file
"""

import json

def check_ulianova_patterns_again():
    """Check what patterns were generated for Ulianova - new version"""

    print("🔍 CHECKING NEW GENERATED ULIANOVA PATTERNS")
    print("=" * 60)

    try:
        with open('ulianova_patterns_test_again.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        patterns = data.get('patterns', [])
        print(f"📊 Total patterns: {len(patterns)}")

        # Look for our specific target pattern
        target_pattern = "Liudmyla Ulianova"
        found = []

        for pattern in patterns:
            pattern_text = pattern.get('pattern', '')
            if pattern_text == target_pattern:
                found.append(pattern)

        if found:
            print(f"\n✅ FOUND TARGET PATTERN: '{target_pattern}' ({len(found)} matches)")
            for pattern in found:
                tier = pattern.get('tier', 'unknown')
                pattern_type = pattern.get('type', 'unknown')
                hints = pattern.get('hints', {})
                print(f"   🎯 Tier {tier}: '{pattern.get('pattern', '')}' ({pattern_type})")
                print(f"      hints: {hints}")
        else:
            print(f"\n❌ TARGET PATTERN NOT FOUND: '{target_pattern}'")

        # Also check for the reversed pattern to make sure it still exists
        reversed_pattern = "Ulianova Liudmyla"
        reversed_found = [p for p in patterns if p.get('pattern', '') == reversed_pattern]

        if reversed_found:
            print(f"\n✅ Original pattern still exists: '{reversed_pattern}' ({len(reversed_found)} matches)")
            for pattern in reversed_found:
                tier = pattern.get('tier', 'unknown')
                pattern_type = pattern.get('type', 'unknown')
                hints = pattern.get('hints', {})
                print(f"   📋 Tier {tier}: '{pattern.get('pattern', '')}' ({pattern_type})")
                print(f"      hints: {hints}")

        # Show tier 2 partial matches specifically
        tier2_partial = [p for p in patterns if p.get('tier', 0) == 2 and p.get('type', '') == 'partial_match']
        print(f"\n📋 All Tier 2 partial matches: {len(tier2_partial)}")
        for pattern in tier2_partial:
            hints = pattern.get('hints', {})
            print(f"   🔹 '{pattern.get('pattern', '')}' (hints: {hints})")

    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    check_ulianova_patterns_again()

if __name__ == "__main__":
    main()