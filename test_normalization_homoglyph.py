#!/usr/bin/env python3

"""
Test homoglyph detection in NormalizationService directly.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_normalization_homoglyph():
    """Test homoglyph detection in normalization service."""
    print("🔍 NORMALIZATION HOMOGLYPH TEST")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        # Create normalization service
        service = NormalizationService()

        test_cases = [
            {
                "name": "Clean Latin",
                "text": "Liudmila Ulianova",
                "expected_homoglyph": False
            },
            {
                "name": "Mixed Script Attack",
                "text": "Liudмуlа Uliаnоvа",  # Mixed Latin/Cyrillic
                "expected_homoglyph": True
            },
            {
                "name": "Cross-word Mixed",
                "text": "Петро Poroshenko",  # Cyrillic + Latin
                "expected_homoglyph": True
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")
            print(f"   Expected homoglyph: {test_case['expected_homoglyph']}")

            try:
                # Process through normalization service
                result = await service.normalize_async(
                    text=test_case['text'],
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True,
                    language=None,
                    preserve_feminine_suffix_uk=True,
                    enable_spacy_uk_ner=False,
                    en_use_nameparser=False,
                    enable_en_nickname_expansion=False,
                    enable_spacy_en_ner=False,
                    ru_yo_strategy="preserve",
                    enable_ru_nickname_expansion=False,
                    enable_spacy_ru_ner=False
                )

                # Check homoglyph fields
                homoglyph_detected = getattr(result, 'homoglyph_detected', None)
                homoglyph_analysis = getattr(result, 'homoglyph_analysis', None)

                print(f"   🔍 homoglyph_detected: {homoglyph_detected}")
                if homoglyph_analysis:
                    print(f"   📊 has_homoglyphs: {homoglyph_analysis.get('has_homoglyphs', 'N/A')}")
                    print(f"   📈 confidence: {homoglyph_analysis.get('confidence', 'N/A')}")
                    print(f"   🚨 suspicious_words: {len(homoglyph_analysis.get('suspicious_words', []))}")
                    if homoglyph_analysis.get('suspicious_words'):
                        for word_info in homoglyph_analysis['suspicious_words'][:2]:
                            print(f"      -> {word_info}")
                else:
                    print(f"   📊 homoglyph_analysis: None")

                # Check if it matches expectation
                detected = homoglyph_detected if homoglyph_detected is not None else False
                if detected == test_case['expected_homoglyph']:
                    print(f"   ✅ PASS")
                else:
                    print(f"   ❌ FAIL - Expected {test_case['expected_homoglyph']}, got {detected}")

            except Exception as e:
                print(f"   ❌ ERROR: {e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Failed to initialize normalization service: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("NORMALIZATION HOMOGLYPH TEST COMPLETE")


if __name__ == "__main__":
    asyncio.run(test_normalization_homoglyph())