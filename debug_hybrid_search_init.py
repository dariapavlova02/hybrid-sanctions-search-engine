#!/usr/bin/env python3

"""
Диагностика инициализации HybridSearchService для понимания причин падения.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def debug_hybrid_search_init():
    """Отладка инициализации HybridSearchService."""
    print("🔍 ДИАГНОСТИКА ИНИЦИАЛИЗАЦИИ HYBRIDSEARCHSERVICE")
    print("=" * 60)

    try:
        # Шаг 1: Импорт модулей
        print("1. Импорт модулей...")
        from ai_service.layers.search.config import HybridSearchConfig
        from ai_service.layers.search.hybrid_search_service import HybridSearchService
        print("✅ Модули импортированы успешно")

        # Шаг 2: Создание конфигурации
        print("\n2. Создание конфигурации...")
        try:
            search_config = HybridSearchConfig.from_env()
            print("✅ Конфигурация создана:")
            print(f"   Elasticsearch hosts: {search_config.elasticsearch.hosts}")
            print(f"   Default index: {search_config.elasticsearch.default_index}")
            print(f"   AC index: {search_config.elasticsearch.ac_index}")
            print(f"   Vector index: {search_config.elasticsearch.vector_index}")
            print(f"   Enable fallback: {search_config.enable_fallback}")
            print(f"   Default mode: {search_config.default_mode}")
        except Exception as config_error:
            print(f"❌ Ошибка создания конфигурации: {config_error}")
            print(f"   Type: {type(config_error)}")
            import traceback
            traceback.print_exc()
            return False

        # Шаг 3: Создание HybridSearchService
        print("\n3. Создание HybridSearchService...")
        try:
            search_service = HybridSearchService(search_config)
            print("✅ HybridSearchService создан")
        except Exception as create_error:
            print(f"❌ Ошибка создания HybridSearchService: {create_error}")
            print(f"   Type: {type(create_error)}")
            import traceback
            traceback.print_exc()
            return False

        # Шаг 4: Инициализация
        print("\n4. Инициализация HybridSearchService...")
        try:
            search_service.initialize()
            print("✅ HybridSearchService инициализирован успешно!")

            # Попробуем health check
            health = await search_service.health_check()
            print(f"✅ Health check: {health}")

            return True

        except Exception as init_error:
            print(f"❌ Ошибка инициализации HybridSearchService: {init_error}")
            print(f"   Type: {type(init_error)}")
            import traceback
            traceback.print_exc()

            # Попробуем понять что именно не работает
            print("\n🔍 Детальная диагностика:")
            try:
                # Проверим доступность Elasticsearch
                print("   - Проверка доступности Elasticsearch...")
                import socket
                for host in search_config.elasticsearch.hosts:
                    try:
                        if ":" in host:
                            hostname, port = host.split(":")
                            port = int(port)
                        else:
                            hostname = host
                            port = 9200

                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex((hostname, port))
                        sock.close()

                        if result == 0:
                            print(f"     ✅ {hostname}:{port} доступен")
                        else:
                            print(f"     ❌ {hostname}:{port} недоступен (connect_ex: {result})")
                    except Exception as conn_error:
                        print(f"     ❌ {host} ошибка подключения: {conn_error}")

            except Exception as diag_error:
                print(f"   Ошибка диагностики: {diag_error}")

            return False

    except Exception as e:
        print(f"❌ Общая ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Главная функция."""
    print("🎯 ДИАГНОСТИКА HYBRIDSEARCHSERVICE")
    print("=" * 50)

    success = await debug_hybrid_search_init()

    print("\n" + "=" * 50)
    if success:
        print("🎉 SUCCESS: HybridSearchService работает корректно!")
    else:
        print("❌ FAILURE: HybridSearchService не может инициализироваться.")
        print("   Поэтому система переходит на MockSearchService.")

    return success

if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)