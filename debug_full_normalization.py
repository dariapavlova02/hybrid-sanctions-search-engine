#!/usr/bin/env python3
"""
Debug full normalization process to see where business signals are lost
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_full_normalization():
    """Debug the full normalization process"""

    print("🔍 Debugging full normalization process")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.processors.normalization_factory_refactored import NormalizationFactoryRefactored

        # Test text with IPN
        test_text = "ІПН 782611846337"
        print(f"📝 Input: '{test_text}'")

        # Initialize factory
        factory = NormalizationFactoryRefactored()

        # Create config
        from ai_service.layers.normalization.processors.config import NormalizationConfig
        config = NormalizationConfig(
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True,
            enable_morphology=True
        )

        # Run full normalization
        import asyncio
        async def run_normalization():
            result = await factory.normalize_text(test_text, config)
            return result

        result = asyncio.run(run_normalization())

        print(f"\n📋 Full Normalization Result:")
        print(f"  Normalized text: '{result.normalized}'")
        print(f"  Tokens: {result.tokens}")
        print(f"  Success: {result.success}")
        print(f"  Errors: {result.errors}")

        print(f"\n🔍 Token Traces:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. '{trace.token}' → role='{trace.role}', output='{trace.output}', rule='{trace.rule}'")
            if hasattr(trace, 'notes') and trace.notes:
                print(f"      Notes: {trace.notes}")

        # Analyze what happened to business signals
        business_signals_in_traces = [(trace.token, trace.role) for trace in result.trace
                                     if trace.role in ["document", "business_id"]]
        business_signals_in_tokens = [token for i, token in enumerate(result.tokens)
                                     if i < len(result.trace) and result.trace[i].role in ["document", "business_id"]]

        print(f"\n📊 Business Signals Analysis:")
        print(f"  Found in traces: {business_signals_in_traces}")
        print(f"  Found in final tokens: {business_signals_in_tokens}")
        print(f"  Total traces: {len(result.trace)}")
        print(f"  Total final tokens: {len(result.tokens)}")

        # Check if business signals are preserved for Signals Service
        ipn_preserved = any(trace.token == "782611846337" and trace.role == "business_id"
                           for trace in result.trace)
        ipn_label_preserved = any(trace.token == "ІПН" and trace.role == "document"
                                 for trace in result.trace)

        print(f"\n✅ Business Signal Preservation:")
        print(f"  IPN number preserved in traces: {'✅ YES' if ipn_preserved else '❌ NO'}")
        print(f"  IPN label preserved in traces: {'✅ YES' if ipn_label_preserved else '❌ NO'}")

        # The key issue: business signals should be in tokens for Signals Service
        ipn_in_tokens = "782611846337" in result.tokens
        ipn_label_in_tokens = "ІПН" in result.tokens

        print(f"  IPN number in final tokens: {'✅ YES' if ipn_in_tokens else '❌ NO'}")
        print(f"  IPN label in final tokens: {'✅ YES' if ipn_label_in_tokens else '❌ NO'}")

        success = ipn_preserved and ipn_label_preserved and ipn_in_tokens and ipn_label_in_tokens
        print(f"\n{'✅ SUCCESS' if success else '❌ ISSUE'}: Business signals {'preserved for Signals Service' if success else 'lost in pipeline'}")

        if not success:
            print("\n🔧 Issue Diagnosis:")
            if not (ipn_in_tokens and ipn_label_in_tokens):
                print("  - Business signals are being filtered out of final tokens array")
                print("  - This prevents Signals Service from processing them")
                print("  - Need to ensure document/business_id roles reach final result")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_full_normalization()