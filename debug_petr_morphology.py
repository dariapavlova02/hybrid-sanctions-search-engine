#!/usr/bin/env python3
"""
Debug почему Петр -> Петри вместо Петро
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def debug_petr_morphology():
    """Debug Ukrainian morphology for Петр"""
    print("🔍 DEBUGGING ПЕТР -> ПЕТРИ issue")
    print("="*40)

    token = "Петр"
    language = "uk"

    try:
        # Test pymorphy3 directly
        print("1️⃣ Testing pymorphy3 Ukrainian directly")
        from ai_service.layers.normalization.morphology_adapter import MorphologyAdapter

        adapter = MorphologyAdapter()

        # Test Ukrainian analyzer
        uk_analyzer = adapter._get_analyzer("uk")
        if uk_analyzer:
            print(f"✅ Ukrainian analyzer available")
            parses = uk_analyzer.parse(token)
            print(f"   Parses for '{token}': {len(parses)}")
            for i, p in enumerate(parses[:3]):
                print(f"     {i+1}. {p.word} - {p.tag} - normal_form: {p.normal_form}")
        else:
            print(f"❌ Ukrainian analyzer not available")

        print("\n2️⃣ Testing MorphologyAdapter normalize_to_nominative_uk")
        result = adapter.normalize_to_nominative_uk(token)
        print(f"   normalize_to_nominative_uk('{token}') -> '{result}'")

        print("\n3️⃣ Testing gender rules")
        try:
            from ai_service.layers.normalization.morphology.gender_rules import (
                convert_given_name_to_nominative_uk
            )
            result_gender = convert_given_name_to_nominative_uk(token, language)
            print(f"   convert_given_name_to_nominative_uk('{token}') -> '{result_gender}'")
        except ImportError as e:
            print(f"   ❌ Cannot import gender rules: {e}")

        print("\n4️⃣ Testing Ukrainian names dictionary")
        try:
            from ai_service.data.dicts.ukrainian_names import UKRAINIAN_NAMES

            if "Петр" in UKRAINIAN_NAMES:
                print(f"   ✅ 'Петр' found in UKRAINIAN_NAMES")
                print(f"       Data: {UKRAINIAN_NAMES['Петр']}")
            else:
                print(f"   ❌ 'Петр' not found in UKRAINIAN_NAMES")

            if "Петро" in UKRAINIAN_NAMES:
                print(f"   ✅ 'Петро' found in UKRAINIAN_NAMES")
                print(f"       Data: {UKRAINIAN_NAMES['Петро']}")
            else:
                print(f"   ❌ 'Петро' not found in UKRAINIAN_NAMES")

        except ImportError as e:
            print(f"   ❌ Cannot import UKRAINIAN_NAMES: {e}")

        print("\n5️⃣ Testing Russian names dictionary")
        try:
            from ai_service.data.dicts.russian_names import RUSSIAN_NAMES

            if "Петр" in RUSSIAN_NAMES:
                print(f"   ✅ 'Петр' found in RUSSIAN_NAMES")
                print(f"       Data: {RUSSIAN_NAMES['Петр']}")
            else:
                print(f"   ❌ 'Петр' not found in RUSSIAN_NAMES")

        except ImportError as e:
            print(f"   ❌ Cannot import RUSSIAN_NAMES: {e}")

        print("\n6️⃣ Testing morphology processor")
        try:
            from ai_service.layers.normalization.processors.morphology_processor import MorphologyProcessor

            processor = MorphologyProcessor(language="uk")
            result_processor = processor._analyzer_normalize(token, language)
            print(f"   MorphologyProcessor._analyzer_normalize('{token}', '{language}') -> '{result_processor}'")

        except Exception as e:
            print(f"   ❌ Error testing MorphologyProcessor: {e}")

        print("\n7️⃣ Testing diminutives expansion")
        try:
            from ai_service.layers.normalization.processors.morphology_processor import MorphologyProcessor

            processor = MorphologyProcessor(language="uk")
            result_dim = processor._expand_diminutive(token, language)
            print(f"   MorphologyProcessor._expand_diminutive('{token}', '{language}') -> '{result_dim}'")

        except Exception as e:
            print(f"   ❌ Error testing diminutive expansion: {e}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_petr_morphology()