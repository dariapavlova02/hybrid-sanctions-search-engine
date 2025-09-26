#!/usr/bin/env python3
"""
Direct test of permutation generation method
"""

import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

def test_direct_permutation():
    """Test direct call to permutation method"""

    print("🔍 DIRECT PERMUTATION TEST")
    print("=" * 60)

    try:
        from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator

        generator = HighRecallACGenerator()

        # Test _generate_name_permutations directly
        surname = "Ulianova"
        first_name = "Liudmyla"
        patronymic = "Oleksandrivna"

        print(f"Testing permutation generation directly:")
        print(f"  Surname: '{surname}'")
        print(f"  First name: '{first_name}'")
        print(f"  Patronymic: '{patronymic}'")

        # Call the method directly
        permutations = generator._generate_name_permutations(surname, first_name, patronymic, "en")

        print(f"\n📊 Generated {len(permutations)} permutations:")
        target_found = False
        for i, perm in enumerate(permutations, 1):
            print(f"  {i:2d}. '{perm}'")
            if perm == "Liudmyla Ulianova":
                print(f"      🎯 TARGET FOUND!")
                target_found = True

        # Test normalization with preserve_case
        print(f"\n🔤 Normalization test:")
        test_text = "Liudmyla Ulianova"
        normal_case = generator.normalize_for_ac(test_text, preserve_case=False)
        title_case = generator.normalize_for_ac(test_text, preserve_case=True)

        print(f"  Original: '{test_text}'")
        print(f"  Normal:   '{normal_case}'")
        print(f"  Title:    '{title_case}'")

        return target_found

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = test_direct_permutation()

    print(f"\n🎯 RESULT: {'SUCCESS - Target permutation found' if success else 'FAILED - Target permutation not found'}")

if __name__ == "__main__":
    main()