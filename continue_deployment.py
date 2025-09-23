#!/usr/bin/env python3
"""
Continue data deployment - load remaining categories and complete person data.
"""

import json
import asyncio
import aiohttp
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

class ContinueDeployment:
    """Continue deployment of remaining data."""

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

        print(f"✅ {category.upper()} data deployed successfully!")
        print(f"📊 Statistics: {statistics.get('total_patterns', 0)} patterns, {statistics.get('total_variants', 0)} variants")

        return True

    async def complete_person_data(self) -> bool:
        """Complete remaining person data."""
        print(f"\n🔄 Checking person data completion...")

        # Check current person document count
        try:
            async with self.session.get(f"{self.es_url}/ac_patterns/_count?q=category:person") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    current_count = result.get("count", 0)
                    print(f"📊 Current person documents: {current_count:,}")

                    # Load expected person count
                    ac_patterns, statistics = self.load_ac_patterns_by_category("person")
                    expected_count = sum(len(patterns) for patterns in ac_patterns.values())
                    print(f"📊 Expected person documents: {expected_count:,}")

                    if current_count >= expected_count * 0.95:  # 95% threshold
                        print(f"✅ Person data is complete ({current_count}/{expected_count})")
                        return True
                    else:
                        print(f"⚠️ Person data incomplete ({current_count}/{expected_count})")
                        print("🔄 Continuing person data upload...")

                        # Continue with remaining tiers
                        for tier, patterns in ac_patterns.items():
                            if patterns:
                                # Check if this tier is already loaded
                                tier_query = f"category:person AND tier:{tier}"
                                async with self.session.get(f"{self.es_url}/ac_patterns/_count?q={tier_query}") as tier_resp:
                                    if tier_resp.status == 200:
                                        tier_result = await tier_resp.json()
                                        tier_count = tier_result.get("count", 0)
                                        if tier_count >= len(patterns) * 0.95:
                                            print(f"✅ {tier} already complete ({tier_count}/{len(patterns)})")
                                            continue

                                success = await self.bulk_index_patterns("ac_patterns", patterns, "person", tier)
                                if not success:
                                    print(f"❌ Failed to complete {tier}")
                                    return False

        except Exception as e:
            print(f"❌ Error checking person data: {e}")
            return False

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

            # Count documents by category
            for category in ["person", "company", "terrorism"]:
                async with self.session.get(f"{self.es_url}/ac_patterns/_count?q=category:{category}") as resp:
                    if resp.status == 200:
                        count_result = await resp.json()
                        count = count_result.get("count", 0)
                        print(f"📈 {category}: {count:,} documents")

            # Count by tier
            for tier in ["tier_0_exact", "tier_1_high_recall", "tier_2_medium_recall"]:
                async with self.session.get(f"{self.es_url}/ac_patterns/_count?q=tier:{tier}") as resp:
                    if resp.status == 200:
                        count_result = await resp.json()
                        count = count_result.get("count", 0)
                        print(f"📈 {tier}: {count:,} documents")

            # Test search for our test names
            test_names = ["kovrikov", "ayvazov", "kazantsev"]
            for name in test_names:
                search_query = {
                    "query": {
                        "match": {
                            "pattern": name
                        }
                    },
                    "size": 3
                }

                async with self.session.post(f"{self.es_url}/ac_patterns/_search", json=search_query) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        hits = result.get("hits", {}).get("total", {}).get("value", 0)
                        print(f"🔍 Search '{name}': {hits} hits")

                        # Show sample results
                        for hit in result.get("hits", {}).get("hits", [])[:2]:
                            source = hit.get("_source", {})
                            print(f"  - {source.get('pattern')} ({source.get('category')}/{source.get('tier')})")

            return True

        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False


async def main():
    async with ContinueDeployment() as deployer:
        print("🚀 Continuing production data deployment...")
        print("=" * 60)

        # Complete person data if needed
        await deployer.complete_person_data()

        # Deploy company data
        success = await deployer.deploy_category_data("company")
        if not success:
            print("❌ Company deployment failed")
            return

        # Deploy terrorism data
        success = await deployer.deploy_category_data("terrorism")
        if not success:
            print("❌ Terrorism deployment failed")
            return

        # Refresh indices
        await deployer.refresh_indices()

        # Verify deployment
        await deployer.verify_deployment()

        print("\n" + "=" * 60)
        print("🎉 All remaining data deployed successfully!")


if __name__ == "__main__":
    asyncio.run(main())