#!/usr/bin/env python3
"""
Fix FSM role tagger to properly handle Russian name order.
"""

def create_improved_person_rule():
    """Create improved person rule that considers morphology."""

    improved_rule = '''
class ImprovedPersonRule(FSMTransitionRule):
    """Improved rule for person name tokens that considers morphology and dictionaries."""

    def __init__(self, role_classifier=None):
        self.role_classifier = role_classifier

    def can_apply(self, state: FSMState, token: Token, context: List[Token]) -> bool:
        # Accept both capitalized and non-capitalized names
        # but exclude punctuation, all-caps, and single characters
        return (not token.is_punct and
                not token.is_all_caps and
                len(token.text) > 1 and
                token.text.isalpha())  # Only alphabetic characters

    def apply(self, state: FSMState, token: Token, context: List[Token]) -> Tuple[FSMState, TokenRole, str, List[str]]:
        evidence = ["person_heuristic"]

        # Use role classifier to determine actual role
        if self.role_classifier:
            predicted_role = self.role_classifier._classify_personal_role(token.text, "ru")

            if predicted_role == "surname":
                if state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence
                elif state == FSMState.GIVEN_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence
                elif state == FSMState.SURNAME_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence

            elif predicted_role == "given":
                if state == FSMState.START:
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence
                elif state == FSMState.SURNAME_EXPECTED:
                    return FSMState.PATRONYMIC_EXPECTED, TokenRole.GIVEN, "given_detected", evidence
                elif state == FSMState.GIVEN_EXPECTED:
                    # Check if this token is the same as the previous given name (duplicate)
                    if context and len(context) >= 1:
                        prev_token = context[-1]  # Previous token
                        if prev_token.text.lower() == token.text.lower():
                            return FSMState.GIVEN_EXPECTED, TokenRole.GIVEN, "duplicate_given_detected", evidence
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence

            elif predicted_role == "patronymic":
                return FSMState.END, TokenRole.PATRONYMIC, "patronymic_detected", evidence

        # Fallback to original logic if no classifier or unknown role
        if state == FSMState.START:
            return FSMState.GIVEN_EXPECTED, TokenRole.GIVEN, "given_detected", evidence
        elif state == FSMState.GIVEN_EXPECTED:
            # Check if this token is the same as the previous given name (duplicate)
            if context and len(context) >= 1:
                prev_token = context[-1]  # Previous token
                if prev_token.text.lower() == token.text.lower():
                    return FSMState.GIVEN_EXPECTED, TokenRole.GIVEN, "duplicate_given_detected", evidence
            return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "given_detected", evidence
        elif state == FSMState.SURNAME_EXPECTED:
            # Check if this token is the same as the previous given name (duplicate)
            if context and len(context) >= 2:
                prev_token = context[-2]  # Previous token
                if prev_token.text.lower() == token.text.lower():
                    return FSMState.SURNAME_EXPECTED, TokenRole.GIVEN, "duplicate_given_detected", evidence
            return FSMState.PATRONYMIC_EXPECTED, TokenRole.SURNAME, "surname_detected", evidence
        else:
            return state, TokenRole.UNKNOWN, "fallback_unknown", evidence
'''

    return improved_rule

if __name__ == "__main__":
    print("Improved Person Rule:")
    print(create_improved_person_rule())