#!/usr/bin/env python3
"""
Debug role classification for 'Коваленко Олександра Сергіївна'
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_role_classification():
    """Debug why 'Олександра' is classified as surname instead of given name."""
    print("🔍 DEBUGGING ROLE CLASSIFICATION")
    print("="*40)

    # Test the specific case from user
    test_text = "Коваленко Олександра Сергіївна"

    try:
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier

        classifier = RoleClassifier()

        # Tokenize first
        tokens = test_text.split()
        print(f"Tokens: {tokens}")

        # Use the main method
        tagged_tokens, traces, organizations = classifier.tag_tokens(tokens, "uk")

        print(f"\n📊 Tagged tokens:")
        for token, role in tagged_tokens:
            print(f"  '{token}' -> '{role}'")

        print(f"\n🔍 Traces:")
        for trace in traces:
            print(f"  {trace}")

        print(f"\n🏢 Organizations:")
        for org in organizations:
            print(f"  {org}")

        # Test individual _classify_personal_role method
        print(f"\n🧪 Individual role classification:")
        for token in tokens:
            role = classifier._classify_personal_role(token, "uk")
            print(f"  '{token}' -> '{role}' (via _classify_personal_role)")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_role_classification()