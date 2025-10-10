#!/usr/bin/env python3
"""
Full Deployment Pipeline
========================

Полный цикл подготовки и развёртывания санкционных данных в Elasticsearch.

Что делает:
1. Проверяет исходные файлы (sanctioned_persons.json, sanctioned_companies.json, terrorism_black_list.json)
2. Генерирует AC patterns из исходников
3. Генерирует vector embeddings из AC patterns
4. Создаёт индексы в Elasticsearch
5. Загружает AC patterns в ES
6. Загружает vectors в ES
7. Делает warmup queries
8. Проверяет результат

Usage:
    # Полный цикл (локально)
    python scripts/full_deployment_pipeline.py

    # Полный цикл (на production)
    python scripts/full_deployment_pipeline.py --es-host elasticsearch:9200

    # Пропустить подготовку данных (если уже есть)
    python scripts/full_deployment_pipeline.py --skip-preparation

    # Только подготовка (без загрузки в ES)
    python scripts/full_deployment_pipeline.py --prepare-only
"""

import argparse
import asyncio
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'='*70}")
    print(f"  {text}")
    print(f"{'='*70}\n")


def print_step(step_num: int, total_steps: int, text: str):
    """Print step indicator"""
    print(f"\n🔹 Step {step_num}/{total_steps}: {text}")
    print("-" * 70)


def check_source_files() -> Dict[str, Path]:
    """Проверка наличия исходных файлов"""
    print_step(1, 7, "Проверка исходных файлов")

    data_dir = project_root / "src" / "ai_service" / "data"

    files = {
        "persons": data_dir / "sanctioned_persons.json",
        "companies": data_dir / "sanctioned_companies.json",
        "terrorism": data_dir / "terrorism_black_list.json"
    }

    all_exist = True
    for name, filepath in files.items():
        if filepath.exists():
            size_mb = filepath.stat().st_size / (1024 * 1024)
            print(f"✅ {name:12} {filepath.name:45} ({size_mb:.1f} MB)")
        else:
            print(f"❌ {name:12} {filepath.name:45} ОТСУТСТВУЕТ!")
            all_exist = False

    if not all_exist:
        print("\n❌ Не все исходные файлы найдены!")
        print("   Убедитесь что файлы санкций находятся в src/ai_service/data/")
        sys.exit(1)

    return files


def prepare_sanctions_data(max_patterns: int = 200, skip_vectors: bool = False) -> Tuple[Path, Optional[Path]]:
    """Подготовка данных: AC patterns + vectors"""
    print_step(2, 7, "Подготовка AC patterns и векторов")

    output_dir = project_root / "output" / "sanctions"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Аргументы для prepare_sanctions_data.py
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "prepare_sanctions_data.py"),
        "--output-dir", str(output_dir),
        "--max-patterns", str(max_patterns)
    ]

    if skip_vectors:
        cmd.append("--skip-vectors")

    print(f"📝 Команда: {' '.join(cmd)}")
    print()

    # Запуск подготовки
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print("\n❌ Подготовка данных завершилась с ошибкой!")
        sys.exit(1)

    # Находим созданные файлы
    patterns_files = sorted(output_dir.glob("ac_patterns_*.json"), reverse=True)
    vectors_files = sorted(output_dir.glob("vectors_*.json"), reverse=True)

    if not patterns_files:
        print("\n❌ AC patterns файл не найден!")
        sys.exit(1)

    patterns_file = patterns_files[0]
    vectors_file = vectors_files[0] if vectors_files else None

    print(f"\n✅ AC patterns: {patterns_file.name}")
    if vectors_file:
        print(f"✅ Vectors: {vectors_file.name}")
    else:
        print(f"⚠️  Vectors не созданы (пропущены)")

    return patterns_file, vectors_file


