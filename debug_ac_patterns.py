#!/usr/bin/env python3
"""
Debug AC pattern generation - see what patterns are actually created
"""

import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

def debug_ac_patterns():
    """Debug what patterns AC generator actually creates"""

    print("🔍 DEBUG AC PATTERN GENERATION")
    print("=" * 60)

    try:
        from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator

        generator = HighRecallACGenerator()

        # Test with our problematic name
        test_name = "Ulianova Liudmyla Oleksandrivna"
        print(f"Testing: '{test_name}'")

        # Generate patterns
        patterns = generator.generate_high_recall_patterns(test_name, language="en")

        print(f"\nGenerated {len(patterns)} patterns")

        # Group patterns by type
        pattern_groups = {}
        for pattern in patterns:
            pattern_str = getattr(pattern, 'pattern', str(pattern))
            pattern_type = getattr(pattern, 'pattern_type', 'unknown')

            if pattern_type not in pattern_groups:
                pattern_groups[pattern_type] = []
            pattern_groups[pattern_type].append(pattern_str)

        # Show patterns by type
        for pattern_type, patterns_list in pattern_groups.items():
            print(f"\n📋 {pattern_type.upper()} ({len(patterns_list)} patterns):")
            for i, pattern in enumerate(patterns_list[:10], 1):
                print(f"   {i:2d}. '{pattern}'")
            if len(patterns_list) > 10:
                print(f"   ... and {len(patterns_list) - 10} more")

        # Look for patterns containing both names
        print(f"\n🔍 PATTERNS CONTAINING 'liudmyla' AND 'ulianova':")
        found_both = []
        for pattern in patterns:
            pattern_str = getattr(pattern, 'pattern', str(pattern))
            pattern_type = getattr(pattern, 'pattern_type', 'unknown')
            if 'liudmyla' in pattern_str.lower() and 'ulianova' in pattern_str.lower():
                found_both.append((pattern_str, pattern_type))

        for pattern, pattern_type in found_both:
            print(f"   ✅ '{pattern}' (type: {pattern_type})")

        if not found_both:
            print("   ❌ No patterns found containing both names!")

        return found_both

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return []

def main():
    found_patterns = debug_ac_patterns()

    print(f"\n🎯 RESULT:")
    if found_patterns:
        print(f"✅ Found {len(found_patterns)} patterns with both names")
        for pattern, pattern_type in found_patterns:
            if "Liudmyla Ulianova" == pattern:
                print(f"   🎯 EXACT TITLE CASE MATCH: '{pattern}'")
            elif "liudmyla ulianova" == pattern:
                print(f"   🔤 EXACT LOWERCASE MATCH: '{pattern}'")
    else:
        print("❌ No patterns found - need to investigate further")

if __name__ == "__main__":
    main()