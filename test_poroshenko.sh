#!/bin/bash
# Test if server has latest security fixes

echo "🧪 TESTING SECURITY FIXES ON SERVER"
echo "Commit: 4dec403 - fix(security): critical homoglyph detection and search functionality"
echo "=" * 60

SERVER="http://95.217.84.234:8000"

echo "TEST 1: Homoglyph Detection"
echo "Input: 'Liudмуlа Uliаnоvа'"
RESULT1=$(curl -s -X POST "$SERVER/process" -H 'Content-Type: application/json' -d '{"text": "Liudмуlа Uliаnоvа"}')

RISK_LEVEL=$(echo "$RESULT1" | grep -o '"risk_level":"[^"]*"' | cut -d'"' -f4)
HOMOGLYPH_DETECTED=$(echo "$RESULT1" | grep -o '"homoglyph_detected":[^,}]*' | cut -d':' -f2)

echo "Risk level: $RISK_LEVEL"
echo "Homoglyph detected: $HOMOGLYPH_DETECTED"

if [ "$RISK_LEVEL" = "HIGH" ]; then
    echo "✅ HOMOGLYPH FIX DEPLOYED!"
else
    echo "❌ Still waiting for deployment..."
fi

echo ""
echo "TEST 2: Search Functionality"
echo "Input: 'Порошенк Петро'"
RESULT2=$(curl -s -X POST "$SERVER/process" -H 'Content-Type: application/json' -d '{"text": "Порошенк Петро"}')

SEARCH_CONTRIB=$(echo "$RESULT2" | grep -o '"search_contribution":[0-9.]*' | cut -d':' -f2)
echo "Search contribution: $SEARCH_CONTRIB"

if [ "$SEARCH_CONTRIB" != "0" ] && [ "$SEARCH_CONTRIB" != "0.0" ]; then
    echo "✅ SEARCH FIX DEPLOYED!"
else
    echo "❌ Search still disabled - may need data loading"
fi