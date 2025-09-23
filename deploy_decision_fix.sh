#!/bin/bash
# Deploy the decision engine and exclusion pattern fixes to production

echo "🚀 Deploying SmartFilter and Decision Engine fixes to production"
echo "=================================================================="

echo "📋 Issues being fixed:"
echo "  1. SmartFilter threshold too high (causing valid names to be skipped)"
echo "  2. Exclusion patterns not applied (need service restart)"
echo "  3. Decision engine weights need optimization"

echo -e "\n🎯 Expected behavior after fix:"
echo "  Input: 'Дарья Павлова' → Output: risk_level='medium' (not 'skip')"
echo "  Input: Insurance garbage → Output: Only 'Holoborodko Liudmyla' extracted"

echo -e "\n⚡ CRITICAL: Production server restart required!"
echo "The following files have been updated but need service restart:"
echo "  - /src/ai_service/data/dicts/smart_filter_patterns.py (exclusion patterns)"
echo "  - /src/ai_service/config/settings.py (decision weights)"
echo "  - /src/ai_service/core/decision_engine.py (exact match bonus)"

echo -e "\n🛠️ Restart commands for production server (95.217.84.234:8002):"
echo "Option 1 - SystemD:"
echo "  ssh user@95.217.84.234"
echo "  sudo systemctl restart ai-service"
echo "  sudo systemctl status ai-service"

echo -e "\nOption 2 - PM2:"
echo "  ssh user@95.217.84.234"
echo "  pm2 restart ai-service"
echo "  pm2 status ai-service"

echo -e "\nOption 3 - Docker:"
echo "  ssh user@95.217.84.234"
echo "  docker restart ai-service-container"
echo "  docker ps | grep ai-service"

echo -e "\nOption 4 - Process Kill/Restart:"
echo "  ssh user@95.217.84.234"
echo "  pkill -f 'ai_service'"
echo "  nohup python -m ai_service.main &"

echo -e "\n🧪 Test commands after restart:"
echo "Test 1 - Simple name (should NOT be skipped):"
echo "curl -X POST http://95.217.84.234:8002/process \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"Дарья Павлова\"}' | jq '.decision.risk_level'"
echo "Expected: \"medium\" or \"high\" (NOT \"skip\")"

echo -e "\nTest 2 - Insurance document cleanup:"
echo "curl -X POST http://95.217.84.234:8002/process \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"Прийом оплат 68ccdc4cd19cabdee2eaa56c TV0015628 Holoborodko Liudmyla д.р. 12.11.1968 іпн 2515321244\"}' | jq '.normalized_text'"
echo "Expected: \"Holoborodko Liudmyla\""

echo -e "\n✅ Success criteria:"
echo "  ✓ 'Дарья Павлова' → risk_level != 'skip'"
echo "  ✓ Insurance garbage codes filtered out"
echo "  ✓ Clean name extraction: 'Holoborodko Liudmyla'"
echo "  ✓ SmartFilter threshold properly configured"

echo -e "\n🔍 Monitoring after deployment:"
echo "  - Check service logs for errors"
echo "  - Verify configuration loaded correctly"
echo "  - Run comprehensive test suite"
echo "  - Monitor performance metrics"

echo -e "\n📞 If issues persist:"
echo "  1. Check /Users/dariapavlova/Desktop/ai-service/SMARTFILTER_PRODUCTION_FIX.md"
echo "  2. Verify environment variables: AI_SMARTFILTER__MIN_PROCESSING_THRESHOLD=0.001"
echo "  3. Check service logs for configuration errors"
echo "  4. Run ./test_new_exclusion_patterns.py locally to verify patterns"

