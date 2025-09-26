#!/usr/bin/env python3
"""
Test legal forms fix for Ukrainian "Інкорпорейтед".
"""

import sys
sys.path.append('src')

from ai_service.data.patterns.legal_forms import is_legal_form, extract_legal_forms, get_legal_forms_set

def test_legal_forms_fix():
    """Test the legal forms fix."""
    print("🧪 TESTING LEGAL FORMS FIX")
    print("=" * 50)

    test_cases = [
        ("Одін Марін Інкорпорейтед", "uk"),
        ("Компанія Лімітед", "uk"),
        ("Test Corporation", "en"),
        ("ООО Тест", "ru"),
    ]

    print("📋 Ukrainian legal forms available:")
    uk_forms = get_legal_forms_set("uk")
    for form in sorted(uk_forms):
        print(f"  - {form}")

    print(f"\n🔍 Testing legal form detection:")

    for text, language in test_cases:
        print(f"\nText: '{text}' (language: {language})")

        # Test detection
        is_detected = is_legal_form(text, language)
        print(f"  Detected: {is_detected}")

        # Test extraction
        forms = extract_legal_forms(text, language)
        if forms:
            print(f"  Extracted forms:")
            for form in forms:
                print(f"    - {form['abbreviation']} -> {form['full_name']}")
        else:
            print(f"  No forms extracted")

    print(f"\n✅ Specific test for 'Інкорпорейтед':")
    test_text = "Одін Марін Інкорпорейтед"
    detected = is_legal_form(test_text, "uk")
    forms = extract_legal_forms(test_text, "uk")

    print(f"Text: '{test_text}'")
    print(f"Detected: {detected}")
    print(f"Forms: {forms}")

    if detected and forms:
        print("🎉 SUCCESS: 'Інкорпорейтед' is now properly detected!")
    else:
        print("❌ FAILED: 'Інкорпорейтед' still not detected")

if __name__ == "__main__":
    test_legal_forms_fix()