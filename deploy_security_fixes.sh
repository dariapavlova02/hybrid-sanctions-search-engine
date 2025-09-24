#!/bin/bash
# Deploy critical security fixes to server 95.217.84.234

echo "🚀 DEPLOYING CRITICAL SECURITY FIXES"
echo "Server: 95.217.84.234"
echo "=" * 50

# Key files that need to be updated on the server
CRITICAL_FILES=(
    "src/ai_service/config/settings.py"                    # ENABLE_SEARCH=true
    "src/ai_service/core/unified_orchestrator.py"          # auto search_service init
    "src/ai_service/layers/normalization/normalization_service.py"  # homoglyph integration
    "src/ai_service/core/decision_engine.py"               # homoglyph risk scoring
    "src/ai_service/layers/normalization/role_tagger_service.py"    # енк suffix
)

echo "📋 FILES TO UPDATE:"
for file in "${CRITICAL_FILES[@]}"; do
    echo "  - $file"
done

echo ""
echo "🔧 CRITICAL CHANGES SUMMARY:"
echo "1. ENABLE_SEARCH default changed: false -> true"
echo "2. Auto-initialize search_service in orchestrator"
echo "3. Homoglyph detection integrated in normalization"
echo "4. Homoglyph +0.85 score bonus in decision engine"
echo "5. Added 'енк' surname suffix pattern"

echo ""
echo "⚠️  DEPLOYMENT REQUIRED:"
echo "1. Copy updated files to server"
echo "2. Restart ai-service"
echo "3. Verify ENABLE_SEARCH=true in environment"
echo "4. Check Elasticsearch is running"
echo "5. Load sanctions data into indices"

echo ""
echo "🧪 TEST COMMANDS AFTER DEPLOYMENT:"
echo ""
echo "# Test 1: Homoglyph attack should give HIGH risk"
echo "curl -X POST http://95.217.84.234:8000/process \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"Liudмуlа Uliаnоvа\"}'"
echo ""
echo "# Expected: risk_level: HIGH, homoglyph_detected: true"
echo ""
echo "# Test 2: Truncated surname should be recognized"
echo "curl -X POST http://95.217.84.234:8000/process \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"Порошенк Петро\"}'"
echo ""
echo "# Expected: 'Порошенк' -> surname, search hits > 0"

echo ""
echo "📦 DEPLOYMENT CHECKLIST:"
echo "□ Update source files on server"
echo "□ Set ENABLE_SEARCH=true in environment"
echo "□ Restart ai-service"
echo "□ Start Elasticsearch if needed"
echo "□ Load sanctions data"
echo "□ Test homoglyph detection"
echo "□ Test search functionality"
echo "□ Verify HIGH risk for attacks"

echo ""
echo "🚨 URGENT: Server is vulnerable until deployed!"
echo "   - Sanctions screening bypassed"
echo "   - Homoglyph attacks undetected"
echo "   - Risk assessment incorrect"