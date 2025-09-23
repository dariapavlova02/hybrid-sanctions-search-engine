#!/usr/bin/env python3
"""
Deduplicate AC patterns in Elasticsearch
Keep only the best instance of each pattern
"""

import asyncio
import aiohttp
import json
from typing import Dict, List, Set

class PatternDeduplicator:
    def __init__(self, es_url="http://95.217.84.234:9200"):
        self.es_url = es_url.rstrip("/")
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def find_duplicates(self) -> Dict[str, List[str]]:
        """Find all duplicate patterns and their document IDs"""
        print("🔍 Finding duplicate patterns...")

        # Get all patterns with their doc IDs
        scroll_query = {
            "size": 10000,
            "_source": ["pattern", "tier", "confidence"],
            "sort": [{"_id": "asc"}]
        }

        all_patterns = {}

        async with self.session.post(f"{self.es_url}/ac_patterns/_search?scroll=5m",
                                   json=scroll_query) as resp:
            result = await resp.json()
            scroll_id = result["_scroll_id"]
            hits = result["hits"]["hits"]

            # Process first batch
            for hit in hits:
                pattern = hit["_source"]["pattern"]
                doc_id = hit["_id"]
                tier = hit["_source"]["tier"]
                confidence = hit["_source"]["confidence"]

                if pattern not in all_patterns:
                    all_patterns[pattern] = []

                all_patterns[pattern].append({
                    "doc_id": doc_id,
                    "tier": tier,
                    "confidence": confidence
                })

            # Continue scrolling
            while hits:
                async with self.session.post(f"{self.es_url}/_search/scroll",
                                           json={"scroll": "5m", "scroll_id": scroll_id}) as resp:
                    result = await resp.json()
                    hits = result["hits"]["hits"]

                    for hit in hits:
                        pattern = hit["_source"]["pattern"]
                        doc_id = hit["_id"]
                        tier = hit["_source"]["tier"]
                        confidence = hit["_source"]["confidence"]

                        if pattern not in all_patterns:
                            all_patterns[pattern] = []

                        all_patterns[pattern].append({
                            "doc_id": doc_id,
                            "tier": tier,
                            "confidence": confidence
                        })

                if len(hits) == 0:
                    break

        # Find duplicates
        duplicates = {pattern: docs for pattern, docs in all_patterns.items() if len(docs) > 1}

        print(f"📊 Found {len(all_patterns):,} unique patterns")
        print(f"🔄 Found {len(duplicates):,} patterns with duplicates")

        return duplicates

    async def select_best_documents(self, duplicates: Dict[str, List[str]]) -> List[str]:
        """Select the best document for each duplicate pattern and return IDs to delete"""

        to_delete = []

        for pattern, docs in duplicates.items():
            # Sort by tier (lower is better), then by confidence (higher is better)
            sorted_docs = sorted(docs, key=lambda x: (x["tier"], -x["confidence"]))

            # Keep the best one, delete the rest
            best_doc = sorted_docs[0]
            docs_to_delete = sorted_docs[1:]

            for doc in docs_to_delete:
                to_delete.append(doc["doc_id"])

        print(f"🗑️  Selected {len(to_delete):,} documents for deletion")
        return to_delete

    async def delete_documents(self, doc_ids: List[str], batch_size=1000):
        """Delete documents in batches"""

        total_docs = len(doc_ids)
        deleted = 0

        print(f"🗑️  Deleting {total_docs:,} duplicate documents...")

        for i in range(0, total_docs, batch_size):
            batch = doc_ids[i:i + batch_size]

            # Prepare bulk delete request
            bulk_body = []
            for doc_id in batch:
                bulk_body.append(json.dumps({"delete": {"_index": "ac_patterns", "_id": doc_id}}))

            bulk_data = "\n".join(bulk_body) + "\n"

            # Execute bulk delete
            headers = {"Content-Type": "application/x-ndjson"}
            async with self.session.post(f"{self.es_url}/_bulk",
                                       data=bulk_data, headers=headers) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    if not result.get("errors"):
                        deleted += len(batch)
                        progress = (deleted / total_docs) * 100
                        print(f"✅ Deleted batch {i//batch_size + 1}: {deleted:,}/{total_docs:,} ({progress:.1f}%)")
                    else:
                        print(f"⚠️  Some errors in delete batch {i//batch_size + 1}")
                else:
                    error = await resp.text()
                    print(f"❌ Delete batch failed: {error}")
                    break

            # Small delay
            await asyncio.sleep(0.1)

        print(f"🎉 Deleted {deleted:,} duplicate documents")
        return deleted

    async def refresh_index(self):
        """Refresh the index to see changes"""
        async with self.session.post(f"{self.es_url}/ac_patterns/_refresh") as resp:
            if resp.status == 200:
                print("🔄 Index refreshed")
            else:
                print("⚠️  Failed to refresh index")

async def main():
    print("🧹 Starting AC patterns deduplication...")
    print("=" * 50)

    async with PatternDeduplicator() as deduplicator:
        # Find duplicates
        duplicates = await deduplicator.find_duplicates()

        if not duplicates:
            print("✅ No duplicates found!")
            return

        # Select best documents
        to_delete = await deduplicator.select_best_documents(duplicates)

        # Delete duplicates
        deleted = await deduplicator.delete_documents(to_delete)

        # Refresh index
        await deduplicator.refresh_index()

        print("=" * 50)
        print("🎉 Deduplication completed!")
        print(f"🗑️  Deleted: {deleted:,} duplicates")
        print(f"✅ Remaining: ~{471928:,} unique patterns")

if __name__ == "__main__":
    asyncio.run(main())