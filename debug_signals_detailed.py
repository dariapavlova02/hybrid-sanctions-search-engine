#!/usr/bin/env python3
"""
Debug signals extraction in detail
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from ai_service.layers.normalization.normalization_service import NormalizationService
from ai_service.layers.signals.signals_service import SignalsService

async def debug_signals():
    """Debug signals extraction for specific test cases."""

    normalization_service = NormalizationService()
    signals_service = SignalsService()

    test_cases = [
        {
            "text": "ООО \"ТЕСТ\" ИНН 1234567890",
            "expect_orgs": True,
            "expect_numbers": True,
            "description": "Russian organization with INN"
        },
        {
            "text": "Иванов Иван Иванович дата рождения 01.01.1990",
            "expect_persons": True,
            "expect_dates": True,
            "description": "Person with birth date"
        },
        {
            "text": "ACME Holdings Ltd. Registration 12345",
            "expect_orgs": True,
            "expect_numbers": True,
            "description": "English organization"
        }
    ]

    for test_case in test_cases:
        text = test_case["text"]
        print(f"\n=== {test_case['description']} ===")
        print(f"Input: '{text}'")

        # Get normalization result first
        norm_result = await normalization_service.normalize_async(text)
        print(f"Normalized: '{norm_result.normalized}'")
        print(f"Tokens: {norm_result.tokens}")

        # Extract signals
        signals = await signals_service.extract_signals(
            text=text,
            normalization_result=norm_result.__dict__ if hasattr(norm_result, '__dict__') else {}
        )

        print(f"Signals type: {type(signals)}")
        print(f"Signals attributes: {dir(signals)}")

        # Check what we have
        has_orgs = hasattr(signals, 'organizations') and len(signals.organizations) > 0
        has_persons = hasattr(signals, 'persons') and len(signals.persons) > 0
        has_numbers = hasattr(signals, 'numbers') and bool(signals.numbers)
        has_dates = hasattr(signals, 'dates') and bool(signals.dates)
        confidence = getattr(signals, 'confidence', 0.0)

        print(f"Has organizations: {has_orgs}")
        if has_orgs:
            print(f"  Organizations: {len(signals.organizations)}")
            for org in signals.organizations:
                print(f"    {org}")

        print(f"Has persons: {has_persons}")
        if has_persons:
            print(f"  Persons: {len(signals.persons)}")
            for i, person in enumerate(signals.persons):
                print(f"    Person {i}: {person}")
                print(f"    Person {i} attributes: {dir(person)}")
                if hasattr(person, 'ids'):
                    print(f"    Person {i} IDs: {person.ids}")
                if hasattr(person, 'birth_date'):
                    print(f"    Person {i} birth_date: {person.birth_date}")
                if hasattr(person, 'dob'):
                    print(f"    Person {i} dob: {person.dob}")
                if hasattr(person, 'dob_raw'):
                    print(f"    Person {i} dob_raw: {person.dob_raw}")
                if hasattr(person, 'core'):
                    print(f"    Person {i} core: {person.core}")

        print(f"Has numbers: {has_numbers}")
        if hasattr(signals, 'numbers'):
            print(f"  Numbers: {signals.numbers}")
        else:
            print(f"  No 'numbers' attribute found")

        print(f"Has dates: {has_dates}")
        if hasattr(signals, 'dates'):
            print(f"  Dates: {signals.dates}")
        else:
            print(f"  No 'dates' attribute found")

        # Check what's in extras
        if hasattr(signals, 'extras'):
            print(f"  Extras: {signals.extras}")
        else:
            print(f"  No 'extras' attribute found")

        print(f"Confidence: {confidence}")

        # Let's also check what extractors return directly
        from ai_service.layers.signals.extractors import IdentifierExtractor, BirthdateExtractor

        id_extractor = IdentifierExtractor()
        bd_extractor = BirthdateExtractor()

        # Try identifier extraction
        try:
            org_ids = id_extractor.extract_organization_ids(text)
            person_ids = id_extractor.extract_person_ids(text)
            print(f"  Direct ID extraction - Org IDs: {org_ids}, Person IDs: {person_ids}")
        except Exception as e:
            print(f"  Direct ID extraction failed: {e}")

        # Try birthdate extraction
        try:
            birthdates = bd_extractor.extract(text)
            print(f"  Direct birthdate extraction: {birthdates}")
        except Exception as e:
            print(f"  Direct birthdate extraction failed: {e}")

        # Check expectations
        expectations_met = True
        if test_case.get("expect_orgs") and not has_orgs:
            print("  ❌ Expected organizations but none found")
            expectations_met = False
        if test_case.get("expect_persons") and not has_persons:
            print("  ❌ Expected persons but none found")
            expectations_met = False
        if test_case.get("expect_numbers") and not has_numbers:
            print("  ❌ Expected numbers but none found")
            expectations_met = False
        if test_case.get("expect_dates") and not has_dates:
            print("  ❌ Expected dates but none found")
            expectations_met = False

        if expectations_met:
            print("  ✅ All expectations met")
        else:
            print("  ❌ Some expectations not met")

if __name__ == "__main__":
    asyncio.run(debug_signals())