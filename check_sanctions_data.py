#!/usr/bin/env python3
"""
Проверяем что загружается в санкционные данные
"""

import requests
import json

def check_sanctions_api():
    """Проверяем что есть в санкционных данных через API"""

    print("🔍 ПРОВЕРКА САНКЦИОННЫХ ДАННЫХ")
    print("=" * 60)

    # Сначала проверим статистику
    try:
        health_response = requests.get("http://localhost:8000/health", timeout=5)
        print(f"✅ Сервис доступен: {health_response.status_code}")
    except Exception as e:
        print(f"❌ Сервис недоступен: {e}")
        return

    # Поиск точно по имени Ulianova
    queries = [
        "Ulianova",
        "Liudmyla",
        "Ulianova Liudmyla",
        "Liudmyla Ulianova",
        "Oleksandrivna",
        "Ulianova Liudmyla Oleksandrivna"
    ]

    print(f"\n📊 ТЕСТИРОВАНИЕ {len(queries)} ПОИСКОВЫХ ЗАПРОСОВ:")

    for i, query in enumerate(queries, 1):
        print(f"\n{i}. Query: '{query}'")
        try:
            response = requests.post(
                "http://localhost:8000/process",
                json={"text": query},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                search_results = data.get('search_results', {})
                total_hits = search_results.get('total_hits', 0)
                results = search_results.get('results', [])

                print(f"   📊 Найдено: {total_hits} результатов")

                if results:
                    for j, result in enumerate(results[:3], 1):  # Топ-3
                        text = result.get('text', 'N/A')
                        score = result.get('score', 0)
                        search_mode = result.get('search_mode', 'N/A')
                        print(f"      {j}. {text:<40} (score: {score:.3f}, mode: {search_mode})")
                else:
                    print("   ❌ Результатов нет")
            else:
                print(f"   ❌ Ошибка API: {response.status_code}")

        except Exception as e:
            print(f"   ❌ Ошибка запроса: {e}")

    # Дополнительная проверка - ищем похожие украинские имена
    print(f"\n🇺🇦 ПОИСК ПОХОЖИХ УКРАИНСКИХ ИМЕН:")
    ukrainian_names = [
        "Ульянова",  # Кириллица
        "Людмила",   # Кириллица
        "Ulyanova",  # Латиница альтернатива
        "Lyudmila"   # Латиница альтернатива
    ]

    for name in ukrainian_names:
        print(f"\n   Query: '{name}'")
        try:
            response = requests.post(
                "http://localhost:8000/process",
                json={"text": name},
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                total_hits = data.get('search_results', {}).get('total_hits', 0)
                print(f"   📊 Найдено: {total_hits} результатов")
            else:
                print(f"   ❌ Ошибка: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")

def main():
    check_sanctions_api()

    print(f"\n🎯 ЗАКЛЮЧЕНИЕ:")
    print("   Если 'Ulianova Liudmyla Oleksandrivna' не находится ни одним запросом,")
    print("   значит этой записи НЕТ в загруженных санкционных данных!")
    print("   Нужно проверить:")
    print("   1. Откуда загружаются данные (файл/база)")
    print("   2. Правильно ли парсится имя из источника")
    print("   3. Есть ли фильтрация при загрузке")

if __name__ == "__main__":
    main()