def deploy_to_elasticsearch(
    es_host: str,
    patterns_file: Path,
    vectors_file: Optional[Path],
    index_prefix: str = "sanctions"
) -> bool:
    """Развёртывание в Elasticsearch"""
    print_step(3, 7, "Развёртывание в Elasticsearch")

    cmd = [
        sys.executable,
        str(project_root / "scripts" / "deploy_to_elasticsearch.py"),
        "--es-host", es_host,
        "--index-prefix", index_prefix,
        "--patterns-file", str(patterns_file)
    ]

    if vectors_file:
        cmd.extend([
            "--vectors-file", str(vectors_file),
            "--create-vector-indices"
        ])

    print(f"📝 Команда: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print("\n❌ Развёртывание завершилось с ошибкой!")
        return False

    print("\n✅ Развёртывание завершено успешно")
    return True


def verify_deployment(es_host: str, index_prefix: str = "sanctions") -> bool:
    """Проверка развёртывания"""
    print_step(4, 7, "Проверка развёртывания")

    import aiohttp

    async def check():
        ac_index = f"{index_prefix}_ac_patterns"
        vector_index = f"{index_prefix}_vectors"

        try:
            async with aiohttp.ClientSession() as session:
                # Проверка AC patterns
                async with session.get(f"http://{es_host}/{ac_index}/_count") as response:
                    if response.status == 200:
                        data = await response.json()
                        ac_count = data.get('count', 0)
                        print(f"✅ {ac_index:30} {ac_count:,} документов")
                    else:
                        print(f"❌ {ac_index:30} не найден")
                        return False

                # Проверка vectors
                async with session.get(f"http://{es_host}/{vector_index}/_count") as response:
                    if response.status == 200:
                        data = await response.json()
                        vector_count = data.get('count', 0)
                        if vector_count > 0:
                            print(f"✅ {vector_index:30} {vector_count:,} документов")
                        else:
                            print(f"⚠️  {vector_index:30} пустой (векторы не загружены)")
                    else:
                        print(f"⚠️  {vector_index:30} не найден")

                return True
        except Exception as e:
            print(f"❌ Ошибка проверки: {e}")
            return False

    return asyncio.run(check())


def print_summary(
    start_time: float,
    patterns_file: Path,
    vectors_file: Optional[Path],
    es_host: str,
    index_prefix: str
):
    """Вывод итоговой сводки"""
    print_header("✅ РАЗВЁРТЫВАНИЕ ЗАВЕРШЕНО")

    elapsed = time.time() - start_time
    elapsed_min = int(elapsed // 60)
    elapsed_sec = int(elapsed % 60)

    print(f"⏱️  Время выполнения: {elapsed_min}m {elapsed_sec}s")
    print()
    print("📦 Созданные файлы:")
    print(f"   • {patterns_file.name}")
    if vectors_file:
        print(f"   • {vectors_file.name}")
    print()
    print("📍 Elasticsearch:")
    print(f"   • Host: {es_host}")
    print(f"   • Индексы:")
    print(f"     - {index_prefix}_ac_patterns")
    print(f"     - {index_prefix}_vectors")
    print()
    print("🧪 Тестовый запрос:")
    print(f"   curl -X POST http://{es_host.replace('elasticsearch:9200', 'localhost:8000')}/process \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"text\": \"Дарья ПАвлова ИНН 2839403975\"}}' | jq")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="Полный цикл подготовки и развёртывания санкционных данных",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--es-host",
        default="localhost:9200",
        help="Elasticsearch host (default: localhost:9200)"
    )

    parser.add_argument(
        "--index-prefix",
        default="sanctions",
        help="Префикс имён индексов (default: sanctions)"
    )

    parser.add_argument(
        "--max-patterns",
        type=int,
        default=200,
        help="Максимум паттернов на entity (default: 200)"
    )

    parser.add_argument(
        "--skip-preparation",
        action="store_true",
        help="Пропустить подготовку данных (использовать существующие файлы)"
    )

    parser.add_argument(
        "--skip-vectors",
        action="store_true",
        help="Пропустить генерацию векторов (быстрее)"
    )

    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Только подготовка данных (без загрузки в ES)"
    )

    args = parser.parse_args()

    start_time = time.time()

    print_header("🚀 ПОЛНЫЙ ЦИКЛ РАЗВЁРТЫВАНИЯ САНКЦИОННЫХ ДАННЫХ")
    print(f"📍 Elasticsearch: {args.es_host}")
    print(f"📦 Index prefix: {args.index_prefix}")
    print(f"⚙️  Max patterns: {args.max_patterns}")

    try:
        # Step 1: Проверка исходных файлов
        check_source_files()

        # Step 2: Подготовка данных
        if args.skip_preparation:
            print_step(2, 7, "Поиск существующих файлов")
            output_dir = project_root / "output" / "sanctions"
            patterns_files = sorted(output_dir.glob("ac_patterns_*.json"), reverse=True)
            vectors_files = sorted(output_dir.glob("vectors_*.json"), reverse=True)

            if not patterns_files:
                print("❌ AC patterns файл не найден! Запустите без --skip-preparation")
                sys.exit(1)

            patterns_file = patterns_files[0]
            vectors_file = vectors_files[0] if vectors_files else None

            print(f"✅ Используем существующий: {patterns_file.name}")
            if vectors_file:
                print(f"✅ Используем существующий: {vectors_file.name}")
        else:
            patterns_file, vectors_file = prepare_sanctions_data(
                max_patterns=args.max_patterns,
                skip_vectors=args.skip_vectors
            )

        # Step 3: Развёртывание (если не prepare-only)
        if args.prepare_only:
            print("\nℹ️  Режим prepare-only: развёртывание пропущено")
            print(f"\n📦 Файлы готовы в: {patterns_file.parent}")
            print(f"\n💡 Для развёртывания запустите:")
            print(f"   python scripts/deploy_to_elasticsearch.py \\")
            print(f"     --es-host {args.es_host} \\")
            print(f"     --patterns-file {patterns_file} \\")
            if vectors_file:
                print(f"     --vectors-file {vectors_file} \\")
                print(f"     --create-vector-indices")
            sys.exit(0)

        success = deploy_to_elasticsearch(
            args.es_host,
            patterns_file,
            vectors_file,
            args.index_prefix
        )

        if not success:
            sys.exit(1)

        # Step 4: Проверка
        verify_deployment(args.es_host, args.index_prefix)

        # Summary
        print_summary(start_time, patterns_file, vectors_file, args.es_host, args.index_prefix)

    except KeyboardInterrupt:
        print("\n\n⚠️  Прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
