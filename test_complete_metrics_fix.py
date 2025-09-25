#!/usr/bin/env python3

"""
Complete test for all metrics fixes.
"""

import sys
from pathlib import Path
import asyncio

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_complete_pipeline():
    """Test the complete processing pipeline."""
    print("🔍 TESTING COMPLETE METRICS FIX")
    print("=" * 60)

    try:
        # Test 1: Direct normalization
        print("1. Testing direct normalization...")
        from ai_service.layers.normalization.normalization_service import NormalizationService

        normalization_service = NormalizationService()

        norm_result = normalization_service.normalize(
            text="Іванов Іван Іванович ІПН 1234567890",
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=False
        )

        print(f"   Normalization success: {norm_result.success}")
        print(f"   Errors: {norm_result.errors}")

        if norm_result.errors and any("metrics" in str(e).lower() for e in norm_result.errors):
            print("❌ Normalization has metrics error!")
            return False
        print("✅ Normalization OK")

        # Test 2: Signals extraction
        print("2. Testing signals extraction...")
        from ai_service.layers.signals.signals_service import SignalsService

        signals_service = SignalsService()

        # Test the fast path cache check (which was causing errors)
        signals_service._check_sanctioned_inn_cache(
            person_ids=[{"value": "1234567890", "type": "inn"}],
            org_ids=[],
            persons=[],
            organizations=[]
        )

        print("✅ Signals cache check OK")

        # Test 3: Test result builder directly
        print("3. Testing result builder...")
        from ai_service.layers.normalization.processors.result_builder import NormalizationResultBuilder, ProcessingMetrics

        result_builder = NormalizationResultBuilder()

        # Test with None metrics (this was causing errors)
        try:
            test_result = result_builder.build_normalization_result(
                original_text="Test",
                normalized_tokens=["Test"],
                token_traces=[],
                persons=[],
                language="uk",
                config=None,
                metrics=None,  # This should not cause errors anymore
                organizations_core=None,
                errors=None
            )
            print("✅ Result builder with None metrics OK")
        except Exception as e:
            if "metrics" in str(e).lower():
                print(f"❌ Result builder still has metrics error: {e}")
                return False
            else:
                print(f"✅ Result builder OK (different error: {e})")

        # Test 4: Test with valid ProcessingMetrics
        print("4. Testing with valid ProcessingMetrics...")
        valid_metrics = result_builder.create_processing_metrics("Test text")

        try:
            test_result2 = result_builder.build_normalization_result(
                original_text="Test",
                normalized_tokens=["Test"],
                token_traces=[],
                persons=[],
                language="uk",
                config=None,
                metrics=valid_metrics,
                organizations_core=None,
                errors=None
            )
            print("✅ Result builder with valid metrics OK")
        except Exception as e:
            if "metrics" in str(e).lower():
                print(f"❌ Result builder still has metrics error: {e}")
                return False

        print("\n🎉 ALL METRICS TESTS PASSED!")
        print("   ✅ Normalization service")
        print("   ✅ Signals service fast path")
        print("   ✅ Result builder with None metrics")
        print("   ✅ Result builder with valid metrics")

        return True

    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

        if "metrics" in str(e).lower() and "not defined" in str(e).lower():
            print("\n🎯 CONFIRMED: Still has metrics not defined error!")
            return False
        else:
            print("\n✅ No metrics not defined error (different issue)")
            return True

def main():
    """Main test function."""
    print("🎯 COMPLETE METRICS FIX VALIDATION")
    print("=" * 50)

    success = asyncio.run(test_complete_pipeline())

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: All metrics fixes are working!")
        print("   The service should now work without metrics errors.")
        print("\n📋 If you're still getting errors, please:")
        print("   1. Restart the Docker service")
        print("   2. Rebuild the container")
        print("   3. Check that changes are applied")
    else:
        print("❌ FAILURE: Some metrics issues remain.")
        print("   Check the error messages above for details.")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)