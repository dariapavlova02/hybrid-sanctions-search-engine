#!/usr/bin/env python3
"""
Debug which FSM rule is being applied to АНДРІЙ and why it's not reaching DefaultPersonRule.
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_fsm_rule_priority():
    """Debug FSM rule priority for АНДРІЙ."""
    print("🔍 DEBUGGING FSM RULE PRIORITY FOR АНДРІЙ")
    print("="*50)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.normalization.role_tagger_service import RoleTaggerService, Token, FSMState

        service = NormalizationService()
        role_tagger = service.normalization_factory.role_tagger_service

        # Create a Token object for АНДРІЙ
        test_token = Token(
            text="АНДРІЙ",
            norm="АНДРІЙ",
            is_capitalized=True,
            is_all_caps=True,
            has_hyphen=False,
            pos=1,  # Second position (after ШЕВЧЕНКО)
            lang="uk"
        )

        # Test each rule individually to see which one would match
        context_tokens = [
            Token(text="ШЕВЧЕНКО", norm="ШЕВЧЕНКО", is_capitalized=True, is_all_caps=True, has_hyphen=False, pos=0, lang="uk"),
            test_token,
            Token(text="АНАТОЛІЙОВИЧ", norm="АНАТОЛІЙОВИЧ", is_capitalized=True, is_all_caps=True, has_hyphen=False, pos=2, lang="uk")
        ]

        # Test each rule in priority order
        state = FSMState.SURNAME_EXPECTED  # After ШЕВЧЕНКО (surname)

        print(f"Testing token: '{test_token.text}' at position {test_token.pos}")
        print(f"Current FSM state: {state}")
        print(f"Token properties: capitalized={test_token.is_capitalized}, all_caps={test_token.is_all_caps}")
        print()

        for i, rule in enumerate(role_tagger.rules_list):
            rule_name = rule.__class__.__name__
            can_apply = rule.can_apply(state, test_token, context_tokens)
            print(f"{i+1:2d}. {rule_name:<30} can_apply: {can_apply}")

            if can_apply:
                try:
                    new_state, role, reason, evidence = rule.apply(state, test_token, context_tokens)
                    print(f"    → Would apply: role={role.value}, reason={reason}, evidence={evidence}")
                    print(f"    → State transition: {state} → {new_state}")
                    print(f"    🔥 FIRST MATCHING RULE - АНДРІЙ would be classified as '{role.value}'")
                    break
                except Exception as e:
                    print(f"    → Error applying rule: {e}")
            print()

        # Also test the DefaultPersonRule specifically
        print("\n" + "="*50)
        print("TESTING DefaultPersonRule SPECIFICALLY:")

        default_rule = None
        for rule in role_tagger.rules_list:
            if rule.__class__.__name__ == "DefaultPersonRule":
                default_rule = rule
                break

        if default_rule:
            can_apply = default_rule.can_apply(state, test_token, context_tokens)
            print(f"DefaultPersonRule can_apply: {can_apply}")

            if can_apply:
                try:
                    new_state, role, reason, evidence = default_rule.apply(state, test_token, context_tokens)
                    print(f"DefaultPersonRule would return: role={role.value}, reason={reason}, evidence={evidence}")

                    # Test the role classifier directly
                    if default_rule.role_classifier:
                        predicted_role = default_rule.role_classifier._classify_personal_role(test_token.text, "uk")
                        print(f"Role classifier returns: {predicted_role}")

                        # Check if АНДРІЙ is in given names
                        if 'андрій' in default_rule.role_classifier.given_names.get('uk', set()):
                            print("✅ 'андрій' IS in given_names['uk']")
                        else:
                            print("❌ 'андрій' NOT in given_names['uk']")

                except Exception as e:
                    print(f"Error applying DefaultPersonRule: {e}")
        else:
            print("❌ DefaultPersonRule not found!")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_fsm_rule_priority()