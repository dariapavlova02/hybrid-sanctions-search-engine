#!/usr/bin/env python3
"""
Debug name component extraction and permutation generation
"""

import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

def test_name_components():
    """Test name component extraction"""

    print("🔍 DEBUG NAME COMPONENT EXTRACTION")
    print("=" * 60)

    try:
        from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator

        generator = HighRecallACGenerator()

        # Test with our name
        test_name = "Ulianova Liudmyla Oleksandrivna"
        print(f"Original: '{test_name}'")

        # Normalize for AC
        normalized = generator.normalize_for_ac(test_name)
        print(f"Normalized: '{normalized}'")

        # Extract components
        components = generator._extract_name_components(normalized, "en")
        print(f"Components: {components}")
        print(f"Component count: {len(components)}")

        if len(components) >= 2:
            surname = components[0] if components else ""
            first_name = components[1] if len(components) > 1 else ""
            patronymic = components[2] if len(components) > 2 else ""

            print(f"Surname: '{surname}'")
            print(f"First name: '{first_name}'")
            print(f"Patronymic: '{patronymic}'")

            if surname and first_name:
                print(f"\n🔄 Generating permutations...")

                # Test permutation generation
                permutations = generator._generate_name_permutations(surname, first_name, patronymic, "en")
                print(f"Raw permutations: {len(permutations)}")

                for i, perm in enumerate(permutations[:10], 1):
                    print(f"   {i:2d}. '{perm}'")
                if len(permutations) > 10:
                    print(f"   ... and {len(permutations) - 10} more")

                # Test Title Case normalization
                print(f"\n🔤 Title Case versions:")
                for perm in permutations[:5]:
                    title_case = generator.normalize_for_ac(perm, preserve_case=True)
                    lowercase = generator.normalize_for_ac(perm, preserve_case=False)
                    print(f"   Original: '{perm}'")
                    print(f"   Title:    '{title_case}'")
                    print(f"   Lower:    '{lowercase}'")
                    print()

                return True
            else:
                print("❌ Surname or first name empty - no permutations generated")
        else:
            print("❌ Less than 2 components - no permutations generated")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    test_name_components()

if __name__ == "__main__":
    main()