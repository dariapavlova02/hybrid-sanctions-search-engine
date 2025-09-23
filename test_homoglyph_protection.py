#!/usr/bin/env python3
"""
Test homoglyph protection with the problematic mixed-script attack case.
"""

import os
import sys
from pathlib import Path

# Set production environment variables
os.environ.update({
    'PRESERVE_FEMININE_SURNAMES': 'true',
    'ENABLE_ENHANCED_GENDER_RULES': 'true',
    'PRESERVE_FEMININE_SUFFIX_UK': 'true',
    'ENABLE_FSM_TUNED_ROLES': 'true',
    'MORPHOLOGY_CUSTOM_RULES_FIRST': 'true',
    'ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_ADVANCED_FEATURES': 'true',
    'NORMALIZATION_ENABLE_MORPHOLOGY': 'true',
    'ENFORCE_NOMINATIVE': 'false',
    'DEBUG_TRACING': 'true'
})

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def analyze_text_characters(text):
    """Analyze characters in text."""
    print(f"\n🔍 CHARACTER ANALYSIS: '{text}'")
    for i, char in enumerate(text):
        print(f"  [{i}] '{char}' -> U+{ord(char):04X} ({char.encode('unicode_escape').decode()})")

def test_homoglyph_protection():
    """Test homoglyph protection with mixed-script attack."""
    print("🛡️ HOMOGLYPH PROTECTION TEST")
    print("="*60)

    # The problematic mixed-script attack case from the user
    attack_text = "Оплaтa Пepoшeнкa Oт J Пeтpa"
    print(f"\n⚠️ ATTACK TEXT: '{attack_text}'")
    analyze_text_characters(attack_text)

    try:
        from ai_service.layers.normalization.homoglyph_detector import homoglyph_detector

        # Test homoglyph detector directly
        print(f"\n🔍 HOMOGLYPH DETECTION:")
        detection = homoglyph_detector.detect_homoglyphs(attack_text)
        print(f"  Has homoglyphs: {detection['has_homoglyphs']}")
        print(f"  Confidence: {detection['confidence']:.3f}")
        print(f"  Suspicious chars: {len(detection['suspicious_chars'])}")
        print(f"  Suspicious words: {len(detection['suspicious_words'])}")

        for char_info in detection['suspicious_chars']:
            print(f"    - '{char_info['char']}' (U+{char_info['unicode']}) -> '{char_info['suggested']}'")

        # Test normalization
        normalized, analysis = homoglyph_detector.secure_normalize(attack_text)
        print(f"\n🔧 NORMALIZATION:")
        print(f"  Original: '{attack_text}'")
        print(f"  Normalized: '{normalized}'")
        print(f"  Changed: {analysis['changed']}")
        print(f"  Safe: {analysis['safe']}")
        print(f"  Warnings: {analysis['warnings']}")

        if analysis['transformations']:
            print(f"  Transformations:")
            for transformation in analysis['transformations']:
                print(f"    - {transformation}")

        # Test with the full normalization service
        print(f"\n📝 FULL NORMALIZATION SERVICE TEST:")
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()
        result = service.normalize_sync(
            text=attack_text,
            language=None,  # Auto-detect
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"  Original: '{attack_text}'")
        print(f"  Result: '{result.normalized}'")
        print(f"  Language: '{result.language}'")
        print(f"  Tokens: {result.tokens}")
        print(f"  Success: {result.success}")

        # Test that it now works properly
        expected_tokens = ["Оплата", "Порошенка", "От", "Петра"]  # Expected after homoglyph fix
        print(f"\n✅ VALIDATION:")
        print(f"  Expected similar to: {expected_tokens}")
        print(f"  Actual tokens: {result.tokens}")

        # Check if homoglyphs were normalized away
        has_latin_chars = any(char for char in result.normalized if 'A' <= char <= 'z')
        print(f"  Contains Latin chars: {has_latin_chars}")

        if not has_latin_chars:
            print("  ✅ SUCCESS: Mixed-script attack was neutralized!")
        else:
            print("  ⚠️ WARNING: Some Latin characters remain")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def test_clean_comparison():
    """Test with clean Ukrainian text for comparison."""
    print("\n\n🔍 CLEAN TEXT COMPARISON")
    print("="*40)

    clean_text = "Оплата Порошенка От Петра"
    print(f"\n✅ CLEAN TEXT: '{clean_text}'")
    analyze_text_characters(clean_text)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()
        result = service.normalize_sync(
            text=clean_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n📝 RESULT: '{result.normalized}'")
        print(f"  Language: '{result.language}'")
        print(f"  Tokens: {result.tokens}")

    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_homoglyph_protection()
    test_clean_comparison()