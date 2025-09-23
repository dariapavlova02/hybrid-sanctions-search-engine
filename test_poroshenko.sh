#!/bin/bash

echo "🧪 Testing Poroshenko search with correct Elasticsearch host..."

# Set correct Elasticsearch host
export ELASTICSEARCH_HOST=95.217.84.234
export ELASTICSEARCH_PORT=9200
export ENABLE_SEARCH=true
export ENABLE_AHO_CORASICK=true

echo "🔧 Environment:"
echo "  ELASTICSEARCH_HOST=$ELASTICSEARCH_HOST"
echo "  ELASTICSEARCH_PORT=$ELASTICSEARCH_PORT"
echo "  ENABLE_SEARCH=$ENABLE_SEARCH"

echo ""
echo "🚀 Testing with local AI service..."

# Test using python directly
python3 -c "
import os
import sys
sys.path.append('src')

from ai_service.core.unified_orchestrator import UnifiedOrchestrator
import asyncio

async def test_poroshenko():
    orchestrator = UnifiedOrchestrator()
    result = await orchestrator.process_async('Петро Порошенко')

    print('✅ Normalization:', result.normalized_text)
    print('📊 Search results:', result.search_results.total_hits if result.search_results else 'None')
    print('⚖️ Risk level:', result.decision.risk_level if result.decision else 'None')
    print('🔍 Search contribution:',
          result.decision.score_breakdown.get('search_contribution', 'Missing') if result.decision else 'None')

if __name__ == '__main__':
    asyncio.run(test_poroshenko())
"
