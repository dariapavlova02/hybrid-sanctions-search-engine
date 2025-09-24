#!/usr/bin/env python3
"""
Debug name dictionary loading
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def debug_name_loading():
    """Debug name dictionary loading."""
    print("🔍 DEBUGGING NAME DICTIONARY LOADING")
    print("="*40)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        service = NormalizationService()

        # Test _load_name_dictionaries directly
        print("🔍 Loading name dictionaries...")
        name_dictionaries = service._load_name_dictionaries()

        print(f"📊 Loaded dictionaries: {list(name_dictionaries.keys())}")
        for key, value in name_dictionaries.items():
            print(f"  '{key}': {len(value) if value else 0} entries")
            if 'uk' in key and value:
                # Show some Ukrainian names
                sample_names = list(value)[:10]
                print(f"    Sample: {sample_names}")

        # Test Ukrainian names import directly
        print(f"\n🔍 Direct Ukrainian names test:")
        try:
            from ai_service.data.dicts import ukrainian_names
            print(f"✅ Ukrainian names module imported")

            if hasattr(ukrainian_names, 'UKRAINIAN_NAMES'):
                print(f"✅ UKRAINIAN_NAMES available: {len(ukrainian_names.UKRAINIAN_NAMES)} entries")

                # Check if Андрій is there
                test_names = ["Андрій", "андрій", "АНДРІЙ"]
                for name in test_names:
                    if name in ukrainian_names.UKRAINIAN_NAMES:
                        print(f"    ✅ Found '{name}' in UKRAINIAN_NAMES")
                        print(f"       Data: {ukrainian_names.UKRAINIAN_NAMES[name]}")
                    else:
                        print(f"    ❌ '{name}' not found in UKRAINIAN_NAMES")
            else:
                print(f"❌ UKRAINIAN_NAMES attribute not found")
        except ImportError as e:
            print(f"❌ Failed to import ukrainian_names: {e}")

        # Test role classifier's given_names
        print(f"\n🔍 Role classifier given_names test:")
        role_classifier = service.normalization_factory.role_classifier

        print(f"Given names by language:")
        for lang, names in role_classifier.given_names.items():
            print(f"  {lang}: {len(names)} names")
            if lang == 'uk' and names:
                sample = [n for n in list(names)[:10]]
                print(f"    Sample: {sample}")

                # Check if андрій is in given_names
                if 'андрій' in names:
                    print(f"    ✅ 'андрій' found in given_names['uk']")
                else:
                    print(f"    ❌ 'андрій' NOT found in given_names['uk']")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_name_loading())