#!/usr/bin/env python3
"""
Test mixed case with both personal names and business signals
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_mixed_signals():
    """Test with both personal names and business signals"""

    print("🔍 Testing mixed personal names and business signals")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        # Initialize normalization service
        service = NormalizationService()

        # Test cases
        test_cases = [
            {
                "text": "Holoborodko Liudmyla ІПН 782611846337",
                "description": "Personal name + IPN",
                "expected_normalized": "Holoborodko Liudmyla",
                "expected_business_signals": ["ІПН", "782611846337"]
            },
            {
                "text": "ІПН 782611846337 Дарья Павлова",
                "description": "IPN + Personal name",
                "expected_normalized": "Дарья Павлова",
                "expected_business_signals": ["ІПН", "782611846337"]
            },
            {
                "text": "EDRPOU 12345678 ООО Компания",
                "description": "EDRPOU + Organization",
                "expected_normalized": "",  # No personal names
                "expected_business_signals": ["EDRPOU", "12345678"]
            },
        ]

        for i, test_case in enumerate(test_cases, 1):
            print(f"\n🧪 Test Case {i}: {test_case['description']}")
            print(f"📝 Input: '{test_case['text']}'")

            result = service.normalize(
                text=test_case['text'],
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            print(f"🔍 Normalized: '{result.normalized}'")
            print(f"📊 Tokens: {result.tokens}")

            # Check traces
            business_signals_in_traces = [(trace.token, trace.role) for trace in result.trace
                                         if trace.role in ["document", "business_id"]]
            personal_names_in_traces = [(trace.token, trace.role) for trace in result.trace
                                       if trace.role in ["given", "surname", "patronymic", "initial"]]

            print(f"👤 Personal names in traces: {personal_names_in_traces}")
            print(f"💼 Business signals in traces: {business_signals_in_traces}")

            # Check if business signals are in final tokens
            business_signals_in_tokens = [token for token in result.tokens
                                         if token in test_case['expected_business_signals']]

            print(f"💼 Business signals in final tokens: {business_signals_in_tokens}")

            # Verify expectations
            normalized_correct = result.normalized.strip() == test_case['expected_normalized'].strip()
            business_signals_preserved = all(sig in result.tokens for sig in test_case['expected_business_signals'])

            print(f"✅ Normalized text correct: {'YES' if normalized_correct else 'NO'}")
            print(f"✅ Business signals preserved: {'YES' if business_signals_preserved else 'NO'}")

            success = normalized_correct and business_signals_preserved
            print(f"📊 Result: {'✅ SUCCESS' if success else '❌ FAILED'}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_mixed_signals()