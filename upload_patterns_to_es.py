#!/usr/bin/env python3
"""
Upload generated AC patterns to Elasticsearch with tier separation
"""

import json
import asyncio
import aiohttp
import time
from typing import Dict, List, Any

class PatternUploader:
    def __init__(self, es_url="http://95.217.84.234:9200"):
        self.es_url = es_url.rstrip("/")
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def create_ac_patterns_index(self):
        """Create optimized index for AC patterns"""
        # Check if index already exists
        async with self.session.head(f"{self.es_url}/ac_patterns") as resp:
            if resp.status == 200:
                print("ℹ️  AC patterns index already exists, skipping creation")
                return True

        index_config = {
            "settings": {
                "number_of_shards": 2,
                "number_of_replicas": 0,
                "index.max_result_window": 500000,
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
                            "keyword": {"type": "keyword"},
                            "raw": {"type": "text", "analyzer": "standard"}
                        }
                    },
                    "canonical": {"type": "keyword"},
                    "tier": {"type": "integer"},
                    "pattern_type": {"type": "keyword"},
                    "language": {"type": "keyword"},
                    "confidence": {"type": "float"},
                    "entity_type": {"type": "keyword"},
                    "entity_id": {"type": "keyword"},
                    "source_field": {"type": "keyword"},
                    "hints": {"type": "object"},
                    "requires_context": {"type": "boolean"},
                    "created_at": {"type": "date"}
                }
            }
        }

        async with self.session.put(f"{self.es_url}/ac_patterns", json=index_config) as resp:
            if resp.status in [200, 201]:
                print("✅ AC patterns index created")
                return True
            else:
                error = await resp.text()
                print(f"❌ Failed to create index: {error}")
                return False

    async def bulk_upload_patterns(self, patterns: List[Dict], batch_size=1000):
        """Upload patterns in batches using Elasticsearch bulk API"""
        total_patterns = len(patterns)
        uploaded = 0

        print(f"📤 Uploading {total_patterns:,} patterns in batches of {batch_size:,}...")

        for i in range(0, total_patterns, batch_size):
            batch = patterns[i:i + batch_size]

            # Prepare bulk request
            bulk_body = []
            for pattern in batch:
                # Index action
                bulk_body.append(json.dumps({"index": {"_index": "ac_patterns"}}))
                # Document
                doc = {
                    "pattern": pattern.get("pattern", ""),
                    "canonical": pattern.get("canonical", ""),
                    "tier": pattern.get("tier", 0),
                    "pattern_type": pattern.get("type", "unknown"),
                    "language": pattern.get("lang", "auto"),
                    "confidence": pattern.get("confidence", 0.0),
                    "entity_type": pattern.get("entity_type", "unknown"),
                    "entity_id": pattern.get("entity_id", ""),
                    "source_field": "pattern",
                    "hints": pattern.get("hints", {}),
                    "requires_context": pattern.get("requires_context", False),
                    "created_at": "2025-09-22T22:36:00Z"
                }
                bulk_body.append(json.dumps(doc))

            bulk_data = "\n".join(bulk_body) + "\n"

            # Upload batch
            headers = {"Content-Type": "application/x-ndjson"}
            async with self.session.post(f"{self.es_url}/_bulk", data=bulk_data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if result.get("errors"):
                        print(f"⚠️  Some errors in batch {i//batch_size + 1}")
                    else:
                        uploaded += len(batch)
                        progress = (uploaded / total_patterns) * 100
                        print(f"✅ Batch {i//batch_size + 1} uploaded: {uploaded:,}/{total_patterns:,} ({progress:.1f}%)")
                else:
                    error = await resp.text()
                    print(f"❌ Batch upload failed: {error}")
                    break

            # Small delay to avoid overwhelming ES
            await asyncio.sleep(0.1)

        print(f"📊 Upload completed: {uploaded:,} patterns")
        return uploaded

async def main():
    print("🚀 Loading patterns from patterns.json...")

    # Load patterns
    with open("patterns.json", "r", encoding="utf-8") as f:
        patterns_data = json.load(f)

    patterns = patterns_data.get("patterns", [])
    print(f"📊 Loaded {len(patterns):,} patterns")

    # Group by tiers for statistics
    tier_counts = {}
    for pattern in patterns:
        tier = pattern.get("tier", 0)
        tier_counts[tier] = tier_counts.get(tier, 0) + 1

    print("📈 Tier distribution:")
    for tier in sorted(tier_counts.keys()):
        print(f"  Tier {tier}: {tier_counts[tier]:,} patterns")

    async with PatternUploader() as uploader:
        # Create index
        if not await uploader.create_ac_patterns_index():
            return

        # Upload patterns
        start_time = time.time()
        uploaded = await uploader.bulk_upload_patterns(patterns, batch_size=2000)
        upload_time = time.time() - start_time

        print(f"🎉 Upload completed in {upload_time:.2f}s")
        print(f"📊 Upload rate: {uploaded/upload_time:.1f} patterns/sec")

if __name__ == "__main__":
    asyncio.run(main())