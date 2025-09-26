#!/usr/bin/env python3
"""Test homoglyph normalization fix"""

from src.ai_service.layers.normalization.homoglyph_detector import HomoglyphDetector

def test_homoglyph_normalization():
    detector = HomoglyphDetector()

    test_cases = [
        ("Liudмуla Ulianova", "Liudmyla Ulianova"),  # Cyrillic м,у -> Latin m,y
        ("Сергій Олійник", "Cepгiй Oлiйник"),  # Cyrillic С,О -> Latin C,O
        ("ABCEHKMOPTXY", "ABCEHKMOPTXY"),  # All Latin, no change
        ("АВСЕНКМОРТХУ", "ABCEHKMOPTXY"),  # All Cyrillic -> Latin
        ("MixedТекстText", "MixedTekctText"),  # Mixed -> all Latin
    ]

    print("🧪 Testing Homoglyph Normalization\n" + "="*50)

    for original, expected_contains in test_cases:
        normalized, transformations = detector.normalize_homoglyphs(original)
        detection = detector.detect_homoglyphs(original)

        print(f"\nOriginal: '{original}'")
        print(f"Normalized: '{normalized}'")
        print(f"Has homoglyphs: {detection['has_homoglyphs']}")
        print(f"Transformations: {len(transformations)}")

        if transformations:
            for t in transformations[:3]:  # Show first 3 transformations
                print(f"  - {t}")

        # Check if normalized correctly
        success = True
        for char in ['м', 'у', 'С', 'О', 'Т', 'А', 'В', 'Е', 'Н', 'К', 'М', 'Р', 'Х', 'У']:
            if char in normalized:
                print(f"  ❌ Still contains Cyrillic '{char}'")
                success = False
                break

        if success and detection['has_homoglyphs']:
            print(f"  ✅ Properly normalized mixed script to Latin")

if __name__ == "__main__":
    test_homoglyph_normalization()