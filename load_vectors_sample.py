#!/usr/bin/env python3
"""
Load vector sample to Elasticsearch.
"""

import json
import requests

def load_vectors_to_es(vectors_file: str, es_host: str, index_name: str):
    """Bulk load vectors to Elasticsearch"""

    print(f"📖 Loading vectors from {vectors_file}...")
    with open(vectors_file, 'r', encoding='utf-8') as f:
        vectors = json.load(f)

    print(f"   Total vectors: {len(vectors)}")

    # Build bulk request
    bulk_data = []
    for vector in vectors:
        # Index action
        bulk_data.append(json.dumps({"index": {"_index": index_name}}))
        # Document
        bulk_data.append(json.dumps(vector))

    bulk_body = "\n".join(bulk_data) + "\n"

    print(f"⬆️  Uploading {len(vectors)} vectors to {es_host}/{index_name}...")

    response = requests.post(
        f"{es_host}/_bulk",
        data=bulk_body.encode('utf-8'),
        headers={"Content-Type": "application/x-ndjson"},
        timeout=120
    )

    if response.status_code == 200:
        result = response.json()

        if result.get('errors'):
            errors = [item for item in result['items'] if 'error' in item.get('index', {})]
            print(f"   ⚠️  {len(errors)} errors during bulk load")
            if errors:
                print(f"   First error: {errors[0]['index']['error']}")
        else:
            print(f"   ✅ Successfully loaded {len(vectors)} vectors")

        # Refresh index
        requests.post(f"{es_host}/{index_name}/_refresh")

        # Get count
        count_resp = requests.get(f"{es_host}/{index_name}/_count")
        count_data = count_resp.json()
        print(f"   📊 Total documents in index: {count_data['count']}")

        return True
    else:
        print(f"   ❌ Bulk load failed: HTTP {response.status_code}")
        print(f"   Error: {response.text[:500]}")
        return False

def main():
    vectors_file = "output/sanctions/vectors_sample.json"
    es_host = "http://localhost:9200"
    index_name = "vectors"

    success = load_vectors_to_es(vectors_file, es_host, index_name)

    if success:
        print("\n✅ Vectors loaded successfully!")
    else:
        print("\n❌ Failed to load vectors")

if __name__ == "__main__":
    main()
