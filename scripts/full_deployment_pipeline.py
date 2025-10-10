#!/usr/bin/env python3
"""
Full Deployment Pipeline
========================

Complete cycle of preparing and deploying sanctions data to Elasticsearch.

What it does:
1. Checks source files (sanctioned_persons.json, sanctioned_companies.json, terrorism_black_list.json)
2. Generates AC patterns from source data
3. Generates vector embeddings from AC patterns
4. Creates indices in Elasticsearch
5. Loads AC patterns into ES
6. Loads vectors into ES
7. Runs warmup queries
8. Verifies results

Usage:
    # Full cycle (locally)
    python scripts/full_deployment_pipeline.py

    # Full cycle (production)
    python scripts/full_deployment_pipeline.py --es-host elasticsearch:9200

    # Skip data preparation (if already exists)
    python scripts/full_deployment_pipeline.py --skip-preparation

    # Preparation only (without ES loading)
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
    print(f"\n[Step {step_num}/{total_steps}] {text}")
    print("-" * 70)


def check_source_files() -> Dict[str, Path]:
    """Check source files existence"""
    print_step(1, 7, "Checking source files")

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
            print(f"[OK] {name:12} {filepath.name:45} ({size_mb:.1f} MB)")
        else:
            print(f"[ERROR] {name:12} {filepath.name:45} MISSING!")
            all_exist = False

    if not all_exist:
        print("\n[ERROR] Not all source files found!")
        print("   Ensure sanction files are in src/ai_service/data/")
        sys.exit(1)

    return files


def prepare_sanctions_data(max_patterns: int = 200, skip_vectors: bool = False) -> Tuple[Path, Optional[Path]]:
    """Prepare data: AC patterns + vectors"""
    print_step(2, 7, "Preparing AC patterns and vectors")

    output_dir = project_root / "output" / "sanctions"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Arguments for prepare_sanctions_data.py
    cmd = [
        sys.executable,
        str(project_root / "scripts" / "prepare_sanctions_data.py"),
        "--output-dir", str(output_dir),
        "--max-patterns", str(max_patterns)
    ]

    if skip_vectors:
        cmd.append("--skip-vectors")

    print(f"[CMD] {' '.join(cmd)}")
    print()

    # Run preparation
    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print("\n[ERROR] Data preparation failed!")
        sys.exit(1)

    # Find created files
    patterns_files = sorted(output_dir.glob("ac_patterns_*.json"), reverse=True)
    vectors_files = sorted(output_dir.glob("vectors_*.json"), reverse=True)

    if not patterns_files:
        print("\n[ERROR] AC patterns file not found!")
        sys.exit(1)

    patterns_file = patterns_files[0]
    vectors_file = vectors_files[0] if vectors_files else None

    print(f"\n[OK] AC patterns: {patterns_file.name}")
    if vectors_file:
        print(f"[OK] Vectors: {vectors_file.name}")
    else:
        print(f"[WARN] Vectors not created (skipped)")

    return patterns_file, vectors_file


def deploy_to_elasticsearch(
    es_host: str,
    patterns_file: Path,
    vectors_file: Optional[Path],
    index_prefix: str = "sanctions"
) -> bool:
    """Deployment в Elasticsearch"""
    print_step(3, 7, "Deployment в Elasticsearch")

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

    print(f"[CMD] Command: {' '.join(cmd)}")
    print()

    result = subprocess.run(cmd, capture_output=False, text=True)

    if result.returncode != 0:
        print("\n[ERROR] Deployment завершилось с ошибкой!")
        return False

    print("\n[OK] Deployment completed successfully")
    return True


def verify_deployment(es_host: str, index_prefix: str = "sanctions") -> bool:
    """Check развёртывания"""
    print_step(4, 7, "Check развёртывания")

    import aiohttp

    async def check():
        ac_index = f"{index_prefix}_ac_patterns"
        vector_index = f"{index_prefix}_vectors"

        try:
            async with aiohttp.ClientSession() as session:
                # Check AC patterns
                async with session.get(f"http://{es_host}/{ac_index}/_count") as response:
                    if response.status == 200:
                        data = await response.json()
                        ac_count = data.get('count', 0)
                        print(f"[OK] {ac_index:30} {ac_count:,} documents")
                    else:
                        print(f"[ERROR] {ac_index:30} не found")
                        return False

                # Check vectors
                async with session.get(f"http://{es_host}/{vector_index}/_count") as response:
                    if response.status == 200:
                        data = await response.json()
                        vector_count = data.get('count', 0)
                        if vector_count > 0:
                            print(f"[OK] {vector_index:30} {vector_count:,} documents")
                        else:
                            print(f"[WARN]  {vector_index:30} пустой (векторы не загружены)")
                    else:
                        print(f"[WARN]  {vector_index:30} не found")

                return True
        except Exception as e:
            print(f"[ERROR] Ошибка проверки: {e}")
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
    print_header("[OK] Deployment ЗАВЕРШЕНО")

    elapsed = time.time() - start_time
    elapsed_min = int(elapsed // 60)
    elapsed_sec = int(elapsed % 60)

    print(f"⏱️  Execution time: {elapsed_min}m {elapsed_sec}s")
    print()
    print("[DATA] Created files:")
    print(f"   • {patterns_file.name}")
    if vectors_file:
        print(f"   • {vectors_file.name}")
    print()
    print("[LOCATION] Elasticsearch:")
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
        description="Full cycle подreadyки и развёртывания санкционных data",
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
        help="Префикс имён indices (default: sanctions)"
    )

    parser.add_argument(
        "--max-patterns",
        type=int,
        default=200,
        help="Максимум patterns на entity (default: 200)"
    )

    parser.add_argument(
        "--skip-preparation",
        action="store_true",
        help="Skip подreadyку data (использовать существующие файлы)"
    )

    parser.add_argument(
        "--skip-vectors",
        action="store_true",
        help="Skip генерацию vectors (быстрее)"
    )

    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="Only Preparation data (without loading в ES)"
    )

    args = parser.parse_args()

    start_time = time.time()

    print_header("[INIT] Full cycle РАЗВЁРТЫВАНИЯ САНКЦИОННЫХ data")
    print(f"[LOCATION] Elasticsearch: {args.es_host}")
    print(f"[DATA] Index prefix: {args.index_prefix}")
    print(f"⚙️  Max patterns: {args.max_patterns}")

    try:
        # Step 1: Check source files
        check_source_files()

        # Step 2: Preparation data
        if args.skip_preparation:
            print_step(2, 7, "Поиск существующих files")
            output_dir = project_root / "output" / "sanctions"
            patterns_files = sorted(output_dir.glob("ac_patterns_*.json"), reverse=True)
            vectors_files = sorted(output_dir.glob("vectors_*.json"), reverse=True)

            if not patterns_files:
                print("[ERROR] AC patterns файл не found! Запустите без --skip-preparation")
                sys.exit(1)

            patterns_file = patterns_files[0]
            vectors_file = vectors_files[0] if vectors_files else None

            print(f"[OK] Используем существующий: {patterns_file.name}")
            if vectors_file:
                print(f"[OK] Используем существующий: {vectors_file.name}")
        else:
            patterns_file, vectors_file = prepare_sanctions_data(
                max_patterns=args.max_patterns,
                skip_vectors=args.skip_vectors
            )

        # Step 3: Deployment (если не prepare-only)
        if args.prepare_only:
            print("\n[INFO]  Режим prepare-only: Deployment пропущено")
            print(f"\n[DATA] Файлы readyы в: {patterns_file.parent}")
            print(f"\n[TIP] Для развёртывания запустите:")
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

        # Step 4: Check
        verify_deployment(args.es_host, args.index_prefix)

        # Summary
        print_summary(start_time, patterns_file, vectors_file, args.es_host, args.index_prefix)

    except KeyboardInterrupt:
        print("\n\n[WARN]  Прервано пользователем")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n[ERROR] Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
