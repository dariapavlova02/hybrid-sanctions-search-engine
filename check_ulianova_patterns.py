#!/usr/bin/env python3
"""
Check generated Ulianova patterns
"""

import json

def check_ulianova_patterns():
    """Check what patterns were generated for Ulianova"""

    print("🔍 CHECKING GENERATED ULIANOVA PATTERNS")
    print("=" * 60)

    try:
        with open('ulianova_patterns.json', 'r', encoding='utf-8') as f:
            data = json.load(f)

        patterns = data.get('patterns', [])
        print(f"📊 Total patterns: {len(patterns)}")

        # Look for patterns containing both names
        liudmyla_ulianova_patterns = []
        ulianova_liudmyla_patterns = []
        other_patterns = []

        for pattern in patterns:
            pattern_text = pattern.get('pattern', '').lower()

            if 'liudmyla' in pattern_text and 'ulianova' in pattern_text:
                if 'liudmyla ulianova' in pattern_text:
                    liudmyla_ulianova_patterns.append(pattern)
                elif 'ulianova liudmyla' in pattern_text:
                    ulianova_liudmyla_patterns.append(pattern)
                else:
                    other_patterns.append(pattern)

        print(f"\n🎯 'Liudmyla Ulianova' patterns: {len(liudmyla_ulianova_patterns)}")
        for pattern in liudmyla_ulianova_patterns:
            tier = pattern.get('tier', 'unknown')
            pattern_type = pattern.get('type', 'unknown')
            print(f"   ✅ Tier {tier}: '{pattern.get('pattern', '')}' ({pattern_type})")

        print(f"\n📝 'Ulianova Liudmyla' patterns: {len(ulianova_liudmyla_patterns)}")
        for pattern in ulianova_liudmyla_patterns:
            tier = pattern.get('tier', 'unknown')
            pattern_type = pattern.get('type', 'unknown')
            print(f"   📋 Tier {tier}: '{pattern.get('pattern', '')}' ({pattern_type})")

        print(f"\n🔄 Other patterns with both names: {len(other_patterns)}")
        for pattern in other_patterns:
            tier = pattern.get('tier', 'unknown')
            pattern_type = pattern.get('type', 'unknown')
            print(f"   🔀 Tier {tier}: '{pattern.get('pattern', '')}' ({pattern_type})")

        # Show all patterns for debugging
        print(f"\n📋 ALL PATTERNS:")
        for i, pattern in enumerate(patterns, 1):
            tier = pattern.get('tier', 'unknown')
            pattern_type = pattern.get('type', 'unknown')
            pattern_text = pattern.get('pattern', '')
            print(f"   {i:2d}. Tier {tier}: '{pattern_text}' ({pattern_type})")

    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    check_ulianova_patterns()

if __name__ == "__main__":
    main()