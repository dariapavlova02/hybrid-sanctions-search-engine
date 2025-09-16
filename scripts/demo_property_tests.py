#!/usr/bin/env python3
"""
Demo Script for Property-Based Tests

This script demonstrates how to run property-based tests for the hybrid search system
and shows examples of the invariants being tested.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tests.property.test_anti_cheat_regression import HybridSearchTester, SearchConfig, SearchType


async def demo_search_invariants():
    """Demonstrate search invariants with real examples"""
    
    print("🔍 Property-Based Test Demo for Hybrid Search System")
    print("=" * 60)
    
    # Initialize search tester
    tester = HybridSearchTester()
    
    try:
        # Check if Elasticsearch is available
        try:
            health_response = await tester.client.get(f"{tester.es_url}/_cluster/health")
            if health_response.status_code != 200:
                print("❌ Elasticsearch is not available. Please start it first:")
                print("   docker-compose -f monitoring/docker-compose.monitoring.yml up -d")
                return
        except Exception:
            print("❌ Cannot connect to Elasticsearch. Please start it first:")
            print("   docker-compose -f monitoring/docker-compose.monitoring.yml up -d")
            return
        
        print("✅ Elasticsearch is available")
        print()
        
        # Demo 1: Exact Match Invariant
        print("1. 🎯 Exact Match Invariant Demo")
        print("-" * 40)
        
        test_queries = ["иван петров", "мария сидорова", "ооо газпром"]
        config = SearchConfig()
        
        for query in test_queries:
            print(f"Testing query: '{query}'")
            results = await tester.hybrid_search(query, config, "person")
            
            if results:
                exact_results = [r for r in results if r.search_type == SearchType.EXACT]
                non_exact_results = [r for r in results if r.search_type != SearchType.EXACT]
                
                if exact_results and non_exact_results:
                    max_exact = max(r.final_score for r in exact_results)
                    max_non_exact = max(r.final_score for r in non_exact_results)
                    
                    print(f"  Exact matches: {len(exact_results)} (max score: {max_exact:.3f})")
                    print(f"  Non-exact matches: {len(non_exact_results)} (max score: {max_non_exact:.3f})")
                    
                    if max_exact >= max_non_exact:
                        print("  ✅ Invariant holds: exact score >= non-exact score")
                    else:
                        print("  ❌ Invariant violated: exact score < non-exact score")
                else:
                    print("  ℹ️  No comparison possible (only one type of results)")
            else:
                print("  ℹ️  No results found")
            print()
        
        # Demo 2: Case Stability Invariant
        print("2. 🔤 Case Stability Invariant Demo")
        print("-" * 40)
        
        base_query = "Иван Петров"
        case_variations = [
            base_query.lower(),
            base_query.upper(),
            base_query.title(),
            base_query.swapcase(),
            base_query.capitalize()
        ]
        
        print(f"Base query: '{base_query}'")
        print(f"Case variations: {case_variations}")
        print()
        
        results_by_variant = {}
        for variant in case_variations:
            results = await tester.hybrid_search(variant, config, "person")
            ac_results = [r for r in results if r.search_type in [SearchType.EXACT, SearchType.PHRASE, SearchType.NGRAM]]
            results_by_variant[variant] = ac_results
            print(f"  '{variant}': {len(ac_results)} AC results")
        
        # Check stability
        all_entity_ids = set()
        for results in results_by_variant.values():
            all_entity_ids.update(r.entity_id for r in results)
        
        if all_entity_ids:
            print(f"\n  Found {len(all_entity_ids)} unique entities across all variations")
            
            # Check appearance rate for each entity
            for entity_id in list(all_entity_ids)[:3]:  # Show first 3 entities
                appearances = sum(1 for results in results_by_variant.values() 
                                if any(r.entity_id == entity_id for r in results))
                appearance_rate = appearances / len(case_variations)
                print(f"  Entity '{entity_id}': appears in {appearances}/{len(case_variations)} variations ({appearance_rate:.1%})")
            
            if len(all_entity_ids) > 3:
                print(f"  ... and {len(all_entity_ids) - 3} more entities")
        else:
            print("  ℹ️  No entities found across variations")
        print()
        
        # Demo 3: Fusion Score Invariant
        print("3. 🔗 Fusion Score Invariant Demo")
        print("-" * 40)
        
        query = "иван петров"
        results = await tester.hybrid_search(query, config, "person")
        
        fusion_results = [r for r in results if r.search_type == SearchType.FUSION]
        
        if fusion_results:
            print(f"Found {len(fusion_results)} fusion results for query: '{query}'")
            
            for i, result in enumerate(fusion_results[:3]):  # Show first 3
                ac_score = result.ac_score
                vector_score = result.vector_score
                fusion_score = result.final_score
                max_individual = max(ac_score, vector_score)
                
                print(f"  Result {i+1}:")
                print(f"    Entity ID: {result.entity_id}")
                print(f"    AC Score: {ac_score:.3f}")
                print(f"    Vector Score: {vector_score:.3f}")
                print(f"    Fusion Score: {fusion_score:.3f}")
                print(f"    Max Individual: {max_individual:.3f}")
                
                if fusion_score >= max_individual:
                    print("    ✅ Invariant holds: fusion score >= max individual score")
                else:
                    print("    ❌ Invariant violated: fusion score < max individual score")
                print()
        else:
            print(f"  ℹ️  No fusion results found for query: '{query}'")
        print()
        
        # Demo 4: Score Monotonicity
        print("4. 📊 Score Monotonicity Invariant Demo")
        print("-" * 40)
        
        query = "иван"
        results = await tester.hybrid_search(query, config, "person")
        
        if len(results) >= 2:
            print(f"Query: '{query}' - {len(results)} results")
            print("Score ranking:")
            
            for i, result in enumerate(results[:5]):  # Show first 5
                print(f"  {i+1}. {result.entity_id}: {result.final_score:.3f} ({result.search_type.value})")
            
            # Check monotonicity
            scores = [r.final_score for r in results]
            is_monotonic = all(scores[i] >= scores[i+1] for i in range(len(scores)-1))
            
            if is_monotonic:
                print("  ✅ Invariant holds: scores are monotonically decreasing")
            else:
                print("  ❌ Invariant violated: scores are not monotonically decreasing")
            
            if len(results) > 5:
                print(f"  ... and {len(results) - 5} more results")
        else:
            print(f"  ℹ️  Not enough results to check monotonicity for query: '{query}'")
        print()
        
        print("🎉 Demo completed! All invariants have been demonstrated.")
        print("\nTo run the full property-based test suite:")
        print("  make -f Makefile.property test-property")
        print("\nTo run quick tests:")
        print("  make -f Makefile.property test-property-quick")
        
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await tester.cleanup()


async def main():
    """Main function"""
    await demo_search_invariants()


if __name__ == "__main__":
    asyncio.run(main())
