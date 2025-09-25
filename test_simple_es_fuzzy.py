#!/usr/bin/env python3

"""
Простой тест ES fuzzy search через HTTP API.
"""

import json
import asyncio
import aiohttp
import sys
from typing import List, Dict, Any

async def test_simple_es_fuzzy():
    """Test ES fuzzy search directly through HTTP API."""
    print("🔍 ПРОСТОЙ ТЕСТ ES FUZZY SEARCH")
    print("=" * 60)

    es_url = "http://95.217.84.234:9200"
    index_name = "ai_service_ac_patterns"
    query_text = "Коврико Роман"

    try:
        async with aiohttp.ClientSession() as session:
            # Test 1: ES Fuzzy Query
            fuzzy_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "fuzzy": {
                                    "pattern": {
                                        "value": query_text,
                                        "fuzziness": "AUTO",
                                        "prefix_length": 1,
                                        "max_expansions": 50,
                                        "boost": 2.0
                                    }
                                }
                            },
                            {
                                "match": {
                                    "pattern": {
                                        "query": query_text,
                                        "fuzziness": "AUTO",
                                        "boost": 1.5
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": 10,
                "_source": ["pattern", "canonical", "confidence", "tier"]
            }

            print(f"🧪 Тест 1: ES Fuzzy Search для '{query_text}'")

            url = f"{es_url}/{index_name}/_search"
            async with session.post(url, json=fuzzy_query) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get("hits", {}).get("hits", [])

                    print(f"   Найдено: {len(hits)} результатов")
                    for i, hit in enumerate(hits[:5], 1):
                        source = hit["_source"]
                        score = hit["_score"]
                        pattern = source.get("pattern", "")
                        canonical = source.get("canonical", "")
                        print(f"   {i}. {pattern} → {canonical} (score: {score:.2f})")

                    # Check if we found Ковриков
                    found_kovrykov = any("ковриков" in hit["_source"].get("pattern", "").lower() or
                                       "ковриков" in hit["_source"].get("canonical", "").lower()
                                       for hit in hits)
                    print(f"   'Ковриков' найден: {found_kovrykov}")

                else:
                    print(f"   ❌ ES request failed: {response.status}")
                    return False

            # Test 2: More aggressive fuzzy search
            print(f"\n🧪 Тест 2: Агрессивный Fuzzy Search")

            aggressive_query = {
                "query": {
                    "bool": {
                        "should": [
                            {
                                "fuzzy": {
                                    "pattern": {
                                        "value": query_text,
                                        "fuzziness": 2,
                                        "prefix_length": 0,
                                        "max_expansions": 100,
                                        "boost": 3.0
                                    }
                                }
                            },
                            {
                                "fuzzy": {
                                    "canonical": {
                                        "value": query_text,
                                        "fuzziness": 2,
                                        "prefix_length": 0,
                                        "max_expansions": 100,
                                        "boost": 2.0
                                    }
                                }
                            },
                            {
                                "wildcard": {
                                    "pattern": {
                                        "value": f"*{query_text[:6]}*",
                                        "boost": 1.0
                                    }
                                }
                            }
                        ]
                    }
                },
                "size": 15,
                "_source": ["pattern", "canonical", "confidence", "tier"]
            }

            async with session.post(url, json=aggressive_query) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get("hits", {}).get("hits", [])

                    print(f"   Найдено: {len(hits)} результатов")
                    for i, hit in enumerate(hits[:8], 1):
                        source = hit["_source"]
                        score = hit["_score"]
                        pattern = source.get("pattern", "")
                        canonical = source.get("canonical", "")
                        print(f"   {i}. {pattern} → {canonical} (score: {score:.2f})")

                    # Check if we found Ковриков
                    found_kovrykov = any("ковриков" in hit["_source"].get("pattern", "").lower() or
                                       "ковриков" in hit["_source"].get("canonical", "").lower()
                                       for hit in hits)
                    print(f"   'Ковриков' найден: {found_kovrykov}")

                    return found_kovrykov
                else:
                    print(f"   ❌ ES request failed: {response.status}")
                    return False

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main function."""
    print("🎯 SIMPLE ES FUZZY SEARCH TEST")
    print("=" * 50)

    success = await test_simple_es_fuzzy()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: ES fuzzy search работает и находит Ковриков!")
    else:
        print("❌ FAILURE: ES fuzzy search не смог найти Ковриков")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)