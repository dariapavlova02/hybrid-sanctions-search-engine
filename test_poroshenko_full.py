#!/usr/bin/env python3
"""
Полная демонстрация процесса для Петро Порошенко
"""
import sys
sys.path.insert(0, 'src')

def test_full_poroshenko_process():
    print("🚀 ПОЛНАЯ ДЕМОНСТРАЦИЯ ПРОЦЕССА: Петро Порошенко")
    print("=" * 60)

    # 1. SmartFilter
    print("\n1️⃣ SmartFilter - предварительная оценка")
    print("-" * 40)

    try:
        from ai_service.layers.smart_filter.smart_filter_service import SmartFilterService

        smart_filter = SmartFilterService(
            language_service=None,
            signal_service=None,
            enable_terrorism_detection=True,
            enable_aho_corasick=True
        )

        test_text = "Петро Порошенко"
        filter_result = smart_filter.should_process_text(test_text)

        print(f"Входной текст: '{test_text}'")
        print(f"Рекомендация: {'ОБРАБАТЫВАТЬ' if filter_result.should_process else 'НЕ ОБРАБАТЫВАТЬ'}")
        print(f"Уверенность: {filter_result.confidence:.3f}")
        print(f"AC совпадения: {filter_result.signal_details.get('aho_corasick_matches', {}).get('total_matches', 0)}")

        if not filter_result.should_process:
            print("❌ SmartFilter блокирует обработку!")
            return False

        print("✅ SmartFilter разрешает обработку")

    except Exception as e:
        print(f"❌ Ошибка SmartFilter: {e}")
        return False

    # 2. Нормализация
    print("\n2️⃣ Нормализация имени")
    print("-" * 40)

    try:
        from ai_service.layers.normalization.normalization_service import NormalizationService

        norm_service = NormalizationService()
        norm_result = norm_service.normalize(
            text=test_text,
            language="uk",
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )

        print(f"Исходный: '{test_text}'")
        print(f"Нормализованный: '{norm_result.normalized}'")
        print(f"Токены: {norm_result.tokens}")
        print(f"Язык: {norm_result.language}")

        if not norm_result.success:
            print("❌ Нормализация не удалась!")
            return False

        print("✅ Нормализация успешна")

    except Exception as e:
        print(f"❌ Ошибка нормализации: {e}")
        return False

    # 3. Поиск
    print("\n3️⃣ Поиск в санкционных списках")
    print("-" * 40)

    try:
        # Прямой поиск в ES
        import requests
        from requests.auth import HTTPBasicAuth

        ES_HOST = "95.217.84.234"
        ES_PORT = 9200
        ES_USER = "elastic"
        ES_PASSWORD = "AiServiceElastic2024!"
        ES_INDEX = "ai_service_ac_patterns"

        url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}/_search"
        auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

        # Поиск паттернов
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "wildcard": {
                                "pattern": {
                                    "value": "*порошенко*",
                                    "case_insensitive": True
                                }
                            }
                        },
                        {
                            "match": {
                                "pattern": {
                                    "query": "порошенко петро",
                                    "fuzziness": "AUTO"
                                }
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 5
        }

        response = requests.post(url, json=search_query, auth=auth)
        if response.status_code == 200:
            result = response.json()
            total_hits = result["hits"]["total"]["value"]

            print(f"Найдено совпадений: {total_hits}")

            if total_hits > 0:
                print("Найденные паттерны:")
                for hit in result["hits"]["hits"]:
                    pattern = hit["_source"]
                    print(f"  📍 '{pattern['pattern']}' (ID: {pattern['entity_id']}, tier: {pattern['tier']})")

                print("✅ Поиск успешен - найдены санкционные записи!")
            else:
                print("❌ Совпадения не найдены")
                return False

        else:
            print(f"❌ Ошибка поиска: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        return False

    # 4. Заключение
    print("\n🎉 ПРОЦЕСС ЗАВЕРШЕН УСПЕШНО!")
    print("=" * 60)
    print("✅ SmartFilter: обработка разрешена")
    print("✅ Нормализация: имя нормализовано")
    print("✅ Поиск: найдены санкционные записи")
    print("\n🚨 РЕЗУЛЬТАТ: Петро Порошенко НАЙДЕН в санкционных списках!")

    return True

if __name__ == "__main__":
    success = test_full_poroshenko_process()
    sys.exit(0 if success else 1)