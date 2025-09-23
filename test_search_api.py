#!/usr/bin/env python3
"""
Test search integration through API call.
"""

import asyncio
import json

async def test_search_api():
    """Test search through production API."""
    print("🔍 PRODUCTION API SEARCH TEST")
    print("="*50)

    try:
        import aiohttp

        # Test names that should trigger search
        test_cases = [
            "Порошенко Петро",
            "Иванов Иван Иванович",
            "Biden Joe"
        ]

        async with aiohttp.ClientSession() as session:
            for test_text in test_cases:
                print(f"\n📝 Testing: '{test_text}'")

                # Call production API
                async with session.post(
                    "http://95.217.84.234:8000/process",
                    json={
                        "text": test_text,
                        "generate_variants": False,
                        "generate_embeddings": False
                    },
                    headers={"Content-Type": "application/json"}
                ) as response:

                    if response.status == 200:
                        result = await response.json()

                        print(f"  ✅ Response: {response.status}")
                        print(f"  📋 Normalized: '{result.get('normalized_text', 'N/A')}'")
                        print(f"  🔍 Has search_results: {'search_results' in result}")

                        if 'search_results' in result:
                            search_results = result['search_results']
                            if search_results:
                                print(f"    Search type: {search_results.get('search_type', 'unknown')}")
                                print(f"    Total hits: {search_results.get('total_hits', 0)}")
                                print(f"    Warnings: {search_results.get('warnings', [])}")
                            else:
                                print(f"    Search results: None")
                        else:
                            print(f"    ❌ NO search_results field found!")

                        # Show keys in response
                        print(f"  🔑 Response keys: {list(result.keys())}")

                    else:
                        print(f"  ❌ Error: {response.status}")
                        text = await response.text()
                        print(f"  Error details: {text}")

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_search_api())