#!/usr/bin/env python
"""
Production diagnostic script for sanctioned INN cache issue.
Run this on the production server to diagnose why INN 2839403975 is not being marked as sanctioned.
"""

import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def diagnose_inn_cache():
    """Diagnose INN cache issues in production."""

    print("=" * 80)
    print("PRODUCTION INN CACHE DIAGNOSTICS")
    print("=" * 80)

    # 1. Check if cache file exists
    print("\n1. CHECKING CACHE FILE LOCATION...")
    cache_file_path = Path(__file__).parent / "src" / "ai_service" / "data" / "sanctioned_inns_cache.json"

    print(f"   Looking for: {cache_file_path}")
    print(f"   Absolute path: {cache_file_path.absolute()}")

    if cache_file_path.exists():
        print(f"   ✅ File EXISTS")
        print(f"   Size: {cache_file_path.stat().st_size:,} bytes")

        # Check permissions
        import stat
        mode = cache_file_path.stat().st_mode
        print(f"   Permissions: {oct(stat.S_IMODE(mode))}")
        print(f"   Readable: {os.access(cache_file_path, os.R_OK)}")
    else:
        print(f"   ❌ FILE NOT FOUND!")
        print(f"   This is likely the problem - the cache file is not deployed to production")

        # Check alternative locations
        print("\n   Checking alternative locations...")
        alt_paths = [
            Path("/app/src/ai_service/data/sanctioned_inns_cache.json"),
            Path("/opt/ai-service/src/ai_service/data/sanctioned_inns_cache.json"),
            Path("./src/ai_service/data/sanctioned_inns_cache.json"),
            Path("../data/sanctioned_inns_cache.json"),
        ]

        for alt_path in alt_paths:
            if alt_path.exists():
                print(f"   ✅ Found at alternative location: {alt_path}")
                break
        else:
            print(f"   ❌ Not found in any alternative locations")

    # 2. Try to load the cache module
    print("\n2. TRYING TO LOAD CACHE MODULE...")
    try:
        from src.ai_service.layers.search.sanctioned_inn_cache import get_inn_cache
        print("   ✅ Module imported successfully")

        # Try to get cache instance
        cache = get_inn_cache()
        print("   ✅ Cache instance created")

        # Check cache stats
        stats = cache.get_stats()
        print(f"   INNs loaded: {stats['total_inns']}")

        if stats['total_inns'] == 0:
            print(f"   ❌ Cache is EMPTY - file loading failed")
        else:
            print(f"   ✅ Cache loaded with {stats['total_inns']} INNs")

            # Test specific INN
            test_inn = "2839403975"
            result = cache.lookup(test_inn)

            if result:
                print(f"   ✅ Test INN {test_inn} FOUND: {result.get('name')}")
            else:
                print(f"   ❌ Test INN {test_inn} NOT FOUND in cache")

    except ImportError as e:
        print(f"   ❌ Failed to import cache module: {e}")
    except Exception as e:
        print(f"   ❌ Error loading cache: {e}")
        import traceback
        traceback.print_exc()

    # 3. Check if the fix is deployed
    print("\n3. CHECKING IF FIX IS DEPLOYED...")
    try:
        # Check signals_service.py for the fix
        signals_file = Path(__file__).parent / "src" / "ai_service" / "layers" / "signals" / "signals_service.py"

        if signals_file.exists():
            with open(signals_file, 'r') as f:
                content = f.read()

            # Check for duplicate code (the bug)
            duplicate_count = content.count("# ИЩЕМ ИНН В NOTES")
            print(f"   'ИЩЕМ ИНН В NOTES' appears {duplicate_count} time(s)")

            if duplicate_count > 1:
                print(f"   ❌ BUG STILL PRESENT: Duplicate code blocks found!")
                print(f"   The fix has NOT been deployed to production")
            elif duplicate_count == 1:
                print(f"   ✅ Fix appears to be deployed (only 1 instance of code)")
            else:
                print(f"   ⚠️  Could not find the marker - code may have changed")

            # Check for the inn_found flag (part of the fix)
            if "inn_found = False" in content:
                print(f"   ✅ Fix variable 'inn_found' present")
            else:
                print(f"   ❌ Fix variable 'inn_found' NOT found - fix not deployed")

    except Exception as e:
        print(f"   ❌ Could not check signals_service.py: {e}")

    # 4. Test the full pipeline
    print("\n4. TESTING FULL PIPELINE...")
    try:
        from src.ai_service.layers.signals.signals_service import SignalsService
        from src.ai_service.layers.normalization.normalization_service import NormalizationService

        print("   ✅ Modules imported")

        # Test text
        text = "Дарья ПАвлова ИНН 2839403975"

        # Normalize
        norm_service = NormalizationService()
        norm_result = norm_service.normalize(
            text=text,
            language="ru",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
        print(f"   ✅ Normalization complete: '{norm_result.normalized}'")

        # Extract signals
        signals_service = SignalsService()
        signals_result = signals_service.extract(
            text=text,
            normalization_result=norm_result.to_dict(),
            language="ru"
        )

        print(f"   ✅ Signals extracted: {len(signals_result['persons'])} persons")

        # Check for sanctioned INN
        sanctioned_found = False
        for person in signals_result.get('persons', []):
            for id_info in person.get('ids', []):
                if id_info.get('value') == '2839403975':
                    print(f"   INN found with type='{id_info.get('type')}'")
                    if id_info.get('sanctioned'):
                        print(f"   ✅ INN marked as SANCTIONED")
                        sanctioned_found = True
                    else:
                        print(f"   ❌ INN NOT marked as sanctioned")
                        print(f"   ID info: {id_info}")

        if not sanctioned_found:
            print(f"   ❌ PROBLEM CONFIRMED: INN not marked as sanctioned in production")

    except Exception as e:
        print(f"   ❌ Pipeline test failed: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 80)
    print("DIAGNOSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    diagnose_inn_cache()