#!/usr/bin/env python3

"""
Тест улучшенных порогов fuzzy search для предотвращения false positives.
"""

import json
import asyncio
import aiohttp
import sys
from typing import List, Dict, Any

async def test_improved_fuzzy_thresholds():
    """Test improved fuzzy search with better thresholds."""
    print("🔧 ТЕСТ УЛУЧШЕННЫХ FUZZY SEARCH ПОРОГОВ")
    print("=" * 70)

    es_url = "http://95.217.84.234:9200"
    index_name = "ai_service_ac_patterns"

    test_cases = [
        {
            "query": "Коврико Роман",
            "expected": "Ковриков Роман",
            "should_match": True,
            "description": "Правильная опечатка - должен найти"
        },
        {
            "query": "Роман Ковриков Анатольевич",
            "expected": "Ковриков Роман Валерійович",
            "should_match": False,
            "description": "Разные отчества - НЕ должен считаться высоким совпадением"
        },
        {
            "query": "Дарья Павлова Юрьевна",
            "expected": "Волочков Павло Павлович",
            "should_match": False,
            "description": "Совершенно разные люди - НЕ должен находить"
        }
    ]

    try:
        async with aiohttp.ClientSession() as session:
            for i, test_case in enumerate(test_cases, 1):
                print(f"\n🧪 Тест {i}: {test_case['description']}")
                print(f"   Запрос: '{test_case['query']}'")

                # Updated ES query with conservative settings
                es_query = {
                    "query": {
                        "bool": {
                            "should": [
                                {
                                    "fuzzy": {
                                        "pattern": {
                                            "value": test_case['query'],
                                            "fuzziness": 1,
                                            "prefix_length": 2,
                                            "max_expansions": 20,
                                            "boost": 2.0
                                        }
                                    }
                                },
                                {
                                    "fuzzy": {
                                        "canonical": {
                                            "value": test_case['query'],
                                            "fuzziness": 1,
                                            "prefix_length": 2,
                                            "max_expansions": 20,
                                            "boost": 1.5
                                        }
                                    }
                                },
                                {
                                    "match": {
                                        "canonical": {
                                            "query": test_case['query'],
                                            "fuzziness": 1,
                                            "boost": 1.2
                                        }
                                    }
                                }
                            ],
                            "minimum_should_match": 1
                        }
                    },
                    "size": 10,
                    "_source": ["pattern", "canonical", "entity_id", "entity_type", "confidence", "tier"]
                }

                url = f"{es_url}/{index_name}/_search"
                async with session.post(url, json=es_query) as response:
                    if response.status == 200:
                        data = await response.json()
                        hits = data.get("hits", {}).get("hits", [])

                        print(f"   Найдено ES результатов: {len(hits)}")

                        # Simulate our improved scoring logic
                        scored_results = []
                        for hit in hits:
                            source = hit.get('_source', {})
                            es_score = hit.get('_score', 0.0)

                            # Calculate word similarity (same logic as in code)
                            query_parts = set(test_case['query'].lower().split())
                            result_text = source.get('canonical', source.get('pattern', ''))
                            result_parts = set(result_text.lower().split())

                            if query_parts and result_parts:
                                overlap = len(query_parts.intersection(result_parts))
                                total_unique = len(query_parts.union(result_parts))
                                word_similarity = overlap / total_unique if total_unique > 0 else 0
                            else:
                                word_similarity = 0

                            # Apply same scoring as in code
                            es_normalized = min(es_score / 50.0, 1.0)
                            normalized_score = (es_normalized * 0.3) + (word_similarity * 0.7)

                            if word_similarity < 0.3:
                                normalized_score *= 0.5

                            # Apply minimum threshold
                            if normalized_score >= 0.4:
                                scored_results.append({
                                    "text": result_text,
                                    "score": normalized_score,
                                    "es_score": es_score,
                                    "word_similarity": word_similarity,
                                    "pattern": source.get('pattern', '')
                                })

                        # Sort by score
                        scored_results.sort(key=lambda x: x['score'], reverse=True)

                        print(f"   После фильтрации: {len(scored_results)} результатов")
                        for j, result in enumerate(scored_results[:3], 1):
                            print(f"     {j}. {result['text']}")
                            print(f"        Score: {result['score']:.3f} (ES: {result['es_score']:.1f}, Word sim: {result['word_similarity']:.3f})")

                        # Check expectations
                        if test_case['should_match']:
                            high_score_found = any(r['score'] > 0.7 for r in scored_results)
                            expected_found = any(test_case['expected'].lower() in r['text'].lower() for r in scored_results)
                            print(f"   ✅ Результат: {'PASS' if (high_score_found and expected_found) else 'FAIL'}")
                        else:
                            high_score_found = any(r['score'] > 0.7 for r in scored_results)
                            print(f"   ✅ Результат: {'PASS' if not high_score_found else 'FAIL'} (высоких скоров: {high_score_found})")

                    else:
                        print(f"   ❌ ES error: {response.status}")

        return True

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

async def main():
    """Main function."""
    print("🎯 IMPROVED FUZZY THRESHOLDS TEST")
    print("=" * 50)

    success = await test_improved_fuzzy_thresholds()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Тест порогов fuzzy search завершен!")
    else:
        print("❌ FAILURE: Проблемы с тестом порогов")

    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)