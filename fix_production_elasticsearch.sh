#!/bin/bash
# Fix production server - restart service to apply exclusion patterns

echo "🔧 Fixing production AI service with exclusion patterns"
echo "Production server: 95.217.84.234:8002"
echo "=========================================="

# Test current state
echo "1. Testing current problematic input..."
curl -s -X POST http://95.217.84.234:8002/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Прийом оплат на рахунок 68ccdc4cd19cabdee2eaa56c TV0015628 GM293232 в пользу OKPO 30929821 за оказанные услуги 7sichey по договору 2515321244 іпн Holoborodko Liudmyla д.р. 12.11.1968"}' | jq -r '.normalized_text'

echo -e "\n2. Production server restart required!"
echo "Current exclusion patterns are not applied."
echo "The service needs to be restarted to load updated smart_filter_patterns.py"

echo -e "\n📋 Restart options (run on production server 95.217.84.234):"
echo "   Option A: systemctl restart ai-service"
echo "   Option B: pm2 restart ai-service"
echo "   Option C: Kill and restart process"
echo "   Option D: Docker container restart"

echo -e "\n⚡ Quick restart commands:"
echo "   ssh user@95.217.84.234"
echo "   sudo systemctl restart ai-service"
echo "   # OR"
echo "   pm2 restart ai-service"

echo -e "\n🧪 After restart, test with:"
echo "   curl -X POST http://95.217.84.234:8002/process \\"
echo "     -H \"Content-Type: application/json\" \\"
echo "     -d '{\"text\": \"Holoborodko Liudmyla д.р. 12.11.1968 іпн 2515321244\"}' | jq '.normalized_text'"

echo -e "\n✅ Expected result: \"Holoborodko Liudmyla\""
echo "❌ Current result:  \"68Ссdс4Сd19Саbdее2Еаа56С Ноlоbоrоdkо Liudmуlа 7Siсhеу Д. Р.\""
