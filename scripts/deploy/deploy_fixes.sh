#!/bin/bash

# Deploy vector search fixes to production server
set -e

SERVER="95.217.84.234"
echo "🚀 Deploying vector search fixes to $SERVER"

# Copy updated files to server
echo "📂 Copying updated files..."
scp -o StrictHostKeyChecking=no \
    src/ai_service/contracts/search_contracts.py \
    src/ai_service/core/unified_orchestrator.py \
    src/ai_service/core/decision_engine.py \
    src/ai_service/config/settings.py \
    root@$SERVER:/root/ai-service/src/ai_service/contracts/search_contracts.py \
    root@$SERVER:/root/ai-service/src/ai_service/core/unified_orchestrator.py \
    root@$SERVER:/root/ai-service/src/ai_service/core/decision_engine.py \
    root@$SERVER:/root/ai-service/src/ai_service/config/settings.py

echo "🐳 Restarting Docker services..."
ssh -o StrictHostKeyChecking=no root@$SERVER << 'EOF'
cd /root/ai-service
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
EOF

echo "✅ Deployment completed!"

# Wait and test
echo "⏳ Waiting for service to start..."
sleep 30

echo "🧪 Testing service..."
curl -s "http://$SERVER:8000/health" | jq '.' || echo "❌ Health check failed"

echo "🎯 Testing vector search fix..."
curl -s -X POST "http://$SERVER:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Дарья Павлова Юрьевна"}' | jq '.search.high_confidence_matches' || echo "❌ Test failed"

echo "🏁 Deployment finished!"