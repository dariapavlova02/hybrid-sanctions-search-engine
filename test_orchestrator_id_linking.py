#!/usr/bin/env python3

"""
Test full integration of ID/DOB linking through UnifiedOrchestrator.
"""

import sys
import asyncio
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_orchestrator_id_linking():
    """Test full pipeline ID/DOB linking through orchestrator."""
    print("🔍 TESTING ORCHESTRATOR ID/DOB LINKING")
    print("=" * 60)

    try:
        from ai_service.core.unified_orchestrator import UnifiedOrchestrator
        from ai_service.core.orchestrator_factory import OrchestratorFactory

        print("✅ Successfully imported orchestrator components")

        # Create orchestrator directly
        try:
            orchestrator = UnifiedOrchestrator()
            print("✅ Successfully created UnifiedOrchestrator")
        except Exception as orch_e:
            print(f"❌ Failed to create orchestrator: {orch_e}")
            return

        # Test cases with persons and their IDs
        test_cases = [
            {
                "name": "Person with EDRPOU - full pipeline",
                "text": "Коваленко Олена Степанівна ЄДРПОУ 12345678",
                "expected_person_name": "Коваленко Олена Степанівна",
                "expected_ids": ["12345678"],
            },
            {
                "name": "Person with Ukrainian INN - full pipeline",
                "text": "Петров Иван Васильевич ІПН 782611846337",
                "expected_person_name": "Петров Иван Васильевич",
                "expected_ids": ["782611846337"],
            },
            {
                "name": "Person with DOB and INN - full pipeline",
                "text": "Іванов Петро Миколайович дата народження 15.03.1985 ІПН 782611846337",
                "expected_person_name": "Іванов Петро Миколайович",
                "expected_ids": ["782611846337"],
                "expected_dob": "1985-03-15"
            }
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n{i}. TEST: {test_case['name']}")
            print(f"   Text: '{test_case['text']}'")

            try:
                # Process through full orchestrator pipeline
                result = await orchestrator.process_async(
                    test_case['text'],
                    hints={"language": "uk"},
                    generate_variants=False,
                    generate_embeddings=False
                )

                print(f"   📋 Processing result:")
                print(f"     Success: {result.success}")
                print(f"     Language: {result.language}")
                print(f"     Normalized: '{result.normalized_text}'")

                # Check signals
                if result.signals and 'persons' in result.signals:
                    persons = result.signals['persons']
                    print(f"     Persons found: {len(persons)}")

                    for j, person in enumerate(persons):
                        person_name = person.get('full_name', '')
                        person_ids = person.get('ids', [])
                        person_dob = person.get('dob', None)

                        print(f"     Person[{j}]: '{person_name}'")
                        print(f"       IDs: {[id_info.get('value', str(id_info)) for id_info in person_ids]}")
                        print(f"       DOB: {person_dob}")

                    # Validate expectations
                    found_correct_person = False
                    for person in persons:
                        if test_case['expected_person_name'] in person.get('full_name', ''):
                            found_correct_person = True
                            person_ids = [id_info.get('value', str(id_info)) for id_info in person.get('ids', [])]

                            # Check IDs
                            ids_match = any(expected_id in person_ids for expected_id in test_case['expected_ids'])
                            if ids_match:
                                print(f"     ✅ ID correctly linked to person in full pipeline")
                            else:
                                print(f"     ❌ ID NOT linked in full pipeline: expected {test_case['expected_ids']}, got {person_ids}")

                            # Check DOB if expected
                            if test_case.get('expected_dob'):
                                person_dob = person.get('dob')
                                if person_dob == test_case['expected_dob']:
                                    print(f"     ✅ DOB correctly linked to person in full pipeline")
                                else:
                                    print(f"     ❌ DOB NOT linked in full pipeline: expected {test_case['expected_dob']}, got {person_dob}")
                            break

                    if not found_correct_person:
                        print(f"     ❌ Expected person '{test_case['expected_person_name']}' not found in full pipeline")

                else:
                    print(f"     ❌ No persons found in signals")

            except Exception as test_e:
                print(f"   ❌ TEST ERROR: {test_e}")
                import traceback
                traceback.print_exc()

    except Exception as e:
        print(f"❌ Setup error: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("ORCHESTRATOR ID/DOB LINKING TEST COMPLETE")

if __name__ == "__main__":
    asyncio.run(test_orchestrator_id_linking())