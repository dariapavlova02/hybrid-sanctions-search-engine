#!/usr/bin/env python3
"""
Direct test for FSM role tagger to check if it works.
"""

import sys
sys.path.append('src')

from ai_service.layers.normalization.role_tagger_service import RoleTaggerService
from ai_service.layers.normalization.lexicon_loader import get_lexicons

def test_fsm_role_tagger():
    """Test FSM role tagger directly."""
    print("🧪 DIRECT FSM ROLE TAGGER TEST")
    print("=" * 40)

    try:
        # Create FSM role tagger
        lexicons = get_lexicons()
        fsm_tagger = RoleTaggerService()

        test_cases = [
            ("Одін Марін Інкорпорейтед", "uk"),
            ("ООО Тест", "ru"),
            ("John Inc", "en"),
        ]

        for tokens_text, language in test_cases:
            print(f"\nTesting: '{tokens_text}' (lang: {language})")
            tokens = tokens_text.split()

            # Tag with FSM
            role_tags = fsm_tagger.tag(tokens, language)

            print(f"Results:")
            for i, (token, tag) in enumerate(zip(tokens, role_tags)):
                print(f"  {i+1}. '{token}' -> {tag.role.value}")
                print(f"     Reason: {tag.reason}")
                print(f"     Evidence: {tag.evidence}")

            # Check for legal form detection
            legal_form_detected = any(
                "legal_form" in tag.reason or
                "legal_form" in str(tag.evidence) or
                tag.role.value == "unknown" and "Інкорпорейтед" in token
                for token, tag in zip(tokens, role_tags)
            )

            print(f"Legal form detected: {legal_form_detected}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_fsm_role_tagger()