#!/usr/bin/env python3
"""
Comprehensive test for morphology normalization after fixing cache_info error.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
import asyncio
import json

async def test_morphology_comprehensive():
    """Test various morphological cases."""
    print("🧪 COMPREHENSIVE MORPHOLOGY TESTS")
    print("=" * 50)

    # Create factory instance
    factory = NormalizationFactory(
        name_dictionaries=None,
        diminutive_maps=None
    )

    # Test configuration
    config = NormalizationConfig(
        language="ru",
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True,
        enable_morphology=True,
        enable_cache=True
    )

    test_cases = [
        # Russian genitive cases
        ("Дарьи Павловой", "Дарья Павлова"),
        ("Ивана Петрова", "Иван Петров"),
        ("Елены Сидоровой", "Елена Сидорова"),
        ("Максима Кузнецова", "Максим Кузнецов"),

        # Ukrainian cases
        ("Олексій Українець", "Олексій Українець"),  # Should stay the same (nominative)
        ("Оксани Петренко", "Оксана Петренко"),

        # Already nominative cases (should not change)
        ("Иван Иванов", "Иван Иванов"),
        ("Мария Петрова", "Мария Петрова"),
    ]

    results = []

    for i, (input_text, expected) in enumerate(test_cases, 1):
        print(f"\n🔍 Test {i}: '{input_text}'")
        try:
            result = await factory.normalize_text(input_text, config)

            success = result.normalized == expected
            status = "✅ PASS" if success else "❌ FAIL"

            print(f"  Expected: '{expected}'")
            print(f"  Got:      '{result.normalized}'")
            print(f"  Status:   {status}")

            if not success:
                print(f"  Tokens: {result.tokens}")
                # Show morphology trace
                morph_applied = []
                for trace in result.trace:
                    if trace.morph_lang or "morph" in str(trace.notes).lower():
                        morph_applied.append(f"{trace.token} -> {trace.output} ({trace.notes})")

                if morph_applied:
                    print(f"  Morphology: {'; '.join(morph_applied)}")
                else:
                    print(f"  Morphology: No morphological processing detected")

            results.append({
                'input': input_text,
                'expected': expected,
                'actual': result.normalized,
                'success': success
            })

        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            results.append({
                'input': input_text,
                'expected': expected,
                'actual': f"ERROR: {e}",
                'success': False
            })

    # Summary
    passed = sum(1 for r in results if r['success'])
    total = len(results)

    print(f"\n📊 SUMMARY")
    print(f"Passed: {passed}/{total}")
    print(f"Success Rate: {passed/total*100:.1f}%")

    if passed == total:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("❌ Some tests failed")
        for r in results:
            if not r['success']:
                print(f"  FAILED: '{r['input']}' -> expected '{r['expected']}', got '{r['actual']}'")

if __name__ == "__main__":
    asyncio.run(test_morphology_comprehensive())