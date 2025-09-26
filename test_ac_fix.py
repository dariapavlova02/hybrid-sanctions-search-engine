#!/usr/bin/env python3
"""
Test AC generator fix for Title Case permutations
"""

import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

def test_ac_generator_title_case():
    """Test that AC generator now produces both Title Case and lowercase patterns"""

    print("🔧 TESTING AC GENERATOR FIX")
    print("=" * 60)

    try:
        from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator

        generator = HighRecallACGenerator()

        # Test with our problematic name
        test_name = "Ulianova Liudmyla Oleksandrivna"
        target_pattern = "Liudmyla Ulianova"

        print(f"Testing: '{test_name}'")
        print(f"Looking for: '{target_pattern}'")

        # Generate patterns
        patterns = generator.generate_high_recall_patterns(test_name, language="en")

        print(f"\nGenerated {len(patterns)} patterns")

        # Search for our target patterns
        title_case_found = []
        lowercase_found = []

        for pattern in patterns:
            pattern_str = getattr(pattern, 'pattern', str(pattern))
            pattern_type = getattr(pattern, 'pattern_type', 'unknown')

            if target_pattern.lower() in pattern_str.lower():
                if target_pattern == pattern_str:
                    title_case_found.append((pattern_str, pattern_type))
                elif target_pattern.lower() == pattern_str.lower():
                    lowercase_found.append((pattern_str, pattern_type))

        print(f"\n🎯 TITLE CASE MATCHES ({len(title_case_found)}):")
        for pattern, pattern_type in title_case_found[:10]:
            print(f"   ✅ '{pattern}' (type: {pattern_type})")

        print(f"\n🔤 LOWERCASE MATCHES ({len(lowercase_found)}):")
        for pattern, pattern_type in lowercase_found[:10]:
            print(f"   ✅ '{pattern}' (type: {pattern_type})")

        # Results
        if title_case_found:
            print(f"\n✅ SUCCESS: Found {len(title_case_found)} Title Case patterns!")
            print("   Homoglyph attacks should now be detected properly.")
        else:
            print(f"\n❌ FAILURE: No Title Case patterns found.")

        if lowercase_found:
            print(f"✅ BACKWARD COMPATIBILITY: Found {len(lowercase_found)} lowercase patterns.")
        else:
            print(f"⚠️  WARNING: No lowercase patterns found.")

        return len(title_case_found) > 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_ac_generator_title_case()

    print(f"\n🎯 SUMMARY:")
    if success:
        print("✅ AC Generator fix SUCCESSFUL")
        print("   • Title Case permutations are generated")
        print("   • Homoglyph detection should now work")
        print("   • Ready for production testing")
    else:
        print("❌ AC Generator fix FAILED")
        print("   • Title Case permutations not generated")
        print("   • Further debugging needed")

if __name__ == "__main__":
    main()