#!/usr/bin/env python3
"""
Debug escalation logic for Poroshenko search.
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def debug_escalation():
    """Debug escalation configuration and logic."""

    print("🔍 ESCALATION DEBUG ANALYSIS")
    print("=" * 60)

    # 1. Check environment variables
    print("📋 Environment Configuration:")
    print(f"  ENABLE_SEARCH: {os.getenv('ENABLE_SEARCH', 'not set')}")
    print(f"  ES_HOSTS: {os.getenv('ES_HOSTS', 'not set')}")

    # 2. Check service configuration
    try:
        from ai_service.config.settings import ServiceConfig
        config = ServiceConfig()
        print(f"  enable_search (config): {config.enable_search}")
    except Exception as e:
        print(f"  ❌ Config error: {e}")

    # 3. Check search configuration
    try:
        from ai_service.layers.search.config import HybridSearchConfig
        search_config = HybridSearchConfig()
        print(f"\n🔧 Search Configuration:")
        print(f"  enable_escalation: {search_config.enable_escalation}")
        print(f"  escalation_threshold: {search_config.escalation_threshold}")
        print(f"  enable_vector_fallback: {search_config.enable_vector_fallback}")
        print(f"  vector_cos_threshold: {search_config.vector_cos_threshold}")
        print(f"  default_mode: {search_config.default_mode}")
    except Exception as e:
        print(f"  ❌ Search config error: {e}")

    # 4. Check escalation logic manually
    print(f"\n🧪 Manual Escalation Logic Test:")

    # Simulate AC search results for "Порошенк Петро"
    ac_candidates = []  # AC finds nothing for typo

    print(f"  AC candidates: {len(ac_candidates)} (empty list)")
    print(f"  Condition: if not ac_candidates → {not ac_candidates}")
    print(f"  Expected escalation: {'YES' if not ac_candidates else 'NO'}")

    # 5. Test SearchOpts configuration
    try:
        sys.path.insert(0, 'src/ai_service/layers/search')
        from mock_search_service import SearchOpts, SearchMode

        opts = SearchOpts(
            search_mode=SearchMode.HYBRID,
            top_k=10,
            threshold=0.3,  # Low threshold for vector search
            enable_escalation=True
        )

        print(f"\n⚙️ SearchOpts Configuration:")
        print(f"  search_mode: {opts.search_mode}")
        print(f"  enable_escalation: {opts.enable_escalation}")
        print(f"  threshold: {opts.threshold}")

    except Exception as e:
        print(f"  ❌ SearchOpts error: {e}")

    # 6. Diagnose why search returns empty
    print(f"\n🚨 Potential Issues:")

    if os.getenv('ENABLE_SEARCH', 'false').lower() != 'true':
        print("  ❌ ENABLE_SEARCH is not 'true' - search is disabled!")
        print("     Solution: export ENABLE_SEARCH=true")

    print("  ⚠️ Check if Elasticsearch is running")
    print("  ⚠️ Check if watchlist index is populated")
    print("  ⚠️ Check if MockSearchService is used instead of real ES")

    # 7. Test escalation threshold edge case
    print(f"\n🧮 Threshold Analysis:")
    escalation_threshold = 0.8
    print(f"  Default escalation_threshold: {escalation_threshold}")
    print(f"  Problem: High threshold means only low-quality AC results trigger escalation")
    print(f"  But for typos, AC returns EMPTY list → should always escalate")

    # 8. Recommendations
    print(f"\n💡 Recommendations:")
    print("  1. Set ENABLE_SEARCH=true")
    print("  2. Lower escalation_threshold to 0.6 for better recall")
    print("  3. Lower vector search threshold to 0.3 for fuzzy matching")
    print("  4. Check MockSearchService contains Poroshenko data")
    print("  5. Verify vector index is not empty")

if __name__ == "__main__":
    debug_escalation()