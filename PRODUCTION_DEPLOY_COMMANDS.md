# Production Deployment Commands

## Quick Deploy (Copy-Paste Ready)

### Option 1: Full Deployment (Recommended)

```bash
# SSH to production server
ssh root@95.217.84.234

# Navigate to project directory
cd /opt/ai-service

# Pull latest changes
git pull origin main

# Copy production environment file
cp .env.production .env

# Stop current containers
docker-compose -f docker-compose.prod.yml down

# Rebuild images (no cache to ensure latest code)
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services (automatic ES initialization)
docker-compose -f docker-compose.prod.yml up -d

# Verify deployment
docker logs ai-service-prod --tail 50

# Check Elasticsearch indices
curl http://localhost:9200/_cat/indices?v | grep sanctions

# Test API
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Дарья ПАвлова ИНН 2839403975"}' | jq '.decision.risk_level'
# Expected: "high"
```

**Important:** Production uses `docker-compose.prod.yml`:
- Container name: `ai-service-prod` (not `ai-service`)
- Dockerfile: `Dockerfile.prod` (production optimized)
- Port: 8000 (external)
- Environment: `.env.production`

### Option 2: Quick Restart (No Code Changes)

```bash
cd /opt/ai-service
docker-compose -f docker-compose.prod.yml restart ai-service
docker logs ai-service-prod --tail 30
```

### Option 3: One-Line Remote Deploy

```bash
'cd /opt/ai-service && git pull origin main && cp .env.production .env && docker-compose -f docker-compose.prod.yml down && docker-compose -f docker-compose.prod.yml build --no-cache && docker-compose -f docker-compose.prod.yml up -d'
```

## Verification Commands

### Check Service Status
```bash
# Container status
docker ps | grep ai-service

# Service logs
docker logs ai-service-prod --tail 100

# Follow logs in real-time
docker logs -f ai-service-prod
```

### Check Elasticsearch
```bash
# Cluster health
curl http://localhost:9200/_cluster/health?pretty

# Indices status
curl http://localhost:9200/_cat/indices?v

# Expected indices:
# - sanctions_ac_patterns (2,768,827 docs)
# - sanctions_vectors (10,000 docs)

# Count documents
curl http://localhost:9200/sanctions_ac_patterns/_count
curl http://localhost:9200/sanctions_vectors/_count
```

### Test API Endpoints
```bash
# Health check
curl http://localhost:8000/health | jq

# Process test request
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Дарья ПАвлова ИНН 2839403975"}' | jq

# Search test
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Петров", "search_type": "hybrid"}' | jq
```

## Troubleshooting

### If Elasticsearch indices are empty:
```bash
# Manual data loading
docker exec -it ai-service-prod python scripts/full_deployment_pipeline.py \
  --es-host elasticsearch:9200
```

### If service won't start:
```bash
# Check logs for errors
docker logs ai-service-prod --tail 200

# Force clean rebuild
docker-compose -f docker-compose.prod.yml down
docker system prune -f
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

### If Elasticsearch is down:
```bash
# Check ES container
docker ps -a | grep elasticsearch

# Restart ES
docker-compose -f docker-compose.prod.yml restart elasticsearch

# Wait 30s, then check health
sleep 30
curl http://localhost:9200/_cluster/health
```

## Expected Output

### Docker logs should show:
```
==================================================
AI Service - Docker Entrypoint
==================================================

Configuration:
  Elasticsearch: elasticsearch:9200
  Index Prefix: sanctions
  Skip Init: false

Waiting for Elasticsearch to be ready...
[OK] Elasticsearch is ready
Checking indices...
  [OK] sanctions_ac_patterns: 2768827 documents
  [OK] sanctions_vectors: 10000 documents
[OK] Indices already exist with data

==================================================
Starting AI Service
==================================================
```

### API test should return:
```json
{
  "decision": {
    "risk_level": "high",
    "sanctioned": true,
    "inn_sanctioned": true
  }
}
```

## Rollback (If Needed)

```bash
# Go back to previous version
ssh root@95.217.84.234
cd /opt/ai-service
git log --oneline -5  # Find commit hash
git checkout <previous-commit-hash>
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml build --no-cache
docker-compose -f docker-compose.prod.yml up -d
```

## Production Server Info

- **Host:** 95.217.84.234
- **User:** root
- **Project Path:** /opt/ai-service
- **Docker Compose File:** `docker-compose.prod.yml` ⚠️ **Important!**
- **Container Name:** `ai-service-prod`
- **Dockerfile:** `Dockerfile.prod`
- **Elasticsearch:** elasticsearch:9200 (internal), localhost:9200 (on server)
- **API Port:** 8000
- **Environment File:** `.env.production`

## Data Files

Data files are automatically loaded by docker-entrypoint.sh:
- **Location:** `/opt/ai-service/output/sanctions/`
- **AC Patterns:** `ac_patterns_YYYYMMDD_HHMMSS.json` (~1.1GB)
- **Vectors:** `vectors_YYYYMMDD_HHMMSS.json` (~206MB)

If files are missing, prepare them locally and scp to server:
```bash
# On local machine
python scripts/prepare_sanctions_data.py
scp output/sanctions/ac_patterns_*.json root@95.217.84.234:/opt/ai-service/output/sanctions/
scp output/sanctions/vectors_*.json root@95.217.84.234:/opt/ai-service/output/sanctions/
```

## Monitoring

```bash
# Resource usage
docker stats ai-service-prod

# Disk space
df -h /opt/ai-service

# Memory usage
free -h

# CPU load
top -bn1 | head -20
```
