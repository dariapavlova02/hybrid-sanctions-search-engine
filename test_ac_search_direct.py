#!/usr/bin/env python3
"""
Прямой тест AC поиска с санкционными именами.
"""

import asyncio
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_ac_search_direct():
    """Тест AC поиска напрямую с санкционными именами."""
    print("🔍 DIRECT AC SEARCH TEST")
    print("="*40)

    # Test names from sanctions lists
    test_names = [
        "Коваленко Олександра Сергіївна",
        "Сергій Олійник",
        "Liudмуlа Uliаnоvа"  # Mixed script
    ]

    try:
        # 1. Load sanctions data directly
        from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader

        loader = SanctionsDataLoader()
        dataset = await loader.load_dataset()

        print(f"✅ Loaded {dataset.total_entries:,} sanctions entries")
        print(f"   Unique names for AC search: {len(dataset.all_names):,}")

        # 2. Check if our test names are in the dataset
        print(f"\n📋 Checking if test names are in sanctions data:")

        for name in test_names:
            found = False
            exact_matches = []
            partial_matches = []

            # Check exact match
            if name in dataset.all_names:
                found = True
                exact_matches.append(name)

            # Check partial matches (name might be part of longer entry)
            for sanctions_name in dataset.all_names:
                if name.lower() in sanctions_name.lower() or sanctions_name.lower() in name.lower():
                    partial_matches.append(sanctions_name)
                    if len(partial_matches) >= 5:  # Limit output
                        break

            print(f"\n   '{name}':")
            if exact_matches:
                print(f"     ✅ Exact match found!")
            elif partial_matches:
                print(f"     ⚠️  {len(partial_matches)} partial matches found:")
                for match in partial_matches[:3]:
                    print(f"       - '{match}'")
            else:
                print(f"     ❌ No matches in sanctions data")

        # 3. Test AC search without Elasticsearch (pure AC)
        print(f"\n🔍 Testing pure AC search (no Elasticsearch):")

        try:
            from ai_service.layers.search.ac_search_service import AhoCorasickSearchService, ACConfig

            ac_config = ACConfig()
            ac_service = AhoCorasickSearchService(ac_config)

            # Build AC patterns from sanctions data
            patterns = dataset.all_names[:10000]  # Limit for speed
            await ac_service.build_patterns(patterns)

            print(f"✅ Built AC patterns from {len(patterns):,} names")

            # Test each name
            for name in test_names:
                print(f"\n   Testing AC search: '{name}'")

                matches = await ac_service.search_async(name)

                if matches:
                    print(f"     ✅ Found {len(matches)} AC matches:")
                    for i, match in enumerate(matches[:3], 1):
                        print(f"       {i}. '{match.matched_text}' (pos: {match.start_pos}-{match.end_pos})")
                else:
                    print(f"     ❌ No AC matches found")

                    # Try fuzzy search as fallback
                    try:
                        from ai_service.layers.search.fuzzy_search_service import FuzzySearchService, FuzzyConfig

                        fuzzy_config = FuzzyConfig(min_score_threshold=0.6)
                        fuzzy_service = FuzzySearchService(fuzzy_config)

                        if fuzzy_service.enabled:
                            fuzzy_matches = await fuzzy_service.search_async(name, patterns[:1000])
                            if fuzzy_matches:
                                print(f"     🔍 Fuzzy fallback: {len(fuzzy_matches)} matches found:")
                                for match in fuzzy_matches[:2]:
                                    print(f"       - '{match.matched_text}' ({match.score:.3f})")
                    except Exception as e:
                        print(f"     ⚠️  Fuzzy fallback failed: {e}")

        except Exception as e:
            print(f"❌ AC search test failed: {e}")
            import traceback
            traceback.print_exc()

        # 4. Test homoglyph detection
        print(f"\n🔤 Testing homoglyph detection:")
        mixed_script_name = "Liudмуlа Uliаnоvа"

        latin_chars = [c for c in mixed_script_name if ord(c) <= 127]
        cyrillic_chars = [c for c in mixed_script_name if ord(c) > 127]

        print(f"   '{mixed_script_name}':")
        print(f"   Latin chars: {''.join(latin_chars)} ({len(latin_chars)})")
        print(f"   Cyrillic chars: {''.join(cyrillic_chars)} ({len(cyrillic_chars)})")

        if latin_chars and cyrillic_chars:
            print(f"   ⚠️  HOMOGLYPH ATTACK DETECTED - mixed scripts!")

            # Try to normalize and search again
            normalized_name = mixed_script_name
            # Simple normalization examples (would need proper unicode normalization)
            replacements = {
                'м': 'm', 'у': 'u', 'l': 'l', 'а': 'a', 'о': 'o'
            }

            print(f"   🔧 Attempted normalization needed for proper search")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ac_search_direct())