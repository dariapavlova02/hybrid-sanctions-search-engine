#!/usr/bin/env python3
"""
Debug why АНДРІЙ is classified as unknown instead of given
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_andrii_unknown():
    """Debug АНДРІЙ classification issue."""
    print("🔍 DEBUGGING АНДРІЙ UNKNOWN CLASSIFICATION")
    print("="*50)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Test the specific case
        test_input = "ШЕВЧЕНКО АНДРІЙ АНАТОЛІЙОВИЧ"
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

        print(f"\n🔍 TRACE ANALYSIS:")
        andrii_traces = []
        for trace in result.trace:
            if 'АНДРІЙ' in trace.token or 'андрій' in trace.token:
                andrii_traces.append(trace)

        print(f"Found {len(andrii_traces)} traces for АНДРІЙ:")
        for i, trace in enumerate(andrii_traces):
            print(f"  {i+1}. Token: '{trace.token}'")
            print(f"     Role: '{trace.role}'")
            print(f"     Rule: '{trace.rule}'")
            print(f"     Output: '{trace.output}'")
            print(f"     Notes: '{trace.notes}'")
            print(f"     Fallback: {trace.fallback}")
            print()

        # Test role classifier directly
        print(f"🔍 DIRECT ROLE CLASSIFIER TEST:")
        classifier = service.normalization_factory.role_classifier

        test_tokens = ["АНДРІЙ", "Андрій", "андрій"]
        for token in test_tokens:
            try:
                result_role = classifier._classify_personal_role(token, "uk")
                print(f"  '{token}' -> '{result_role}'")

                # Test if it's in given names dict
                if 'андрій' in classifier.given_names.get('uk', set()):
                    print(f"    ✅ Found 'андрій' in given_names")
                else:
                    print(f"    ❌ 'андрій' NOT in given_names")

                # Check Ukrainian names dict
                try:
                    from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES
                    if token in UKRAINIAN_NAMES or token.lower() in UKRAINIAN_NAMES:
                        print(f"    ✅ Found in UKRAINIAN_NAMES")
                    else:
                        print(f"    ❌ Not in UKRAINIAN_NAMES")
                except ImportError:
                    print(f"    ⚠️ Cannot import UKRAINIAN_NAMES")

            except Exception as e:
                print(f"  ❌ Error: {e}")

        # Check why tokens are duplicated
        print(f"\n🔍 DUPLICATION ANALYSIS:")
        token_counts = {}
        for trace in result.trace:
            token_key = trace.token.lower()
            if token_key not in token_counts:
                token_counts[token_key] = []
            token_counts[token_key].append({
                'token': trace.token,
                'role': trace.role,
                'rule': trace.rule,
                'output': trace.output
            })

        for token_key, traces in token_counts.items():
            if len(traces) > 1:
                print(f"  DUPLICATE '{token_key}': {len(traces)} times")
                for i, trace_info in enumerate(traces):
                    print(f"    {i+1}. {trace_info}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_andrii_unknown()