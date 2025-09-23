#!/usr/bin/env python3
"""
Deploy Full Pattern Data to Production

Loads complete pattern data with variants, precision hints, and rich metadata.
This is the comprehensive dataset for advanced search capabilities.
"""

import json
import asyncio
import aiohttp
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import sys

class FullDataDeployer:
    """Deploy complete pattern data with all variants and metadata."""

    def __init__(self, es_url: str = "http://95.217.84.234:9200"):
        self.es_url = es_url.rstrip("/")
        self.session = None
        self.data_dir = Path(__file__).parent / "data" / "templates"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=600))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def create_full_patterns_index(self, index_name: str) -> bool:
        """Create optimized index for full pattern data with variants."""
        print(f"🔧 Creating full patterns index: {index_name}")

        index_config = {
            "settings": {
                "number_of_shards": 2,  # More shards for larger dataset
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "pattern_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase", "asciifolding"]
                        },
                        "variant_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding", "stop"]
                        },
                        "exact_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "pattern": {
                        "type": "text",
                        "analyzer": "pattern_analyzer",
                        "search_analyzer": "pattern_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"},
                            "exact": {"type": "text", "analyzer": "exact_analyzer"}
                        }
                    },
                    "pattern_type": {
                        "type": "keyword"
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "recall_tier": {
                        "type": "integer"
                    },
                    "precision_hint": {
                        "type": "float"
                    },
                    "language": {
                        "type": "keyword"
                    },
                    "variants": {
                        "type": "text",
                        "analyzer": "variant_analyzer",
                        "fields": {
                            "keyword": {"type": "keyword"}
                        }
                    },
                    "variant_count": {
                        "type": "integer"
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "data_source": {
                        "type": "keyword"
                    }
                }
            }
        }

        try:
            # Delete existing index if it exists
            async with self.session.delete(f"{self.es_url}/{index_name}") as resp:
                if resp.status in [200, 404]:
                    print(f"🗑️ Cleared existing index: {index_name}")

            # Create new index
            async with self.session.put(f"{self.es_url}/{index_name}", json=index_config) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    print(f"✅ Full patterns index created: {result.get('acknowledged', False)}")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"❌ Index creation failed: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Index creation error: {e}")
            return False

    def load_full_patterns_by_category(self, category: str) -> Tuple[List[Dict], Dict[str, Any]]:
        """Load full pattern data for a specific category."""
        patterns_file = self.data_dir / f"{category}_patterns.json"
        stats_file = self.data_dir / f"{category}_statistics.json"

        if not patterns_file.exists():
            print(f"❌ Full patterns file not found: {patterns_file}")
            return [], {}

        if not stats_file.exists():
            print(f"❌ Statistics file not found: {stats_file}")
            return [], {}

        with open(patterns_file, 'r', encoding='utf-8') as f:
            patterns = json.load(f)

        with open(stats_file, 'r', encoding='utf-8') as f:
            statistics = json.load(f)

        print(f"📊 Loaded {category} full patterns: {len(patterns):,} records")

        # Show tier distribution
        tier_counts = {}
        for pattern in patterns:
            tier = pattern.get('recall_tier', 0)
            tier_counts[tier] = tier_counts.get(tier, 0) + 1

        for tier, count in sorted(tier_counts.items()):
            print(f"  Tier {tier}: {count:,} patterns")

        return patterns, statistics

    def load_merged_patterns(self) -> List[Dict]:
        """Load the complete merged dataset."""
        # Try multiple possible locations for pattern data
        possible_files = [
            self.data_dir / "all_templates_merged.json",
            Path("./test_patterns_20250919_135941.json"),
            Path("./src/high_recall_ac_patterns_sample.json")
        ]

        for pattern_file in possible_files:
            if pattern_file.exists():
                print(f"📊 Loading patterns from {pattern_file}...")
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Handle different file formats
                if isinstance(data, list):
                    patterns = data
                elif isinstance(data, dict) and 'patterns' in data:
                    patterns = data['patterns']
                else:
                    print(f"❌ Unknown format in {pattern_file}")
                    continue

                if patterns:
                    print(f"✅ Loaded {len(patterns):,} patterns from {pattern_file}")

                    # Show source distribution
                    source_counts = {}
                    for pattern in patterns:
                        source = pattern.get('source', pattern.get('pattern_type', 'unknown'))
                        source_counts[source] = source_counts.get(source, 0) + 1

                    for source, count in sorted(source_counts.items()):
                        print(f"  {source}: {count:,} patterns")

                    return patterns

        print(f"❌ No pattern files found in any location")
        return []

    async def bulk_index_full_patterns(self, index_name: str, patterns: List[Dict],
                                     category: str = None, batch_size: int = 1000) -> bool:
        """Bulk index full pattern data to Elasticsearch."""
        if not patterns:
            return True

        print(f"📤 Indexing {len(patterns):,} full patterns...")

        # Process in batches
        for i in range(0, len(patterns), batch_size):
            batch = patterns[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(patterns) + batch_size - 1) // batch_size

            print(f"  📦 Batch {batch_num}/{total_batches} ({len(batch):,} patterns)")

            # Prepare bulk request
            bulk_data = []
            for pattern_data in batch:
                # Index operation
                bulk_data.append(json.dumps({"index": {"_index": index_name}}))

                # Prepare document
                doc = {
                    "pattern": pattern_data.get("pattern", ""),
                    "pattern_type": pattern_data.get("pattern_type", "unknown"),
                    "recall_tier": pattern_data.get("recall_tier", 0),
                    "precision_hint": pattern_data.get("precision_hint", 0.5),
                    "language": pattern_data.get("language", "unknown"),
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                    "data_source": "full_patterns"
                }

                # Add category from parameter or source field
                if category:
                    doc["category"] = category
                elif "source" in pattern_data:
                    doc["category"] = pattern_data["source"]
                else:
                    doc["category"] = "unknown"

                # Handle variants
                variants = pattern_data.get("variants", [])
                if variants:
                    doc["variants"] = variants
                    doc["variant_count"] = len(variants)
                else:
                    doc["variants"] = []
                    doc["variant_count"] = 0

                bulk_data.append(json.dumps(doc))

            bulk_body = "\n".join(bulk_data) + "\n"

            try:
                headers = {"Content-Type": "application/x-ndjson"}
                async with self.session.post(f"{self.es_url}/_bulk", data=bulk_body, headers=headers) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        errors = [item for item in result.get("items", []) if "error" in item.get("index", {})]
                        if errors:
                            print(f"    ⚠️ {len(errors)} errors in batch {batch_num}")
                            for error in errors[:3]:  # Show first 3 errors
                                print(f"      Error: {error['index']['error']}")
                        else:
                            print(f"    ✅ Batch {batch_num} indexed successfully")
                    else:
                        error_text = await resp.text()
                        print(f"    ❌ Batch {batch_num} failed: {error_text}")
                        return False
            except Exception as e:
                print(f"    ❌ Batch {batch_num} error: {e}")
                return False

            # Small delay between batches
            await asyncio.sleep(0.1)

        return True

    async def deploy_category_full_data(self, category: str) -> bool:
        """Deploy full data for a specific category."""
        print(f"\n🗂️ Deploying {category.upper()} full data...")

        # Load full patterns
        patterns, statistics = self.load_full_patterns_by_category(category)
        if not patterns:
            return False

        # Index full patterns
        success = await self.bulk_index_full_patterns("full_patterns", patterns, category)
        if not success:
            print(f"❌ Failed to index full patterns for {category}")
            return False

        print(f"✅ {category.upper()} full data deployed successfully!")
        print(f"📊 Statistics: {statistics.get('total_patterns', 0)} patterns, {statistics.get('total_variants', 0)} variants")

        return True

    async def deploy_merged_data(self) -> bool:
        """Deploy the complete merged dataset."""
        print(f"\n🔗 Deploying merged full data...")

        # Load merged patterns
        patterns = self.load_merged_patterns()
        if not patterns:
            return False

        # Index merged patterns
        success = await self.bulk_index_full_patterns("full_patterns", patterns)
        if not success:
            print(f"❌ Failed to index merged patterns")
            return False

        print(f"✅ Merged data deployed successfully!")
        return True

    async def refresh_indices(self) -> bool:
        """Refresh indices to make data searchable."""
        print("🔄 Refreshing indices...")

        try:
            async with self.session.post(f"{self.es_url}/_refresh") as resp:
                if resp.status == 200:
                    print("✅ Indices refreshed")
                    return True
                else:
                    print(f"❌ Refresh failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Refresh error: {e}")
            return False

    async def verify_full_deployment(self) -> bool:
        """Verify that full data was deployed correctly."""
        print("\n🔍 Verifying full data deployment...")

        try:
            # Check indices
            async with self.session.get(f"{self.es_url}/_cat/indices?v") as resp:
                if resp.status == 200:
                    indices_info = await resp.text()
                    print("📊 All Elasticsearch indices:")
                    print(indices_info)

            # Count full patterns
            async with self.session.get(f"{self.es_url}/full_patterns/_count") as resp:
                if resp.status == 200:
                    count_result = await resp.json()
                    count = count_result.get("count", 0)
                    print(f"📈 Full patterns: {count:,} documents")

            # Count by category in full patterns
            for category in ["person", "company", "terrorism"]:
                async with self.session.get(f"{self.es_url}/full_patterns/_count?q=category:{category}") as resp:
                    if resp.status == 200:
                        count_result = await resp.json()
                        count = count_result.get("count", 0)
                        print(f"📈 Full {category}: {count:,} documents")

            # Test advanced search with variants
            advanced_search = {
                "query": {
                    "bool": {
                        "should": [
                            {"match": {"pattern": "kovrikov"}},
                            {"match": {"variants": "kovrikov"}}
                        ]
                    }
                },
                "size": 5
            }

            async with self.session.post(f"{self.es_url}/full_patterns/_search", json=advanced_search) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    hits = result.get("hits", {}).get("total", {}).get("value", 0)
                    print(f"🔍 Advanced search 'kovrikov': {hits} hits")

                    # Show sample results
                    for hit in result.get("hits", {}).get("hits", [])[:3]:
                        source = hit.get("_source", {})
                        variants = source.get("variants", [])
                        variant_count = len(variants)
                        print(f"  - {source.get('pattern')} ({source.get('category')}, {variant_count} variants)")
                        if variants:
                            print(f"    Variants: {', '.join(variants[:5])}")

            # Test precision-based search
            precision_search = {
                "query": {
                    "range": {
                        "precision_hint": {
                            "gte": 0.8
                        }
                    }
                },
                "size": 0
            }

            async with self.session.post(f"{self.es_url}/full_patterns/_search", json=precision_search) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    hits = result.get("hits", {}).get("total", {}).get("value", 0)
                    print(f"🎯 High precision patterns (≥0.8): {hits:,}")

            return True

        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False

    async def deploy_all_full_data(self) -> bool:
        """Deploy all full pattern data."""
        print("🚀 Starting full pattern data deployment...")
        print(f"🎯 Target Elasticsearch: {self.es_url}")
        print("=" * 60)

        # Create full patterns index
        if not await self.create_full_patterns_index("full_patterns"):
            return False

        # Option 1: Deploy merged data (contains everything)
        success = await self.deploy_merged_data()
        if not success:
            print("❌ Merged data deployment failed")
            return False

        # Option 2: Alternatively, deploy by category
        # categories = ["person", "company", "terrorism"]
        # for category in categories:
        #     success = await self.deploy_category_full_data(category)
        #     if not success:
        #         print(f"❌ Full deployment failed for {category}")
        #         return False

        # Refresh indices
        await self.refresh_indices()

        print("\n" + "=" * 60)
        print("🎉 All full pattern data deployed successfully!")
        return True


async def main():
    async with FullDataDeployer() as deployer:
        success = await deployer.deploy_all_full_data()
        if success:
            await deployer.verify_full_deployment()

        if success:
            print("\n🎯 Full data deployment completed successfully!")
            print("\n🔗 Test advanced searches:")
            print("  # Search with variants:")
            print("  curl -X POST 'http://95.217.84.234:9200/full_patterns/_search' -H 'Content-Type: application/json' -d '{")
            print('    "query": {"bool": {"should": [{"match": {"pattern": "kovrikov"}}, {"match": {"variants": "kovrikov"}}]}}')
            print("  }'")
            print("\n  # High precision patterns:")
            print("  curl -X GET 'http://95.217.84.234:9200/full_patterns/_search?q=precision_hint:[0.8 TO 1.0]&size=5'")
        else:
            print("\n💥 Full data deployment failed!")
            return False


if __name__ == "__main__":
    asyncio.run(main())