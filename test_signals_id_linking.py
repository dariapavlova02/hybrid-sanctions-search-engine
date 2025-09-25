#!/usr/bin/env python3

"""
Test DOB/ID linking to persons in SignalsService.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_signals_id_linking():
    """Test that DOB and ID are properly linked to persons."""
    print("🔍 TESTING SIGNALS ID/DOB LINKING")
    print("=" * 60)

    try:
        from ai_service.layers.signals.signals_service import SignalsService
        from ai_service.layers.normalization.normalization_service import NormalizationService

        print("✅ Successfully imported SignalsService")

        # Create services
        signals_service = SignalsService()

        # Try to create normalization service for full test
        try:
            normalization_service = NormalizationService()
            print("✅ Successfully imported NormalizationService")
        except Exception as norm_e:
            print(f"❌ Failed to create NormalizationService: {norm_e}")
            normalization_service = None

        # Test cases with persons and their IDs/DOB
        test_cases = [
            {
                "name": "Person with Ukrainian INN",
                "text": "Петров Иван Васильевич ІПН 782611846337",
                "expected_person_name": "Петров Иван Васильевич",
                "expected_ids": ["782611846337"],
                "expected_dob": None
            },
            {
                "name": "Person with DOB and INN",
                "text": "Іванов Петро Миколайович дата народження 15.03.1985 ІПН 782611846337",
                "expected_person_name": "Іванов Петро Миколайович",
                "expected_ids": ["782611846337"],
                "expected_dob": "1985-03-15"
            },
            {
                "name": "Person with EDRPOU",
                "text": "Коваленко Олена Степанівна ЄДРПОУ 12345678",
                "expected_person_name": "Коваленко Олена Степанівна",
                "expected_ids": ["12345678"],
                "expected_dob": None
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")

            try:
                # Test WITH normalization_result if available
                normalization_result = None

                # Create a mock normalization result with trace for testing
                # This simulates what would happen if normalization properly detected the ID tokens
                print(f"   Creating mock normalization result with trace...")

                # Extract expected ID from text for mock
                mock_trace = []
                tokens = test_case['text'].split()

                for i, token in enumerate(tokens):
                    if token in test_case['expected_ids']:
                        # This is the ID token, create trace entry
                        mock_trace.append({
                            'type': 'role',
                            'token': token,
                            'role': 'id',
                            'confidence': 1.0,
                            'reason': 'numeric_identifier_rule',
                            'evidence': ['numeric_id_detected', f'length_{len(token)}']
                        })
                        print(f"   📋 Mock trace: Added ID token '{token}' with role 'id'")
                    else:
                        # Regular token
                        mock_trace.append({
                            'type': 'role',
                            'token': token,
                            'role': 'given' if i < 3 else 'unknown',  # Simple heuristic
                            'confidence': 0.8,
                            'reason': 'mock_rule'
                        })

                # Create mock normalization result
                normalization_result = {
                    'normalized': ' '.join(tokens[:3]),  # Assume first 3 are person name
                    'tokens': tokens[:3],
                    'trace': mock_trace,
                    'persons_core': [tokens[:3]] if len(tokens) >= 3 else [],
                    'organizations_core': [],
                    'language': 'uk',
                    'success': True
                }

                print(f"   ✅ Mock normalization result created with {len(mock_trace)} trace entries")

                # Extract signals with normalization result
                signals_result = signals_service.extract(
                    text=test_case['text'],
                    normalization_result=normalization_result,
                    language="uk"
                )

                print(f"   Results WITH normalization:")
                print(f"     Persons found: {len(signals_result.get('persons', []))}")

                for j, person in enumerate(signals_result.get('persons', [])):
                    person_name = person.get('full_name', '')
                    person_ids = person.get('ids', [])
                    person_dob = person.get('dob', None)

                    print(f"     Person[{j}]: '{person_name}'")
                    print(f"       IDs: {[id_info.get('value', id_info) for id_info in person_ids]}")
                    print(f"       DOB: {person_dob}")

                # Check if person found and ID linked correctly
                found_correct_person = False
                for person in signals_result.get('persons', []):
                    if test_case['expected_person_name'] in person.get('full_name', ''):
                        found_correct_person = True
                        person_ids = [id_info.get('value', str(id_info)) for id_info in person.get('ids', [])]

                        # Check IDs
                        ids_match = any(expected_id in person_ids for expected_id in test_case['expected_ids'])
                        if ids_match:
                            print(f"     ✅ ID correctly linked to person")
                        else:
                            print(f"     ❌ ID NOT linked: expected {test_case['expected_ids']}, got {person_ids}")

                        # Check DOB
                        person_dob = person.get('dob')
                        if test_case['expected_dob']:
                            if person_dob == test_case['expected_dob']:
                                print(f"     ✅ DOB correctly linked to person")
                            else:
                                print(f"     ❌ DOB NOT linked: expected {test_case['expected_dob']}, got {person_dob}")
                        break

                if not found_correct_person:
                    print(f"     ❌ Expected person '{test_case['expected_person_name']}' not found")

            except Exception as test_e:
                print(f"   ❌ TEST ERROR: {test_e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("SIGNALS ID/DOB LINKING TEST COMPLETE")

if __name__ == "__main__":
    test_signals_id_linking()