#!/usr/bin/env python3
"""
Debug result builder specifically
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_result_builder():
    """Debug the result builder specifically"""

    print("🔍 Debugging result builder")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        # Test text with IPN
        test_text = "ІПН 782611846337"
        print(f"📝 Input: '{test_text}'")

        # Initialize normalization service
        service = NormalizationService()

        # Run normalization
        result = service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\n📋 Result Details:")
        print(f"  Normalized: '{result.normalized}'")
        print(f"  Tokens: {result.tokens}")
        print(f"  Trace count: {len(result.trace)}")

        print(f"\n🔍 Detailed Trace Analysis:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. Token: '{trace.token}'")
            print(f"      Role: '{trace.role}'")
            print(f"      Output: '{trace.output}'")
            print(f"      Rule: '{trace.rule}'")
            if hasattr(trace, 'notes') and trace.notes:
                print(f"      Notes: {trace.notes}")
            print()

        # Check what's happening in result builder logic
        print(f"📊 Result Builder Analysis:")

        processed_tokens_would_be = []
        for i, trace in enumerate(result.trace):
            if hasattr(trace, 'output') and trace.output:
                processed_tokens_would_be.append(trace.output)
                print(f"  Would include: '{trace.output}' (from trace {i+1})")
            else:
                print(f"  Would skip: trace {i+1} - no valid output")

        print(f"\n  Expected tokens from traces: {processed_tokens_would_be}")
        print(f"  Actual tokens in result: {result.tokens}")
        print(f"  Match: {'✅ YES' if processed_tokens_would_be == result.tokens else '❌ NO'}")

        if processed_tokens_would_be != result.tokens:
            print(f"\n🔧 Mismatch Details:")
            print(f"  Expected: {processed_tokens_would_be}")
            print(f"  Actual: {result.tokens}")
            print(f"  Issue: Result builder logic may not be working as expected")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_result_builder()