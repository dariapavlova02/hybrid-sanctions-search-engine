#!/usr/bin/env python3
"""
Simple test for role classification fix.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_role_classifier_directly():
    """Test the role classifier directly to see if suffix detection works."""
    print("Testing role classifier suffix detection...")

    try:
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier
        from ai_service.data.dicts.diminutives_extra import get_diminutive_maps, get_name_dictionaries

        # Initialize role classifier
        name_dicts = get_name_dictionaries()
        dim_maps = get_diminutive_maps()
        classifier = RoleClassifier(name_dicts, dim_maps)

        # Test cases
        test_cases = [
            ("Павловой", "ru"),  # Should be surname (genitive/dative case)
            ("Дарья", "ru"),     # Should be given name
            ("Юрьевна", "ru"),   # Should be patronymic
            ("Иванов", "ru"),    # Should be surname
            ("Петр", "ru"),      # Should be given name
            ("Сергеевич", "ru")  # Should be patronymic
        ]

        print("\nDirect role classification tests:")
        for token, lang in test_cases:
            role = classifier._classify_personal_role(token, lang)
            print(f"  {token} ({lang}) -> {role}")

        # Check if "Павловой" is correctly identified as surname
        pavlova_role = classifier._classify_personal_role("Павловой", "ru")
        if pavlova_role == "surname":
            print("\n✅ SUCCESS: 'Павловой' correctly identified as surname")
        else:
            print(f"\n❌ FAIL: 'Павловой' identified as '{pavlova_role}', expected 'surname'")

        return True

    except Exception as e:
        print(f"Error testing role classifier: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_fsm_rule_directly():
    """Test the FSM rule directly."""
    print("\n" + "="*50)
    print("Testing FSM rule directly...")

    try:
        from ai_service.layers.normalization.role_tagger_service import DefaultPersonRule, Token, FSMState
        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier
        from ai_service.data.dicts.diminutives_extra import get_diminutive_maps, get_name_dictionaries

        # Initialize role classifier
        name_dicts = get_name_dictionaries()
        dim_maps = get_diminutive_maps()
        classifier = RoleClassifier(name_dicts, dim_maps)

        # Create the improved FSM rule
        rule = DefaultPersonRule(role_classifier=classifier, language="ru")

        # Create test tokens
        def create_token(text):
            return Token(
                text=text,
                is_punct=False,
                is_all_caps=text.isupper(),
                lang="ru"
            )

        tokens = [
            create_token("Павловой"),
            create_token("Дарья"),
            create_token("Юрьевна")
        ]

        print("\nFSM rule tests:")
        state = FSMState.START
        context = []

        for token in tokens:
            if rule.can_apply(state, token, context):
                new_state, role, reason, evidence = rule.apply(state, token, context)
                print(f"  {token.text}: {state.name} -> {new_state.name}, role={role.value}, reason={reason}, evidence={evidence}")
                state = new_state
                context.append(token)
            else:
                print(f"  {token.text}: rule cannot apply")

        return True

    except Exception as e:
        print(f"Error testing FSM rule: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success1 = test_role_classifier_directly()
    success2 = test_fsm_rule_directly()

    if success1 and success2:
        print("\n🎉 All tests completed!")
    else:
        print("\n❌ Some tests failed")