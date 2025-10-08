#!/bin/bash

echo "🚀 Deploying INN cache fix to production..."

# 1. Copy updated files to server
echo "📁 Copying updated files..."
scp src/ai_service/layers/signals/signals_service.py root@95.217.84.234:/app/src/ai_service/layers/signals/

# 2. Restart the service
echo "🔄 Restarting AI service..."
ssh root@95.217.84.234 "cd /app && docker-compose restart ai-service"

# 3. Wait for service to be ready
echo "⏳ Waiting for service to start..."
sleep 10

# 4. Test the fix
echo "🧪 Testing the fix..."
curl -X POST "http://95.217.84.234:8000/process" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer test-token" \
  -d '{
    "text": "Дарья Павлова ИНН 2839403975",
    "request_id": "test-inn-production",
    "options": {
      "enable_signals": true,
      "enable_search": true,
      "enable_decision": true
    }
  }' | python -c "
import json
import sys
data = json.load(sys.stdin)
print('Risk level:', data['decision']['risk_level'])
print('ID match:', data['decision']['decision_details']['normalized_features']['id_match'])
print('ID bonus:', data['decision']['decision_details']['score_breakdown']['id_bonus'])
if data['signals']['persons']:
    person = data['signals']['persons'][0]
    print('Person IDs:')
    for pid in person.get('ids', []):
        if pid.get('sanctioned'):
            print(f'  🚨 SANCTIONED: {pid}')
        else:
            print(f'  {pid}')
"

echo "✅ Deployment complete!"