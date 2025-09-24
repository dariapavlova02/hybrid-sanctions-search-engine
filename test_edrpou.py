#!/usr/bin/env python3
"""
Test EDRPOU recognition specifically
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_edrpou():
    """Test EDRPOU recognition"""

    print("🔍 Testing EDRPOU recognition")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.processors.role_classifier import _is_business_document_marker

        # Test EDRPOU variations
        test_cases = ["EDRPOU", "edrpou", "Edrpou", "ЕДРПОУ", "едрпоу"]

        for test_case in test_cases:
            is_recognized = _is_business_document_marker(test_case)
            print(f"'{test_case}' → {'✅ RECOGNIZED' if is_recognized else '❌ NOT RECOGNIZED'}")

        # Test with full normalization
        from ai_service.layers.normalization.normalization_service import NormalizationService
        service = NormalizationService()

        test_text = "EDRPOU 12345678"
        print(f"\n📝 Testing: '{test_text}'")

        result = service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"📊 Tokens: {result.tokens}")
        print(f"📋 Traces:")
        for trace in result.trace:
            print(f"  '{trace.token}' → role='{trace.role}', output='{trace.output}'")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_edrpou()