#!/usr/bin/env python3
"""
Debug real FSM processing to see what happens to Юрьевной.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_real_fsm():
    """Debug the real FSM processing."""
    print("Debugging real FSM processing...")

    try:
        from ai_service.layers.normalization.processors.normalization_factory import NormalizationFactory
        from ai_service.layers.normalization.processors.config import NormalizationConfig

        # Initialize factory
        factory = NormalizationFactory()

        # Create config
        config = NormalizationConfig(
            language="ru",
            enable_advanced_features=True,
            remove_stop_words=True,
            preserve_names=True
        )

        # Get tokens
        test_text = "Павловой Даши Юрьевной"
        tokens = test_text.split()

        print(f"Testing tokens: {tokens}")

        # Test FSM role tagger directly
        print("\n=== FSM Role Tagger Test ===")
        if hasattr(factory, 'role_tagger_service') and factory.role_tagger_service:
            role_tags = factory.role_tagger_service.tag(tokens, config.language)
            print(f"FSM role tags:")
            for i, tag in enumerate(role_tags):
                print(f"  {i}: '{tokens[i]}' -> {tag.role.value} (reason: {tag.reason}, evidence: {tag.evidence})")

            # Show FSM roles
            fsm_roles = [tag.role.value for tag in role_tags]
            print(f"FSM roles: {fsm_roles}")
        else:
            print("No FSM role tagger service available")

        # Test role classifier directly
        print("\n=== Role Classifier Test ===")
        if hasattr(factory, 'role_classifier') and factory.role_classifier:
            for token in tokens:
                role = factory.role_classifier._classify_personal_role(token, config.language)
                print(f"  '{token}' -> {role}")
        else:
            print("No role classifier available")

        # Check if the DefaultPersonRule has role classifier
        print("\n=== DefaultPersonRule Test ===")
        if hasattr(factory, 'role_tagger_service') and factory.role_tagger_service:
            for rule in factory.role_tagger_service.rules_list:
                if hasattr(rule, '__class__') and 'DefaultPersonRule' in str(rule.__class__):
                    print(f"Found DefaultPersonRule: {rule}")
                    print(f"  has role_classifier: {hasattr(rule, 'role_classifier')}")
                    if hasattr(rule, 'role_classifier'):
                        print(f"  role_classifier is None: {rule.role_classifier is None}")
                        if rule.role_classifier:
                            test_result = rule.role_classifier._classify_personal_role("Юрьевной", "ru")
                            print(f"  Test Юрьевной: {test_result}")
                    break
        else:
            print("No FSM rules available")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_real_fsm()