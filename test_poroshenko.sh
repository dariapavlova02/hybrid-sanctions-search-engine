#!/bin/bash
# Test Poroshenko API call
echo "🧪 Testing Poroshenko on production API..."

# Test full API response
echo ""
echo "📋 Full API response:"
curl -X POST 'http://95.217.84.234:8002/process' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.'

echo ""
echo "🎯 Score breakdown only:"
curl -X POST 'http://95.217.84.234:8002/process' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.decision.score_breakdown'

echo ""
echo "🔍 Search info:"
curl -X POST 'http://95.217.84.234:8002/process' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.search'

echo ""
echo "⚡ Decision info:"
curl -X POST 'http://95.217.84.234:8002/process' \
  -H 'Content-Type: application/json' \
  -d '{"text": "Петро Порошенко"}' | jq '.decision'
