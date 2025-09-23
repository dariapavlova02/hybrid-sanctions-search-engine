# 🚨 URGENT: Production Elasticsearch Down - AC Search Failing

## ❗ Current Status

**From Production Logs**:
```
Error in real AC search: ('Connection aborted.', ConnectionResetError(104, 'Connection reset by peer'))
Failed to create AC patterns index: Connection error caused by: ConnectionError(Connection error caused by: ServerDisconnectedError(Server disconnected))
Failed to connect to Elasticsearch: Connection error caused by: ConnectionError(Connection error caused by: ServerDisconnectedError(Server disconnected))
AC search failed
Vector search failed
```

**API Results**:
```json
{
  "search_results": {
    "query": "Порошенко Петро",
    "results": [],
    "total_hits": 0,  // ← SHOULD BE 2+
    "search_type": "hybrid",
    "processing_time_ms": 0
  }
}
```

## 🔍 Root Cause

**Elasticsearch is completely unreachable** from the AI service container:
- `curl http://95.217.84.234:9200/_cluster/health` → Connection error
- Both AC patterns and vector indices are inaccessible
- Service falls back to normalization-only mode

## 🚨 Impact

1. **❌ AC Search**: All pattern matching disabled → sanctions not detected
2. **❌ Vector Search**: Semantic search disabled → no similarity matching
3. **❌ Decision Engine**: Even with our fix, no search data to process

## 🔧 Immediate Actions Needed

### 1. **Check Elasticsearch Service**
```bash
# On production server (95.217.84.234)
docker ps | grep elasticsearch
systemctl status elasticsearch
```

### 2. **Restart Elasticsearch**
```bash
# If using Docker
docker-compose restart elasticsearch

# If using systemd
systemctl restart elasticsearch
systemctl enable elasticsearch
```

### 3. **Check Network/Firewall**
```bash
# Test connectivity from AI service container
docker exec ai-service curl -v http://95.217.84.234:9200/_cluster/health

# Check if ES is bound to localhost only
netstat -tulpn | grep 9200
```

### 4. **Verify Index Status After ES Restart**
```bash
curl http://95.217.84.234:9200/_cat/indices?v
curl http://95.217.84.234:9200/ai_service_ac_patterns/_count
```

## 📋 Expected Results After Fix

1. **Elasticsearch Health**: `curl http://95.217.84.234:9200/_cluster/health` returns `{"status":"green"}`
2. **AC Patterns Count**: `~942,282` patterns in index
3. **AI Service Search**: `"total_hits": 2+` for "Петро Порошенко"
4. **Decision Engine**: Risk scoring includes search contribution

## 🔄 Next Steps

1. **Fix Elasticsearch** (immediate priority)
2. **Deploy decision engine fix** (commit `51e80c4`)
3. **Test complete pipeline** AC + Decision → "high risk"

## ⚠️ Critical Note

**Even our decision engine fix won't work until Elasticsearch is restored** because there will be no search results to contribute to the risk score.

**Both issues must be resolved**:
1. **Infrastructure**: Elasticsearch connectivity
2. **Code**: Decision engine missing search parameter

Priority: **Elasticsearch first**, then decision engine deployment.