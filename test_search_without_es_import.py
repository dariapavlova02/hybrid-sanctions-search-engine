#!/usr/bin/env python3

import os
import sys
import asyncio
import json
sys.path.insert(0, '/Users/dariapavlova/Desktop/ai-service/src')

# Enable search and embeddings
os.environ['ENABLE_SEARCH'] = 'true'
os.environ['ENABLE_EMBEDDINGS'] = 'true'

async def test_poroshenko_search_bypass():
    """Test Poroshenko search with search enabled but bypassing elasticsearch import issues"""

    # Import the orchestrator but catch any elasticsearch-related import errors
    try:
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

    except ImportError as e:
        print(f"❌ Import error: {e}")
        if "elasticsearch" in str(e).lower() or "httpx" in str(e).lower():
            print("💡 This confirms the elasticsearch/httpx dependency issue")
            print("   The search service cannot be initialized due to import conflicts")
            return None
        else:
            raise
    except Exception as e:
        print(f"❌ Other error: {e}")
        import traceback
        traceback.print_exc()
        return None

async def test_alternative_approach():
    """Test if we can at least get the AI service running without search"""
    print("\n🔄 Testing alternative approach: AI service without search")

    # Disable search to see if core functionality works
    os.environ['ENABLE_SEARCH'] = 'false'
    os.environ['ENABLE_EMBEDDINGS'] = 'false'

    try:
        from ai_service.core.orchestrator_factory import OrchestratorFactory

        factory = OrchestratorFactory()
        orchestrator = await factory.create_async(
            enable_search=False,
            enable_embeddings=False,
            enable_variants=True
        )

        print(f"Search enabled: {orchestrator.enable_search}")
        print(f"Search service: {orchestrator.search_service is not None}")

        # Test basic normalization
        result = await orchestrator.process_async("Порошенко Петро")

        print(f"✅ Basic normalization works: '{result.normalized_text}'")
        print(f"Tokens: {result.tokens}")

        return result

    except Exception as e:
        print(f"❌ Even basic functionality fails: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    print("🧪 Testing search functionality with dependency workarounds")

    # Test 1: Try with search enabled
    result1 = asyncio.run(test_poroshenko_search_bypass())

    # Test 2: Try with search disabled
    result2 = asyncio.run(test_alternative_approach())

    print("\n📝 Summary:")
    print(f"Search enabled test: {'✅ Success' if result1 else '❌ Failed'}")
    print(f"Search disabled test: {'✅ Success' if result2 else '❌ Failed'}")