#!/usr/bin/env python3
"""
Search Integration Example

Demonstrates how to use the new search integration in the AI service pipeline.
Shows the complete flow from text input to decision output with search results.
"""

import asyncio
import os
from typing import Dict, Any

# Set up environment variables for search
os.environ["ENABLE_HYBRID_SEARCH"] = "true"
os.environ["ES_URL"] = "http://localhost:9200"
os.environ["ES_AUTH"] = "elastic:password"
os.environ["ES_VERIFY_SSL"] = "false"

# Search weights for Decision layer
os.environ["AI_DECISION__W_SEARCH_EXACT"] = "0.3"
os.environ["AI_DECISION__W_SEARCH_PHRASE"] = "0.25"
os.environ["AI_DECISION__W_SEARCH_NGRAM"] = "0.2"
os.environ["AI_DECISION__W_SEARCH_VECTOR"] = "0.15"

# Search thresholds
os.environ["AI_DECISION__THR_SEARCH_EXACT"] = "0.8"
os.environ["AI_DECISION__THR_SEARCH_PHRASE"] = "0.7"
os.environ["AI_DECISION__THR_SEARCH_NGRAM"] = "0.6"
os.environ["AI_DECISION__THR_SEARCH_VECTOR"] = "0.5"

# Search bonuses
os.environ["AI_DECISION__BONUS_MULTIPLE_MATCHES"] = "0.1"
os.environ["AI_DECISION__BONUS_HIGH_CONFIDENCE"] = "0.05"

from src.ai_service.core.orchestrator_factory_with_search import OrchestratorFactoryWithSearch
from src.ai_service.contracts.search_contracts import SearchOpts, SearchMode


async def main():
    """Main example function"""
    print("🚀 Search Integration Example")
    print("=" * 60)
    
    # Create orchestrator with search enabled
    print("📦 Creating orchestrator with search integration...")
    orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
        enable_smart_filter=True,
        enable_decision_engine=True,
        enable_hybrid_search=True,  # Enable search
        allow_smart_filter_skip=False
    )
    
    print("✅ Orchestrator created successfully")
    print()
    
    # Test cases
    test_cases = [
        {
            "name": "Person with DOB",
            "text": "Иван Петров, дата рождения 15.05.1980, гражданин России",
            "expected_entities": ["person"]
        },
        {
            "name": "Organization",
            "text": "ООО Приватбанк, Украина",
            "expected_entities": ["organization"]
        },
        {
            "name": "Mixed entities",
            "text": "Мария Сидорова работает в ТОВ Розум",
            "expected_entities": ["person", "organization"]
        },
        {
            "name": "No entities",
            "text": "Обычный текст без имен и организаций",
            "expected_entities": []
        }
    ]
    
    # Process each test case
    for i, test_case in enumerate(test_cases, 1):
        print(f"🧪 Test Case {i}: {test_case['name']}")
        print("-" * 40)
        print(f"Input: {test_case['text']}")
        print()
        
        try:
            # Process with search
            result = await orchestrator.process(
                text=test_case["text"],
                remove_stop_words=True,
                preserve_names=True,
                enable_advanced_features=True,
                search_opts=SearchOpts(
                    top_k=50,
                    threshold=0.7,
                    search_mode=SearchMode.HYBRID,
                    enable_escalation=True
                )
            )
            
            # Display results
            print(f"✅ Processing successful: {result.success}")
            print(f"⏱️  Processing time: {result.processing_time:.3f}s")
            print(f"🌐 Language: {result.language}")
            print(f"📝 Normalized: {result.normalized_text}")
            print()
            
            # Display signals
            if result.signals:
                persons = result.signals.get("persons", [])
                organizations = result.signals.get("organizations", [])
                
                print(f"👥 Persons found: {len(persons)}")
                for person in persons[:3]:  # Show first 3
                    print(f"   - {person.get('normalized_name', 'Unknown')} (conf: {person.get('confidence', 0):.2f})")
                
                print(f"🏢 Organizations found: {len(organizations)}")
                for org in organizations[:3]:  # Show first 3
                    print(f"   - {org.get('normalized_name', 'Unknown')} (conf: {org.get('confidence', 0):.2f})")
                print()
            
            # Display search results
            if "search" in result.metadata:
                search_meta = result.metadata["search"]
                print("🔍 Search Results:")
                print(f"   Total matches: {search_meta.get('total_matches', 0)}")
                print(f"   High confidence: {search_meta.get('high_confidence_matches', 0)}")
                print(f"   Search time: {search_meta.get('search_time', 0):.3f}s")
                print(f"   Exact matches: {search_meta.get('has_exact_matches', False)}")
                print(f"   Phrase matches: {search_meta.get('has_phrase_matches', False)}")
                print(f"   N-gram matches: {search_meta.get('has_ngram_matches', False)}")
                print(f"   Vector matches: {search_meta.get('has_vector_matches', False)}")
                print()
            
            # Display decision results
            if "decision" in result.metadata:
                decision_meta = result.metadata["decision"]
                print("⚖️  Decision Results:")
                print(f"   Risk level: {decision_meta.get('risk', 'Unknown')}")
                print(f"   Score: {decision_meta.get('score', 0):.3f}")
                print(f"   Reasons: {decision_meta.get('reasons', [])}")
                print()
            
            # Display errors if any
            if result.errors:
                print("❌ Errors:")
                for error in result.errors:
                    print(f"   - {error}")
                print()
            
        except Exception as e:
            print(f"❌ Processing failed: {e}")
            print()
        
        print("=" * 60)
        print()
    
    print("🎉 Example completed!")


