# 🔍 Search Deployment Guide for Production

## Overview

This guide will enable search functionality in the AI Service production environment. The search layer has been integrated into the UnifiedOrchestrator and will provide similarity search results for normalized names.

## ✅ Prerequisites

1. **Elasticsearch 8.11.0** is already running on production server (confirmed)
2. **Production server access** with Docker and git
3. **Backup** of current configuration

## 🛠️ Deployment Steps

### Step 1: Connect to Production Server

```bash
ssh your-production-server
cd /path/to/ai-service
```

### Step 2: Backup Current State

```bash
# Backup current environment
cp env.production env.production.backup.$(date +%Y%m%d_%H%M%S)

# Backup current docker setup
docker-compose -f docker-compose.prod.yml ps > docker-state.backup.$(date +%Y%m%d_%H%M%S)
```

### Step 3: Pull Latest Code

```bash
git pull origin main
```

### Step 4: Run Automated Deployment

```bash
# Run the deployment script
./scripts/deploy_search_production.sh
```

**OR Manual Steps:**

### Step 4a: Update Environment Configuration

```bash
# Copy search-enabled configuration
cp env.production.search env.production
```

### Step 4b: Setup Elasticsearch

```bash
# Run Elasticsearch setup
cd scripts
python3 setup_elasticsearch.py
cd ..
```

### Step 4c: Rebuild and Restart Service

```bash
# Stop current service
docker-compose -f docker-compose.prod.yml down ai-service

# Rebuild with latest code
docker-compose -f docker-compose.prod.yml build --no-cache ai-service

# Start with search enabled
docker-compose -f docker-compose.prod.yml up -d ai-service
```

## 🧪 Verification

### 1. Health Check

```bash
curl http://localhost:8000/health
```

### 2. Test Search Integration

```bash
# Test basic processing with search
curl -X POST http://localhost:8000/process \
  -H "Content-Type: application/json" \
  -d '{"text": "Порошенко Петр", "generate_variants": false}'
```

**Expected Response Structure:**
```json
{
  "normalized_text": "Порошенко Петр",
  "tokens": ["Порошенко", "Петр"],
  "language": "uk",
  "success": true,
  "search_results": {
    "query": "Порошенко Петр",
    "results": [],
    "total_hits": 0,
    "search_type": "similarity_mock",
    "warnings": ["Similarity search not available - using mock"]
  },
  "processing_time": 0.05
}
```

### 3. Check Elasticsearch

```bash
# Verify ES health
curl http://localhost:9200/_cluster/health

# Check watchlist index
curl http://localhost:9200/watchlist/_search?size=0
```

## 📊 What Changes

### ✅ New Features

1. **Search Layer Added**: Layer 9 in processing pipeline
2. **search_results Field**: New field in API responses
3. **Elasticsearch Integration**: Connection to existing ES cluster
4. **Mock Fallback**: Graceful degradation when ES unavailable

### ⚙️ Configuration Changes

**New Environment Variables:**
```bash
ENABLE_SEARCH=true
ES_HOSTS=localhost:9200
ENABLE_HYBRID_SEARCH=true
ENABLE_FALLBACK=true
```

### 🔄 API Response Changes

**Before:**
```json
{
  "normalized_text": "...",
  "tokens": [...],
  "language": "...",
  "signals": {...},
  "decision": {...}
}
```

**After:**
```json
{
  "normalized_text": "...",
  "tokens": [...],
  "language": "...",
  "search_results": {
    "query": "...",
    "results": [...],
    "total_hits": 0
  },
  "signals": {...},
  "decision": {...}
}
```

## 🚨 Troubleshooting

### Common Issues

1. **Elasticsearch Connection Failed**
   ```bash
   # Check ES status
   curl http://localhost:9200

   # Check ES logs
   docker logs elasticsearch-container
   ```

2. **Search Results Always Empty**
   ```bash
   # Check watchlist index
   curl http://localhost:9200/watchlist/_count

   # Add test data
   python3 scripts/setup_elasticsearch.py
   ```

3. **Service Won't Start**
   ```bash
   # Check service logs
   docker logs ai-service-prod

   # Check dependency issues
   docker-compose -f docker-compose.prod.yml logs ai-service
   ```

### Recovery Steps

**Rollback to Previous Version:**
```bash
# Stop current service
docker-compose -f docker-compose.prod.yml down ai-service

# Restore previous configuration
cp env.production.backup.YYYYMMDD_HHMMSS env.production

# Restart with old config
docker-compose -f docker-compose.prod.yml up -d ai-service
```

## 📈 Monitoring

### Key Metrics

1. **Search Performance**
   ```bash
   # Check search response times
   curl -w "@curl-format.txt" http://localhost:8000/process -d '{"text":"test"}'
   ```

2. **Elasticsearch Health**
   ```bash
   # Monitor cluster health
   watch curl -s http://localhost:9200/_cluster/health
   ```

3. **Service Logs**
   ```bash
   # Monitor search layer activity
   docker logs -f ai-service-prod | grep -i search
   ```

## 🎯 Expected Results

After successful deployment:

- ✅ **search_results** field appears in all `/process` responses
- ✅ Search warnings indicate mock service is working
- ✅ Empty results for unknown names (expected)
- ✅ Performance remains similar (search adds ~1-5ms)
- ✅ All existing functionality unchanged

## 📞 Support

If issues occur:

1. **Check service logs**: `docker logs ai-service-prod`
2. **Check ES health**: `curl http://localhost:9200/_cluster/health`
3. **Verify config**: `cat env.production | grep -i search`
4. **Test locally**: Run same queries against staging/development

The search functionality provides foundation for future watchlist integration and similarity matching capabilities.