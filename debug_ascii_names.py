#!/usr/bin/env python3
"""
Debug ASCII names in mixed script contexts.
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_ascii_names():
    """Debug ASCII names in mixed contexts."""
    print("🔍 DEBUGGING ASCII NAMES IN MIXED CONTEXTS")
    print("="*50)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Test case from the failing test
        test_input = "Владимир и John Smith работают вместе"
        print(f"Testing: '{test_input}'")

        result = service.normalize_sync(
            test_input,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"\nResult normalized: '{result.normalized}'")
        print(f"Tokens: {result.tokens}")
        print(f"Success: {result.success}")
        print(f"Errors: {result.errors}")

        print(f"\n🔍 TRACE ANALYSIS:")
        for i, trace in enumerate(result.trace):
            print(f"  {i+1}. Token: '{trace.token}' -> Role: '{trace.role}' -> Output: '{trace.output}'")
            print(f"     Rule: '{trace.rule}'")
            if trace.notes:
                print(f"     Notes: '{trace.notes[:100]}...' " if len(trace.notes) > 100 else f"     Notes: '{trace.notes}'")
            print()

        # Check if John is in the trace but not in final result
        john_traces = [trace for trace in result.trace if 'john' in trace.token.lower()]
        if john_traces:
            print("🔍 JOHN TRACE FOUND:")
            for trace in john_traces:
                print(f"  Token: '{trace.token}' -> Role: '{trace.role}' -> Output: '{trace.output}'")

        # Check if there are homoglyph warnings
        if result.homoglyph_detected:
            print("⚠️ HOMOGLYPH DETECTED:")
            print(f"  Analysis: {result.homoglyph_analysis}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ascii_names()