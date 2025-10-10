# Quick Deploy - Copy & Paste

## 🚀 Standard Deployment (5 minutes)

```bash
ssh root@95.217.84.234 << 'EOF'
cd /opt/ai-service
git pull origin main
cp .env.production .env
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
echo "Waiting for service to start..."
sleep 15
docker logs ai-service-prod --tail 30
curl http://localhost:9200/_cat/indices?v | grep sanctions
echo "Deployment complete!"
EOF
```

**Note:** Uses `docker-compose.prod.yml` (not default docker-compose.yml)
- Container: `ai-service-prod`
- Dockerfile: `Dockerfile.prod`
- Environment: `.env.production` → `.env` (copied automatically)
- Port: 8000

## ⚡ Quick Verification

```bash
# Check service is running
ssh root@95.217.84.234 'docker ps | grep ai-service'

# Test API
ssh root@95.217.84.234 'curl -s http://localhost:8000/health | jq'

# Test sanctioned INN
ssh root@95.217.84.234 'curl -s -X POST http://localhost:8000/process -H "Content-Type: application/json" -d "{\"text\": \"ИНН 2839403975\"}" | jq ".decision.risk_level"'
# Expected: "high"
```

## 📊 Check Elasticsearch

```bash
ssh root@95.217.84.234 << 'EOF'
curl -s http://localhost:9200/_cat/indices?v | grep sanctions
echo ""
echo "AC Patterns count:"
curl -s http://localhost:9200/sanctions_ac_patterns/_count | jq '.count'
echo "Vectors count:"
curl -s http://localhost:9200/sanctions_vectors/_count | jq '.count'
EOF
```

## 🔍 View Logs

```bash
ssh root@95.217.84.234 'docker logs ai-service-prod --tail 50'
```

## 🆘 If Something Goes Wrong

```bash
# Restart service
ssh root@95.217.84.234 'cd /opt/ai-service && docker-compose -f docker-compose.prod.yml restart ai-service'

# Full rebuild
ssh root@95.217.84.234 'cd /opt/ai-service && docker-compose -f docker-compose.prod.yml down && docker system prune -f && docker-compose -f docker-compose.prod.yml up -d'

# Manual ES data loading
ssh root@95.217.84.234 'docker exec -it ai-service-prod python scripts/full_deployment_pipeline.py --es-host elasticsearch:9200'
```

## ✅ Expected Results

**Indices:**
- `sanctions_ac_patterns`: 2,768,827 documents
- `sanctions_vectors`: 10,000 documents

**API Response:**
```json
{
  "decision": {
    "risk_level": "high",
    "sanctioned": true
  }
}
```

---

**Server:** root@95.217.84.234
**Path:** /opt/ai-service
**Port:** 8000
