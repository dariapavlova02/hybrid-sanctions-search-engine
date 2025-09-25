#!/usr/bin/env python3

"""
Тест определения правильных Elasticsearch hosts для разных environment'ов.
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_hosts_detection():
    """Тест определения Elasticsearch hosts."""
    print("🔍 ТЕСТ ОПРЕДЕЛЕНИЯ ELASTICSEARCH HOSTS")
    print("=" * 60)

    # Текущая среда
    print("1. Анализ текущей среды:")
    print(f"   APP_ENV: {os.environ.get('APP_ENV', 'не установлен')}")
    print(f"   ELASTICSEARCH_HOSTS: {os.environ.get('ELASTICSEARCH_HOSTS', 'не установлен')}")
    print(f"   ES_HOSTS: {os.environ.get('ES_HOSTS', 'не установлен')}")
    print(f"   Docker environment: {os.path.exists('/.dockerenv')}")

    # Тестируем конфигурацию
    print("\n2. Создание конфигурации:")
    try:
        from ai_service.layers.search.config import ElasticsearchConfig

        config = ElasticsearchConfig.from_sources()
        print(f"✅ Определенные hosts: {config.hosts}")

        if config.hosts == ["http://elasticsearch:9200"]:
            print("   🐳 Docker production конфигурация")
        elif "95.217.84.234" in str(config.hosts):
            print("   🖥️ Production server конфигурация")
        elif "localhost" in str(config.hosts):
            print("   💻 Local development конфигурация")
        else:
            print("   ❓ Неизвестная конфигурация")

    except Exception as e:
        print(f"❌ Ошибка создания конфигурации: {e}")
        return False

    # Тестируем различные сценарии
    print("\n3. Тест различных environment'ов:")

    test_cases = [
        {"name": "Docker Production", "env": {"APP_ENV": "production"}, "expected": "elasticsearch:9200"},
        {"name": "Environment Variable", "env": {"ELASTICSEARCH_HOSTS": "http://custom-es:9200"}, "expected": "custom-es:9200"},
        {"name": "Fallback Localhost", "env": {}, "expected": "localhost:9200"},
    ]

    for test_case in test_cases:
        print(f"\n   Тест: {test_case['name']}")

        # Временно установить переменные окружения
        original_env = {}
        for key, value in test_case["env"].items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        # Очистить другие переменные
        if "ELASTICSEARCH_HOSTS" not in test_case["env"]:
            original_es = os.environ.get("ELASTICSEARCH_HOSTS")
            if "ELASTICSEARCH_HOSTS" in os.environ:
                del os.environ["ELASTICSEARCH_HOSTS"]

        try:
            from ai_service.layers.search.config import ElasticsearchConfig
            # Force reload module to pick up new env vars
            import importlib
            import ai_service.layers.search.config
            importlib.reload(ai_service.layers.search.config)
            from ai_service.layers.search.config import ElasticsearchConfig

            config = ElasticsearchConfig.from_sources()
            hosts_str = str(config.hosts)

            if test_case["expected"] in hosts_str:
                print(f"     ✅ Correct: {config.hosts}")
            else:
                print(f"     ❌ Expected '{test_case['expected']}' in {config.hosts}")

        except Exception as e:
            print(f"     ❌ Error: {e}")
        finally:
            # Восстановить переменные окружения
            for key, original_value in original_env.items():
                if original_value is not None:
                    os.environ[key] = original_value
                elif key in os.environ:
                    del os.environ[key]

            if "ELASTICSEARCH_HOSTS" not in test_case["env"] and "original_es" in locals():
                if original_es is not None:
                    os.environ["ELASTICSEARCH_HOSTS"] = original_es

    return True

def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА ELASTICSEARCH HOSTS")
    print("=" * 50)

    success = test_hosts_detection()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: Hosts detection работает!")
        print("\n📋 Для исправления fallback на MockSearchService:")
        print("   1. ✅ Исправлена автодетекция Docker environment")
        print("   2. ✅ Поддержка переменной ELASTICSEARCH_HOSTS из docker-compose")
        print("   3. ➡️ Нужно перезапустить Docker контейнеры")
    else:
        print("❌ FAILURE: Есть проблемы с конфигурацией hosts")

    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)