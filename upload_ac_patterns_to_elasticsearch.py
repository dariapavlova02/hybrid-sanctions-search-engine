#!/usr/bin/env python3
"""
Upload AC patterns to Elasticsearch
"""

import json
import sys
import os
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import time

sys.path.append('/Users/dariapavlova/Desktop/ai-service/src')

def get_elasticsearch_client():
    """Get Elasticsearch client"""

    # Try different connection configs
    configs = [
        {"hosts": ["http://localhost:9200"]},
        {"hosts": ["https://localhost:9200"]},
        {"hosts": ["http://elasticsearch:9200"]},
        {"hosts": ["http://127.0.0.1:9200"]},
    ]

    for config in configs:
        try:
            client = Elasticsearch(**config)
            # Test connection
            if client.ping():
                print(f"✅ Connected to Elasticsearch: {config['hosts'][0]}")
                return client
        except Exception as e:
            print(f"❌ Failed to connect to {config['hosts'][0]}: {e}")
            continue

    print("❌ Could not connect to Elasticsearch")
    return None

def upload_patterns_to_elasticsearch(patterns_file: str, index_name: str = "ac_patterns"):
    """Upload AC patterns to Elasticsearch"""

    print(f"🔍 UPLOADING AC PATTERNS TO ELASTICSEARCH")
    print("=" * 60)

    # Get Elasticsearch client
    client = get_elasticsearch_client()
    if not client:
        return False

    # Load patterns
    print(f"📂 Loading patterns from {patterns_file}...")
    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading patterns file: {e}")
        return False

    patterns = data.get('patterns', [])
    print(f"📊 Loaded {len(patterns)} patterns")

    # Check if index exists and delete it
    if client.indices.exists(index=index_name):
        print(f"🗑️ Deleting existing index: {index_name}")
        client.indices.delete(index=index_name)

    # Create index with proper mapping
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

    print(f"🔧 Creating index: {index_name}")
    client.indices.create(index=index_name, body=mapping)

    # Prepare bulk data
    def generate_docs():
        for i, pattern in enumerate(patterns):
            yield {
                "_index": index_name,
                "_id": i + 1,
                "_source": {
                    **pattern,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ")
                }
            }

    # Bulk upload
    print(f"⬆️ Uploading {len(patterns)} patterns...")
    start_time = time.time()

    try:
        success, failed = bulk(client, generate_docs(), chunk_size=1000)
        upload_time = time.time() - start_time

        print(f"✅ Upload completed!")
        print(f"   Success: {success}")
        print(f"   Failed: {len(failed) if failed else 0}")
        print(f"   Time: {upload_time:.2f}s")

        # Refresh index
        client.indices.refresh(index=index_name)

        # Verify upload
        count = client.count(index=index_name)['count']
        print(f"📊 Index now contains {count} documents")

        # Show some sample patterns
        print(f"\n📋 Sample patterns in index:")
        result = client.search(
            index=index_name,
            body={"query": {"match_all": {}}, "size": 5}
        )

        for i, hit in enumerate(result['hits']['hits'], 1):
            source = hit['_source']
            print(f"   {i}. '{source.get('pattern', '')}' (tier={source.get('tier', 0)}, type={source.get('type', '')})")

        return True

    except Exception as e:
        print(f"❌ Error during bulk upload: {e}")
        return False

def search_pattern_in_elasticsearch(pattern: str, index_name: str = "ac_patterns"):
    """Search for specific pattern in Elasticsearch"""

    client = get_elasticsearch_client()
    if not client:
        return False

    print(f"🔍 Searching for pattern: '{pattern}'")

    try:
        result = client.search(
            index=index_name,
            body={
                "query": {
                    "term": {
                        "pattern": pattern
                    }
                }
            }
        )

        hits = result['hits']['hits']
        print(f"📊 Found {len(hits)} matches")

        for i, hit in enumerate(hits, 1):
            source = hit['_source']
            print(f"   {i}. Tier {source.get('tier', 0)}: '{source.get('pattern', '')}' ({source.get('type', '')})")
            if source.get('hints'):
                print(f"      Hints: {source.get('hints', {})}")

        return len(hits) > 0

    except Exception as e:
        print(f"❌ Error searching pattern: {e}")
        return False

def main():
    import argparse

    parser = argparse.ArgumentParser(description='Upload AC patterns to Elasticsearch')
    parser.add_argument('--patterns-file', default='high_recall_ac_patterns.json', help='AC patterns JSON file')
    parser.add_argument('--index', default='ac_patterns', help='Elasticsearch index name')
    parser.add_argument('--search', help='Search for specific pattern after upload')
    parser.add_argument('--test-search-only', action='store_true', help='Only test search, no upload')

    args = parser.parse_args()

    if args.test_search_only:
        if args.search:
            search_pattern_in_elasticsearch(args.search, args.index)
        else:
            print("❌ --search required when using --test-search-only")
        return

    # Upload patterns
    success = upload_patterns_to_elasticsearch(args.patterns_file, args.index)

    if success and args.search:
        print(f"\n" + "="*60)
        search_pattern_in_elasticsearch(args.search, args.index)

if __name__ == "__main__":
    main()