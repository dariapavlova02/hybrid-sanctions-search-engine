#!/usr/bin/env python3
"""
Debug why 'Порошенк' is classified differently in different contexts
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_order_sensitivity():
    """Debug order sensitivity in classification."""
    print("🔍 DEBUGGING ORDER SENSITIVITY")
    print("="*50)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService
        from ai_service.layers.normalization.role_tagger_service import RoleTaggerService, Token, FSMState

        service = NormalizationService()

        # Test what language detection returns
        print("🌍 LANGUAGE DETECTION TEST:")
        test_inputs = [
            "Порошенк Петро",
            "Порошенко Петро Олексійович"
        ]

        for text in test_inputs:
            from ai_service.layers.language.language_detection_service import LanguageDetectionService
            lang_service = LanguageDetectionService()
            detected = lang_service.detect_language(text)
            print(f"  '{text}' -> language: {detected['language']} (conf: {detected['confidence']:.2f})")

        # Now test FSM with detected language
        print("\n🔍 FSM ROLE TAGGER TEST:")

        role_tagger = service.normalization_factory.role_tagger_service

        # Create tokens for "Порошенк Петро"
        tokens = ["Порошенк", "Петро"]

        # Test with different languages
        for lang in ["uk", "ru", "unknown", "auto"]:
            print(f"\n  Language: {lang}")
            role_tags = role_tagger.tag(tokens, lang)

            for i, (token, tag) in enumerate(zip(tokens, role_tags)):
                print(f"    {token}: {tag.role.value} (reason: {tag.reason})")
                if tag.evidence:
                    print(f"      Evidence: {tag.evidence}")

        # Test the DefaultPersonRule directly
        print("\n🔍 DEFAULT PERSON RULE TEST:")

        from ai_service.layers.normalization.role_tagger_service import DefaultPersonRule

        # Create test token for Порошенк
        test_token = Token(
            text="Порошенк",
            norm="Порошенк",
            is_capitalized=True,
            is_all_caps=False,
            has_hyphen=False,
            pos=0,
            lang="uk"
        )

        # Check what DefaultPersonRule would do at START state
        default_rule = DefaultPersonRule(role_classifier=role_tagger.role_classifier, language="uk", lexicons=role_tagger.lexicons)

        if default_rule.can_apply(FSMState.START, test_token, [test_token]):
            new_state, role, reason, evidence = default_rule.apply(FSMState.START, test_token, [test_token])
            print(f"  DefaultPersonRule at START would assign: {role.value}")
            print(f"    Reason: {reason}")
            print(f"    Evidence: {evidence}")

        # Check role classifier prediction
        if default_rule.role_classifier:
            predicted = default_rule.role_classifier._classify_personal_role("Порошенк", "uk")
            print(f"\n  Role classifier predicts: {predicted}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_order_sensitivity()