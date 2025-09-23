#!/usr/bin/env python3
"""
Recreate AC patterns index with deduplication
Read from patterns.json and deduplicate during upload
"""

import json
import asyncio
import aiohttp
import time
from typing import Dict, List, Set

class DeduplicatedUploader:
    def __init__(self, es_url="http://95.217.84.234:9200"):
        self.es_url = es_url.rstrip("/")
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def delete_and_recreate_index(self):
        """Delete old index and create new one"""
        print("🗑️  Deleting old ac_patterns index...")

        # Delete index
        async with self.session.delete(f"{self.es_url}/ac_patterns") as resp:
            if resp.status in [200, 404]:
                print("✅ Old index deleted")
            else:
                print(f"⚠️  Error deleting index: {resp.status}")

        # Create new index
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
                print("✅ New index created")
                return True
            else:
                error = await resp.text()
                print(f"❌ Failed to create index: {error}")
                return False

    def deduplicate_patterns(self, patterns: List[Dict]) -> List[Dict]:
        """Deduplicate patterns keeping the best one for each unique pattern"""
        print("🔄 Deduplicating patterns...")

        pattern_map = {}

        for pattern in patterns:
            pattern_text = pattern.get("pattern", "")

            if pattern_text not in pattern_map:
                pattern_map[pattern_text] = pattern
            else:
                # Keep the one with lower tier (better) or higher confidence
                existing = pattern_map[pattern_text]
                existing_tier = existing.get("tier", 999)
                existing_conf = existing.get("confidence", 0.0)

                new_tier = pattern.get("tier", 999)
                new_conf = pattern.get("confidence", 0.0)

                # Lower tier is better, then higher confidence
                if (new_tier < existing_tier) or (new_tier == existing_tier and new_conf > existing_conf):
                    pattern_map[pattern_text] = pattern

        unique_patterns = list(pattern_map.values())

        print(f"📊 Original patterns: {len(patterns):,}")
        print(f"📊 Unique patterns: {len(unique_patterns):,}")
        print(f"🗑️  Duplicates removed: {len(patterns) - len(unique_patterns):,}")

        return unique_patterns

    async def bulk_upload_patterns(self, patterns: List[Dict], batch_size=2000):
        """Upload deduplicated patterns"""
        total_patterns = len(patterns)
        uploaded = 0

        print(f"📤 Uploading {total_patterns:,} deduplicated patterns...")

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
                    if not result.get("errors"):
                        uploaded += len(batch)
                        progress = (uploaded / total_patterns) * 100
                        print(f"✅ Batch {i//batch_size + 1} uploaded: {uploaded:,}/{total_patterns:,} ({progress:.1f}%)")
                    else:
                        print(f"⚠️  Some errors in batch {i//batch_size + 1}")
                else:
                    error = await resp.text()
                    print(f"❌ Batch upload failed: {error}")
                    break

            # Small delay
            await asyncio.sleep(0.05)

        return uploaded

async def main():
    print("🧹 Recreating AC patterns index with deduplication...")
    print("=" * 60)

    # Load patterns
    print("📂 Loading patterns from patterns.json...")
    with open("patterns.json", "r", encoding="utf-8") as f:
        patterns_data = json.load(f)

    patterns = patterns_data.get("patterns", [])
    print(f"📊 Loaded {len(patterns):,} patterns")

    async with DeduplicatedUploader() as uploader:
        # Delete and recreate index
        if not await uploader.delete_and_recreate_index():
            return

        # Deduplicate patterns
        unique_patterns = uploader.deduplicate_patterns(patterns)

        # Show tier distribution
        tier_counts = {}
        for pattern in unique_patterns:
            tier = pattern.get("tier", 0)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        print("📈 Deduplicated tier distribution:")
        for tier in sorted(tier_counts.keys()):
            print(f"  Tier {tier}: {tier_counts[tier]:,} patterns")

        # Upload unique patterns
        start_time = time.time()
        uploaded = await uploader.bulk_upload_patterns(unique_patterns)
        upload_time = time.time() - start_time

        print("=" * 60)
        print("🎉 Index recreation completed!")
        print(f"📊 Uploaded: {uploaded:,} unique patterns")
        print(f"⏱️  Time: {upload_time:.2f}s")
        print(f"🚀 Rate: {uploaded/upload_time:.1f} patterns/sec")

if __name__ == "__main__":
    asyncio.run(main())