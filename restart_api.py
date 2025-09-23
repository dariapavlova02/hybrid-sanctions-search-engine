#!/usr/bin/env python3
"""
Быстрый перезапуск API сервера с исправлениями
"""
import subprocess
import sys
import time
import requests

def restart_api():
    print("🔄 Перезапуск API сервера с исправлениями...")

    # Остановить существующие процессы
    try:
        subprocess.run(["pkill", "-f", "python.*main.py"], check=False)
        time.sleep(2)
    except:
        pass

    # Запуск API сервера
    print("🚀 Запуск API сервера...")
    try:
        process = subprocess.Popen([
            sys.executable, "-m", "src.ai_service.main"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # Дать серверу время на запуск
        time.sleep(5)

        # Проверить что сервер запустился
        try:
            response = requests.get("http://localhost:8080/health", timeout=5)
            if response.status_code == 200:
                print("✅ API сервер запущен успешно!")
                return True
            else:
                print(f"⚠️  API сервер ответил с кодом {response.status_code}")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Не удалось подключиться к API серверу")
            return False

    except Exception as e:
        print(f"❌ Ошибка запуска API: {e}")
        return False

def test_api():
    print("\n🧪 Тестирование API с исправлениями...")

    test_data = {
        "text": "Ковриков Роман Валерійович",
        "options": {
            "enable_advanced_features": True,
            "generate_variants": False,
            "generate_embeddings": False,
            "enable_search": True
        }
    }

    try:
        response = requests.post(
            "http://localhost:8080/process",
            json=test_data,
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()

            decision = result.get("decision", {})
            search_results = result.get("search_results", {})

            print(f"✅ API ответил успешно")
            print(f"SmartFilter should_process: {decision.get('decision_details', {}).get('smartfilter_should_process', 'N/A')}")
            print(f"Search results: {search_results.get('total_hits', 0)} hits")

            if decision.get('decision_details', {}).get('smartfilter_should_process') and search_results.get('total_hits', 0) > 0:
                print("🎉 СИСТЕМА РАБОТАЕТ! SmartFilter разрешает обработку и поиск возвращает результаты!")
                return True
            else:
                print("⚠️  Система еще не полностью исправлена")
                return False

        else:
            print(f"❌ API ошибка: {response.status_code}")
            return False

    except Exception as e:
        print(f"❌ Ошибка тестирования: {e}")
        return False

if __name__ == "__main__":
    if restart_api():
        if test_api():
            print("\n🎯 Миссия выполнена! API сервер работает с исправлениями.")
        else:
            print("\n⚠️  API запущен, но требует дополнительной отладки.")
    else:
        print("\n❌ Не удалось запустить API сервер.")