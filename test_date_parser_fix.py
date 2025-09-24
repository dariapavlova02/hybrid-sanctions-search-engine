#!/usr/bin/env python3
"""
Test for date parser fix - д.р. should not become separate person tokens.

Tests that "д.р." or "дата народження" don't turn into separate person tokens.
The rule: if "д.р." is encountered → skip as marker, following date goes to person.dob.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_date_parser_fix():
    """Test that д.р. date markers don't become person tokens."""

    print("🔍 Testing date parser fix for д.р. markers")
    print("=" * 60)

    try:
        from ai_service.layers.signals.signals_service import SignalsService

        service = SignalsService()

        # Test case specified in the task
        test_cases = [
            {
                "text": "Holoborodko Liudmyla, д.р. 12.11.1968",
                "expected_person_name": "Holoborodko Liudmyla",
                "expected_dob": "1968-11-12",
                "description": "Ukrainian person with д.р. - should not create separate person 'д.'"
            },
            {
                "text": "Иванов Петр д.р. 15.05.1975",
                "expected_person_name": "Иванов Петр",
                "expected_dob": "1975-05-15",
                "description": "Russian person with д.р."
            },
            {
                "text": "Smith John д.р. 20.03.1980",
                "expected_person_name": "Smith John",
                "expected_dob": "1980-03-20",
                "description": "English person with д.р."
            },
            {
                "text": "д.р. 12.11.1968 Holoborodko Liudmyla",
                "expected_person_name": "Holoborodko Liudmyla",
                "expected_dob": "1968-11-12",
                "description": "Date marker before name"
            },
            {
                "text": "Кухарук Виктория дата народження 25.12.1985",
                "expected_person_name": "Кухарук Виктория",
                "expected_dob": "1985-12-25",
                "description": "Full 'дата народження' phrase"
            }
        ]

        all_passed = True

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}: {test_case['description']}")
            print(f"📝 Input: '{test_case['text']}'")

            result = service.extract(test_case['text'], language='uk')

            print(f"📊 Results:")
            print(f"  Persons count: {len(result.get('persons', []))}")

            # Test 1: Exactly one person should be extracted
            persons = result.get('persons', [])
            single_person = len(persons) == 1
            print(f"  ✅ Single person found: {'PASS' if single_person else 'FAIL'} (found {len(persons)})")

            if single_person:
                person = persons[0]

                # Test 2: Person name should be correct (without д.р.)
                actual_name = person.get('full_name', '')
                name_correct = actual_name == test_case['expected_person_name']
                print(f"  ✅ Person name correct: {'PASS' if name_correct else 'FAIL'} (expected '{test_case['expected_person_name']}', got '{actual_name}')")

                # Test 3: Person should have correct DOB
                actual_dob = person.get('dob')
                dob_correct = actual_dob == test_case['expected_dob']
                print(f"  ✅ DOB correct: {'PASS' if dob_correct else 'FAIL'} (expected '{test_case['expected_dob']}', got '{actual_dob}')")

                # Test 4: No person should have "д." or similar as name
                person_core = person.get('core', [])
                no_date_markers_in_name = not any(
                    token.lower() in ['д.', 'р.', 'д', 'р', 'дата', 'народження', 'рождения']
                    for token in person_core
                )
                print(f"  ✅ No date markers in name: {'PASS' if no_date_markers_in_name else 'FAIL'} (core: {person_core})")

                # Test 5: Evidence should include birthdate_found
                evidence = person.get('evidence', [])
                has_birthdate_evidence = 'birthdate_found' in evidence
                print(f"  ✅ Birthdate evidence found: {'PASS' if has_birthdate_evidence else 'FAIL'} (evidence: {evidence})")

                # Overall test result
                test_passed = (single_person and name_correct and dob_correct and
                              no_date_markers_in_name and has_birthdate_evidence)
            else:
                test_passed = False

            if not test_passed:
                all_passed = False

            print(f"  {'🎉 PASS' if test_passed else '❌ FAIL'}: Test case {i}")

        # Additional test: Multiple persons with dates
        print(f"\n🔧 Multiple Persons with Dates Test")
        multi_test = "Иванов Петр д.р. 15.05.1975 и Сидорова Мария д.р. 10.08.1980"
        print(f"Testing: '{multi_test}'")

        multi_result = service.extract(multi_test, language='ru')
        multi_persons = multi_result.get('persons', [])

        print(f"  Persons found: {len(multi_persons)}")
        multi_passed = True
        for i, person in enumerate(multi_persons):
            person_name = person.get('full_name', 'Unknown')
            person_dob = person.get('dob', 'None')
            person_core = person.get('core', [])

            # Check that no date markers are in the person name
            has_date_markers = any(
                token.lower() in ['д.', 'р.', 'д', 'р']
                for token in person_core
            )

            print(f"  Person {i+1}: {person_name} | DOB: {person_dob} | Clean name: {'YES' if not has_date_markers else 'NO'}")

            if has_date_markers:
                multi_passed = False

        if not multi_passed:
            all_passed = False

        print(f"  {'🎉 PASS' if multi_passed else '❌ FAIL'}: Multiple persons test")

        # Test normalization directly to verify token roles
        print(f"\n🔧 Token Role Verification Test")
        from ai_service.layers.normalization.normalization_service import NormalizationService
        norm_service = NormalizationService()

        norm_result = norm_service.normalize(
            text="Holoborodko Liudmyla д.р. 12.11.1968",
            language='uk',
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"  Normalized text: '{norm_result.normalized}'")
        print(f"  Token roles:")
        date_marker_roles = []
        for trace in norm_result.trace:
            if trace.token.lower() in ['д.', 'р.']:
                date_marker_roles.append(trace.role)
                print(f"    '{trace.token}' -> {trace.role}")

        roles_correct = all(role == 'document' for role in date_marker_roles)
        normalized_clean = 'д.' not in norm_result.normalized and 'р.' not in norm_result.normalized

        print(f"  ✅ Date markers classified as 'document': {'PASS' if roles_correct else 'FAIL'}")
        print(f"  ✅ Normalized text clean of date markers: {'PASS' if normalized_clean else 'FAIL'}")

        normalization_passed = roles_correct and normalized_clean
        if not normalization_passed:
            all_passed = False

        print(f"  {'🎉 PASS' if normalization_passed else '❌ FAIL'}: Normalization test")

        # Summary
        print(f"\n{'🎉 SUCCESS' if all_passed else '❌ FAILURES'}: Date parser fix tests {'passed' if all_passed else 'have issues'}")

        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_date_parser_fix()
    sys.exit(0 if success else 1)