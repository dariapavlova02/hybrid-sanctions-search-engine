#!/usr/bin/env python3
"""
Debug why АНДРІЙ is marked as unknown
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_andrii_role():
    """Debug why АНДРІЙ is not recognized as given name."""
    print("🔍 DEBUGGING АНДРІЙ ROLE CLASSIFICATION")
    print("="*40)

    test_tokens = ["ШЕВЧЕНКО", "АНДРІЙ", "АНАТОЛІЙОВИЧ"]

    try:
        # Use the same classifier instance as normalization service
        from ai_service.layers.normalization.normalization_service import NormalizationService
        service = NormalizationService()
        classifier = service.normalization_factory.role_classifier

        print(f"🔍 Classifier given_names for uk: {len(classifier.given_names.get('uk', set()))} names")
        uk_names = classifier.given_names.get('uk', set())
        if 'андрій' in uk_names:
            print(f"    ✅ 'андрій' is in classifier.given_names['uk']")
        else:
            print(f"    ❌ 'андрій' is NOT in classifier.given_names['uk']")

        print("🔍 Individual token classification:")
        for token in test_tokens:
            try:
                result = classifier._classify_personal_role(token, "uk")
                print(f"  '{token}' -> '{result}'")

                # Also test with lowercase
                result_lower = classifier._classify_personal_role(token.lower(), "uk")
                print(f"  '{token.lower()}' -> '{result_lower}'")

                # Test if it's in Ukrainian names dict
                try:
                    from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES
                    if token in UKRAINIAN_NAMES:
                        print(f"    ✅ Found in UKRAINIAN_NAMES")
                        print(f"    Data: {UKRAINIAN_NAMES[token]}")
                    elif token.lower() in UKRAINIAN_NAMES:
                        print(f"    ✅ Found in UKRAINIAN_NAMES (lowercase)")
                    elif token.capitalize() in UKRAINIAN_NAMES:
                        print(f"    ✅ Found in UKRAINIAN_NAMES (capitalized)")
                        print(f"    Data: {UKRAINIAN_NAMES[token.capitalize()]}")
                    else:
                        print(f"    ❌ Not found in UKRAINIAN_NAMES")
                except ImportError:
                    print(f"    ⚠️ Cannot import UKRAINIAN_NAMES")

            except Exception as e:
                print(f"  ❌ Error classifying '{token}': {e}")

        print(f"\n🔍 Full token sequence classification:")
        try:
            tagged_tokens, traces, organizations = classifier.tag_tokens(test_tokens, "uk")

            print("Tagged tokens:")
            for token, role in tagged_tokens:
                print(f"  '{token}' -> '{role}'")

            print("\nTraces:")
            for trace in traces:
                print(f"  {trace}")

        except Exception as e:
            print(f"❌ Error in full classification: {e}")

        print(f"\n🔍 Testing recognition patterns:")
        # Test if АНДРІЙ matches Ukrainian given name patterns
        test_cases = ["Андрій", "АНДРІЙ", "андрій"]
        for case in test_cases:
            print(f"\nTesting '{case}':")

            # Check if it looks like given name
            is_given = classifier._is_personal_candidate(case, "uk")
            print(f"  _is_personal_candidate: {is_given}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_andrii_role()