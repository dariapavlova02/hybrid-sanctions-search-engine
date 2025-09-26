#!/usr/bin/env python3
"""
Test the full normalization pipeline for "Одін Марін Інкорпорейтед".
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory, NormalizationConfig
from ai_service.layers.signals.signals_service import SignalsService
import asyncio
import json

async def test_odin_marin_full_pipeline():
    """Test the full pipeline for Odin Marin Incorporated."""
    print("🧪 TESTING FULL PIPELINE FOR 'Одін Марін Інкорпорейтед'")
    print("=" * 60)

    # Create factory instance
    factory = NormalizationFactory(
        name_dictionaries=None,
        diminutive_maps=None
    )

    # Test configuration
    config = NormalizationConfig(
        language="uk",
        remove_stop_words=True,
        preserve_names=True,
        enable_advanced_features=True,
        enable_morphology=True,
        enable_cache=True,
        enable_fsm_tuned_roles=True  # Enable FSM role tagger!
    )

    test_text = "Одін Марін Інкорпорейтед"
    print(f"Testing: '{test_text}'")

    try:
        # Step 1: Normalization
        print(f"\n🔄 Step 1: Normalization")
        norm_result = await factory.normalize_text(test_text, config)

        print(f"Normalized: '{norm_result.normalized}'")
        print(f"Tokens: {norm_result.tokens}")

        print(f"\nToken trace:")
        for i, trace in enumerate(norm_result.trace):
            print(f"  {i+1}. '{trace.token}' -> '{trace.output}' (role: {trace.role})")
            if trace.notes:
                print(f"      Notes: {trace.notes[:100]}...")  # First 100 chars

        # Step 2: Signals extraction
        print(f"\n🔄 Step 2: Signals Extraction")
        signals_service = SignalsService()

        signals_result = signals_service.extract_signals(
            original_text=test_text,
            normalized_result=norm_result,
            language="uk"
        )

        print(f"Persons found: {len(signals_result.persons)}")
        for person in signals_result.persons:
            print(f"  Person: {person.core} -> {person.full_name}")

        print(f"Organizations found: {len(signals_result.organizations)}")
        for org in signals_result.organizations:
            print(f"  Org: core='{org.core}', legal_form='{org.legal_form}', full='{org.full}'")

        print(f"Overall confidence: {signals_result.confidence}")

        # Expected result: Should be an organization, not a person
        if signals_result.organizations:
            org = signals_result.organizations[0]
            if org.legal_form == "Інкорпорейтед" and org.core and "Марін" in str(org.core):
                print(f"\n✅ SUCCESS: Correctly identified as organization!")
                print(f"  Core: {org.core}")
                print(f"  Legal form: {org.legal_form}")
                print(f"  Full name: {org.full}")
            else:
                print(f"\n⚠️  PARTIAL: Organization found but details may be incomplete")
                print(f"  Legal form: {org.legal_form}")
                print(f"  Core: {org.core}")
        else:
            print(f"\n❌ FAILED: Not identified as organization")

        if signals_result.persons and not signals_result.organizations:
            print(f"  Issue: Still classified as person instead of organization")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_odin_marin_full_pipeline())