#!/bin/bash
# Test critical security fixes after deployment

echo "🧪 TESTING SECURITY FIXES ON PRODUCTION SERVER"
echo "Server: 95.217.84.234:8000"
echo "=" * 60

SERVER="http://95.217.84.234:8000"

# Test 1: Homoglyph attack detection
echo "🔍 TEST 1: Homoglyph attack detection"
echo "Input: 'Liudмуlа Uliаnоvа' (mixed Latin/Cyrillic)"
echo ""

HOMOGLYPH_RESULT=$(curl -s -X POST "$SERVER/process" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Liudмуlа Uliаnоvа"}')

RISK_LEVEL=$(echo "$HOMOGLYPH_RESULT" | grep -o '"risk_level":"[^"]*"' | cut -d'"' -f4)
RISK_SCORE=$(echo "$HOMOGLYPH_RESULT" | grep -o '"risk_score":[0-9.]*' | cut -d':' -f2)
HOMOGLYPH_DETECTED=$(echo "$HOMOGLYPH_RESULT" | grep -o '"homoglyph_detected":[^,}]*' | cut -d':' -f2)

echo "Results:"
echo "  Risk level: $RISK_LEVEL"
echo "  Risk score: $RISK_SCORE"
echo "  Homoglyph detected: $HOMOGLYPH_DETECTED"

if [ "$RISK_LEVEL" = "HIGH" ]; then
    echo "  ✅ PASS: HIGH risk correctly assigned"
else
    echo "  ❌ FAIL: Should be HIGH risk, got $RISK_LEVEL"
fi

if [[ $(echo "$RISK_SCORE > 0.8" | bc -l) -eq 1 ]]; then
    echo "  ✅ PASS: Risk score > 0.8"
else
    echo "  ❌ FAIL: Risk score too low: $RISK_SCORE"
fi

# Test 2: Truncated surname recognition
echo ""
echo "🔍 TEST 2: Truncated surname recognition"
echo "Input: 'Порошенк Петро'"
echo ""

SURNAME_RESULT=$(curl -s -X POST "$SERVER/process" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Порошенк Петро"}')

SURNAME_ROLE=$(echo "$SURNAME_RESULT" | grep -A5 '"token":"Порошенк"' | grep -o '"role":"[^"]*"' | cut -d'"' -f4)
SEARCH_HITS=$(echo "$SURNAME_RESULT" | grep -o '"total_hits":[0-9]*' | cut -d':' -f2)

echo "Results:"
echo "  'Порошенк' role: $SURNAME_ROLE"
echo "  Search hits: $SEARCH_HITS"

if [ "$SURNAME_ROLE" = "surname" ]; then
    echo "  ✅ PASS: 'Порошенк' correctly classified as surname"
else
    echo "  ❌ FAIL: Should be surname, got $SURNAME_ROLE"
fi

if [ "$SEARCH_HITS" -gt 0 ]; then
    echo "  ✅ PASS: Search found matches"
else
    echo "  ❌ FAIL: No search matches found (search may be disabled)"
fi

# Test 3: Search functionality
echo ""
echo "🔍 TEST 3: Search functionality"
echo "Input: 'Порошенко Петр'"
echo ""

SEARCH_RESULT=$(curl -s -X POST "$SERVER/process" \
  -H 'Content-Type: application/json' \
  -d '{"text": "Порошенко Петр"}')

SEARCH_TOTAL=$(echo "$SEARCH_RESULT" | grep -o '"total_hits":[0-9]*' | cut -d':' -f2)
SEARCH_CONTRIBUTION=$(echo "$SEARCH_RESULT" | grep -o '"search_contribution":[0-9.]*' | cut -d':' -f2)

echo "Results:"
echo "  Total search hits: $SEARCH_TOTAL"
echo "  Search contribution: $SEARCH_CONTRIBUTION"

if [ "$SEARCH_TOTAL" -gt 0 ]; then
    echo "  ✅ PASS: Search is working"
elif [ "$SEARCH_CONTRIBUTION" = "0" ]; then
    echo "  ❌ FAIL: Search is disabled (contribution = 0)"
else
    echo "  ⚠️  WARNING: Search may not have data loaded"
fi

# Test 4: All-caps Ukrainian name
echo ""
echo "🔍 TEST 4: All-caps Ukrainian name"
echo "Input: 'АНДРІЙ'"
echo ""

CAPS_RESULT=$(curl -s -X POST "$SERVER/process" \
  -H 'Content-Type: application/json' \
  -d '{"text": "АНДРІЙ"}')

CAPS_ROLE=$(echo "$CAPS_RESULT" | grep -A5 '"token":"АНДРІЙ"' | grep -o '"role":"[^"]*"' | cut -d'"' -f4)

echo "Results:"
echo "  'АНДРІЙ' role: $CAPS_ROLE"

if [ "$CAPS_ROLE" = "given" ]; then
    echo "  ✅ PASS: All-caps Ukrainian name classified correctly"
else
    echo "  ❌ FAIL: Should be given, got $CAPS_ROLE"
fi

# Summary
echo ""
echo "📊 SUMMARY:"
echo "=" * 30

TESTS_PASSED=0
TESTS_TOTAL=4

[ "$RISK_LEVEL" = "HIGH" ] && ((TESTS_PASSED++))
[ "$SURNAME_ROLE" = "surname" ] && ((TESTS_PASSED++))
[ "$SEARCH_TOTAL" -gt 0 ] && ((TESTS_PASSED++))
[ "$CAPS_ROLE" = "given" ] && ((TESTS_PASSED++))

echo "Tests passed: $TESTS_PASSED/$TESTS_TOTAL"

if [ $TESTS_PASSED -eq $TESTS_TOTAL ]; then
    echo "🎉 ALL TESTS PASSED - Security fixes deployed successfully!"
    exit 0
elif [ $TESTS_PASSED -ge 2 ]; then
    echo "⚠️  PARTIAL SUCCESS - Some fixes deployed, others pending"
    exit 1
else
    echo "❌ DEPLOYMENT FAILED - Critical security issues remain"
    exit 2
fi