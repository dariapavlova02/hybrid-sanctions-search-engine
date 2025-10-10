# Production Deployment - Complete Guide

## 🎯 Quick Start (Copy & Paste)

### Full Deployment (Recommended)

```bash
ssh root@95.217.84.234 << 'EOF'
cd /opt/ai-service
git pull origin main
cp .env.production .env
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
echo ""
echo "=== Waiting for services to start ==="
sleep 20
echo ""
echo "=== Service Status ==="
docker ps | grep ai-service
echo ""
echo "=== Elasticsearch Indices ==="
curl -s http://localhost:9200/_cat/indices?v | grep sanctions
echo ""
echo "=== API Health Check ==="
curl -s http://localhost:8000/health | jq
echo ""
echo "=== Test Sanctioned INN ==="
curl -s -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "ИНН 2839403975"}' | jq '.decision.risk_level'
echo ""
echo "=== Deployment Complete ==="
EOF
```

### Expected Output:
```
✓ Service: ai-service-prod running
✓ Elasticsearch: sanctions_ac_patterns (2,768,827 docs)
✓ Elasticsearch: sanctions_vectors (10,000 docs)
✓ API Health: {"status": "healthy"}
✓ Sanctioned INN Test: "high"
```

---

## 🔍 Individual Commands

### 1. Deploy
```bash
ssh root@95.217.84.234 'cd /opt/ai-service && git pull origin main && cp .env.production .env && docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml build --no-cache && docker-compose -f docker-compose.prod.yml up -d'
```

### 2. Check Status
```bash
ssh root@95.217.84.234 'docker ps | grep ai-service'
```

### 3. View Logs
```bash
ssh root@95.217.84.234 'docker logs ai-service-prod --tail 50'
```

### 4. Check Elasticsearch
```bash
ssh root@95.217.84.234 'curl -s http://localhost:9200/_cat/indices?v | grep sanctions'
```

### 5. Test API
```bash
ssh root@95.217.84.234 'curl -s http://localhost:8000/health | jq'
```

### 6. Test Sanctioned Data
```bash
ssh root@95.217.84.234 'curl -s -X POST http://localhost:8000/process -H "Content-Type: application/json" -d "{\"text\": \"ИНН 2839403975\"}" | jq ".decision.risk_level"'
```
Expected: `"high"`

---

## 🆘 Emergency Commands

### Restart Service
```bash
ssh root@95.217.84.234 'cd /opt/ai-service && docker-compose -f docker-compose.prod.yml restart ai-service'
```

### Full Rebuild
```bash
ssh root@95.217.84.234 'cd /opt/ai-service && docker-compose -f docker-compose.prod.yml down && docker system prune -f && docker-compose -f docker-compose.prod.yml build --no-cache && docker-compose -f docker-compose.prod.yml up -d'
```

### Manual Elasticsearch Data Load
```bash
ssh root@95.217.84.234 'docker exec -it ai-service-prod python scripts/full_deployment_pipeline.py --es-host elasticsearch:9200'
```

### Rollback to Previous Version
```bash
ssh root@95.217.84.234 'cd /opt/ai-service && git log --oneline -5'
# Copy desired commit hash, then:
ssh root@95.217.84.234 'cd /opt/ai-service && git checkout <COMMIT_HASH> && cp .env.production .env && docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml build --no-cache && docker-compose -f docker-compose.prod.yml up -d'
```

---

## 📋 Production Server Details

| Parameter | Value |
|-----------|-------|
| **Host** | 95.217.84.234 |
| **User** | root |
| **Path** | /opt/ai-service |
| **Compose File** | docker-compose.prod.yml |
| **Container** | ai-service-prod |
| **Dockerfile** | Dockerfile.prod |
| **Environment** | .env.production → .env |
| **API Port** | 8000 |
| **ES Host** | elasticsearch:9200 (internal) |

---

## 📊 What Happens During Deployment

1. ✅ Git pull latest code
2. ✅ Copy `.env.production` → `.env`
3. ✅ Stop running containers
4. ✅ Rebuild Docker images (no cache)
5. ✅ Start containers
6. ✅ **docker-entrypoint.sh** automatically:
   - Waits for Elasticsearch (up to 60s)
   - Checks if indices exist
   - If missing: loads AC patterns (2.7M) + vectors (10K)
   - Sets environment variables
   - Starts API service

**Total time:** ~2-3 minutes (or ~5 minutes if data needs loading)

---

## ✅ Verification Checklist

- [ ] Container `ai-service-prod` is running
- [ ] Elasticsearch index `sanctions_ac_patterns` has 2,768,827 docs
- [ ] Elasticsearch index `sanctions_vectors` has 10,000 docs
- [ ] API `/health` returns `{"status": "healthy"}`
- [ ] Test INN `2839403975` returns `risk_level: "high"`

---

## 📞 Support

If deployment fails:
1. Check logs: `docker logs ai-service-prod --tail 200`
2. Check ES health: `curl http://localhost:9200/_cluster/health`
3. Check data files exist: `ls -lh /opt/ai-service/output/sanctions/`

For detailed troubleshooting, see `PRODUCTION_DEPLOY_COMMANDS.md`
