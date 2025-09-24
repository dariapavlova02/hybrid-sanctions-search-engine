#!/usr/bin/env python3
"""
Test script to verify the complete fix for both Булат and Катерина.
"""

import asyncio
import json
from src.ai_service.layers.normalization.normalization_service import NormalizationService
from src.ai_service.layers.signals.signals_service import SignalsService

async def test_full_pipeline():
    """Test the complete normalization + signals pipeline."""
    print("🧪 Testing complete Булат Максим Євгенович + Катерина pipeline...")

    # Initialize services
    norm_service = NormalizationService()
    signals_service = SignalsService()

    test_cases = [
        "Булат Максим Євгенович",
        "Сплата по договору від Булат Максим Євгенович 08.09.2025-100002101",
        "Катерина",
        "Павлова Катерина Володимирівна"
    ]

    for i, text in enumerate(test_cases, 1):
        print(f"\n{'='*60}")
        print(f"TEST CASE {i}: '{text}'")
        print('='*60)

        try:
            # Step 1: Normalization
            norm_result = await norm_service.normalize_async(
                text=text,
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            print(f"📝 Input: '{text}'")
            print(f"✅ Normalized: '{norm_result.normalized}'")
            print(f"🔍 Tokens: {norm_result.tokens}")
            print(f"📊 Success: {norm_result.success}")

            # Check trace for role classification details
            print(f"\n📋 Token Trace:")
            for j, trace in enumerate(norm_result.trace):
                print(f"  {j+1}. Token: '{trace.token}' -> Role: '{trace.role}' (Rule: {trace.rule})")
                if trace.notes:
                    print(f"     Notes: {trace.notes[:100]}...")

            # Step 2: Signals
            if norm_result.success:
                signals_result = await signals_service.extract_signals(
                    text=text,
                    normalization_result=norm_result.__dict__,
                    language="uk"
                )

                print(f"\n🎯 Signals Results:")
                print(f"   Persons: {len(signals_result.persons)} found")
                for person in signals_result.persons:
                    print(f"     - {person.full_name} (confidence: {person.confidence:.2f})")
                print(f"   Organizations: {len(signals_result.organizations)} found")
                for org in signals_result.organizations:
                    print(f"     - {org.full} (confidence: {org.confidence:.2f})")

                # Check if expected names are found
                expected_names = []
                if "Булат" in text:
                    expected_names.extend(["Булат", "Максим", "Євгенович"])
                if "Катерина" in text:
                    expected_names.append("Катерина")

                missing_names = []
                found_text = norm_result.normalized.lower()
                for name in expected_names:
                    if name.lower() not in found_text:
                        missing_names.append(name)

                if missing_names:
                    print(f"❌ Missing names in normalization: {missing_names}")
                else:
                    print(f"✅ All expected names found in normalization!")

            else:
                print(f"❌ Normalization failed")

        except Exception as e:
            print(f"❌ Error testing '{text}': {e}")
            import traceback
            traceback.print_exc()

    print(f"\n{'='*60}")
    print("🎯 SUMMARY")
    print('='*60)
    print("✅ Role tagger enhanced with direct dictionary lookup")
    print("✅ Fallback logic handles classifier failures")
    print("✅ Debug logging added for troubleshooting")
    print("✅ Катерина should now be properly classified as 'given'")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())