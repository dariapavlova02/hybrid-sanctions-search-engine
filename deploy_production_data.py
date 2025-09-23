#!/usr/bin/env python3
"""
Production Data Deployment Script

Deploys AC patterns and vectors to production server with proper tier separation.
Uploads data to 95.217.84.234:8000 following the designed logic.
"""

import json
import asyncio
import aiohttp
import time
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple
import sys
import os

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

class ProductionDataDeployer:
    """Deploy data to production server with tier-based AC patterns and vectors."""

    def __init__(self, base_url: str = "http://95.217.84.234:8000"):
        self.base_url = base_url.rstrip("/")
        self.session = None
        self.data_dir = Path(__file__).parent / "data" / "templates"

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=300))
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def check_server_health(self) -> bool:
        """Check if the production server is healthy."""
        try:
            async with self.session.get(f"{self.base_url}/health") as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    print(f"✅ Server is healthy: {health_data}")
                    return True
                else:
                    print(f"❌ Server health check failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Server unreachable: {e}")
            return False

    async def check_elasticsearch(self) -> bool:
        """Check Elasticsearch health on the server."""
        try:
            async with self.session.get("http://95.217.84.234:9200/_cluster/health") as resp:
                if resp.status == 200:
                    health_data = await resp.json()
                    print(f"✅ Elasticsearch is healthy: {health_data['status']}")
                    return True
                else:
                    print(f"❌ Elasticsearch health check failed: {resp.status}")
                    return False
        except Exception as e:
            print(f"❌ Elasticsearch unreachable: {e}")
            return False

    async def setup_elasticsearch_indices(self) -> bool:
        """Setup Elasticsearch indices via API."""
        print("🔧 Setting up Elasticsearch indices...")

        try:
            async with self.session.post(f"{self.base_url}/admin/elasticsearch/setup") as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Elasticsearch setup: {result['message']}")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"❌ Elasticsearch setup failed: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Elasticsearch setup error: {e}")
            return False

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

    async def upload_ac_patterns_by_tier(self, category: str, tier: str, patterns: List[Dict], batch_size: int = 1000) -> bool:
        """Upload AC patterns for a specific tier."""
        if not patterns:
            print(f"⚠️ No patterns for {category}/{tier}")
            return True

        print(f"📤 Uploading {len(patterns)} AC patterns for {category}/{tier}...")

        # Split into batches
        for i in range(0, len(patterns), batch_size):
            batch = patterns[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(patterns) + batch_size - 1) // batch_size

            print(f"  📦 Batch {batch_num}/{total_batches} ({len(batch)} patterns)")

            payload = {
                "patterns": batch,
                "category": category,
                "tier": tier,
                "batch_size": len(batch)
            }

            try:
                async with self.session.post(f"{self.base_url}/admin/ac-patterns/bulk", json=payload) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        print(f"    ✅ {result.get('message', 'Success')}")
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

    async def generate_and_upload_vectors(self, category: str, patterns: Dict[str, List],
                                        model_name: str = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2") -> bool:
        """Generate vectors from patterns and upload them."""
        print(f"🧮 Generating vectors for {category} with model {model_name}...")

        # Collect all patterns for vector generation
        all_texts = []
        all_metadata = []

        for tier, tier_patterns in patterns.items():
            for pattern_data in tier_patterns:
                text = pattern_data.get('pattern', '')
                if text:
                    all_texts.append(text)
                    all_metadata.append({
                        'category': category,
                        'tier': tier,
                        'pattern_type': pattern_data.get('pattern_type', 'unknown'),
                        'recall_tier': pattern_data.get('recall_tier', 0)
                    })

        if not all_texts:
            print(f"⚠️ No texts found for vector generation in {category}")
            return True

        print(f"  📝 Generating vectors for {len(all_texts)} texts...")

        # Call vector generation API
        payload = {
            "texts": all_texts,
            "metadata": all_metadata,
            "category": category,
            "model_name": model_name,
            "batch_size": 500
        }

        try:
            async with self.session.post(f"{self.base_url}/admin/vectors/generate", json=payload) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    print(f"✅ Vector generation: {result.get('message', 'Success')}")
                    return True
                else:
                    error_text = await resp.text()
                    print(f"❌ Vector generation failed: {error_text}")
                    return False
        except Exception as e:
            print(f"❌ Vector generation error: {e}")
            return False

    async def deploy_category_data(self, category: str) -> bool:
        """Deploy all data for a specific category."""
        print(f"\n🗂️ Deploying {category.upper()} data...")

        # Load AC patterns with tier separation
        ac_patterns, statistics = self.load_ac_patterns_by_category(category)
        if not ac_patterns:
            return False

        # Upload AC patterns by tier
        for tier, patterns in ac_patterns.items():
            if patterns:
                success = await self.upload_ac_patterns_by_tier(category, tier, patterns)
                if not success:
                    print(f"❌ Failed to upload {category}/{tier}")
                    return False

        # Generate and upload vectors
        success = await self.generate_and_upload_vectors(category, ac_patterns)
        if not success:
            print(f"❌ Failed to generate vectors for {category}")
            return False

        print(f"✅ {category.upper()} data deployed successfully!")
        print(f"📊 Statistics: {statistics.get('total_patterns', 0)} patterns, {statistics.get('total_variants', 0)} variants")

        return True

    async def deploy_all_data(self) -> bool:
        """Deploy all categories of data."""
        print("🚀 Starting production data deployment...")
        print(f"🎯 Target server: {self.base_url}")
        print("=" * 60)

        # Check server health
        if not await self.check_server_health():
            return False

        # Check Elasticsearch health
        if not await self.check_elasticsearch():
            return False

        # Setup Elasticsearch indices
        if not await self.setup_elasticsearch_indices():
            return False

        # Deploy data by category
        categories = ["person", "company", "terrorism"]

        for category in categories:
            success = await self.deploy_category_data(category)
            if not success:
                print(f"❌ Deployment failed for {category}")
                return False

        print("\n" + "=" * 60)
        print("🎉 All data deployed successfully!")
        return True

    async def verify_deployment(self) -> bool:
        """Verify that data was deployed correctly."""
        print("\n🔍 Verifying deployment...")

        try:
            # Check indices
            async with self.session.get("http://95.217.84.234:9200/_cat/indices?v") as resp:
                if resp.status == 200:
                    indices_info = await resp.text()
                    print("📊 Elasticsearch indices:")
                    print(indices_info)
                else:
                    print(f"❌ Failed to get indices info: {resp.status}")
                    return False

            # Test search endpoints
            test_queries = [
                {"text": "коврик", "category": "person"},
                {"text": "компания", "category": "company"},
                {"text": "терор", "category": "terrorism"}
            ]

            for query in test_queries:
                async with self.session.post(f"{self.base_url}/search/ac", json=query) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        hits = len(result.get('results', []))
                        print(f"✅ AC Search '{query['text']}' in {query['category']}: {hits} hits")
                    else:
                        print(f"❌ AC Search failed for '{query['text']}': {resp.status}")

                async with self.session.post(f"{self.base_url}/search/vector", json=query) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        hits = len(result.get('results', []))
                        print(f"✅ Vector Search '{query['text']}' in {query['category']}: {hits} hits")
                    else:
                        print(f"❌ Vector Search failed for '{query['text']}': {resp.status}")

            return True

        except Exception as e:
            print(f"❌ Verification error: {e}")
            return False


async def main():
    parser = argparse.ArgumentParser(description="Deploy data to production server")
    parser.add_argument("--server", default="http://95.217.84.234:8000", help="Server URL")
    parser.add_argument("--category", help="Deploy specific category only (person, company, terrorism)")
    parser.add_argument("--verify-only", action="store_true", help="Only verify existing deployment")

    args = parser.parse_args()

    async with ProductionDataDeployer(args.server) as deployer:
        if args.verify_only:
            success = await deployer.verify_deployment()
        elif args.category:
            success = await deployer.deploy_category_data(args.category)
        else:
            success = await deployer.deploy_all_data()
            if success:
                await deployer.verify_deployment()

        if success:
            print("\n🎯 Deployment completed successfully!")
            sys.exit(0)
        else:
            print("\n💥 Deployment failed!")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())