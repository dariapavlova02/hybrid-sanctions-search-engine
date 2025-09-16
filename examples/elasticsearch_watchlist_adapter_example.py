#!/usr/bin/env python3
"""
Example usage of ElasticsearchWatchlistAdapter.

Demonstrates how to use the adapter as a bridge from local vector indexes
to Elasticsearch while maintaining compatible interfaces.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from src.ai_service.layers.embeddings.indexing.elasticsearch_watchlist_adapter import (
    ElasticsearchWatchlistAdapter,
    ElasticsearchWatchlistConfig,
    create_elasticsearch_watchlist_adapter,
    create_elasticsearch_enhanced_adapter
)
from src.ai_service.layers.embeddings.indexing.vector_index_service import VectorIndexConfig
from src.ai_service.layers.embeddings.indexing.watchlist_index_service import WatchlistIndexService


async def example_basic_usage():
    """Example of basic adapter usage."""
    print("=== Basic ElasticsearchWatchlistAdapter Usage ===")
    
    # Configure Elasticsearch connection
    config = ElasticsearchWatchlistConfig(
        es_url=os.getenv("ES_URL", "http://localhost:9200"),
        es_auth=os.getenv("ES_AUTH"),  # "username:password" or None
        es_verify_ssl=os.getenv("ES_VERIFY_SSL", "false").lower() == "true",
        ac_threshold=0.7,
        max_ac_results=50,
        max_vector_results=100
    )
    
    # Create adapter
    adapter = ElasticsearchWatchlistAdapter(config)
    
    # Sample corpus data
    corpus = [
        ("person_001", "иван петров", "person", {
            "country": "RU",
            "dob": "1980-05-15",
            "aliases": ["и. петров", "ivan petrov"]
        }),
        ("person_002", "мария сидорова", "person", {
            "country": "UA",
            "dob": "1975-12-03",
            "aliases": ["м. сидорова"]
        }),
        ("org_001", "ооо приватбанк", "org", {
            "country": "UA",
            "aliases": ["приватбанк", "privatbank"]
        }),
        ("org_002", "apple inc", "org", {
            "country": "US",
            "aliases": ["apple", "apple computer"]
        })
    ]
    
    try:
        # Build index from corpus
        print("Building index from corpus...")
        await adapter.build_from_corpus(corpus, "example_index")
        print(f"✅ Index built with {len(corpus)} documents")
        
        # Perform searches
        queries = [
            "иван петров",
            "мария сидорова", 
            "приватбанк",
            "apple inc",
            "иван"  # Partial match
        ]
        
        for query in queries:
            print(f"\nSearching for: '{query}'")
            results = await adapter.search(query, top_k=5)
            
            if results:
                print(f"Found {len(results)} results:")
                for entity_id, score in results:
                    print(f"  - {entity_id}: {score:.3f}")
            else:
                print("No results found")
        
        # Check status
        print(f"\nService status:")
        status = adapter.status()
        for key, value in status.items():
            if key != "metrics":
                print(f"  {key}: {value}")
        
        print(f"\nMetrics:")
        metrics = status["metrics"]
        for key, value in metrics.items():
            print(f"  {key}: {value}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        # Cleanup
        await adapter.close()
        print("\n✅ Adapter closed")


async def example_with_fallback():
    """Example with fallback service."""
    print("\n=== Adapter with Fallback Service ===")
    
    # Create fallback service
    fallback_config = VectorIndexConfig()
    fallback_service = WatchlistIndexService(fallback_config)
    
    # Create adapter with fallback
    config = ElasticsearchWatchlistConfig(
        es_url="http://unavailable-es:9200",  # Unavailable ES
        enable_fallback=True
    )
    
    adapter = ElasticsearchWatchlistAdapter(config, fallback_service)
    
    # Sample corpus
    corpus = [
        ("person_001", "иван петров", "person", {"country": "RU"}),
        ("org_001", "ооо приватбанк", "org", {"country": "UA"})
    ]
    
    try:
        # This will use fallback since ES is unavailable
        print("Building index (will use fallback)...")
        await adapter.build_from_corpus(corpus, "fallback_index")
        print("✅ Index built using fallback service")
        
        # Search will also use fallback
        print("\nSearching (will use fallback)...")
        results = await adapter.search("иван петров", top_k=5)
        print(f"Found {len(results)} results using fallback")
        
        # Check status
        status = adapter.status()
        print(f"\nFallback available: {status['fallback_available']}")
        print(f"ES available: {status['elasticsearch_available']}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await adapter.close()


async def example_factory_functions():
    """Example using factory functions."""
    print("\n=== Using Factory Functions ===")
    
    # Create adapter using factory function
    config = ElasticsearchWatchlistConfig(
        es_url=os.getenv("ES_URL", "http://localhost:9200")
    )
    fallback_config = VectorIndexConfig()
    
    adapter = create_elasticsearch_watchlist_adapter(config, fallback_config)
    
    print(f"Created adapter with config: {adapter.config.es_url}")
    print(f"Fallback service available: {adapter.fallback_service is not None}")
    
    await adapter.close()


async def example_snapshot_operations():
    """Example of snapshot operations."""
    print("\n=== Snapshot Operations ===")
    
    config = ElasticsearchWatchlistConfig(
        es_url=os.getenv("ES_URL", "http://localhost:9200")
    )
    adapter = ElasticsearchWatchlistAdapter(config)
    
    try:
        # Build some data
        corpus = [
            ("person_001", "иван петров", "person", {"country": "RU"}),
            ("org_001", "ооо приватбанк", "org", {"country": "UA"})
        ]
        
        await adapter.build_from_corpus(corpus, "snapshot_test")
        
        # Save snapshot
        print("Saving snapshot...")
        snapshot_result = await adapter.save_snapshot("/tmp/watchlist_snapshot")
        print(f"Snapshot result: {snapshot_result}")
        
        # Reload snapshot
        print("Reloading snapshot...")
        reload_result = await adapter.reload_snapshot("/tmp/watchlist_snapshot")
        print(f"Reload result: {reload_result}")
        
    except Exception as e:
        print(f"❌ Snapshot error: {e}")
    
    finally:
        await adapter.close()


async def example_metrics_and_monitoring():
    """Example of metrics and monitoring."""
    print("\n=== Metrics and Monitoring ===")
    
    config = ElasticsearchWatchlistConfig(
        es_url=os.getenv("ES_URL", "http://localhost:9200")
    )
    adapter = ElasticsearchWatchlistAdapter(config)
    
    try:
        # Build index
        corpus = [
            ("person_001", "иван петров", "person", {"country": "RU"}),
            ("person_002", "мария сидорова", "person", {"country": "UA"}),
            ("org_001", "ооо приватбанк", "org", {"country": "UA"})
        ]
        
        await adapter.build_from_corpus(corpus, "metrics_test")
        
        # Perform multiple searches to generate metrics
        queries = ["иван петров", "мария сидорова", "приватбанк", "apple"]
        
        for query in queries:
            results = await adapter.search(query, top_k=10)
            print(f"Query '{query}': {len(results)} results")
        
        # Display metrics
        status = adapter.status()
        metrics = status["metrics"]
        
        print(f"\n=== Metrics Summary ===")
        print(f"Total searches: {metrics['total_searches']}")
        print(f"AC searches: {metrics['ac_searches']}")
        print(f"Vector searches: {metrics['vector_searches']}")
        print(f"Escalations: {metrics['escalations']}")
        print(f"Fallbacks: {metrics['fallbacks']}")
        print(f"Errors: {metrics['errors']}")
        print(f"Average search time: {metrics['avg_search_time']:.3f}s")
        
    except Exception as e:
        print(f"❌ Metrics error: {e}")
    
    finally:
        await adapter.close()


async def main():
    """Main example function."""
    print("🚀 ElasticsearchWatchlistAdapter Examples")
    print("=" * 50)
    
    # Check if Elasticsearch is available
    es_url = os.getenv("ES_URL", "http://localhost:9200")
    print(f"Elasticsearch URL: {es_url}")
    print("Note: Make sure Elasticsearch is running for full functionality")
    print()
    
    # Run examples
    await example_basic_usage()
    await example_with_fallback()
    await example_factory_functions()
    await example_snapshot_operations()
    await example_metrics_and_monitoring()
    
    print("\n✅ All examples completed!")


if __name__ == "__main__":
    # Set up environment variables if needed
    if not os.getenv("ES_URL"):
        os.environ["ES_URL"] = "http://localhost:9200"
    
    asyncio.run(main())
