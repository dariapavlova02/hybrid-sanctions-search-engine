#!/usr/bin/env python3
"""
Upload all 26K entities AC patterns to Elasticsearch
"""

import json
import requests
import time
from requests.auth import HTTPBasicAuth
from tqdm import tqdm

# Elasticsearch configuration
ES_HOST = "95.217.84.234"
ES_PORT = 9200
ES_USER = "elastic"
ES_PASSWORD = "AiServiceElastic2024!"
ES_INDEX = "ai_service_ac_patterns"

def clear_existing_patterns():
    """Delete existing AC patterns index"""
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}"
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

    print("🗑️  Deleting existing patterns index...")
    response = requests.delete(url, auth=auth)

    if response.status_code in [200, 404]:
        print("✅ Existing index cleared")
    else:
        print(f"⚠️  Warning: {response.status_code} - {response.text}")

def create_patterns_index():
    """Create AC patterns index with proper mapping"""
    url = f"http://{ES_HOST}:{ES_PORT}/{ES_INDEX}"
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

    mapping = {
        "mappings": {
            "properties": {
                "pattern": {
                    "type": "keyword"
                },
                "tier": {
                    "type": "integer"
                },
                "type": {
                    "type": "keyword"
                },
                "entity_type": {
                    "type": "keyword"
                },
                "entity_id": {
                    "type": "keyword"
                },
                "confidence": {
                    "type": "float"
                }
            }
        }
    }

    print("🔧 Creating patterns index...")
    response = requests.put(url, json=mapping, auth=auth)

    if response.status_code == 200:
        print("✅ Patterns index created")
    else:
        print(f"❌ Failed to create index: {response.status_code} - {response.text}")
        return False

    return True

def upload_patterns_bulk(patterns, batch_size=500):
    """Upload patterns to Elasticsearch in bulk"""
    url = f"http://{ES_HOST}:{ES_PORT}/_bulk"
    auth = HTTPBasicAuth(ES_USER, ES_PASSWORD)

    total_uploaded = 0
    total_patterns = len(patterns)

    print(f"📤 Uploading {total_patterns:,} patterns in batches of {batch_size}...")

    for i in tqdm(range(0, total_patterns, batch_size), desc="Uploading batches"):
        batch = patterns[i:i + batch_size]

        # Prepare bulk request
        bulk_data = []
        for pattern in batch:
            # Index command
            bulk_data.append(json.dumps({
                "index": {
                    "_index": ES_INDEX
                }
            }))

            # Document data
            bulk_data.append(json.dumps(pattern))

        bulk_body = "\n".join(bulk_data) + "\n"

        # Send bulk request
        response = requests.post(
            url,
            data=bulk_body,
            headers={"Content-Type": "application/x-ndjson"},
            auth=auth
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("errors"):
                print(f"⚠️  Batch {i//batch_size + 1} had errors")
            else:
                total_uploaded += len(batch)
        else:
            print(f"❌ Batch {i//batch_size + 1} failed: {response.status_code}")
            print(response.text)
            break

    return total_uploaded

def main():
    print("🚀 Starting upload of all 26K entities AC patterns...")
    print("=" * 60)

    # Load patterns from file
    patterns_file = "patterns_all_26k_fixed.json"
    print(f"📂 Loading patterns from {patterns_file}...")

    with open(patterns_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    patterns = data['patterns']
    stats = data['statistics']

    print(f"✅ Loaded {len(patterns):,} patterns")
    print(f"📊 Statistics:")
    print(f"   Persons: {stats['persons_processed']:,}")
    print(f"   Companies: {stats['companies_processed']:,}")
    print(f"   Terrorism: {stats['terrorism_processed']:,}")
    print(f"   Total entities: {stats['persons_processed'] + stats['companies_processed'] + stats['terrorism_processed']:,}")
    print()

    # Clear existing patterns
    clear_existing_patterns()

    # Create index
    if not create_patterns_index():
        return 1

    # Upload patterns
    start_time = time.time()
    uploaded_count = upload_patterns_bulk(patterns)
    upload_time = time.time() - start_time

    print(f"\n📊 Upload Results:")
    print(f"   Uploaded: {uploaded_count:,}/{len(patterns):,} patterns")
    print(f"   Time: {upload_time:.2f}s")
    print(f"   Rate: {uploaded_count/upload_time:.0f} patterns/sec")

    if uploaded_count == len(patterns):
        print("🎉 All patterns uploaded successfully!")
        return 0
    else:
        print("❌ Some patterns failed to upload")
        return 1

if __name__ == "__main__":
    exit(main())