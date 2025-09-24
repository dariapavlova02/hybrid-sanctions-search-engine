# AI Service Production Deployment Guide

## 🎯 Quick Start

```bash
# 1. Deploy to production
./deploy_production.sh

# 2. Check status
./deploy_production.sh status

# 3. Test search escalation
curl -X POST http://localhost:8000/api/v1/process \
     -H "Content-Type: application/json" \
     -d '{"text": "Порошенк Петро", "language": "uk", "enable_search": true}'
```

## 🔧 Configuration Overview

### Critical Search Settings (Fixed Issues)

| Setting | Value | Purpose |
|---------|-------|---------|
| `ENABLE_SEARCH` | `true` | **🔥 Fixes main issue - search was disabled** |
| `SEARCH_ESCALATION_THRESHOLD` | `0.6` | Lower threshold for better escalation (was 0.8) |
| `VECTOR_SEARCH_THRESHOLD` | `0.3` | Allows fuzzy matching for typos |
| `ENABLE_VECTOR_FALLBACK` | `true` | Enables AC→Vector escalation |

### Search Escalation Logic

```
Query: "Порошенк Петро" (typo in surname)
  ↓
1. AC Search: [] (empty - no exact matches)
2. Escalation Check: if not ac_candidates → TRUE ✅
3. Vector Search: fuzzy matching finds "Порошенко Петро"
4. Result: 1 candidate with score ~0.45
```

## 📁 Key Files

### Environment Configuration
- **`.env.production`** - Production environment variables
- **`.env.secrets`** - Generated secrets (created by deploy script)

### Docker Configuration
- **`docker-compose.prod.yml`** - Production Docker setup
- **`nginx.conf`** - Nginx reverse proxy with rate limiting
- **`deploy_production.sh`** - Automated deployment script

### Search Data
- **`src/ai_service/data/sanctioned_persons.json`** - 145K+ sanctions records
- **`src/ai_service/data/sanctioned_companies.json`** - Company records

## 🚀 Deployment Process

### 1. Automated Deployment
```bash
./deploy_production.sh
```

**What it does:**
- ✅ Checks requirements (Docker, files)
- ✅ Sets up directories and permissions
- ✅ Generates secrets
- ✅ Builds and starts containers
- ✅ Health checks all services
- ✅ Verifies search configuration
- ✅ Tests search escalation

### 2. Manual Deployment
```bash
# Start Elasticsearch first
docker-compose -f docker-compose.prod.yml up -d elasticsearch

# Wait for ES to be ready
curl http://localhost:9200/_cluster/health

# Start AI Service
docker-compose -f docker-compose.prod.yml up -d ai-service

# Optional: Start Nginx
docker-compose -f docker-compose.prod.yml up -d nginx
```

## 🔍 Search Escalation Verification

### Test Cases

```bash
# 1. Exact match (should work in AC mode)
curl -X POST http://localhost:8000/api/v1/process \
     -H "Content-Type: application/json" \
     -d '{"text": "Порошенко Петро Олексійович", "enable_search": true}'

# 2. Typo (should escalate to vector search)
curl -X POST http://localhost:8000/api/v1/process \
     -H "Content-Type: application/json" \
     -d '{"text": "Порошенк Петро", "enable_search": true}'

# 3. Different typo
curl -X POST http://localhost:8000/api/v1/process \
     -H "Content-Type: application/json" \
     -d '{"text": "Парошенко Петро", "enable_search": true}'
```

### Expected Results

| Query | AC Results | Escalation | Vector Results | Total Hits |
|-------|------------|------------|----------------|------------|
| "Порошенко Петро" | 1 | No | - | 1 |
| "Порошенк Петро" | 0 | **Yes** ✅ | 1 (score ~0.45) | 1 |
| "Парошенко Петро" | 0 | **Yes** ✅ | 0 (no fuzzy match) | 0 |

## 📊 Monitoring & Health Checks

### Service Health
```bash
# Quick health check
curl http://localhost:8000/health

# Detailed status
./deploy_production.sh status

# View logs
./deploy_production.sh logs ai-service
```

### Elasticsearch Health
```bash
# Cluster health
curl http://localhost:9200/_cluster/health

# Index status
curl http://localhost:9200/_cat/indices?v
```

