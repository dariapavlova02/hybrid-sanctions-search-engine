#!/bin/bash

echo "🔍 Testing Poroshenko search with ENABLE_SEARCH=true"

export ENABLE_SEARCH=true
export ENABLE_EMBEDDINGS=true

curl -s -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Порошенко Петро"}' | \
  jq '{
    normalized_text,
    search_results: {
      total_hits: .search_results.total_hits,
      search_type: .search_results.search_type,
      results: (.search_results.results // [] | length)
    },
    embedding: (.embedding != null),
    decision: {
      risk_level: .decision.risk_level,
      risk_score: .decision.risk_score
    }
  }'