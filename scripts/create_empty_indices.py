#!/usr/bin/env python3
"""
Creating пустых indices Elasticsearch
Используется когда нет files with data для загрузки
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import aiohttp


async def create_ac_patterns_index(es_host: str, index_name: str) -> bool:
    """Создать индекс AC patterns с маппингами"""
    print(f"[BUILD]  Creating индекса: {index_name}")

    index_config = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "pattern_analyzer": {
                        "type": "custom",
                        "tokenizer": "keyword",
                        "filter": ["lowercase"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "pattern": {
                    "type": "text",
                    "analyzer": "pattern_analyzer",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "tier": {"type": "integer"},
                "confidence": {"type": "float"},
                "entity_id": {"type": "integer"},
                "entity_type": {"type": "keyword"},
                "original_name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "variations": {"type": "keyword"}
            }
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Проверяем существование индекса
            async with session.head(f"http://{es_host}/{index_name}") as response:
                if response.status == 200:
                    print(f"   [OK] Индекс уже существует")
                    return True

            # Создаём индекс
            async with session.put(
                f"http://{es_host}/{index_name}",
                json=index_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    print(f"   [OK] Индекс создан успешно")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   [ERROR] Ошибка создания: HTTP {response.status}")
                    print(f"   {error_text}")
                    return False

    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
        return False


async def create_vectors_index(es_host: str, index_name: str, vector_dim: int = 384) -> bool:
    """Создать индекс vectors с kNN маппингами"""
    print(f"[BUILD]  Creating индекса: {index_name}")

    index_config = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0
        },
        "mappings": {
            "properties": {
                "entity_id": {"type": "integer"},
                "entity_type": {"type": "keyword"},
                "name": {
                    "type": "text",
                    "fields": {
                        "keyword": {"type": "keyword"}
                    }
                },
                "vector": {
                    "type": "dense_vector",
                    "dims": vector_dim,
                    "index": True,
                    "similarity": "cosine"
                }
            }
        }
    }

    try:
        async with aiohttp.ClientSession() as session:
            # Проверяем существование индекса
            async with session.head(f"http://{es_host}/{index_name}") as response:
                if response.status == 200:
                    print(f"   [OK] Индекс уже существует")
                    return True

            # Создаём индекс
            async with session.put(
                f"http://{es_host}/{index_name}",
                json=index_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    print(f"   [OK] Индекс создан успешно")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   [ERROR] Ошибка: HTTP {response.status}")
                    print(f"   {error_text}")
                    return False

    except Exception as e:
        print(f"   [ERROR] Ошибка: {e}")
        return False


async def main_async(args):
    """Основная логика"""
    es_host = args.es_host
    prefix = args.index_prefix

    print("=" * 60)
    print("Creating ПУСТЫХ indices ELASTICSEARCH")
    print("=" * 60)
    print(f"Elasticsearch: {es_host}")
    print(f"Префикс: {prefix}")
    print()

    # Создаём индексы
    ac_index = f"{prefix}_ac_patterns"
    vector_index = f"{prefix}_vectors"

    ac_success = await create_ac_patterns_index(es_host, ac_index)
    vector_success = await create_vectors_index(es_host, vector_index)

    print()
    if ac_success and vector_success:
        print("[OK] All indices созданы успешно")
        return 0
    elif ac_success:
        print("[WARN]  Создан Only AC индекс (vector индекс не создан)")
        return 0
    else:
        print("[ERROR] Не удалось создать индексы")
        return 1


def main():
    parser = argparse.ArgumentParser(
        description="Создать пустые индексы Elasticsearch"
    )

    parser.add_argument(
        "--es-host",
        required=True,
        help="Elasticsearch host (например, localhost:9200)"
    )

    parser.add_argument(
        "--index-prefix",
        default="sanctions",
        help="Префикс имён indices (по умолчанию: sanctions)"
    )

    parser.add_argument(
        "--vector-dim",
        type=int,
        default=384,
        help="Размерность vectors (по умолчанию: 384)"
    )

    args = parser.parse_args()

    # Start async main
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[WARN]  Прервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
