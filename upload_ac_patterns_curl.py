#!/usr/bin/env python3
"""
Upload AC patterns to Elasticsearch using curl (no elasticsearch library dependency)
"""

import json
import subprocess
import sys
import time

def upload_patterns_to_elasticsearch(patterns_file: str, es_host: str = "95.217.84.234:9200", index_name: str = "ac_patterns_updated"):
    """Upload AC patterns to Elasticsearch using curl"""

    print(f"🔍 UPLOADING AC PATTERNS TO ELASTICSEARCH")
    print("=" * 60)
    print(f"📍 Host: {es_host}")
    print(f"📂 File: {patterns_file}")
    print(f"📋 Index: {index_name}")

    # Load patterns
    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading patterns file: {e}")
        return False

    patterns = data.get('patterns', [])
    print(f"📊 Loaded {len(patterns)} patterns")

    # Test connection
    print(f"🔗 Testing connection to Elasticsearch...")
    result = subprocess.run([
        "curl", "-s", "-X", "GET", f"http://{es_host}/_cluster/health"
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Cannot connect to Elasticsearch: {result.stderr}")
        return False

    try:
        health = json.loads(result.stdout)
        print(f"✅ Connected! Cluster status: {health.get('status', 'unknown')}")
    except:
        print(f"✅ Connected! (raw response)")

    # Delete existing index if it exists
    print(f"🗑️ Deleting existing index if exists...")
    subprocess.run([
        "curl", "-s", "-X", "DELETE", f"http://{es_host}/{index_name}"
    ], capture_output=True)

    # Create index with mapping
    mapping = {
        "mappings": {
            "properties": {
                "pattern": {"type": "keyword"},
                "tier": {"type": "integer"},
                "type": {"type": "keyword"},
                "lang": {"type": "keyword"},
                "hints": {"type": "object"},
                "entity_id": {"type": "keyword"},
                "entity_type": {"type": "keyword"},
                "confidence": {"type": "float"},
                "requires_context": {"type": "boolean"},
                "canonical": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    }

    print(f"🔧 Creating index with mapping...")
    result = subprocess.run([
        "curl", "-s", "-X", "PUT", f"http://{es_host}/{index_name}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(mapping)
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error creating index: {result.stderr}")
        return False

    try:
        response = json.loads(result.stdout)
        if response.get('acknowledged'):
            print(f"✅ Index created successfully")
        else:
            print(f"⚠️ Index creation response: {response}")
    except:
        print(f"✅ Index created (raw response)")

    # Upload patterns in batches
    batch_size = 100
    total_uploaded = 0
    start_time = time.time()

    print(f"⬆️ Uploading {len(patterns)} patterns in batches of {batch_size}...")

    for i in range(0, len(patterns), batch_size):
        batch = patterns[i:i + batch_size]

        # Create bulk request
        bulk_data = ""
        for j, pattern in enumerate(batch):
            doc_id = i + j + 1
            index_line = json.dumps({"index": {"_index": index_name, "_id": doc_id}})
            doc = {
                **pattern,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            }
            doc_line = json.dumps(doc)
            bulk_data += index_line + "\n" + doc_line + "\n"

        # Upload batch
        result = subprocess.run([
            "curl", "-s", "-X", "POST", f"http://{es_host}/_bulk",
            "-H", "Content-Type: application/x-ndjson",
            "-d", bulk_data
        ], capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ Error uploading batch {i//batch_size + 1}: {result.stderr}")
            continue

        try:
            response = json.loads(result.stdout)
            if response.get('errors'):
                print(f"⚠️ Batch {i//batch_size + 1} had errors")
            else:
                total_uploaded += len(batch)
                print(f"✅ Batch {i//batch_size + 1}: {len(batch)} patterns uploaded")
        except:
            print(f"✅ Batch {i//batch_size + 1}: uploaded (raw response)")
            total_uploaded += len(batch)

    upload_time = time.time() - start_time

    # Refresh index
    print(f"🔄 Refreshing index...")
    subprocess.run([
        "curl", "-s", "-X", "POST", f"http://{es_host}/{index_name}/_refresh"
    ], capture_output=True)

    # Verify count
    print(f"📊 Verifying upload...")
    result = subprocess.run([
        "curl", "-s", "-X", "GET", f"http://{es_host}/{index_name}/_count"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        try:
            count_response = json.loads(result.stdout)
            count = count_response.get('count', 0)
            print(f"✅ Index now contains {count} documents")
        except:
            print(f"✅ Upload completed (count check failed)")

    print(f"\n📈 SUMMARY:")
    print(f"   Total patterns: {len(patterns)}")
    print(f"   Uploaded: {total_uploaded}")
    print(f"   Time: {upload_time:.2f}s")
    print(f"   Rate: {total_uploaded/upload_time:.0f} patterns/sec")

    return True

def search_pattern_in_elasticsearch(pattern: str, es_host: str = "95.217.84.234:9200", index_name: str = "ac_patterns_updated"):
    """Search for specific pattern in Elasticsearch"""

    print(f"🔍 Searching for pattern: '{pattern}' in {index_name}")

    query = {
        "query": {
            "term": {
                "pattern": pattern
            }
        }
    }

    result = subprocess.run([
        "curl", "-s", "-X", "GET", f"http://{es_host}/{index_name}/_search",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(query)
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Error searching: {result.stderr}")
        return False

    try:
        response = json.loads(result.stdout)
        hits = response.get('hits', {}).get('hits', [])
        print(f"📊 Found {len(hits)} matches")

        for i, hit in enumerate(hits, 1):
            source = hit.get('_source', {})
            print(f"   {i}. Tier {source.get('tier', 0)}: '{source.get('pattern', '')}' ({source.get('type', '')})")
            if source.get('hints'):
                print(f"      Hints: {source.get('hints', {})}")

        return len(hits) > 0

    except Exception as e:
        print(f"❌ Error parsing search response: {e}")
        return False

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Upload AC patterns to Elasticsearch via curl')
    parser.add_argument('--patterns-file', default='production_ac_patterns_fixed.json', help='AC patterns JSON file')
    parser.add_argument('--index', default='ac_patterns_updated', help='Elasticsearch index name')
    parser.add_argument('--host', default='95.217.84.234:9200', help='Elasticsearch host:port')
    parser.add_argument('--search', help='Search for specific pattern after upload')
    parser.add_argument('--test-search-only', action='store_true', help='Only test search, no upload')

    args = parser.parse_args()

    if args.test_search_only:
        if args.search:
            search_pattern_in_elasticsearch(args.search, args.host, args.index)
        else:
            print("❌ --search required when using --test-search-only")
        return

    # Upload patterns
    success = upload_patterns_to_elasticsearch(args.patterns_file, args.host, args.index)

    if success and args.search:
        print(f"\n" + "="*60)
        search_pattern_in_elasticsearch(args.search, args.host, args.index)

if __name__ == "__main__":
    main()