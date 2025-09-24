#!/usr/bin/env python3
"""
Comprehensive test for Poroshenko classification fix
"""

import sys
import json
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def test_poroshenko_fix():
    """Test the Poroshenko classification fix comprehensively."""
    print("🔍 COMPREHENSIVE POROSHENKO FIX TEST")
    print("="*60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Test cases with various scenarios
        test_cases = [
            {
                'input': 'Порошенк Петро',
                'expected_surname': 'Порошенк',
                'expected_given': 'Петро',
                'description': 'Typo case: Порошенк instead of Порошенко'
            },
            {
                'input': 'Порошенко Петро',
                'expected_surname': 'Порошенко',
                'expected_given': 'Петро',
                'description': 'Correct case: Full surname'
            },
            {
                'input': 'Порошенк',
                'expected_surname': 'Порошенк',
                'expected_given': None,
                'description': 'Single surname with typo'
            },
            {
                'input': 'Петро Порошенк',
                'expected_surname': 'Порошенк',
                'expected_given': 'Петро',
                'description': 'Reversed order: Given Surname'
            },
            {
                'input': 'ПОРОШЕНК ПЕТРО',
                'expected_surname': 'Порошенк',
                'expected_given': 'Петро',
                'description': 'All caps case'
            }
        ]

        success_count = 0
        total_count = len(test_cases)

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📝 Test {i}/{total_count}: {test_case['description']}")
            print(f"   Input: '{test_case['input']}'")

            # Test with different language settings
            for lang in ['uk', 'ru', 'auto']:
                result = service.normalize_sync(
                    test_case['input'],
                    language=lang,
                    remove_stop_words=True,
                    preserve_names=True,
                    enable_advanced_features=True
                )

                print(f"   Lang {lang}: '{result.normalized}' | Tokens: {result.tokens}")

                # Check roles in trace
                roles_found = {}
                for trace in result.trace:
                    roles_found[trace.token] = trace.role

                # Verify surname classification
                surname_correct = False
                given_correct = True  # Default to true if no expected given

                if test_case['expected_surname']:
                    surname_tokens = [token for token in roles_found.keys()
                                    if token.lower().startswith(test_case['expected_surname'].lower()[:6])]
                    if surname_tokens:
                        surname_role = roles_found[surname_tokens[0]]
                        surname_correct = surname_role == 'surname'
                        print(f"     Surname '{surname_tokens[0]}': {surname_role} {'✅' if surname_correct else '❌'}")

                if test_case['expected_given']:
                    given_tokens = [token for token in roles_found.keys()
                                  if token.lower().startswith(test_case['expected_given'].lower()[:4])]
                    if given_tokens:
                        given_role = roles_found[given_tokens[0]]
                        given_correct = given_role == 'given'
                        print(f"     Given '{given_tokens[0]}': {given_role} {'✅' if given_correct else '❌'}")

                if surname_correct and given_correct and lang == 'uk':
                    success_count += 1

        print(f"\n📊 FINAL RESULTS:")
        print(f"   Successful tests: {success_count}/{total_count}")
        print(f"   Success rate: {(success_count/total_count)*100:.1f}%")

        # Test FSM surname suffixes directly
        print(f"\n🔍 FSM SUFFIX PATTERNS TEST:")
        from ai_service.layers.normalization.role_tagger_service import RoleTaggerService

        tagger = RoleTaggerService()
        suffixes_to_check = ['енк', 'енко', 'ук', 'ов', 'ова']

        print(f"   Available surname suffixes:")
        for suffix in suffixes_to_check:
            in_patterns = suffix in tagger.rules.surname_suffixes
            print(f"     '{suffix}': {'✅' if in_patterns else '❌'}")

        # Test language detection impact
        print(f"\n🌍 LANGUAGE DETECTION TEST:")
        from ai_service.layers.language.language_detection_service import LanguageDetectionService

        lang_service = LanguageDetectionService()
        for test_case in test_cases[:3]:  # Test first 3 cases
            detection = lang_service.detect_language(test_case['input'])
            print(f"   '{test_case['input']}' -> {detection['language']} (conf: {detection['confidence']:.2f})")

        if success_count == total_count:
            print(f"\n🎉 ALL TESTS PASSED! Poroshenko fix is working correctly.")
        else:
            print(f"\n⚠️  Some tests failed. Please review the results above.")

        return success_count == total_count

    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_poroshenko_fix()
    sys.exit(0 if success else 1)