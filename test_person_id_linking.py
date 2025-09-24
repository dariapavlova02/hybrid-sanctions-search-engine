#!/usr/bin/env python3
"""
Test for person ID linking functionality.

Tests that found IDs and dates are linked to the nearest person (core=ФИО)
instead of being placed in organizations or unknown.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_person_id_linking():
    """Test that IDs are properly linked to persons instead of organizations."""

    print("🔍 Testing person ID linking")
    print("=" * 60)

    try:
        from ai_service.layers.signals.signals_service import SignalsService

        service = SignalsService()

        # Test case specified in the task
        test_cases = [
            {
                "text": "Кухарук Виктория ІПН 782611846337",
                "expected_person_name": "Кухарук Виктория",
                "expected_ids": ["782611846337"],
                "description": "Ukrainian person with IPN - ID should link to person"
            },
            {
                "text": "Петров Иван ИНН 1234567890",
                "expected_person_name": "Петров Иван",
                "expected_ids": ["1234567890"],
                "description": "Russian person with INN - ID should link to person"
            },
            {
                "text": "Smith John TIN 9876543210",
                "expected_person_name": "Smith John",
                "expected_ids": ["9876543210"],
                "description": "English person with TIN - ID should link to person"
            },
            {
                "text": "Дарья Павлова паспорт 123456789",
                "expected_person_name": "Дарья Павлова",
                "expected_ids": ["123456789"],
                "description": "Person with passport number - ID should link to person"
            }
        ]

        all_passed = True

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}: {test_case['description']}")
            print(f"📝 Input: '{test_case['text']}'")

            result = service.extract(test_case['text'], language='uk')

            print(f"📊 Results:")
            print(f"  Persons count: {len(result.get('persons', []))}")
            print(f"  Organizations count: {len(result.get('organizations', []))}")

            # Test 1: Person should be extracted
            persons = result.get('persons', [])
            person_found = len(persons) >= 1
            print(f"  ✅ Person found: {'PASS' if person_found else 'FAIL'}")

            if person_found:
                person = persons[0]

                # Test 2: Person name should be correct (without document markers)
                actual_name = person.get('full_name', '')
                name_correct = actual_name == test_case['expected_person_name']
                print(f"  ✅ Person name correct: {'PASS' if name_correct else 'FAIL'} (expected '{test_case['expected_person_name']}', got '{actual_name}')")

                # Test 3: Person should have IDs linked
                person_ids = person.get('ids', [])
                has_ids = len(person_ids) > 0
                print(f"  ✅ Person has IDs: {'PASS' if has_ids else 'FAIL'} (found {len(person_ids)} IDs)")

                # Test 4: Check if expected ID values are present
                if has_ids:
                    id_values = [id_info['value'] for id_info in person_ids]
                    ids_correct = all(expected_id in id_values for expected_id in test_case['expected_ids'])
                    print(f"  ✅ Expected IDs linked: {'PASS' if ids_correct else 'FAIL'} (expected {test_case['expected_ids']}, got {id_values})")

                    # Show ID details
                    for j, id_info in enumerate(person_ids):
                        print(f"    ID {j+1}: {id_info['type']}={id_info['value']} (confidence: {id_info['confidence']})")
                else:
                    ids_correct = False

                # Test 5: IDs should NOT be in organizations
                organizations = result.get('organizations', [])
                ids_in_orgs = False
                if organizations:
                    for org in organizations:
                        org_ids = org.get('ids', [])
                        if any(expected_id in [id_info['value'] for id_info in org_ids] for expected_id in test_case['expected_ids']):
                            ids_in_orgs = True
                            break

                no_ids_in_orgs = not ids_in_orgs
                print(f"  ✅ IDs not in organizations: {'PASS' if no_ids_in_orgs else 'FAIL'}")

                # Overall test result
                test_passed = (person_found and name_correct and has_ids and ids_correct and no_ids_in_orgs)
            else:
                test_passed = False

            if not test_passed:
                all_passed = False

            print(f"  {'🎉 PASS' if test_passed else '❌ FAIL'}: Test case {i}")

        # Additional test: Multiple persons with IDs
        print(f"\n🔧 Multiple Persons Test")
        multi_test = "Иванов Петр ИНН 1111111111 и Сидорова Мария ИНН 2222222222"
        print(f"Testing: '{multi_test}'")

        multi_result = service.extract(multi_test, language='ru')
        multi_persons = multi_result.get('persons', [])

        print(f"  Persons found: {len(multi_persons)}")
        for i, person in enumerate(multi_persons):
            person_ids = [id_info['value'] for id_info in person.get('ids', [])]
            print(f"  Person {i+1}: {person.get('full_name', 'Unknown')} - IDs: {person_ids}")

        multi_passed = len(multi_persons) >= 1  # At least some persons should be found
        if not multi_passed:
            all_passed = False

        print(f"  {'🎉 PASS' if multi_passed else '❌ FAIL'}: Multiple persons test")

        # Summary
        print(f"\n{'🎉 SUCCESS' if all_passed else '❌ FAILURES'}: Person ID linking tests {'passed' if all_passed else 'have issues'}")

        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_person_id_linking()
    sys.exit(0 if success else 1)