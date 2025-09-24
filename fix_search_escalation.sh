#!/bin/bash
"""
Fix search escalation for Poroshenko query.
"""

echo "🔧 Fixing Search Escalation Configuration"
echo "========================================"

# 1. Enable search
echo "1. Enabling search..."
export ENABLE_SEARCH=true
echo "   ✅ ENABLE_SEARCH=true"

# 2. Lower escalation threshold for better recall
echo "2. Setting optimal thresholds..."
export SEARCH_ESCALATION_THRESHOLD=0.6
export VECTOR_SEARCH_THRESHOLD=0.3
echo "   ✅ escalation_threshold=0.6 (was 0.8)"
echo "   ✅ vector_threshold=0.3 (better fuzzy matching)"

# 3. Test with enabled search
echo "3. Testing with enabled search..."
python3 << 'EOF'
import os
import sys
sys.path.insert(0, 'src')

# Test search configuration
print("📋 Current Configuration:")
print(f"  ENABLE_SEARCH: {os.getenv('ENABLE_SEARCH')}")
print(f"  SEARCH_ESCALATION_THRESHOLD: {os.getenv('SEARCH_ESCALATION_THRESHOLD')}")
print(f"  VECTOR_SEARCH_THRESHOLD: {os.getenv('VECTOR_SEARCH_THRESHOLD')}")

try:
    from ai_service.config.settings import ServiceConfig
    config = ServiceConfig()
    print(f"  enable_search (config): {config.enable_search}")

    if config.enable_search:
        print("  ✅ Search is ENABLED")
    else:
        print("  ❌ Search is still DISABLED")

except Exception as e:
    print(f"  ❌ Config error: {e}")

EOF

echo ""
echo "🧪 Test Recommendations:"
echo "  1. Run: export ENABLE_SEARCH=true"
echo "  2. Test Poroshenko query again"
echo "  3. Should see escalation to vector search"
echo "  4. MockSearchService should return Poroshenko match"

echo ""
echo "🎯 Expected Results:"
echo "  - AC search: 0 results (typo)"
echo "  - Escalation: YES (empty AC results)"
echo "  - Vector search: 1 result (Порошенко with score ~0.45)"
echo "  - Total hits: 1"