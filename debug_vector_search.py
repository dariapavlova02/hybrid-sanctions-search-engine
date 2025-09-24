#!/usr/bin/env python3
"""
Debug script to understand why vector search is not working for typos.
"""

import asyncio
import json
import requests
from src.ai_service.layers.search.hybrid_search_service import HybridSearchService
from src.ai_service.layers.search.config import HybridSearchConfig

async def test_vector_search():
    """Test vector search functionality for typo handling."""
    print("🔍 Debugging Vector Search for Typos")
    print("="*50)

    # Test original query through main API first
    print("1. Testing through main API...")
    try:
        response = requests.post(
            "http://localhost:8000/process",
            json={
                "text": "Порошенк Петро",
                "language": "uk",
                "enable_search": True,
                "enable_variants": False,
                "enable_embeddings": False
            },
            timeout=30
        )

        if response.status_code == 200:
            result = response.json()
            search_results = result.get("search_results", {})
            print(f"   API Search Results: {search_results.get('total_hits', 0)} hits")
            print(f"   Search Type: {search_results.get('search_type', 'unknown')}")
            print(f"   Processing Time: {search_results.get('processing_time_ms', 0)} ms")

            if search_results.get('results'):
                print("   Top results:")
                for i, hit in enumerate(search_results['results'][:3]):
                    name = hit.get('name', 'Unknown')
                    score = hit.get('score', 0)
                    print(f"     {i+1}. {name} (score: {score:.3f})")
            else:
                print("   ❌ No search results found!")
        else:
            print(f"   ❌ API returned status {response.status_code}")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")

    # Test direct search service
    print("\n2. Testing direct search service...")
    try:
        # Initialize search service
        config = HybridSearchConfig()
        print(f"   Config - enable_vector_fallback: {config.enable_vector_fallback}")
        print(f"   Config - vector_cos_threshold: {config.vector_cos_threshold}")
        print(f"   Config - vector_fallback_threshold: {config.vector_fallback_threshold}")

        search_service = HybridSearchService(config)
        await search_service.initialize()

        # Test the search directly
        query = "Порошенк Петро"
        print(f"   Searching for: '{query}'")

        # Check if embedding service is available
        embedding_service = await search_service._get_embedding_service()
        if embedding_service:
            print("   ✅ Embedding service is available")
        else:
            print("   ❌ Embedding service is NOT available - this is the problem!")

        # Try to get embedding for the query
        try:
            vector = await search_service._generate_query_vector(query)
            print(f"   Vector generated: {len(vector) if vector else 0} dimensions")
            if vector and len(vector) > 0:
                print(f"   Vector sample: [{vector[0]:.3f}, {vector[1]:.3f}, ...]")
            else:
                print("   ❌ No vector generated!")
        except Exception as e:
            print(f"   ❌ Vector generation failed: {e}")

        # Test search
        results = await search_service.search_async(query)
        print(f"   Search results: {len(results.results)} hits")
        print(f"   Total hits: {results.total_hits}")
        print(f"   Search type: {results.search_type}")

        if results.results:
            print("   Top results:")
            for i, hit in enumerate(results.results[:3]):
                name = hit.name if hasattr(hit, 'name') else str(hit)
                score = hit.score if hasattr(hit, 'score') else 0
                print(f"     {i+1}. {name} (score: {score:.3f})")
        else:
            print("   ❌ No results from direct search!")

    except Exception as e:
        print(f"   ❌ Direct search failed: {e}")
        import traceback
        traceback.print_exc()

    # Test fuzzy string matching as comparison
    print("\n3. Testing fuzzy matching approach...")
    try:
        import rapidfuzz

        # Known names for comparison
        test_names = [
            "Петро Порошенко",
            "Порошенко Петро",
            "Володимир Зеленський",
            "Юлія Тимошенко"
        ]

        query = "Порошенк Петро"
        print(f"   Query: '{query}'")
        print(f"   Testing against {len(test_names)} names...")

        matches = []
        for name in test_names:
            ratio = rapidfuzz.fuzz.ratio(query, name) / 100.0
            token_ratio = rapidfuzz.fuzz.token_sort_ratio(query, name) / 100.0
            partial_ratio = rapidfuzz.fuzz.partial_ratio(query, name) / 100.0

            best_score = max(ratio, token_ratio, partial_ratio)
            matches.append((name, best_score, ratio, token_ratio, partial_ratio))

        # Sort by best score
        matches.sort(key=lambda x: x[1], reverse=True)

        print("   Fuzzy matching results:")
        for name, best, ratio, token, partial in matches[:3]:
            print(f"     {name}: {best:.3f} (ratio:{ratio:.3f}, token:{token:.3f}, partial:{partial:.3f})")

        # Check if fuzzy would find the match
        if matches and matches[0][1] > 0.8:
            print(f"   ✅ Fuzzy matching would find: {matches[0][0]} (score: {matches[0][1]:.3f})")
        else:
            print("   ❌ Fuzzy matching also struggles with this typo")

    except ImportError:
        print("   ❌ rapidfuzz not available for testing")
    except Exception as e:
        print(f"   ❌ Fuzzy test failed: {e}")

    print("\n" + "="*50)
    print("🎯 DIAGNOSIS SUMMARY:")
    print("="*50)

    print("💡 RECOMMENDATIONS:")
    print("1. ✅ Add fuzzy search layer with rapidfuzz for typo tolerance")
    print("2. ✅ Check if embedding service is properly configured")
    print("3. ✅ Verify vector index exists and is populated")
    print("4. ✅ Consider hybrid approach: AC → Fuzzy → Vector")
    print("5. ✅ Lower vector similarity thresholds for typos")

if __name__ == "__main__":
    asyncio.run(test_vector_search())