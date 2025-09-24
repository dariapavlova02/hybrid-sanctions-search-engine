#!/usr/bin/env python3
"""
Unit tests for numeric token preservation in normalization.

Tests that numeric tokens (INN, ІПН, passport, ЄДРПОУ codes) are not removed
as "unknown" and are properly marked as candidate:identifier.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_numeric_token_preservation():
    """Test that numeric tokens are preserved and marked as candidate:identifier."""

    print("🔍 Testing numeric token preservation")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Test cases as specified in the task - focus on numeric token preservation
        test_cases = [
            {
                "text": "ІПН 2515321244",
                "expected_identifier": "2515321244",
                "description": "Ukrainian IPN - should preserve numeric identifier"
            },
            {
                "text": "TIN 782611846337",
                "expected_identifier": "782611846337",
                "description": "English TIN - should preserve numeric identifier"
            },
            {
                "text": "EDRPOU 12345678",
                "expected_identifier": "12345678",
                "description": "EDRPOU - should preserve numeric identifier"
            },
            {
                "text": "паспорт 123456789",
                "expected_identifier": "123456789",
                "description": "Passport - should preserve numeric identifier"
            },
            {
                "text": "1234567890",
                "expected_identifier": "1234567890",
                "description": "Pure numeric identifier without marker"
            }
        ]

        all_passed = True

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

            print(f"📊 Results:")
            print(f"  Tokens: {result.tokens}")
            print(f"  Token count: {len(result.tokens)}")

            # Test 1: Identifier token is preserved
            identifier_found = test_case['expected_identifier'] in result.tokens
            print(f"  ✅ Identifier preserved: {'PASS' if identifier_found else 'FAIL'} ('{test_case['expected_identifier']}')")

            # Test 2: Check trace for candidate:identifier role
            identifier_trace = None
            for trace in result.trace:
                if trace.token == test_case['expected_identifier']:
                    identifier_trace = trace
                    break

            identifier_role_correct = identifier_trace and identifier_trace.role == "candidate:identifier"
            print(f"  ✅ Identifier role: {'PASS' if identifier_role_correct else 'FAIL'} (expected 'candidate:identifier', got '{identifier_trace.role if identifier_trace else 'NOT_FOUND'}')")

            # Test 3: Identifier not filtered out as unknown
            identifier_not_unknown = identifier_trace and identifier_trace.role != "unknown"
            print(f"  ✅ Not marked as unknown: {'PASS' if identifier_not_unknown else 'FAIL'}")

            # Overall test result - focus on numeric token preservation and correct role
            test_passed = (identifier_found and identifier_role_correct and identifier_not_unknown)
            if not test_passed:
                all_passed = False

            print(f"  {'🎉 PASS' if test_passed else '❌ FAIL'}: Test case {i}")

        # Additional test: Verify FSM filtering doesn't remove numeric tokens
        print(f"\n🔧 FSM Filtering Test")
        print(f"Testing that strict_stopwords doesn't remove numeric identifiers...")

        # Test with various flags to ensure numeric tokens are always preserved
        fsm_test_text = "ІПН 1234567890 для оплати"
        fsm_result = service.normalize(
            text=fsm_test_text,
            language="uk",
            remove_stop_words=True,  # This triggers strict_stopwords in FSM
            preserve_names=True,
            enable_advanced_features=True
        )

        fsm_numeric_found = "1234567890" in fsm_result.tokens
        fsm_numeric_trace = next((trace for trace in fsm_result.trace if trace.token == "1234567890"), None)
        fsm_role_correct = fsm_numeric_trace and fsm_numeric_trace.role == "candidate:identifier"

        print(f"  Input: '{fsm_test_text}'")
        print(f"  Tokens: {fsm_result.tokens}")
        print(f"  ✅ Numeric token preserved: {'PASS' if fsm_numeric_found else 'FAIL'}")
        print(f"  ✅ Correct role assigned: {'PASS' if fsm_role_correct else 'FAIL'}")

        fsm_passed = fsm_numeric_found and fsm_role_correct
        if not fsm_passed:
            all_passed = False

        # Summary
        print(f"\n{'🎉 SUCCESS' if all_passed else '❌ FAILURES'}: All numeric token preservation tests {'passed' if all_passed else 'have issues'}")

        return all_passed

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_numeric_token_preservation()
    sys.exit(0 if success else 1)