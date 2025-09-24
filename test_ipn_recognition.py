#!/usr/bin/env python3
"""
Test IPN recognition and sanctions search
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_ipn_recognition():
    """Test that IPN numbers are recognized and trigger sanctions search"""

    print("🔍 Testing IPN recognition and sanctions search")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        # Initialize normalization service
        service = NormalizationService()

        # Test text with IPN
        test_text = "ІПН 782611846337"

        print(f"📝 Input: '{test_text}'")

        # Run normalization
        result = service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"🔍 Normalized: '{result.normalized}'")
        print(f"📊 Tokens: {result.tokens}")

        # Check traces
        print(f"\n📋 Token traces:")
        for trace in result.trace:
            print(f"  {trace.token} → role={trace.role}, rule={trace.rule}, output={trace.output}")
            if hasattr(trace, 'notes') and trace.notes:
                print(f"    Notes: {trace.notes}")

        # Test if IPN is being properly recognized
        ipn_found = any("782611846337" in token for token in result.tokens)
        ipn_trace_found = any("782611846337" in trace.token for trace in result.trace)

        print(f"\n🎯 IPN number found in tokens: {'✅ YES' if ipn_found else '❌ NO'}")
        print(f"🎯 IPN number found in traces: {'✅ YES' if ipn_trace_found else '❌ NO'}")

        # Check if IPN-related tokens are properly classified
        ipn_label_trace = None
        ipn_number_trace = None

        for trace in result.trace:
            if "ІПН" in trace.token.upper():
                ipn_label_trace = trace
            elif "782611846337" in trace.token:
                ipn_number_trace = trace

        if ipn_label_trace:
            print(f"🏷️  IPN label '{ipn_label_trace.token}' → role={ipn_label_trace.role}")
        if ipn_number_trace:
            print(f"🔢 IPN number '{ipn_number_trace.token}' → role={ipn_number_trace.role}")

        # Expected behavior: IPN should be recognized as business signal, not unknown
        success = (
            ipn_found and
            ipn_trace_found and
            ipn_number_trace and
            ipn_number_trace.role != "unknown"
        )

        print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: IPN recognition {'works' if success else 'does not work'}")

        if not success:
            print("\n🔧 Issues found:")
            if not ipn_found:
                print("  - IPN number not found in tokens")
            if not ipn_trace_found:
                print("  - IPN number not found in traces")
            if ipn_number_trace and ipn_number_trace.role == "unknown":
                print(f"  - IPN number classified as 'unknown' instead of business signal")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_ipn_recognition()