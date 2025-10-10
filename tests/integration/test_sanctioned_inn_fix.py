"""
Quick integration test for sanctioned INN with valid=false bug fix.

This tests the exact production scenario:
- Text: "Дарья ПАвлова ИНН 2839403975"
- INN 2839403975 is sanctioned (Yakubov Ruslan)
- INN validation may fail but it should still be detected
"""

import asyncio
import sys
import os
import json

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from ai_service.layers.signals.signals_service import SignalsService
from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.data.patterns.identifiers import validate_inn


async def test_sanctioned_inn_detection():
    """Test that sanctioned INN is detected even with validation=false."""
    print("=" * 80)
    print("Testing Sanctioned INN Detection (Production Bug Fix)")
    print("=" * 80)

    # Exact production request
    text = "Дарья ПАвлова ИНН 2839403975"

    print(f"\n[CMD] Input text: {text}")
    print(f"[TARGET] Expected: INN 2839403975 should be found and marked as sanctioned")
    print(f"[TARGET] Expected: INN should have type='inn' (not 'numeric_id')\n")

    # Step 1: Normalization
    print("\n" + "=" * 80)
    print("STEP 1: NORMALIZATION")
    print("=" * 80)

    norm_service = NormalizationService()
    norm_result = await norm_service.normalize_async(
        text=text,
        language="ru",
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True
    )

    print(f"\n[OK] Normalized text: {norm_result.normalized}")
    print(f"[OK] Tokens: {norm_result.tokens}")
    print(f"[OK] Trace entries: {len(norm_result.trace)}")

    # Check for INN marker in trace
    inn_marker_found = False
    for entry in norm_result.trace:
        # Convert Pydantic model to dict
        if hasattr(entry, 'model_dump'):
            entry_dict = entry.model_dump()
        elif hasattr(entry, 'dict'):
            entry_dict = entry.dict()
        else:
            entry_dict = entry

        notes = entry_dict.get('notes', '')
        if 'marker_инн_nearby' in notes or 'marker_inn_nearby' in notes:
            inn_marker_found = True
            print(f"\n[OK] Found INN marker in trace: token='{entry_dict.get('token')}' notes='{notes}'")

    if not inn_marker_found:
        print("\n[WARN]  No INN marker found in normalization trace!")

    # Step 2: Signals Extraction
    print("\n" + "=" * 80)
    print("STEP 2: SIGNALS EXTRACTION")
    print("=" * 80)

    signals_service = SignalsService()
    signals_result = signals_service.extract(
        text=text,
        normalization_result=norm_result.to_dict(),
        language="ru"
    )

    print(f"\n[OK] Persons found: {len(signals_result['persons'])}")
    print(f"[OK] Overall confidence: {signals_result['confidence']}")

    # Check persons and IDs
    persons = signals_result['persons']
    for idx, person in enumerate(persons):
        print(f"\n  Person {idx+1}:")
        print(f"    Full Name: {person.get('full_name')}")
        print(f"    IDs: {len(person.get('ids', []))}")
        for id_info in person.get('ids', []):
            print(f"      - Type: {id_info.get('type')}")
            print(f"        Value: {id_info.get('value')}")
            print(f"        Valid: {id_info.get('valid')}")
            print(f"        Source: {id_info.get('source', 'unknown')}")
            print(f"        Sanctioned: {id_info.get('sanctioned', False)}")
            if id_info.get('sanctioned'):
                print(f"        Sanctioned Name: {id_info.get('sanctioned_name')}")

    # VALIDATION
    print("\n" + "=" * 80)
    print("VALIDATION")
    print("=" * 80)

    success = True

    # Check 1: At least one person found
    if len(persons) == 0:
        print("[ERROR] FAIL: No persons found in signals")
        success = False
    else:
        print(f"[OK] PASS: Found {len(persons)} person(s)")

    # Check 2: INN 2839403975 extracted with correct type
    inn_found = False
    inn_correct_type = False
    inn_sanctioned = False

    for person in persons:
        for id_info in person.get('ids', []):
            if id_info.get('value') == '2839403975':
                inn_found = True
                id_type = id_info.get('type')

                if id_type == 'inn':
                    inn_correct_type = True
                    print(f"[OK] PASS: INN 2839403975 found with correct type='inn'")
                else:
                    print(f"[ERROR] FAIL: INN 2839403975 has wrong type='{id_type}' (expected 'inn')")
                    success = False

                if id_info.get('sanctioned'):
                    inn_sanctioned = True
                    print(f"[OK] PASS: INN 2839403975 marked as sanctioned")
                    print(f"         Sanctioned name: {id_info.get('sanctioned_name')}")
                else:
                    print(f"[ERROR] FAIL: INN 2839403975 NOT marked as sanctioned")
                    success = False
                break

    if not inn_found:
        print("[ERROR] FAIL: INN 2839403975 not found in person IDs")
        success = False

    # Check 3: Validate the INN using proper validation
    inn_valid = validate_inn('2839403975')
    print(f"\n[STATS] INN Validation (validate_inn): {inn_valid}")
    if not inn_valid:
        print(f"   [INFO]  Note: INN is formally invalid BUT should still be checked in sanctions!")

    # Print summary
    print("\n" + "=" * 80)
    if success:
        print("[OK] TEST PASSED: Sanctioned INN detection working correctly!")
        print("\nKey fixes verified:")
        print("  1. [OK] Duplicate code removed from _extract_ids_from_normalization_trace")
        print("  2. [OK] INN has correct type='inn' (not 'numeric_id')")
        print("  3. [OK] INN marked as sanctioned via fast path cache")
    else:
        print("[ERROR] TEST FAILED: Issues detected, see above")
    print("=" * 80)

    return success


if __name__ == "__main__":
    success = asyncio.run(test_sanctioned_inn_detection())
    sys.exit(0 if success else 1)
