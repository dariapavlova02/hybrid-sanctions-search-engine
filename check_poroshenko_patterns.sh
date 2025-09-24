#!/bin/bash
# Check if Poroshenko patterns are working on server

echo "🔍 CHECKING POROSHENKO PATTERNS ON SERVER"
echo "=" * 50

SERVER="http://95.217.84.234:8000"

# Test Порошенк Петро
echo "Testing: Порошенк Петро"
RESULT=$(curl -s -X POST "$SERVER/process" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Порошенк Петро"}')

echo "Raw result:"
echo "$RESULT" | jq . 2>/dev/null || echo "$RESULT"

echo ""
echo "Key fields:"
SURNAME_ROLE=$(echo "$RESULT" | grep -o '"token":"Порошенк"[^}]*' | grep -o '"role":"[^"]*"' | cut -d'"' -f4)
SEARCH_HITS=$(echo "$RESULT" | grep -o '"total_hits":[0-9]*' | cut -d':' -f2)
SEARCH_CONTRIB=$(echo "$RESULT" | grep -o '"search_contribution":[0-9.]*' | cut -d':' -f2)

echo "Surname role: $SURNAME_ROLE"
echo "Search hits: $SEARCH_HITS"
echo "Search contribution: $SEARCH_CONTRIB"

if [ "$SURNAME_ROLE" = "surname" ]; then
    echo "✅ 'Порошенк' classified as surname"
else
    echo "❌ 'Порошенк' not classified as surname (got: $SURNAME_ROLE)"
fi

if [ "$SEARCH_CONTRIB" != "0" ]; then
    echo "✅ Search is working (contribution: $SEARCH_CONTRIB)"
else
    echo "❌ Search disabled (contribution: 0)"
fi