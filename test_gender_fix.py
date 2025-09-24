#!/usr/bin/env python3
"""
Test gender fix for 'Олександра' -> should stay 'Олександра'
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_gender_fix():
    """Test that Олександра is not converted to Олександр."""
    print("🎯 TESTING GENDER FIX")
    print("="*40)

    test_cases = [
        {
            "input": "Коваленко Олександра Сергіївна",
            "expected": "Коваленко Олександра Сергіївна",
            "note": "Feminine name should be preserved"
        },
        {
            "input": "Олександра",
            "expected": "Олександра",
            "note": "Single feminine name should be preserved"
        },
        {
            "input": "Сергій Олійник",
            "expected": "Сергій Олійник",
            "note": "Masculine names should work normally"
        }
    ]

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        for i, case in enumerate(test_cases, 1):
            input_text = case["input"]
            expected = case["expected"]
            note = case["note"]

            print(f"\n{i}. Testing: '{input_text}'")
            print(f"   Expected: '{expected}'")
            print(f"   Note: {note}")

            result = await service.normalize_async(
                input_text,
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                preserve_feminine_suffix_uk=True
            )

            actual = result.normalized
            success = actual == expected

            print(f"   📝 Result: '{actual}' {'✅' if success else '❌'}")

            if not success:
                print(f"     Expected: '{expected}'")
                print(f"     Got: '{actual}'")

        print(f"\n{'='*40}")
        print("🎉 GENDER FIX TEST COMPLETE!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_gender_fix())