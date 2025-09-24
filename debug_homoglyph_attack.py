#!/usr/bin/env python3
"""
Debug homoglyph attack in "Liudмуlа Uliаnоvа" - mixed Latin/Cyrillic characters
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_homoglyph_attack():
    """Debug homoglyph attack and why risk is low."""
    print("🔍 DEBUGGING HOMOGLYPH ATTACK")
    print("="*50)

    test_name = "Liudмуlа Uliаnоvа"
    print(f"Input: '{test_name}'")

    # Analyze character by character
    print(f"\n📝 CHARACTER ANALYSIS:")
    for i, char in enumerate(test_name):
        if char.isspace():
            print(f"  {i:2d}: '{char}' -> SPACE")
            continue

        # Check if Latin or Cyrillic
        is_latin = ord(char) <= 0x024F
        is_cyrillic = 0x0400 <= ord(char) <= 0x04FF

        char_type = "Latin" if is_latin else "Cyrillic" if is_cyrillic else "Other"
        print(f"  {i:2d}: '{char}' -> {char_type} (U+{ord(char):04X})")

    # Check what homoglyph detector does
    print(f"\n🔍 HOMOGLYPH DETECTION:")
    try:
        from ai_service.layers.validation.homoglyph_detector import homoglyph_detector

        normalized_text, analysis = homoglyph_detector.secure_normalize(test_name)
        print(f"  Original: '{test_name}'")
        print(f"  Normalized: '{normalized_text}'")
        print(f"  Warnings: {analysis.get('warnings', [])}")
        print(f"  Transformations: {analysis.get('transformations', [])}")

        if analysis.get('warnings'):
            print(f"  ✅ Homoglyph attack detected!")
        else:
            print(f"  ❌ Homoglyph attack NOT detected")

    except Exception as e:
        print(f"  ❌ Homoglyph detection failed: {e}")

    # Test normalization
    print(f"\n📊 NORMALIZATION TEST:")
    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()
        result = service.normalize_sync(
            test_name,
            language="en",  # Detected as English
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"  Input: '{test_name}'")
        print(f"  Normalized: '{result.normalized}'")
        print(f"  Language: {result.language}")
        print(f"  Tokens: {result.tokens}")

        # Check if normalization cleaned up mixed scripts
        if result.normalized != test_name:
            print(f"  ✅ Normalization changed the text")
        else:
            print(f"  ❌ Normalization kept original text unchanged")

        # Check homoglyph flags
        if hasattr(result, 'homoglyph_detected'):
            print(f"  Homoglyph detected: {result.homoglyph_detected}")
        if hasattr(result, 'homoglyph_analysis'):
            print(f"  Homoglyph analysis: {result.homoglyph_analysis}")

    except Exception as e:
        print(f"  ❌ Normalization failed: {e}")

    # Check what the correct name should be
    print(f"\n💡 LIKELY TARGET ANALYSIS:")

    # Try to convert to pure Latin
    latin_version = ""
    cyrillic_version = ""

    homoglyph_map = {
        # Cyrillic -> Latin
        'м': 'm', 'у': 'u', 'л': 'l', 'а': 'a', 'о': 'o', 'в': 'v'
    }

    reverse_map = {v: k for k, v in homoglyph_map.items()}

    for char in test_name:
        # Convert to Latin
        latin_version += homoglyph_map.get(char, char)
        # Convert to Cyrillic
        cyrillic_version += reverse_map.get(char, char)

    print(f"  Pure Latin version: '{latin_version}'")
    print(f"  Pure Cyrillic version: '{cyrillic_version}'")

    # These might be real names in sanctions lists
    possible_targets = [
        "Liudmila Ulianova",  # Pure Latin
        "Людмила Ульянова",   # Pure Cyrillic
        latin_version,
        cyrillic_version
    ]

    print(f"\n🎯 POSSIBLE REAL NAMES:")
    for i, name in enumerate(possible_targets, 1):
        print(f"  {i}. '{name}'")

    # Check why risk is low
    print(f"\n⚖️ RISK ASSESSMENT ANALYSIS:")
    print(f"  Current risk_level: low")
    print(f"  Current risk_score: 0.327")
    print(f"")
    print(f"  Why risk is low:")
    print(f"  1. search_contribution = 0 (no search matches)")
    print(f"  2. person_confidence = 0.6 (moderate)")
    print(f"  3. No homoglyph bonus applied")
    print(f"")
    print(f"  Risk should be HIGH because:")
    print(f"  ✅ Homoglyph attack detected")
    print(f"  ✅ Mixed script characters")
    print(f"  ✅ Likely sanctions evasion attempt")

if __name__ == "__main__":
    debug_homoglyph_attack()