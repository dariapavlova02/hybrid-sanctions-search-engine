#!/usr/bin/env python3
"""
Полный тест процесса для "Петро Порошенко"
"""
import sys
sys.path.insert(0, 'src')

import requests
from requests.auth import HTTPBasicAuth

def test_poroshenko_ac_patterns():
    """Проверяем AC паттерны для Порошенко"""
    print("🔍 Проверяем AC паттерны для Петро Порошенко...")

    # ES подключение
    ES_HOST = "95.217.84.234"
    ES_PORT = 9200
    ES_USER = "elastic"
    ES_PASSWORD = "AiServiceElastic2024!"
    ES_INDEX = "ai_service_ac_patterns"

    url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}/_search"
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

    # Поиск паттернов для Порошенко
    search_query = {
        "query": {
            "wildcard": {
                "pattern": {
                    "value": "*порошенко*",
                    "case_insensitive": True
                }
            }
        },
        "size": 10
    }

    try:
        response = requests.post(url, json=search_query, auth=auth)
        if response.status_code == 200:
            result = response.json()
            total_hits = result["hits"]["total"]["value"]
            print(f"Найдено {total_hits} паттернов для 'порошенко'")

            if total_hits > 0:
                print("Примеры паттернов:")
                for hit in result["hits"]["hits"][:5]:
                    pattern = hit["_source"]
                    print(f"  - '{pattern['pattern']}' (tier {pattern['tier']}, {pattern['type']})")
                return True
            else:
                print("❌ Паттерны для Порошенко не найдены")
                return False
        else:
            print(f"❌ Ошибка поиска в ES: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Ошибка подключения к ES: {e}")
        return False

def test_poroshenko_smartfilter():
    """Тест SmartFilter для Порошенко"""
    print("\n🔍 Тестируем SmartFilter для Петро Порошенко...")

    try:
        from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService

        smart_filter = SmartFilterService(
            language_service=None,
            signal_service=None,
            enable_terrorism_detection=True,
            enable_aho_corasick=True
        )

        test_text = "Петро Порошенко"
        result = smart_filter.should_process_text(test_text)

        print(f"Текст: {test_text}")
        print(f"Should process: {result.should_process}")
        print(f"Confidence: {result.confidence}")
        print(f"AC matches: {result.signal_details.get('aho_corasick_matches', {}).get('total_matches', 0)}")

        # Тест AC поиска напрямую
        ac_result = smart_filter.search_aho_corasick(test_text)
        print(f"Прямой AC поиск: {ac_result.get('total_matches', 0)} совпадений")

        if result.should_process and ac_result.get('total_matches', 0) > 0:
            print("✅ SmartFilter работает для Порошенко!")
            return True
        else:
            print("❌ SmartFilter блокирует Порошенко")
            return False

    except Exception as e:
        print(f"❌ Ошибка SmartFilter: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_poroshenko_normalization():
    """Тест нормализации для Порошенко"""
    print("\n🔍 Тестируем нормализацию для Петро Порошенко...")

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        # Инициализация без внешних зависимостей
        norm_service = NormalizationService()

        test_text = "Петро Порошенко"
        result = norm_service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"Исходный текст: {test_text}")
        print(f"Нормализованный: {result.normalized}")
        print(f"Токены: {result.tokens}")
        print(f"Успех: {result.success}")

        if result.success and result.normalized:
            print("✅ Нормализация работает для Порошенко!")
            return True
        else:
            print("❌ Нормализация не работает")
            return False

    except Exception as e:
        print(f"❌ Ошибка нормализации: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_poroshenko_full_process():
    """Полный тест процесса через API"""
    print("\n🚀 Полный тест процесса через curl...")

    import subprocess
    import json

    curl_cmd = [
        'curl', '-X', 'POST',
        'http://localhost:8080/process',
        '-H', 'Content-Type: application/json',
        '-d', json.dumps({
            "text": "Петро Порошенко",
            "options": {
                "enable_advanced_features": True,
                "generate_variants": True,
                "generate_embeddings": False,
                "enable_search": True
            }
        }),
        '--connect-timeout', '5',
        '--max-time', '30'
    ]

    try:
        result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=35)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                print("✅ API ответил успешно!")

                print(f"Success: {response.get('success', False)}")
                print(f"Original: {response.get('original_text', 'N/A')}")
                print(f"Normalized: {response.get('normalized_text', 'N/A')}")
                print(f"Language: {response.get('language', 'N/A')}")

                # Проверяем результаты поиска
                search_results = response.get('search_results', {})
                if search_results:
                    total_hits = search_results.get('total_hits', 0)
                    print(f"Search results: {total_hits} hits")

                    if total_hits > 0:
                        results = search_results.get('results', [])
                        if results:
                            for i, hit in enumerate(results[:3], 1):
                                print(f"  {i}. {hit.get('entity_name', 'N/A')} (confidence: {hit.get('confidence', 0):.3f})")
                        print("🎉 СИСТЕМА РАБОТАЕТ! Полный процесс успешен!")
                        return True
                    else:
                        print("❌ Поиск не вернул результатов")
                        return False
                else:
                    print("⚠️  Нет результатов поиска в ответе")
                    return False

            except json.JSONDecodeError as e:
                print(f"❌ Ошибка парсинга JSON: {e}")
                print(f"Raw response: {result.stdout}")
                return False

        else:
            print(f"❌ Curl failed: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("❌ Timeout - API не отвечает")
        return False
    except Exception as e:
        print(f"❌ Ошибка curl: {e}")
        return False

def main():
    print("🎯 ПОЛНЫЙ ТЕСТ ПРОЦЕССА: Петро Порошенко")
    print("=" * 50)

    tests = [
        ("AC Паттерны", test_poroshenko_ac_patterns),
        ("Нормализация", test_poroshenko_normalization),
        ("SmartFilter", test_poroshenko_smartfilter),
        ("Полный API процесс", test_poroshenko_full_process)
    ]

    passed = 0
    total = len(tests)

    for name, test_func in tests:
        print(f"\n=== {name} ===")
        if test_func():
            passed += 1
            print(f"✅ {name} - УСПЕХ")
        else:
            print(f"❌ {name} - ОШИБКА")

    print(f"\n📊 ИТОГОВЫЙ РЕЗУЛЬТАТ: {passed}/{total} тестов прошли")

    if passed == total:
        print("🎉 ВСЕ СИСТЕМЫ РАБОТАЮТ! Петро Порошенко обрабатывается корректно!")
        return True
    else:
        print("⚠️  Есть проблемы в системе")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)