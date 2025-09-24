#!/usr/bin/env python3
"""
Debug why 'Порошенк' is classified as given instead of surname and why fuzzy matching doesn't work
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_poroshenko():
    """Debug Poroshenko classification and fuzzy matching."""
    print("🔍 DEBUGGING ПОРОШЕНК CLASSIFICATION")
    print("="*50)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Test cases
        test_cases = [
            "Порошенк Петро",      # With typo
            "Порошенко Петро",     # Correct
            "Порошенк",            # Only surname with typo
            "Порошенко",           # Only correct surname
        ]

        for test_input in test_cases:
            print(f"\n📝 Testing: '{test_input}'")

            result = service.normalize_sync(
                test_input,
                language="uk",
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True
            )

            print(f"  Result: '{result.normalized}'")
            print(f"  Tokens: {result.tokens}")

            # Check roles
            for trace in result.trace:
                if 'Порошен' in trace.token:
                    print(f"  Role for '{trace.token}': {trace.role}")
                    if trace.notes:
                        # Extract key info from notes
                        if "FSM role tagger" in trace.notes:
                            fsm_part = trace.notes.split("FSM role tagger:")[1].split(";")[0]
                            print(f"    FSM: {fsm_part.strip()}")
                        if "morphology_" in trace.notes:
                            morph_part = [p for p in trace.notes.split(",") if "morphology_" in p]
                            if morph_part:
                                print(f"    Morphology: {morph_part[0].strip()}")

        # Now test the role classifier directly
        print("\n" + "="*50)
        print("🔍 DIRECT ROLE CLASSIFIER TEST:")

        from ai_service.layers.normalization.processors.role_classifier import RoleClassifier
        classifier = RoleClassifier()

        test_tokens = ["Порошенк", "Порошенко", "порошенк", "порошенко"]
        for token in test_tokens:
            role = classifier._classify_personal_role(token, "uk")
            print(f"  '{token}' -> role: '{role}'")

            # Check if it's in surname dictionary
            if token.lower() in classifier.surnames.get('uk', set()):
                print(f"    ✅ Found in surnames dict")
            else:
                print(f"    ❌ NOT in surnames dict")

            # Check if it's in given names dictionary
            if token.lower() in classifier.given_names.get('uk', set()):
                print(f"    ⚠️ Found in given_names dict (unexpected!)")

        # Check FSM patterns for surname detection
        print("\n" + "="*50)
        print("🔍 CHECKING FSM SURNAME PATTERNS:")

        from ai_service.layers.normalization.role_tagger_service import RoleTaggerService

        tagger = RoleTaggerService()

        # Check if 'енк' suffix is in patterns
        if 'енк' in tagger.rules.surname_suffixes:
            print("  ✅ 'енк' suffix is in surname patterns")
        else:
            print("  ❌ 'енк' suffix NOT in surname patterns")
            print(f"  Available suffixes: {sorted(tagger.rules.surname_suffixes)}")

        # Check if 'енко' suffix is in patterns
        if 'енко' in tagger.rules.surname_suffixes:
            print("  ✅ 'енко' suffix is in surname patterns")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_poroshenko()