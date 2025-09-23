#!/usr/bin/env python3
"""
Debug FSM processing for patronymic classification.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def debug_fsm_process():
    """Debug FSM processing step by step."""
    print("Debugging FSM processing...")

    try:
        from ai_service.layers.normalization.role_tagger_service import DefaultPersonRule, Token, FSMState
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier

        # Create role classifier
        classifier = RoleClassifier({}, {})

        # Create the FSM rule
        rule = DefaultPersonRule(role_classifier=classifier, language="ru")

        # Create test tokens for the full phrase
        def create_token(text):
            return Token(
                text=text,
                is_punct=False,
                is_all_caps=text.isupper(),
                lang="ru"
            )

        tokens = [
            create_token("Павловой"),  # Should be surname
            create_token("Даши"),      # Should be given (diminutive)
            create_token("Юрьевной")   # Should be patronymic
        ]

        print("\nTesting individual role classification:")
        for token in tokens:
            role = classifier._classify_personal_role(token.text, "ru")
            print(f"  '{token.text}' -> {role}")

        print("\nTesting FSM step by step:")
        state = FSMState.START
        context = []

        for i, token in enumerate(tokens):
            print(f"\nStep {i+1}: Processing '{token.text}'")
            print(f"  Current state: {state.name}")
            print(f"  Context: {[t.text for t in context]}")

            if rule.can_apply(state, token, context):
                # Check what the role classifier says
                predicted_role = classifier._classify_personal_role(token.text, "ru")
                print(f"  Role classifier says: '{predicted_role}'")

                new_state, role, reason, evidence = rule.apply(state, token, context)
                print(f"  FSM result: {state.name} -> {new_state.name}")
                print(f"  Assigned role: {role.value}")
                print(f"  Reason: {reason}")
                print(f"  Evidence: {evidence}")

                state = new_state
                context.append(token)
            else:
                print(f"  Rule cannot apply")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_fsm_process()