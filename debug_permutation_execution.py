#!/usr/bin/env python3
"""
Debug why permutation generation code isn't executing
"""

import sys
sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

def debug_permutation_execution():
    """Debug why permutation generation isn't running"""

    print("🔍 DEBUG PERMUTATION EXECUTION PATH")
    print("=" * 60)

    try:
        from ai_service.layers.variants.templates.high_recall_ac_generator import HighRecallACGenerator

        # Create custom generator to inject debug
        class DebugACGenerator(HighRecallACGenerator):
            def generate_high_recall_patterns(self, text, language="auto", entity_metadata=None):
                print(f"📍 Called generate_high_recall_patterns with:")
                print(f"   text: '{text}'")
                print(f"   language: '{language}'")

                # Determine language before normalization
                if language == "auto":
                    language = self._detect_language(text)
                    print(f"   detected language: '{language}'")

                # Normalize text for AC
                normalized_text = self.normalize_for_ac(text)
                print(f"   normalized_text: '{normalized_text}'")

                patterns = []
                entity_metadata = entity_metadata or {}

                # Skip all other processing, go directly to permutation generation
                print(f"\n🔄 PERMUTATION GENERATION TEST:")

                # Extract components from original text (before normalization) for Title Case
                original_parts = self._extract_name_components(text, language)
                normalized_parts = self._extract_name_components(normalized_text, language)

                print(f"   original_parts: {original_parts}")
                print(f"   normalized_parts: {normalized_parts}")
                print(f"   len(original_parts) >= 2: {len(original_parts) >= 2}")
                print(f"   len(normalized_parts) >= 2: {len(normalized_parts) >= 2}")

                if len(original_parts) >= 2 and len(normalized_parts) >= 2:
                    print(f"   ✅ Conditions met for permutation generation")

                    # Original case versions for Title Case patterns
                    orig_surname = original_parts[0] if original_parts else ""
                    orig_first_name = original_parts[1] if len(original_parts) > 1 else ""
                    orig_patronymic = original_parts[2] if len(original_parts) > 2 else ""

                    print(f"   orig_surname: '{orig_surname}'")
                    print(f"   orig_first_name: '{orig_first_name}'")
                    print(f"   orig_patronymic: '{orig_patronymic}'")
                    print(f"   orig_surname and orig_first_name: {orig_surname and orig_first_name}")

                    if orig_surname and orig_first_name:
                        print(f"   ✅ Generating Title Case permutations...")

                        # Generate Title Case permutations
                        title_case_permutations = self._generate_name_permutations(orig_surname, orig_first_name, orig_patronymic, language)
                        print(f"   title_case_permutations count: {len(title_case_permutations)}")

                        for i, perm in enumerate(title_case_permutations[:5], 1):
                            title_case_variant = self.normalize_for_ac(perm, preserve_case=True)
                            print(f"      {i}. '{perm}' → '{title_case_variant}'")
                            patterns.append(f"TITLE_CASE: {title_case_variant}")

                        # Check for our target
                        target_found = False
                        for perm in title_case_permutations:
                            title_case_variant = self.normalize_for_ac(perm, preserve_case=True)
                            if "Liudmyla Ulianova" in title_case_variant:
                                print(f"   🎯 TARGET FOUND: '{title_case_variant}'")
                                target_found = True

                        if not target_found:
                            print(f"   ❌ Target 'Liudmyla Ulianova' not found in permutations")

                else:
                    print(f"   ❌ Conditions NOT met for permutation generation")

                print(f"\n📊 Generated {len(patterns)} debug patterns")
                return patterns

        generator = DebugACGenerator()

        # Test with our name
        test_name = "Ulianova Liudmyla Oleksandrivna"
        patterns = generator.generate_high_recall_patterns(test_name, language="en")

        return len(patterns) > 0

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    success = debug_permutation_execution()

    print(f"\n🎯 RESULT: {'SUCCESS' if success else 'FAILED'}")

if __name__ == "__main__":
    main()