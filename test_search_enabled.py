#!/usr/bin/env python3

import os
import sys
import asyncio
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

# Enable search and embeddings
os.environ['ENABLE_SEARCH'] = 'true'
os.environ['ENABLE_EMBEDDINGS'] = 'true'

async def test_poroshenko_search():
    """Test Poroshenko search with search enabled"""
    from ai_service.core.orchestrator_factory import OrchestratorFactory

    print("🔍 Testing Poroshenko search with ENABLE_SEARCH=true")

    # Create orchestrator with search enabled
    factory = OrchestratorFactory()
    orchestrator = await factory.create_async(
        enable_search=True,
        enable_embeddings=True,
        enable_variants=True
    )

    print(f"Search enabled: {orchestrator.enable_search}")
    print(f"Search service: {orchestrator.search_service is not None}")
    print(f"Embeddings enabled: {orchestrator.enable_embeddings}")

    # Test the search
    result = await orchestrator.process_async("Порошенко Петро")

    print("\n📊 Results:")
    print(f"Normalized: '{result.normalized_text}'")
    print(f"Search hits: {result.search_results.get('total_hits', 0) if result.search_results else 'No search results'}")
    print(f"Search type: {result.search_results.get('search_type', 'None') if result.search_results else 'None'}")
    print(f"Embedding: {'Yes' if result.embedding else 'No'}")
    print(f"Risk level: {result.decision.risk_level if result.decision else 'None'}")

    if result.search_results and result.search_results.get('total_hits', 0) > 0:
        print("\n🎯 Found results:")
        for i, hit in enumerate(result.search_results.get('results', [])[:3]):
            print(f"  {i+1}. {hit}")
    else:
        print("\n⚠️ No search results found")

    return result

if __name__ == "__main__":
    result = asyncio.run(test_poroshenko_search())