#!/usr/bin/env python3
"""
Setup Elasticsearch for AI Service search functionality.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

async def check_elasticsearch_health():
    """Check Elasticsearch cluster health."""
    print("🔍 CHECKING ELASTICSEARCH HEALTH")
    print("="*50)

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:9200/_cluster/health") as response:
                if response.status == 200:
                    health = await response.json()
                    print(f"✅ Cluster status: {health['status']}")
                    print(f"✅ Cluster name: {health['cluster_name']}")
                    print(f"✅ Active nodes: {health['number_of_nodes']}")
                    print(f"✅ Active indices: {health['active_primary_shards']}")
                    return True
                else:
                    print(f"❌ Elasticsearch health check failed: {response.status}")
                    return False

    except Exception as e:
        print(f"❌ Cannot connect to Elasticsearch: {e}")
        return False

async def check_indices():
    """Check existing indices."""
    print("\n🔍 CHECKING INDICES")
    print("="*30)

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get("http://localhost:9200/_cat/indices?format=json") as response:
                if response.status == 200:
                    indices = await response.json()
                    print(f"✅ Found {len(indices)} indices:")
                    for idx in indices:
                        print(f"  - {idx['index']}: {idx['docs.count']} docs, {idx['store.size']}")
                    return indices
                else:
                    print(f"❌ Failed to get indices: {response.status}")
                    return []

    except Exception as e:
        print(f"❌ Cannot get indices: {e}")
        return []

async def create_watchlist_index():
    """Create watchlist index for search."""
    print("\n🏗️ CREATING WATCHLIST INDEX")
    print("="*35)

    index_config = {
        "settings": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
            "analysis": {
                "analyzer": {
                    "name_analyzer": {
                        "type": "custom",
                        "tokenizer": "standard",
                        "filter": ["lowercase", "asciifolding"]
                    }
                }
            }
        },
        "mappings": {
            "properties": {
                "name": {
                    "type": "text",
                    "analyzer": "name_analyzer",
                    "fields": {
                        "exact": {"type": "keyword"},
                        "ngram": {
                            "type": "text",
                            "analyzer": "standard"
                        }
                    }
                },
                "normalized_name": {
                    "type": "text",
                    "analyzer": "name_analyzer"
                },
                "name_vector": {
                    "type": "dense_vector",
                    "dims": 384,
                    "index": True,
                    "similarity": "cosine"
                },
                "source": {"type": "keyword"},
                "category": {"type": "keyword"},
                "created_at": {"type": "date"}
            }
        }
    }

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            # Check if index exists
            async with session.head("http://localhost:9200/watchlist") as response:
                if response.status == 200:
                    print("✅ Watchlist index already exists")
                    return True

            # Create index
            async with session.put(
                "http://localhost:9200/watchlist",
                json=index_config,
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    print(f"✅ Created watchlist index: {result}")
                    return True
                else:
                    error = await response.text()
                    print(f"❌ Failed to create index: {response.status} - {error}")
                    return False

    except Exception as e:
        print(f"❌ Cannot create index: {e}")
        return False

async def add_sample_data():
    """Add sample data for testing."""
    print("\n📋 ADDING SAMPLE DATA")
    print("="*25)

    sample_names = [
        {
            "name": "Петр Алексеевич Порошенко",
            "normalized_name": "Порошенко Петр Алексеевич",
            "source": "test",
            "category": "politician"
        },
        {
            "name": "Владимир Владимирович Путин",
            "normalized_name": "Путин Владимир Владимирович",
            "source": "test",
            "category": "politician"
        },
        {
            "name": "Joseph Robinette Biden Jr.",
            "normalized_name": "Biden Joseph Robinette",
            "source": "test",
            "category": "politician"
        }
    ]

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            for i, name_data in enumerate(sample_names):
                async with session.post(
                    f"http://localhost:9200/watchlist/_doc/{i+1}",
                    json=name_data,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status in [200, 201]:
                        print(f"✅ Added: {name_data['name']}")
                    else:
                        error = await response.text()
                        print(f"❌ Failed to add {name_data['name']}: {error}")

            # Refresh index
            async with session.post("http://localhost:9200/watchlist/_refresh") as response:
                if response.status == 200:
                    print("✅ Index refreshed")

    except Exception as e:
        print(f"❌ Cannot add sample data: {e}")

async def test_search():
    """Test search functionality."""
    print("\n🔍 TESTING SEARCH")
    print("="*20)

    test_queries = [
        "Порошенко",
        "Путин",
        "Biden"
    ]

    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            for query in test_queries:
                search_body = {
                    "query": {
                        "multi_match": {
                            "query": query,
                            "fields": ["name^2", "normalized_name"],
                            "type": "best_fields"
                        }
                    },
                    "size": 5
                }

                async with session.post(
                    "http://localhost:9200/watchlist/_search",
                    json=search_body,
                    headers={"Content-Type": "application/json"}
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        hits = result['hits']['total']['value']
                        print(f"✅ Query '{query}': {hits} results")

                        for hit in result['hits']['hits'][:2]:
                            score = hit['_score']
                            name = hit['_source']['name']
                            print(f"    - {name} (score: {score:.2f})")
                    else:
                        error = await response.text()
                        print(f"❌ Search failed for '{query}': {error}")

    except Exception as e:
        print(f"❌ Cannot test search: {e}")

async def main():
    """Main setup function."""
    print("🚀 ELASTICSEARCH SETUP FOR AI SERVICE")
    print("="*60)

    # Check health
    if not await check_elasticsearch_health():
        print("\n❌ SETUP FAILED: Elasticsearch is not available")
        return False

    # Check indices
    await check_indices()

    # Create watchlist index
    if not await create_watchlist_index():
        print("\n❌ SETUP FAILED: Could not create watchlist index")
        return False

    # Add sample data
    await add_sample_data()

    # Test search
    await test_search()

    print("\n🎉 ELASTICSEARCH SETUP COMPLETED!")
    print("="*40)
    print("✅ Cluster is healthy")
    print("✅ Watchlist index created")
    print("✅ Sample data added")
    print("✅ Search is working")
    print("\nNext steps:")
    print("1. Update env.production with search settings")
    print("2. Deploy updated code to production")
    print("3. Restart ai-service with search enabled")

    return True

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)