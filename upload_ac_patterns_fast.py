#!/usr/bin/env python3
"""
Fast AC patterns upload to Elasticsearch with large batches
"""

import json
import subprocess
import sys
import time

def upload_patterns_fast(patterns_file: str, es_host: str = "95.217.84.234:9200", index_name: str = "ai_service_ac_patterns", batch_size: int = 1000):
    """Fast upload with large batches"""

    print(f"🚀 FAST AC PATTERNS UPLOAD")
    print("=" * 60)
    print(f"📍 Host: {es_host}")
    print(f"📂 File: {patterns_file}")
    print(f"📋 Index: {index_name}")
    print(f"📊 Batch size: {batch_size}")

    # Load patterns
    with open(patterns_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    patterns = data.get('patterns', [])
    print(f"📊 Loaded {len(patterns):,} patterns")

    # Delete and recreate index
    print(f"🗑️ Recreating index...")
    subprocess.run([
        "curl", "-s", "-X", "DELETE", f"http://{es_host}/{index_name}"
    ], capture_output=True)

    mapping = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,  # No replicas for speed
            "refresh_interval": "30s"  # Slower refresh for speed
        },
        "mappings": {
            "properties": {
                "pattern": {"type": "keyword"},
                "tier": {"type": "integer"},
                "pattern_type": {"type": "keyword"},
                "language": {"type": "keyword"},
                "hints": {"type": "object"},
                "entity_id": {"type": "keyword"},
                "entity_type": {"type": "keyword"},
                "confidence": {"type": "float"},
                "source_field": {"type": "keyword"},
                "canonical": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    }

    subprocess.run([
        "curl", "-s", "-X", "PUT", f"http://{es_host}/{index_name}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(mapping)
    ], capture_output=True)

    print(f"✅ Index recreated")

    # Upload in large batches
    total_uploaded = 0
    start_time = time.time()

    for i in range(0, len(patterns), batch_size):
        batch = patterns[i:i + batch_size]

        # Create bulk request with larger batch
        bulk_data = ""
        for j, pattern in enumerate(batch):
            doc_id = i + j + 1
            index_line = json.dumps({"index": {"_index": index_name, "_id": doc_id}})

            # Map old field names to new if needed
            doc = {
                "pattern": pattern.get("pattern", ""),
                "tier": pattern.get("tier", 0),
                "pattern_type": pattern.get("type", "unknown"),
                "language": pattern.get("lang", "unknown"),
                "hints": pattern.get("hints", {}),
                "entity_id": pattern.get("entity_id", ""),
                "entity_type": pattern.get("entity_type", ""),
                "confidence": pattern.get("confidence", 0.0),
                "source_field": "name",
                "canonical": pattern.get("canonical", ""),
                "created_at": "2025-09-26T12:00:00Z"
            }
            doc_line = json.dumps(doc)
            bulk_data += index_line + "\n" + doc_line + "\n"

        # Upload batch
        with open(f"/tmp/bulk_batch_{i//batch_size}.json", 'w') as f:
            f.write(bulk_data)

        result = subprocess.run([
            "curl", "-s", "-X", "POST", f"http://{es_host}/_bulk",
            "-H", "Content-Type: application/x-ndjson",
            "--data-binary", f"@/tmp/bulk_batch_{i//batch_size}.json"
        ], capture_output=True, text=True)

        if result.returncode == 0:
            total_uploaded += len(batch)
            elapsed = time.time() - start_time
            rate = total_uploaded / elapsed if elapsed > 0 else 0
            progress = (i + batch_size) / len(patterns) * 100
            print(f"✅ Batch {i//batch_size + 1:4d}: {total_uploaded:6,}/{len(patterns):,} patterns ({progress:5.1f}%) - {rate:6.0f}/sec")
        else:
            print(f"❌ Batch {i//batch_size + 1} failed: {result.stderr}")

        # Clean up temp file
        subprocess.run(["rm", f"/tmp/bulk_batch_{i//batch_size}.json"], capture_output=True)

        # Small delay to prevent overwhelming
        time.sleep(0.01)

    # Final refresh
    print(f"🔄 Final refresh...")
    subprocess.run([
        "curl", "-s", "-X", "POST", f"http://{es_host}/{index_name}/_refresh"
    ], capture_output=True)

    # Verify
    result = subprocess.run([
        "curl", "-s", "-X", "GET", f"http://{es_host}/{index_name}/_count"
    ], capture_output=True, text=True)

    if result.returncode == 0:
        try:
            count_response = json.loads(result.stdout)
            final_count = count_response.get('count', 0)
            upload_time = time.time() - start_time
            print(f"\n📈 UPLOAD COMPLETE:")
            print(f"   Total patterns: {len(patterns):,}")
            print(f"   Uploaded: {total_uploaded:,}")
            print(f"   Final count: {final_count:,}")
            print(f"   Time: {upload_time:.1f}s")
            print(f"   Rate: {final_count/upload_time:.0f} patterns/sec")
        except:
            print(f"✅ Upload completed")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Fast upload AC patterns')
    parser.add_argument('--patterns-file', required=True, help='Patterns file')
    parser.add_argument('--batch-size', type=int, default=1000, help='Batch size')
    args = parser.parse_args()

    upload_patterns_fast(args.patterns_file, batch_size=args.batch_size)

if __name__ == "__main__":
    main()