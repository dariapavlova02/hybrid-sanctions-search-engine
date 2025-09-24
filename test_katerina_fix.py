#!/usr/bin/env python3
"""
Test script to verify that Катерина is properly classified as given name.
"""

import asyncio
import json
from src.ai_service.layers.normalization.normalization_service import NormalizationService

async def test_katerina():
    """Test that Катерина is classified as given name."""
    print("🧪 Testing Катерина role classification...")

    # Initialize normalization service
    service = NormalizationService()

    # Test the problematic case
    text = "Катерина"

    try:
        result = await service.normalize_async(
            text=text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"📝 Input: '{text}'")
        print(f"✅ Normalized: '{result.normalized}'")
        print(f"🔍 Tokens: {result.tokens}")
        print(f"📊 Success: {result.success}")

        # Check trace for role classification details
        print(f"\n📋 Token Trace:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. Token: '{trace.token}' -> Role: '{trace.role}' (Rule: {trace.rule})")
            if trace.notes:
                print(f"     Notes: {trace.notes}")

        # Check persons core
        if hasattr(result, 'persons_core') and result.persons_core:
            print(f"\n👥 Persons Core: {result.persons_core}")

        return result.success and 'Катерина' in result.normalized

    except Exception as e:
        print(f"❌ Error testing Катерина: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_katerina())
    if success:
        print(f"\n✅ TEST PASSED: Катерина is properly classified!")
    else:
        print(f"\n❌ TEST FAILED: Катерина classification issue persists")
        exit(1)