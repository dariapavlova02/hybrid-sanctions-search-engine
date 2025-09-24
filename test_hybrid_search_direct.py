#!/usr/bin/env python3
"""
Прямой тест HybridSearch с санкционными именами.
"""

import asyncio
import sys
import time
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

async def test_hybrid_search_with_sanctions():
    """Тест HybridSearch с санкционными именами."""
    print("🔍 HYBRID SEARCH WITH SANCTIONS TEST")
    print("="*50)

    # Real test names
    test_cases = [
        {
            "name": "Коваленко Олександра Сергіївна",
            "expected": "HIGH RISK - exact match in sanctions",
            "in_sanctions": True
        },
        {
            "name": "Сергій Олійник",
            "expected": "MEDIUM RISK - not in sanctions but Ukrainian name",
            "in_sanctions": False
        },
        {
            "name": "Liudмуlа Uliаnоvа",
            "expected": "HIGH RISK - homoglyph attack potential",
            "in_sanctions": False
        }
    ]

    try:
        # 1. Initialize HybridSearchService without Elasticsearch
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        from ai_service.layers.search.sanctions_data_loader import SanctionsDataLoader

        # Load sanctions data
        loader = SanctionsDataLoader()
        dataset = await loader.load_dataset()
        print(f"✅ Loaded {dataset.total_entries:,} sanctions entries")

        # Initialize search service
        search_service = HybridSearchService()
        print(f"✅ HybridSearchService initialized")

        # 2. Test each case
        for i, case in enumerate(test_cases, 1):
            name = case["name"]
            expected = case["expected"]
            in_sanctions = case["in_sanctions"]

            print(f"\n{i}. Testing: '{name}'")
            print(f"   Expected: {expected}")
            print(f"   Should be in sanctions: {in_sanctions}")

            # Check if actually in sanctions
            exact_match = name in dataset.all_names
            partial_matches = [s for s in dataset.all_names if name.lower() in s.lower()][:3]

            print(f"   📋 Sanctions check:")
            print(f"     - Exact match: {'✅ YES' if exact_match else '❌ NO'}")
            if partial_matches and not exact_match:
                print(f"     - Partial matches ({len(partial_matches)}):")
                for match in partial_matches:
                    print(f"       • '{match}'")

            # Test search (without Elasticsearch, will use fallback)
            try:
                start_time = time.time()

                # This should trigger AC → Fuzzy → fallback search
                search_results = await search_service.search_async(
                    query_text=name,
                    options={"max_results": 5}
                )

                search_time = (time.time() - start_time) * 1000

                print(f"   🔍 Search results ({search_time:.1f}ms):")

                if search_results:
                    print(f"     ✅ Found {len(search_results)} matches:")
                    for j, result in enumerate(search_results[:3], 1):
                        # Handle different result types
                        if hasattr(result, 'matched_text'):
                            text = result.matched_text
                            score = getattr(result, 'score', 'N/A')
                            method = getattr(result, 'source', getattr(result, 'algorithm', 'unknown'))
                        else:
                            text = str(result)
                            score = 'N/A'
                            method = 'unknown'

                        print(f"       {j}. '{text}' - {score} ({method})")
                else:
                    print(f"     ❌ No matches found")

                    # If no matches but should be in sanctions, it's a problem
                    if in_sanctions and exact_match:
                        print(f"     🚨 CRITICAL: Name is in sanctions but search missed it!")

            except Exception as e:
                print(f"   ❌ Search failed: {e}")

            # Test homoglyph detection for mixed script
            if any(ord(c) <= 127 for c in name) and any(ord(c) > 127 for c in name):
                latin = ''.join(c for c in name if ord(c) <= 127)
                cyrillic = ''.join(c for c in name if ord(c) > 127)
                print(f"   ⚠️  HOMOGLYPH DETECTED:")
                print(f"     - Latin: '{latin}'")
                print(f"     - Cyrillic: '{cyrillic}'")

        # 3. Summary
        print(f"\n{'='*50}")
        print("📊 SEARCH ANALYSIS SUMMARY")
        print("="*50)

        for case in test_cases:
            name = case["name"]
            in_sanctions = case["in_sanctions"]
            exact_match = name in dataset.all_names

            status = "✅ CORRECT" if (in_sanctions == exact_match) else "❌ MISMATCH"
            print(f"• '{name}': {status}")
            print(f"  Expected in sanctions: {in_sanctions}")
            print(f"  Actually in sanctions: {exact_match}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_hybrid_search_with_sanctions())