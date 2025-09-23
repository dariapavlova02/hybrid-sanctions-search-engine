#!/usr/bin/env python3
"""
Direct Elasticsearch Data Deployment

Deploys AC patterns and vectors directly to Elasticsearch without API.
Sets up indices and loads data with proper tier separation.
"""

import json
import asyncio
import aiohttp
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import sys

class DirectElasticsearchDeployer:
    """Deploy data directly to Elasticsearch with tier-based AC patterns."""

    def __init__(self, es_url: str = "http://95.217.84.234:9200"):
        self.es_url = es_url.rstrip("/")
        self.session = None
        self.data_dir = Path(__file__).parent / "data" / "templates"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_elasticsearch_health(self) -> bool:
        """Check Elasticsearch health."""
        try:
            async with self.session.get(f"{self.es_url}/_cluster/health") as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    print(f"✅ Elasticsearch cluster: {health_data['cluster_name']} ({health_data['status']})")
                    return True
                else:
                    print(f"❌ Elasticsearch health check failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Elasticsearch unreachable: {e}")
            return False

    async def create_ac_patterns_index(self, index_name: str) -> bool:
        """Create optimized index for AC patterns."""
        print(f"🔧 Creating AC patterns index: {index_name}")

        index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0,
                "analysis": {
                    "analyzer": {
                        "pattern_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase"]
                        },
                        "pattern_search": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "pattern": {
                        "type": "text",
                        "analyzer": "pattern_analyzer",
                        "search_analyzer": "pattern_search",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "pattern_type": {
                        "type": "keyword"
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "tier": {
                        "type": "keyword"
                    },
                    "recall_tier": {
                        "type": "integer"
                    },
                    "created_at": {
                        "type": "date"
                    }
                }
            }
        }

        try:
            async with self.session.put(f"{self.es_url}/{index_name}", json=index_config) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    print(f"✅ Index created: {result.get('acknowledged', False)}")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"❌ Index creation failed: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Index creation error: {e}")
            return False

    async def create_vectors_index(self, index_name: str, vector_dim: int = 768) -> bool:
        """Create simplified index for vector metadata (without actual vectors due to missing kNN plugin)."""
        print(f"🔧 Creating vectors metadata index: {index_name}")

        index_config = {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 0
            },
            "mappings": {
                "properties": {
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "vector_metadata": {
                        "type": "text",
                        "index": False
                    },
                    "category": {
                        "type": "keyword"
                    },
                    "tier": {
                        "type": "keyword"
                    },
                    "pattern_type": {
                        "type": "keyword"
                    },
                    "recall_tier": {
                        "type": "integer"
                    },
                    "model_name": {
                        "type": "keyword"
                    },
                    "created_at": {
                        "type": "date"
                    }
                }
            }
        }

        try:
            async with self.session.put(f"{self.es_url}/{index_name}", json=index_config) as resp:
                if resp.status in [200, 201]:
                    result = await resp.json()
                    print(f"✅ Vectors index created: {result.get('acknowledged', False)}")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"❌ Vectors index creation failed: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Vectors index creation error: {e}")
            return False

    async def setup_indices(self) -> bool:
        """Setup all required indices."""
        print("🔧 Setting up Elasticsearch indices...")

        # Create AC patterns index
        if not await self.create_ac_patterns_index("ac_patterns"):
            return False

        # Create vectors index (sentence-transformers dimension = 768)
        if not await self.create_vectors_index("vectors", 768):
            return False

        print("✅ All indices created successfully!")
        return True

    def load_ac_patterns_by_category(self, category: str) -> Tuple[Dict[str, List], Dict[str, Any]]:
        """Load AC patterns for a specific category with tier separation."""
        ac_file = self.data_dir / f"{category}_ac_export.json"
        stats_file = self.data_dir / f"{category}_statistics.json"

        if not ac_file.exists():
            print(f"❌ AC patterns file not found: {ac_file}")
            return {}, {}

        if not stats_file.exists():
            print(f"❌ Statistics file not found: {stats_file}")
            return {}, {}

        with open(ac_file, 'r', encoding='utf-8') as f:
            ac_patterns = json.load(f)

        with open(stats_file, 'r', encoding='utf-8') as f:
            statistics = json.load(f)

        print(f"📊 Loaded {category} patterns:")
        for tier, patterns in ac_patterns.items():
            if patterns:
                print(f"  {tier}: {len(patterns)} patterns")

        return ac_patterns, statistics

    async def bulk_index_patterns(self, index_name: str, patterns: List[Dict], category: str, tier: str, batch_size: int = 1000) -> bool:
        """Bulk index AC patterns to Elasticsearch."""
        if not patterns:
            return True

        print(f"📤 Indexing {len(patterns)} patterns for {category}/{tier}...")

        # Process in batches
        for i in range(0, len(patterns), batch_size):
            batch = patterns[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(patterns) + batch_size - 1) // batch_size

            print(f"  📦 Batch {batch_num}/{total_batches} ({len(batch)} patterns)")

            # Prepare bulk request
            bulk_data = []
            for pattern_data in batch:
                # Index operation
                bulk_data.append(json.dumps({"index": {"_index": index_name}}))

                # Document data
                doc = {
                    "pattern": pattern_data.get("pattern", ""),
                    "pattern_type": pattern_data.get("pattern_type", "unknown"),
                    "category": category,
                    "tier": tier,
                    "recall_tier": pattern_data.get("recall_tier", 0),
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                }
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

    async def generate_vector_metadata(self, patterns: List[Dict], category: str, tier: str) -> List[Dict]:
        """Generate vector metadata for patterns (without actual vectors due to missing kNN plugin)."""
        vector_docs = []

        for pattern_data in patterns:
            text = pattern_data.get("pattern", "")
            if text:
                # Store metadata for future vector generation
                vector_docs.append({
                    "text": text,
                    "vector_metadata": f"pending_generation_for_{text[:50]}",
                    "category": category,
                    "tier": tier,
                    "pattern_type": pattern_data.get("pattern_type", "unknown"),
                    "recall_tier": pattern_data.get("recall_tier", 0),
                    "model_name": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S.000Z")
                })

        return vector_docs

    async def bulk_index_vectors(self, index_name: str, vector_docs: List[Dict], category: str, tier: str, batch_size: int = 500) -> bool:
        """Bulk index vectors to Elasticsearch."""
        if not vector_docs:
            return True

        print(f"📤 Indexing {len(vector_docs)} vectors for {category}/{tier}...")

        # Process in batches
        for i in range(0, len(vector_docs), batch_size):
            batch = vector_docs[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(vector_docs) + batch_size - 1) // batch_size

            print(f"  📦 Batch {batch_num}/{total_batches} ({len(batch)} vectors)")

            # Prepare bulk request
            bulk_data = []
            for doc in batch:
                # Index operation
                bulk_data.append(json.dumps({"index": {"_index": index_name}}))
                # Document data
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

    async def deploy_category_data(self, category: str) -> bool:
        """Deploy all data for a specific category."""
        print(f"\n🗂️ Deploying {category.upper()} data...")

        # Load AC patterns with tier separation
        ac_patterns, statistics = self.load_ac_patterns_by_category(category)
        if not ac_patterns:
            return False

        # Index AC patterns by tier
        for tier, patterns in ac_patterns.items():
            if patterns:
                success = await self.bulk_index_patterns("ac_patterns", patterns, category, tier)
                if not success:
                    print(f"❌ Failed to index {category}/{tier}")
                    return False

                # Generate and index vector metadata (for future vector generation)
                vector_docs = await self.generate_vector_metadata(patterns, category, tier)
                success = await self.bulk_index_vectors("vectors", vector_docs, category, tier)
                if not success:
                    print(f"❌ Failed to index vectors for {category}/{tier}")
                    return False

        print(f"✅ {category.upper()} data deployed successfully!")
        print(f"📊 Statistics: {statistics.get('total_patterns', 0)} patterns, {statistics.get('total_variants', 0)} variants")

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

    async def verify_deployment(self) -> bool:
        """Verify that data was deployed correctly."""
        print("\n🔍 Verifying deployment...")

        try:
            # Check indices
            async with self.session.get(f"{self.es_url}/_cat/indices?v") as resp:
                if resp.status == 200:
                    indices_info = await resp.text()
                    print("📊 Elasticsearch indices:")
                    print(indices_info)

            # Count documents in each index
            for index in ["ac_patterns", "vectors"]:
                async with self.session.get(f"{self.es_url}/{index}/_count") as resp:
                    if resp.status == 200:
                        count_result = await resp.json()
                        count = count_result.get("count", 0)
                        print(f"📈 {index}: {count:,} documents")

            # Test basic search
            search_query = {
                "query": {
                    "match": {
                        "pattern": "kovrikov"
                    }
                },
                "size": 5
            }

            async with self.session.post(f"{self.es_url}/ac_patterns/_search", json=search_query) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    hits = result.get("hits", {}).get("total", {}).get("value", 0)
                    print(f"🔍 Test search 'kovrikov': {hits} hits")

                    # Show sample results
                    for hit in result.get("hits", {}).get("hits", [])[:3]:
                        source = hit.get("_source", {})
                        print(f"  - {source.get('pattern')} ({source.get('category')}/{source.get('tier')})")

            return True

        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False

    async def deploy_all_data(self) -> bool:
        """Deploy all categories of data."""
        print("🚀 Starting direct Elasticsearch deployment...")
        print(f"🎯 Target Elasticsearch: {self.es_url}")
        print("=" * 60)

        # Check Elasticsearch health
        if not await self.check_elasticsearch_health():
            return False

        # Setup indices
        if not await self.setup_indices():
            return False

        # Deploy data by category
        categories = ["person", "company", "terrorism"]

        for category in categories:
            success = await self.deploy_category_data(category)
            if not success:
                print(f"❌ Deployment failed for {category}")
                return False

        # Refresh indices
        await self.refresh_indices()

        print("\n" + "=" * 60)
        print("🎉 All data deployed successfully!")
        return True


async def main():
    async with DirectElasticsearchDeployer() as deployer:
        success = await deployer.deploy_all_data()
        if success:
            await deployer.verify_deployment()

        if success:
            print("\n🎯 Deployment completed successfully!")
            print("🔗 Test searches:")
            print("  curl -X GET 'http://95.217.84.234:9200/ac_patterns/_search?q=kovrikov&size=5'")
            print("  curl -X GET 'http://95.217.84.234:9200/vectors/_count'")
        else:
            print("\n💥 Deployment failed!")
            return False


if __name__ == "__main__":
    asyncio.run(main())