async def demonstrate_search_configuration():
    """Demonstrate search configuration options"""
    print("⚙️  Search Configuration Demo")
    print("=" * 60)
    
    # Show different search modes
    search_modes = [
        SearchMode.AC,
        SearchMode.VECTOR,
        SearchMode.HYBRID,
        SearchMode.FALLBACK_AC,
        SearchMode.FALLBACK_VECTOR
    ]
    
    for mode in search_modes:
        print(f"🔍 Search Mode: {mode.value}")
        
        opts = SearchOpts(
            top_k=50,
            threshold=0.7,
            search_mode=mode,
            enable_escalation=(mode == SearchMode.HYBRID)
        )
        
        print(f"   Top K: {opts.top_k}")
        print(f"   Threshold: {opts.threshold}")
        print(f"   Escalation: {opts.enable_escalation}")
        print()
    
    # Show environment variables
    print("🌍 Environment Variables:")
    env_vars = [
        "ENABLE_HYBRID_SEARCH",
        "ES_URL",
        "ES_AUTH",
        "ES_VERIFY_SSL",
        "AI_DECISION__W_SEARCH_EXACT",
        "AI_DECISION__W_SEARCH_PHRASE",
        "AI_DECISION__W_SEARCH_NGRAM",
        "AI_DECISION__W_SEARCH_VECTOR",
        "AI_DECISION__THR_SEARCH_EXACT",
        "AI_DECISION__THR_SEARCH_PHRASE",
        "AI_DECISION__THR_SEARCH_NGRAM",
        "AI_DECISION__THR_SEARCH_VECTOR",
        "AI_DECISION__BONUS_MULTIPLE_MATCHES",
        "AI_DECISION__BONUS_HIGH_CONFIDENCE"
    ]
    
    for var in env_vars:
        value = os.getenv(var, "Not set")
        print(f"   {var}: {value}")
    
    print()


async def demonstrate_error_handling():
    """Demonstrate error handling in search integration"""
    print("🛡️  Error Handling Demo")
    print("=" * 60)
    
    # Create orchestrator with search disabled (to simulate errors)
    orchestrator = await OrchestratorFactoryWithSearch.create_orchestrator(
        enable_smart_filter=True,
        enable_decision_engine=True,
        enable_hybrid_search=False,  # Disable search
        allow_smart_filter_skip=False
    )
    
    test_text = "Иван Петров, дата рождения 15.05.1980"
    
    print(f"Input: {test_text}")
    print("Search: Disabled (simulating search service unavailable)")
    print()
    
    try:
        result = await orchestrator.process(
            text=test_text,
            remove_stop_words=True,
            preserve_names=True,
            enable_advanced_features=True
        )
        
        print(f"✅ Processing successful: {result.success}")
        print(f"⏱️  Processing time: {result.processing_time:.3f}s")
        
        # Check if search metadata is missing (expected)
        if "search" not in result.metadata:
            print("ℹ️  Search metadata missing (expected when search is disabled)")
        
        # Check for errors
        if result.errors:
            print("❌ Errors found:")
            for error in result.errors:
                print(f"   - {error}")
        else:
            print("✅ No errors (search gracefully skipped)")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
    
    print()


if __name__ == "__main__":
    print("🔧 AI Service Search Integration Example")
    print("=" * 60)
    print()
    
    # Run examples
    asyncio.run(main())
    asyncio.run(demonstrate_search_configuration())
    asyncio.run(demonstrate_error_handling())
    
    print("🎯 Integration example completed!")
    print()
    print("Next steps:")
    print("1. Set up Elasticsearch with watchlist indices")
    print("2. Load sanctioned entities using bulk_loader.py")
    print("3. Configure search weights and thresholds")
    print("4. Monitor search metrics and performance")
    print("5. Tune search parameters based on results")