### Search Performance
```bash
# Test search endpoint
curl -X POST http://localhost:8000/api/v1/search \
     -H "Content-Type: application/json" \
     -d '{"query": "Порошенк", "mode": "hybrid"}'
```

## 🔧 Management Commands

### Service Management
```bash
./deploy_production.sh deploy    # Full deployment
./deploy_production.sh stop      # Stop all services
./deploy_production.sh restart   # Restart services
./deploy_production.sh status    # Show container status
./deploy_production.sh health    # Quick health check
./deploy_production.sh logs      # Show logs
```

### Docker Compose Commands
```bash
# Scale AI service
docker-compose -f docker-compose.prod.yml up -d --scale ai-service=3

# Update single service
docker-compose -f docker-compose.prod.yml up -d --no-deps ai-service

# View resource usage
docker stats
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Search Returns Empty Results
**Problem:** `"total_hits": 0` even for known names

**Solution:**
```bash
# Check if search is enabled
docker-compose -f docker-compose.prod.yml exec ai-service printenv | grep ENABLE_SEARCH

# Should show: ENABLE_SEARCH=true
```

#### 2. No Vector Escalation
**Problem:** Only AC search runs, no escalation to vector

**Check Configuration:**
```bash
docker-compose -f docker-compose.prod.yml exec ai-service python -c "
import os
print('SEARCH_ESCALATION_THRESHOLD:', os.getenv('SEARCH_ESCALATION_THRESHOLD'))
print('ENABLE_VECTOR_FALLBACK:', os.getenv('ENABLE_VECTOR_FALLBACK'))
"
```

#### 3. Elasticsearch Connection Issues
**Problem:** AI service can't connect to Elasticsearch

**Debug:**
```bash
# Check ES health
curl http://localhost:9200/_cluster/health

# Check network connectivity
docker-compose -f docker-compose.prod.yml exec ai-service curl http://elasticsearch:9200

# Check ES logs
docker-compose -f docker-compose.prod.yml logs elasticsearch
```

#### 4. High Memory Usage
**Problem:** Service consuming too much memory

**Monitor:**
```bash
docker stats

# Adjust memory limits in docker-compose.prod.yml
```

### Log Analysis
```bash
# Search-related logs
docker-compose -f docker-compose.prod.yml logs ai-service | grep -i search

# Escalation logs
docker-compose -f docker-compose.prod.yml logs ai-service | grep -i escalat

# Error logs
docker-compose -f docker-compose.prod.yml logs ai-service | grep -i error
```

## 🔐 Security Considerations

### Environment Variables
- ✅ Secrets stored in `.env.secrets` (not committed)
- ✅ Production settings in `.env.production`
- ✅ No hardcoded passwords

### Network Security
- ✅ Nginx rate limiting (10 req/s API, 5 req/s search)
- ✅ Internal Docker network for service communication
- ✅ Optional SSL/TLS configuration

### Elasticsearch Security
- ⚠️ Currently disabled for simplicity (`xpack.security.enabled=false`)
- 🔧 Enable in production: Set `ENABLE_ELASTICSEARCH_AUTH=true`

## 📈 Performance Tuning

### Scaling
```bash
# Scale AI service horizontally
docker-compose -f docker-compose.prod.yml up -d --scale ai-service=3

# Add load balancer in nginx.conf
```

### Caching
- ✅ Morphology caching enabled (50K entries)
- ✅ Search result caching (30 min TTL)
- ✅ Normalization caching enabled

### Resource Limits
```yaml
# Current limits in docker-compose.prod.yml
ai-service:
  deploy:
    resources:
      limits:
        memory: 4G      # Adjust based on load
        cpus: '2.0'
      reservations:
        memory: 2G
        cpus: '1.0'
```

## 🎯 Success Metrics

### Deployment Success
- ✅ All containers healthy
- ✅ Search escalation working
- ✅ Response time < 1 second
- ✅ Health checks passing

### Search Quality
- ✅ Exact matches found via AC search
- ✅ Typos handled via vector escalation
- ✅ Fuzzy matching working
- ✅ No false positives in production

---

## 📞 Support

For issues with search escalation or deployment:

1. Check this troubleshooting guide
2. Review logs: `./deploy_production.sh logs`
3. Test search manually with curl commands above
4. Verify configuration with diagnostic commands

**Key Files to Check:**
- `.env.production` - Environment variables
- `docker-compose.prod.yml` - Container configuration
- Container logs for error details