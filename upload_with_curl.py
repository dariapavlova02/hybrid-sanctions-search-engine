#!/usr/bin/env python3

import json
import subprocess
import os

def upload_patterns_with_curl():
    """Upload patterns using curl to avoid dependency issues"""

    print("📤 Loading patterns from file...")
    with open('patterns_with_partial_names.json', 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Check if it's the new format with "patterns" key
    if isinstance(data, dict) and 'patterns' in data:
        patterns = data['patterns']
    else:
        patterns = data

    print(f"📊 Found {len(patterns)} patterns to upload")

    # Split into chunks for bulk upload
    chunk_size = 1000
    total_chunks = (len(patterns) + chunk_size - 1) // chunk_size

    uploaded = 0
    for i in range(0, len(patterns), chunk_size):
        chunk = patterns[i:i+chunk_size]
        chunk_num = i // chunk_size + 1

        # Create NDJSON for bulk upload
        ndjson_lines = []
        for pattern in chunk:
            # Index operation
            index_op = {
                "index": {
                    "_index": "ai_service_ac_patterns"
                }
            }

            # Document
            doc = {
                "pattern": pattern["pattern"],
                "canonical": pattern["canonical"],
                "tier": pattern["tier"],
                "pattern_type": pattern["type"],
                "language": pattern["lang"],
                "confidence": pattern["confidence"],
                "source_field": "name",  # Default value
                "entity_id": pattern["entity_id"],
                "entity_type": pattern["entity_type"],
                "hints": pattern["hints"]
            }

            ndjson_lines.append(json.dumps(index_op))
            ndjson_lines.append(json.dumps(doc))

        # Write to temp file
        bulk_data = '\n'.join(ndjson_lines) + '\n'
        temp_file = f'bulk_chunk_{chunk_num}.json'

        with open(temp_file, 'w', encoding='utf-8') as f:
            f.write(bulk_data)

        # Upload via curl
        curl_cmd = [
            'curl', '-X', 'POST',
            '95.217.84.234:9200/_bulk',
            '-u', 'elastic:AiServiceElastic2024!',
            '-H', 'Content-Type: application/x-ndjson',
            '--data-binary', f'@{temp_file}'
        ]

        print(f"  📤 Uploading chunk {chunk_num}/{total_chunks} ({len(chunk)} patterns)...")

        result = subprocess.run(curl_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            # Parse response to count successful uploads
            try:
                response = json.loads(result.stdout)
                if not response.get('errors', True):
                    uploaded += len(chunk)
                    print(f"    ✅ Chunk {chunk_num} uploaded successfully")
                else:
                    print(f"    ⚠️ Chunk {chunk_num} had some errors")
            except:
                print(f"    ✅ Chunk {chunk_num} completed")
                uploaded += len(chunk)
        else:
            print(f"    ❌ Chunk {chunk_num} failed: {result.stderr}")

        # Clean up temp file
        os.remove(temp_file)

    print(f"\n✅ Upload completed! {uploaded}/{len(patterns)} patterns uploaded")

    # Test search for partial patterns
    print("\n🔍 Testing search for partial patterns...")

    test_searches = [
        ("порошенко петро", "Poroshenko firstname+lastname"),
        ("петро порошенко", "Poroshenko reversed order"),
        ("порошенко", "Poroshenko surname only")
    ]

    for query, description in test_searches:
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "wildcard": {
                                "pattern": {
                                    "value": f"*{query}*",
                                    "case_insensitive": True
                                }
                            }
                        },
                        {
                            "term": {
                                "pattern": query
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "size": 5
        }

        # Write search query to temp file
        with open('search_temp.json', 'w', encoding='utf-8') as f:
            json.dump(search_query, f, ensure_ascii=False)

        search_cmd = [
            'curl', '-X', 'GET',
            '95.217.84.234:9200/ai_service_ac_patterns/_search',
            '-u', 'elastic:AiServiceElastic2024!',
            '-H', 'Content-Type: application/json',
            '--data-binary', '@search_temp.json'
        ]

        result = subprocess.run(search_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            try:
                response = json.loads(result.stdout)
                hits = response['hits']['total']['value']
                print(f"  🔍 '{query}' ({description}): {hits} matches")

                if hits > 0:
                    for hit in response['hits']['hits'][:3]:
                        pattern = hit['_source']['pattern']
                        pattern_type = hit['_source']['pattern_type']
                        confidence = hit['_source']['confidence']
                        print(f"    - '{pattern}' ({pattern_type}, conf: {confidence})")
            except Exception as e:
                print(f"  ❌ Error parsing search result: {e}")
        else:
            print(f"  ❌ Search failed: {result.stderr}")

        # Clean up temp file
        if os.path.exists('search_temp.json'):
            os.remove('search_temp.json')

if __name__ == "__main__":
    upload_patterns_with_curl()