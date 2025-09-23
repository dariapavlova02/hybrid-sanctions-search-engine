#!/usr/bin/env python3
"""
Отладка поиска для Порошенко
"""
import sys
sys.path.insert(0, 'src')

import requests
from requests.auth import HTTPBasicAuth

def debug_poroshenko_search():
    print("🔍 Отладка поиска AC паттернов для Порошенко...")

    # ES подключение
    ES_HOST = "95.217.84.234"
    ES_PORT = 9200
    ES_USER = "elastic"
    ES_PASSWORD = "AiServiceElastic2024!"
    ES_INDEX = "ai_service_ac_patterns"

    url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}/_search"
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

    # Тест различных вариантов поиска
    test_queries = [
        "Петро Порошенко",
        "петро порошенко",
        "ПЕТРО ПОРОШЕНКО",
        "Порошенко Петро",
        "порошенко петро",
        "порошенко",
        "петро"
    ]

    for query in test_queries:
        print(f"\n--- Поиск: '{query}' ---")

        # Тест нормализации
        try:
            from ai_service.layers.unicode.unicode_service import UnicodeService
            unicode_service = UnicodeService()
            normalized_result = unicode_service.normalize_text(query, normalize_homoglyphs=True)
            normalized = normalized_result["normalized"]
            print(f"Нормализованный: '{normalized}'")
        except Exception as e:
            print(f"Ошибка нормализации: {e}")
            normalized = query.lower()

        # Поиск wildcard
        search_query = {
            "query": {
                "wildcard": {
                    "pattern": {
                        "value": f"*{normalized.lower()}*",
                        "case_insensitive": True
                    }
                }
            },
            "size": 5
        }

        try:
            response = requests.post(url, json=search_query, auth=auth)
            if response.status_code == 200:
                result = response.json()
                total_hits = result["hits"]["total"]["value"]
                print(f"Wildcard результаты: {total_hits}")

                if total_hits > 0:
                    for hit in result["hits"]["hits"][:3]:
                        pattern = hit["_source"]
                        print(f"  - '{pattern['pattern']}'")
            else:
                print(f"Ошибка wildcard поиска: {response.status_code}")
        except Exception as e:
            print(f"Ошибка wildcard: {e}")

        # Поиск match
        match_query = {
            "query": {
                "match": {
                    "pattern": {
                        "query": normalized,
                        "fuzziness": "AUTO"
                    }
                }
            },
            "size": 5
        }

        try:
            response = requests.post(url, json=match_query, auth=auth)
            if response.status_code == 200:
                result = response.json()
                total_hits = result["hits"]["total"]["value"]
                print(f"Match результаты: {total_hits}")

                if total_hits > 0:
                    for hit in result["hits"]["hits"][:3]:
                        pattern = hit["_source"]
                        print(f"  - '{pattern['pattern']}'")
            else:
                print(f"Ошибка match поиска: {response.status_code}")
        except Exception as e:
            print(f"Ошибка match: {e}")

def debug_smartfilter_search():
    print("\n🔍 Отладка SmartFilter AC поиска...")

    try:
        from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService

        smart_filter = SmartFilterService(
            language_service=None,
            signal_service=None,
            enable_terrorism_detection=True,
            enable_aho_corasick=True
        )

        test_texts = [
            "Петро Порошенко",
            "Порошенко Петро",
            "петро порошенко",
            "порошенко петро олексійович"
        ]

        for text in test_texts:
            print(f"\n--- SmartFilter тест: '{text}' ---")

            ac_result = smart_filter.search_aho_corasick(text)
            print(f"AC результат: {ac_result.get('total_matches', 0)} совпадений")
            print(f"Время запроса: {ac_result.get('query_time_ms', 0)}ms")

            if ac_result.get('total_matches', 0) > 0:
                matches = ac_result.get('matches', [])
                for match in matches[:3]:
                    print(f"  - {match}")

    except Exception as e:
        print(f"Ошибка SmartFilter: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_poroshenko_search()
    debug_smartfilter_search()