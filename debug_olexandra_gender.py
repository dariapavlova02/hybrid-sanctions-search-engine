#!/usr/bin/env python3
"""
Debug gender conversion of Олександра -> олександр
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_gender_conversion():
    """Test gender conversion functions directly."""
    print("🔍 DEBUGGING GENDER CONVERSION")
    print("="*40)

    # Test the specific case
    test_name = "Олександра"
    language = "uk"

    try:
        # 1. Test gender rules function
        from ai_service.layers.normalization.morphology.gender_rules import convert_given_name_to_nominative_uk

        result_uk = convert_given_name_to_nominative_uk(test_name)
        print(f"1. convert_given_name_to_nominative_uk('{test_name}') -> '{result_uk}'")

        # 2. Test general function
        from ai_service.layers.normalization.morphology.gender_rules import convert_given_name_to_nominative

        result_general = convert_given_name_to_nominative(test_name, language)
        print(f"2. convert_given_name_to_nominative('{test_name}', '{language}') -> '{result_general}'")

        # 3. Test morphology processor
        from ai_service.layers.normalization.processors.morphology_processor import MorphologyProcessor

        processor = MorphologyProcessor()
        result_morph, trace = await processor.normalize_slavic_token(test_name, "given", language)
        print(f"3. MorphologyProcessor.normalize_slavic_token('{test_name}', 'given', '{language}') -> '{result_morph}'")
        print(f"   Trace: {trace}")

        # 4. Test Ukrainian morphology analyzer directly
        try:
            from ai_service.layers.normalization.morphology.ukrainian_morphology import UkrainianMorphologyAnalyzer

            analyzer = UkrainianMorphologyAnalyzer()
            parses = analyzer.parse(test_name)
            print(f"4. UkrainianMorphologyAnalyzer.parse('{test_name}'):")

            for i, parse in enumerate(parses[:5]):  # Show first 5 parses
                print(f"   {i+1}. {parse}")

        except Exception as e:
            print(f"4. Ukrainian morphology test failed: {e}")

        # 5. Test with different roles
        roles = ['given', 'surname', 'patronymic']
        for role in roles:
            try:
                result_role, trace_role = await processor.normalize_slavic_token(test_name, role, language)
                print(f"5. Role '{role}': '{test_name}' -> '{result_role}'")
            except Exception as e:
                print(f"5. Role '{role}' failed: {e}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gender_conversion())