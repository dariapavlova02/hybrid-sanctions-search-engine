#!/usr/bin/env python3
"""
Deploy to Elasticsearch
=======================

One-click script to create indices and load sanctions data into Elasticsearch.

Features:
- Interactive ES host input (or via argument)
- Create indices with proper mappings
- Bulk load AC patterns and vectors
- Health checks and verification
- Warmup queries

Usage:
    # Interactive mode (asks for ES host)
    python scripts/deploy_to_elasticsearch.py

    # With ES host argument
    python scripts/deploy_to_elasticsearch.py --es-host localhost:9200

    # Docker localhost
    python scripts/deploy_to_elasticsearch.py --es-host localhost:9200

    # Remote ES
    python scripts/deploy_to_elasticsearch.py --es-host 192.168.1.100:9200

    # Load specific manifest
    python scripts/deploy_to_elasticsearch.py \\
        --manifest output/sanctions/deployment_manifest.json \\
        --es-host localhost:9200
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import aiohttp

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def print_header(text: str):
    """Print formatted header"""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_step(step_num: int, text: str):
    """Print step indicator"""
    print(f"\n🔹 Step {step_num}: {text}")
    print("-" * 50)


def get_es_host_interactive() -> str:
    """Interactive ES host input"""
    print_header("📍 ELASTICSEARCH CONNECTION")

    print("Enter Elasticsearch host (examples):")
    print("  • localhost:9200        (local Docker)")
    print("  • 192.168.1.100:9200    (remote server)")
    print("  • es.example.com:9200   (production)")
    print()

    while True:
        es_host = input("Elasticsearch host: ").strip()

        if not es_host:
            print("❌ Host cannot be empty")
            continue

        # Add http:// if not present
        if not es_host.startswith(('http://', 'https://')):
            es_host = f"http://{es_host}"

        # Confirm
        print(f"\n📍 Will connect to: {es_host}")
        confirm = input("Correct? (y/n): ").strip().lower()

        if confirm == 'y':
            return es_host

        print()


async def check_elasticsearch_health(es_host: str) -> bool:
    """Check Elasticsearch cluster health"""
    print_step(1, "Checking Elasticsearch health")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{es_host}/_cluster/health", timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Cluster status: {health['status']}")
                    print(f"✅ Cluster name: {health['cluster_name']}")
                    print(f"✅ Nodes: {health['number_of_nodes']}")
                    print(f"✅ Active shards: {health['active_primary_shards']}")
                    return True
                else:
                    print(f"❌ Health check failed: HTTP {response.status}")
                    return False

    except asyncio.TimeoutError:
        print(f"❌ Connection timeout to {es_host}")
        print("   Check that Elasticsearch is running")
        return False
    except aiohttp.ClientConnectorError:
        print(f"❌ Cannot connect to {es_host}")
        print("   Check host and port, ensure Elasticsearch is running")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def create_ac_patterns_index(es_host: str, index_name: str) -> bool:
    """Create AC patterns index with mappings"""
    print(f"\n🏗️  Creating index: {index_name}")

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
            # Check if index exists
            async with session.head(f"{es_host}/{index_name}") as response:
                if response.status == 200:
                    print(f"   ⚠️  Index already exists")
                    overwrite = input(f"   Delete and recreate {index_name}? (y/n): ").strip().lower()

                    if overwrite == 'y':
                        async with session.delete(f"{es_host}/{index_name}") as del_response:
                            if del_response.status == 200:
                                print(f"   🗑️  Deleted existing index")
                            else:
                                print(f"   ❌ Failed to delete index: HTTP {del_response.status}")
                                return False
                    else:
                        print(f"   ℹ️  Keeping existing index")
                        return True

            # Create index
            async with session.put(
                f"{es_host}/{index_name}",
                json=index_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    print(f"   ✅ Index created successfully")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Failed to create index: HTTP {response.status}")
                    print(f"   {error_text}")
                    return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def create_vectors_index(es_host: str, index_name: str, vector_dim: int = 384) -> bool:
    """Create vectors index with kNN mappings"""
    print(f"\n🏗️  Creating index: {index_name}")

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
            # Check if index exists
            async with session.head(f"{es_host}/{index_name}") as response:
                if response.status == 200:
                    print(f"   ⚠️  Index already exists, skipping")
                    return True

            # Create index
            async with session.put(
                f"{es_host}/{index_name}",
                json=index_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    print(f"   ✅ Index created successfully")
                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Failed: HTTP {response.status}")
                    print(f"   {error_text}")
                    return False

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def bulk_load_patterns(es_host: str, index_name: str, patterns_file: Path, batch_size: int = 5000) -> bool:
    """Bulk load AC patterns into Elasticsearch with batching"""
    print(f"\n📦 Loading patterns from: {patterns_file.name}")

    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        patterns = data.get('patterns', [])
        total = len(patterns)

        if total == 0:
            print("   ⚠️  No patterns to load")
            return True

        print(f"   📊 Total patterns: {total:,}")
        print(f"   📦 Batch size: {batch_size:,}")

        # Process in batches
        batches = [patterns[i:i + batch_size] for i in range(0, len(patterns), batch_size)]
        total_batches = len(batches)

        print(f"   ⬆️  Uploading {total_batches} batches to Elasticsearch...")

        async with aiohttp.ClientSession() as session:
            total_errors = 0

            for batch_num, batch in enumerate(batches, 1):
                # Build bulk request for this batch
                bulk_data = []
                for pattern in batch:
                    bulk_data.append(json.dumps({"index": {"_index": index_name}}))
                    bulk_data.append(json.dumps(pattern))

                bulk_body = "\n".join(bulk_data) + "\n"

                # Send bulk request
                async with session.post(
                    f"{es_host}/_bulk",
                    data=bulk_body,
                    headers={"Content-Type": "application/x-ndjson"},
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status == 200:
                        result = await response.json()

                        if result.get('errors'):
                            errors = [item for item in result['items'] if 'error' in item.get('index', {})]
                            total_errors += len(errors)

                        print(f"      Batch {batch_num}/{total_batches}: ✅ {len(batch):,} patterns")
                    else:
                        error_text = await response.text()
                        print(f"      Batch {batch_num}/{total_batches}: ❌ HTTP {response.status}")
                        print(f"      {error_text[:200]}")
                        return False

            if total_errors > 0:
                print(f"   ⚠️  Loaded {total:,} patterns with {total_errors} errors")
            else:
                print(f"   ✅ Successfully loaded {total:,} patterns")

            return True

    except FileNotFoundError:
        print(f"   ❌ File not found: {patterns_file}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def bulk_load_vectors(es_host: str, index_name: str, vectors_file: Path) -> bool:
    """Bulk load vector embeddings into Elasticsearch"""
    print(f"\n📦 Loading vectors from: {vectors_file.name}")

    try:
        with open(vectors_file, 'r', encoding='utf-8') as f:
            vectors_data = json.load(f)

        if not vectors_data:
            print("   ⚠️  No vector data to load")
            return True

        total = len(vectors_data)
        print(f"   📊 Total vectors: {total:,}")

        # Build bulk request
        bulk_data = []
        for vector_entry in vectors_data:
            # Index action
            bulk_data.append(json.dumps({
                "index": {"_index": index_name}
            }))
            # Document
            doc = {
                "name": vector_entry.get("name", ""),
                "vector": vector_entry.get("vector", []),
                "metadata": vector_entry.get("metadata", {})
            }
            bulk_data.append(json.dumps(doc))

        bulk_body = "\n".join(bulk_data) + "\n"

        # Send bulk request
        print(f"   ⬆️  Uploading to Elasticsearch...")

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{es_host}/_bulk",
                data=bulk_body,
                headers={"Content-Type": "application/x-ndjson"},
                timeout=aiohttp.ClientTimeout(total=300)
            ) as response:
                if response.status == 200:
                    result = await response.json()

                    if result.get('errors'):
                        errors = [item for item in result['items'] if 'error' in item.get('index', {})]
                        print(f"   ⚠️  Loaded with {len(errors)} errors")
                        if errors:
                            print(f"   First error: {errors[0]['index']['error']}")
                    else:
                        print(f"   ✅ Successfully loaded {total:,} vectors")

                    return True
                else:
                    error_text = await response.text()
                    print(f"   ❌ Bulk load failed: HTTP {response.status}")
                    print(f"   {error_text[:500]}")
                    return False

    except FileNotFoundError:
        print(f"   ❌ File not found: {vectors_file}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False


async def verify_indices(es_host: str, expected_indices: List[str]) -> bool:
    """Verify that indices were created and have data"""
    print_step(3, "Verifying indices")

    try:
        async with aiohttp.ClientSession() as session:
            all_ok = True

            for index in expected_indices:
                # Get index stats
                async with session.get(f"{es_host}/{index}/_count") as response:
                    if response.status == 200:
                        result = await response.json()
                        count = result.get('count', 0)
                        print(f"✅ {index:40} {count:,} documents")

                        if count == 0:
                            print(f"   ⚠️  Index is empty!")
                            all_ok = False
                    else:
                        print(f"❌ {index:40} not found")
                        all_ok = False

            return all_ok

    except Exception as e:
        print(f"❌ Error verifying indices: {e}")
        return False


async def run_warmup_queries(es_host: str, index_name: str):
    """Run warmup queries to cache data"""
    print_step(4, "Running warmup queries")

    warmup_patterns = [
        "путин",
        "газпром",
        "ukraine",
        "sanctions"
    ]

    print(f"🔥 Warming up index: {index_name}")

    try:
        async with aiohttp.ClientSession() as session:
            for pattern in warmup_patterns:
                query = {
                    "query": {
                        "match": {
                            "pattern": pattern
                        }
                    },
                    "size": 10
                }

                async with session.post(
                    f"{es_host}/{index_name}/_search",
                    json=query,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        hits = result['hits']['total']['value']
                        print(f"   ✅ '{pattern}': {hits} hits")
                    else:
                        print(f"   ⚠️  '{pattern}': query failed")

        print("✅ Warmup complete")

    except Exception as e:
        print(f"⚠️  Warmup error: {e}")


async def main_async(args):
    """Main async deployment logic"""

    # Get ES host
    if args.es_host:
        es_host = args.es_host
        if not es_host.startswith(('http://', 'https://')):
            es_host = f"http://{es_host}"
    else:
        es_host = get_es_host_interactive()

    print_header("🚀 ELASTICSEARCH DEPLOYMENT")
    print(f"📍 Elasticsearch: {es_host}")

    # Step 1: Health check
    if not await check_elasticsearch_health(es_host):
        print("\n❌ Cannot proceed without healthy Elasticsearch cluster")
        return 1

    # Step 2: Create indices
    print_step(2, "Creating indices")

    # AC patterns index
    ac_index = f"{args.index_prefix}_ac_patterns"
    if not await create_ac_patterns_index(es_host, ac_index):
        print(f"❌ Failed to create AC patterns index")
        return 1

    # Vectors index (if needed)
    vector_index = None
    if args.create_vector_indices or args.vectors_file:
        vector_index = f"{args.index_prefix}_vectors"
        if not await create_vectors_index(es_host, vector_index):
            print(f"❌ Failed to create vectors index")
            return 1

    # Step 3: Load AC patterns
    if args.patterns_file:
        patterns_path = Path(args.patterns_file)
    else:
        # Find latest patterns file in output
        output_dir = project_root / "output" / "sanctions"
        patterns_files = list(output_dir.glob("ac_patterns_*.json"))

        if not patterns_files:
            print("❌ No AC patterns file found")
            print(f"   Run: python scripts/prepare_sanctions_data.py")
            return 1

        patterns_path = max(patterns_files, key=lambda p: p.stat().st_mtime)
        print(f"ℹ️  Using latest patterns file: {patterns_path.name}")

    if not await bulk_load_patterns(es_host, ac_index, patterns_path):
        print(f"❌ Failed to load patterns")
        return 1

    # Load vectors if file provided
    if vector_index and args.vectors_file:
        vectors_path = args.vectors_file
        if not await bulk_load_vectors(es_host, vector_index, vectors_path):
            print(f"⚠️  Failed to load vectors (continuing anyway)")
    elif vector_index and not args.vectors_file:
        # Try to auto-detect vectors file
        output_dir = project_root / "output" / "sanctions"
        vectors_files = list(output_dir.glob("vectors_*.json"))

        if vectors_files:
            vectors_path = max(vectors_files, key=lambda p: p.stat().st_mtime)
            print(f"ℹ️  Using latest vectors file: {vectors_path.name}")
            if not await bulk_load_vectors(es_host, vector_index, vectors_path):
                print(f"⚠️  Failed to load vectors (continuing anyway)")
        else:
            print("ℹ️  No vectors file found, skipping vector loading")

    # Step 4: Verify
    indices_to_verify = [ac_index]
    if vector_index:
        indices_to_verify.append(vector_index)

    if not await verify_indices(es_host, indices_to_verify):
        print("\n⚠️  Some indices have issues")

    # Step 5: Warmup
    if not args.skip_warmup:
        await run_warmup_queries(es_host, ac_index)

    # Summary
    print_header("✅ DEPLOYMENT COMPLETE")
    print(f"📍 Elasticsearch: {es_host}")
    print(f"📋 Indices created:")
    for idx in indices_to_verify:
        print(f"   • {idx}")
    print(f"\n💡 Test search:")
    print(f"   curl '{es_host}/{ac_index}/_search?q=pattern:путин&pretty'")

    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Deploy sanctions data to Elasticsearch",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "--es-host",
        help="Elasticsearch host (e.g., localhost:9200, 192.168.1.100:9200)"
    )

    parser.add_argument(
        "--index-prefix",
        default="sanctions",
        help="Index name prefix (default: sanctions)"
    )

    parser.add_argument(
        "--patterns-file",
        type=Path,
        help="Path to AC patterns JSON file (auto-detects latest if not specified)"
    )

    parser.add_argument(
        "--vectors-file",
        type=Path,
        help="Path to vectors JSON file (auto-detects latest if not specified)"
    )

    parser.add_argument(
        "--create-vector-indices",
        action="store_true",
        help="Also create vector indices (kNN)"
    )

    parser.add_argument(
        "--skip-warmup",
        action="store_true",
        help="Skip warmup queries"
    )

    parser.add_argument(
        "--manifest",
        type=Path,
        help="Use deployment manifest file"
    )

    args = parser.parse_args()

    # Run async main
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
