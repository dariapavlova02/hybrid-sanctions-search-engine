#!/usr/bin/env python3
"""
Debug IPN recognition pipeline step by step
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_ipn_pipeline():
    """Debug the IPN recognition pipeline step by step"""

    print("🔍 Debugging IPN recognition pipeline")
    print("=" * 60)

    try:
        from ai_service.layers.normalization.processors.token_processor import TokenProcessor
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier

        # Test text with IPN
        test_text = "ІПН 782611846337"
        print(f"📝 Input: '{test_text}'")

        # Step 1: Tokenization
        processor = TokenProcessor()
        tokens, traces, metadata = processor.strip_noise_and_tokenize(
            test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True
        )

        print(f"\n🔧 Step 1 - Tokenization:")
        print(f"  Tokens: {tokens}")
        print(f"  Traces: {traces[-3:] if len(traces) > 3 else traces}")  # Last few traces

        # Step 2: Role Classification
        classifier = RoleClassifier()
        tagged_tokens, role_traces, organizations = classifier.tag_tokens(
            tokens, language="uk"
        )

        print(f"\n🏷️  Step 2 - Role Classification:")
        for token, role in tagged_tokens:
            print(f"  '{token}' → role='{role}'")
        print(f"  Role traces: {role_traces}")
        print(f"  Organizations detected: {organizations}")

        # Check if business signals are preserved
        business_signals = [(token, role) for token, role in tagged_tokens
                          if role in ["document", "business_id"]]
        name_tokens = [(token, role) for token, role in tagged_tokens
                      if role in ["given", "surname", "patronymic", "initial"]]

        print(f"\n📊 Analysis:")
        print(f"  Business signals found: {business_signals}")
        print(f"  Name tokens found: {name_tokens}")
        print(f"  Total tokens: {len(tagged_tokens)}")

        # Expected results
        expected_ipn_label = any(token == "ІПН" and role == "document" for token, role in tagged_tokens)
        expected_ipn_number = any(token == "782611846337" and role == "business_id" for token, role in tagged_tokens)

        print(f"\n✅ Expected Results:")
        print(f"  IPN label classified as 'document': {'✅ YES' if expected_ipn_label else '❌ NO'}")
        print(f"  IPN number classified as 'business_id': {'✅ YES' if expected_ipn_number else '❌ NO'}")

        success = expected_ipn_label and expected_ipn_number
        print(f"\n{'✅ SUCCESS' if success else '❌ FAILED'}: Pipeline step-by-step {'works' if success else 'has issues'}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ipn_pipeline()