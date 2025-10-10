# Hybrid Search Runbook

## Overview

This runbook provides step-by-step instructions for SRE and developers to manage the hybrid search system. The system combines Aho-Corasick (AC) lexical search with kNN vector search for optimal performance and accuracy.

## Table of Contents

1. [Local Development Setup](#local-development-setup)
2. [Corpus Loading](#corpus-loading)
3. [Testing AC/Vector Search](#testing-acvector-search)
4. [Metrics Monitoring](#metrics-monitoring)
5. [Troubleshooting](#troubleshooting)
6. [Emergency Procedures](#emergency-procedures)

---

## Local Development Setup

### Prerequisites

- Docker and Docker Compose
- Python 3.10+
- Git

### 1. Start Elasticsearch and Monitoring Stack

```bash
# Start the complete monitoring stack with Elasticsearch
cd /path/to/ai-service
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Verify services are running
docker-compose -f monitoring/docker-compose.monitoring.yml ps
```

**Expected Output:**
```
Name                     Command               State           Ports
-------------------------------------------------------------------------------
search-elasticsearch     /usr/local/bin/docke ...   Up      0.0.0.0:9200->9200/tcp
search-grafana          /run.sh                 Up      0.0.0.0:3000->3000/tcp
search-prometheus       /bin/prometheus --con ...   Up      0.0.0.0:9090->9090/tcp
search-alertmanager     /bin/alertmanager --c ...   Up      0.0.0.0:9093->9093/tcp
```

### 2. Verify Elasticsearch Health

```bash
# Check cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check indices
curl -X GET "localhost:9200/_cat/indices?v"
```

**Expected Output:**
```json
{
  "cluster_name" : "docker-cluster",
  "status" : "green",
  "timed_out" : false,
  "number_of_nodes" : 1,
  "number_of_data_nodes" : 1,
  "active_primary_shards" : 0,
  "active_shards" : 0,
  "relocating_shards" : 0,
  "initializing_shards" : 0,
  "unassigned_shards" : 0,
  "delayed_unassigned_shards" : 0,
  "number_of_pending_tasks" : 0,
  "number_of_in_flight_fetch" : 0,
  "task_max_waiting_in_queue_millis" : 0,
  "active_shards_percent_as_number" : 100.0
}
```

### 3. Apply Elasticsearch Templates

```bash
# Apply component template
curl -X PUT "localhost:9200/_component_template/search_analyzers" \
  -H "Content-Type: application/json" \
  -d @templates/elasticsearch/component_template.json

# Apply index templates
curl -X PUT "localhost:9200/_index_template/persons_template" \
  -H "Content-Type: application/json" \
  -d @templates/elasticsearch/persons_template.json

curl -X PUT "localhost:9200/_index_template/orgs_template" \
  -H "Content-Type: application/json" \
  -d @templates/elasticsearch/orgs_template.json

# Verify templates
curl -X GET "localhost:9200/_index_template/persons_template?pretty"
curl -X GET "localhost:9200/_index_template/orgs_template?pretty"
```

### 4. Create Initial Indices

```bash
# Create persons index
curl -X PUT "localhost:9200/watchlist_persons_v1_001" \
  -H "Content-Type: application/json" \
  -d '{
    "aliases": {
      "watchlist_persons_current": {}
    }
  }'

# Create orgs index
curl -X PUT "localhost:9200/watchlist_orgs_v1_001" \
  -H "Content-Type: application/json" \
  -d '{
    "aliases": {
      "watchlist_orgs_current": {}
    }
  }'

# Verify indices
curl -X GET "localhost:9200/_cat/indices?v"
```

---

## Corpus Loading

### 1. Prepare Sample Data

```bash
# Create sample entities file
cat > sample_entities.jsonl << EOF
{"entity_id": "person_001", "entity_type": "person", "normalized_name": "иван петров", "aliases": ["и. петров"], "country": "RU", "dob": "1980-05-15", "meta": {"source": "sanctions"}}
{"entity_id": "person_002", "entity_type": "person", "normalized_name": "мария сидорова", "aliases": ["м. сидорова"], "country": "RU", "dob": "1975-12-03", "meta": {"source": "sanctions"}}
{"entity_id": "org_001", "entity_type": "org", "normalized_name": "ооо газпром", "aliases": ["газпром", "gazprom"], "country": "RU", "meta": {"source": "sanctions"}}
{"entity_id": "org_002", "entity_type": "org", "normalized_name": "тнк-bp", "aliases": ["tnk-bp"], "country": "RU", "meta": {"source": "sanctions"}}
EOF
```

### 2. Load Data Using Bulk Loader

```bash
# Install dependencies
pip install httpx pyyaml pydantic

# Load persons
python scripts/bulk_loader.py \
  --input sample_entities.jsonl \
  --entity-type person \
  --upsert \
  --batch-size 100 \
  --flush-interval 0.5

# Load organizations
python scripts/bulk_loader.py \
  --input sample_entities.jsonl \
  --entity-type org \
  --upsert \
  --batch-size 100 \
  --flush-interval 0.5
```

**Expected Output:**
```
2024-01-15 10:30:15 [BULK-LOADER] [INFO] Loading entities from sample_entities.jsonl
2024-01-15 10:30:15 [BULK-LOADER] [INFO] Loaded 4 entities from sample_entities.jsonl
2024-01-15 10:30:15 [BULK-LOADER] [INFO] Generating embeddings for 4 entities
2024-01-15 10:30:16 [BULK-LOADER] [INFO] Embedding generation completed. P95 latency: 0.012s
2024-01-15 10:30:16 [BULK-LOADER] [INFO] Starting bulk upsert of 2 person entities to watchlist_persons_current
2024-01-15 10:30:16 [BULK-LOADER] [INFO] Successfully upserted batch 1 (2 entities)
2024-01-15 10:30:16 [BULK-LOADER] [INFO] Bulk upsert completed. Success rate: 100.0%

============================================================
BULK LOADER METRICS
============================================================
Total processed: 2
Successful upserts: 2
Failed upserts: 0
Success rate: 100.0%
Throughput: 50.0 records/sec
Embeddings generated: 2
Embedding cache hits: 0
Cache hit rate: 0.0%
Embedding P95 latency: 0.012s
Bulk operations: 1
Bulk errors: 0
============================================================

✅ Successfully loaded 2 person entities
```

### 3. Verify Data Loading

```bash
# Check document count
curl -X GET "localhost:9200/watchlist_persons_current/_count?pretty"
curl -X GET "localhost:9200/watchlist_orgs_current/_count?pretty"

# Check sample documents
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty&size=2"
```

---

## Testing AC/Vector Search

### 1. Test AC Search (Exact Match)

```bash
# Test exact match for persons
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"terms": {"normalized_name": ["иван петров"]}}
        ]
      }
    },
    "size": 10
  }'
```

**Expected Output:**
```json
{
  "took" : 2,
  "timed_out" : false,
  "_shards" : {
    "total" : 1,
    "successful" : 1,
    "skipped" : 0,
    "failed" : 0
  },
  "hits" : {
    "total" : {
      "value" : 1,
      "relation" : "eq"
    },
    "max_score" : 2.0,
    "hits" : [
      {
        "_index" : "watchlist_persons_v1_001",
        "_type" : "_doc",
        "_id" : "person_001",
        "_score" : 2.0,
        "_source" : {
          "entity_id" : "person_001",
          "entity_type" : "person",
          "normalized_name" : "иван петров",
          "aliases" : ["и. петров"],
          "country" : "RU",
          "dob" : "1980-05-15",
          "meta" : {"source" : "sanctions"}
        }
      }
    ]
  }
}
```

### 2. Test AC Search (Phrase Match)

```bash
# Test phrase match with shingles
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"match_phrase": {
            "name_text.shingle": {
              "query": "иван петров",
              "slop": 1
            }
          }}
        ]
      }
    },
    "size": 10
  }'
```

### 3. Test AC Search (Ngram Match)

```bash
# Test ngram match
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"match": {
            "name_ngrams": {
              "query": "иван петров",
              "operator": "AND",
              "minimum_should_match": "100%"
            }
          }}
        ]
      }
    },
    "size": 10
  }'
```

### 4. Test Vector Search (kNN)

```bash
# Test kNN search (requires name_vector field)
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "knn": {
      "field": "name_vector",
      "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5],
      "k": 10,
      "num_candidates": 20,
      "similarity": "cosine"
    },
    "size": 10
  }'
```

### 5. Test Multi-Search (AC + Vector)

```bash
# Test multi-search combining AC and Vector
curl -X POST "localhost:9200/_msearch?pretty" \
  -H "Content-Type: application/x-ndjson" \
  --data-binary @- << EOF
{"index": "watchlist_persons_current"}
{"query": {"bool": {"must": [{"term": {"entity_type": "person"}}, {"terms": {"normalized_name": ["иван петров"]}}]}}, "size": 10}
{"index": "watchlist_persons_current"}
{"knn": {"field": "name_vector", "query_vector": [0.1, 0.2, 0.3, 0.4, 0.5], "k": 10, "similarity": "cosine"}}, "size": 10}
EOF
```

### 6. Test Search Thresholds

```bash
# Test with different score thresholds
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"match": {
            "name_ngrams": {
              "query": "иван",
              "operator": "AND",
              "minimum_should_match": "100%"
            }
          }}
        ]
      }
    },
    "min_score": 0.6,
    "size": 10
  }'
```

---

## Metrics Monitoring

### 1. Access Monitoring Dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Alertmanager**: http://localhost:9093

### 2. Key Metrics to Monitor

#### Search Performance Metrics
```bash
# Search request rate by mode
curl -X GET "localhost:9090/api/v1/query?query=rate(hybrid_search_requests_total[5m])"

# Search latency percentiles
curl -X GET "localhost:9090/api/v1/query?query=histogram_quantile(0.95, rate(hybrid_search_latency_ms_bucket[5m]))"

# Search success rate
curl -X GET "localhost:9090/api/v1/query?query=rate(hybrid_search_requests_total{status=\"success\"}[5m]) / rate(hybrid_search_requests_total[5m])"
```

#### AC Search Metrics
```bash
# AC hits by type
curl -X GET "localhost:9090/api/v1/query?query=rate(ac_hits_total[5m])"

# AC weak hits
curl -X GET "localhost:9090/api/v1/query?query=rate(ac_weak_hits_total[5m])"
```

#### Vector Search Metrics
```bash
# Vector search hits
curl -X GET "localhost:9090/api/v1/query?query=rate(knn_hits_total[5m])"

# Fusion consensus
curl -X GET "localhost:9090/api/v1/query?query=rate(fusion_consensus_total[5m])"
```

#### Elasticsearch Health Metrics
```bash
# ES connection errors
curl -X GET "localhost:9090/api/v1/query?query=rate(es_errors_total{type=\"conn\"}[5m])"

# ES timeout errors
curl -X GET "localhost:9090/api/v1/query?query=rate(es_errors_total{type=\"timeout\"}[5m])"
```

### 3. Threshold Escalation Procedures

#### High Latency (P95 > 120ms for 5 minutes)
```bash
# 1. Check ES cluster health
curl -X GET "localhost:9200/_cluster/health?pretty"

# 2. Check ES node stats
curl -X GET "localhost:9200/_nodes/stats?pretty"

# 3. Check active connections
curl -X GET "localhost:9090/api/v1/query?query=active_search_connections

# 4. If needed, disable kNN search temporarily
export DISABLE_VECTOR_SEARCH=true
# Restart search service
```

#### High Error Rate (> 2% for 3 minutes)
```bash
# 1. Check ES error logs
docker logs search-elasticsearch --tail 100

# 2. Check search service logs
docker logs search-service --tail 100

# 3. Check ES cluster status
curl -X GET "localhost:9200/_cluster/health?pretty"

# 4. If needed, fallback to local index
export ELASTICSEARCH_FALLBACK=true
# Restart search service
```

#### Low Hit Rate (< 0.01 hits/sec for 15 minutes)
```bash
# 1. Check if data is loaded
curl -X GET "localhost:9200/watchlist_persons_current/_count?pretty"
curl -X GET "localhost:9200/watchlist_orgs_current/_count?pretty"

# 2. Test search manually
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}, "size": 1}'

# 3. Check index mappings
curl -X GET "localhost:9200/watchlist_persons_current/_mapping?pretty"

# 4. Rebuild indices if needed
python scripts/bulk_loader.py --rebuild-alias --entity-type person
```

---

## Troubleshooting

### Common Errors and Quick Fixes

#### 1. Mapping Conflicts

**Error:**
```json
{
  "error": {
    "type": "mapper_parsing_exception",
    "reason": "failed to parse field [name_vector] of type [dense_vector]"
  }
}
```

**Fix:**
```bash
# Delete and recreate index with correct mapping
curl -X DELETE "localhost:9200/watchlist_persons_v1_001"
curl -X PUT "localhost:9200/watchlist_persons_v1_001" \
  -H "Content-Type: application/json" \
  -d @templates/elasticsearch/persons_template.json

# Rebuild alias
curl -X POST "localhost:9200/_aliases" \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {"add": {"index": "watchlist_persons_v1_001", "alias": "watchlist_persons_current"}}
    ]
  }'
```

#### 2. Vector Dimension Mismatch

**Error:**
```json
{
  "error": {
    "type": "illegal_argument_exception",
    "reason": "Query vector has invalid dimension: 384. Dimension should be 128"
  }
}
```

**Fix:**
```bash
# Check current mapping
curl -X GET "localhost:9200/watchlist_persons_current/_mapping?pretty"

# Update mapping to correct dimension
curl -X PUT "localhost:9200/watchlist_persons_current/_mapping" \
  -H "Content-Type: application/json" \
  -d '{
    "properties": {
      "name_vector": {
        "type": "dense_vector",
        "dims": 384
      }
    }
  }'
```

#### 3. Elasticsearch Connection Errors

**Error:**
```
ConnectionError: Failed to establish connection to Elasticsearch
```

**Fix:**
```bash
# 1. Check ES container status
docker ps | grep elasticsearch

# 2. Check ES logs
docker logs search-elasticsearch --tail 50

# 3. Restart ES container
docker restart search-elasticsearch

# 4. Wait for ES to be ready
while ! curl -s localhost:9200/_cluster/health > /dev/null; do
  echo "Waiting for Elasticsearch..."
  sleep 5
done

# 5. Verify health
curl -X GET "localhost:9200/_cluster/health?pretty"
```

#### 4. Index Not Found

**Error:**
```json
{
  "error": {
    "type": "index_not_found_exception",
    "reason": "no such index [watchlist_persons_current]"
  }
}
```

**Fix:**
```bash
# 1. Check available indices
curl -X GET "localhost:9200/_cat/indices?v"

# 2. Create index if missing
curl -X PUT "localhost:9200/watchlist_persons_v1_001" \
  -H "Content-Type: application/json" \
  -d '{
    "aliases": {
      "watchlist_persons_current": {}
    }
  }'

# 3. Load data
python scripts/bulk_loader.py --input sample_entities.jsonl --entity-type person --upsert
```

#### 5. Low Memory Errors

**Error:**
```json
{
  "error": {
    "type": "circuit_breaker_exception",
    "reason": "Parent circuit breaker is open"
  }
}
```

**Fix:**
```bash
# 1. Check ES memory usage
curl -X GET "localhost:9200/_nodes/stats/jvm?pretty"

# 2. Increase ES heap size
docker-compose -f monitoring/docker-compose.monitoring.yml down
# Edit docker-compose.monitoring.yml:
# environment:
#   - ES_JAVA_OPTS=-Xms2g -Xmx2g
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# 3. Clear ES caches
curl -X POST "localhost:9200/_cache/clear?pretty"
```

#### 6. Search Timeout Errors

**Error:**
```json
{
  "error": {
    "type": "search_timeout_exception",
    "reason": "Search request timed out"
  }
}
```

**Fix:**
```bash
# 1. Increase search timeout
curl -X GET "localhost:9200/watchlist_persons_current/_search?timeout=30s&pretty" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}, "size": 10}'

# 2. Check ES cluster load
curl -X GET "localhost:9200/_cluster/health?pretty"

# 3. Reduce search complexity
# Use smaller k values for kNN
# Use more specific filters
# Reduce batch sizes
```

### Performance Optimization

#### 1. Index Optimization
```bash
# Force merge indices for better performance
curl -X POST "localhost:9200/watchlist_persons_current/_forcemerge?max_num_segments=1"

# Refresh indices
curl -X POST "localhost:9200/watchlist_persons_current/_refresh"

# Check index stats
curl -X GET "localhost:9200/watchlist_persons_current/_stats?pretty"
```

#### 2. Query Optimization
```bash
# Use explain API to analyze slow queries
curl -X GET "localhost:9200/watchlist_persons_current/_search?explain=true&pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "query": {
      "bool": {
        "must": [
          {"term": {"entity_type": "person"}},
          {"match": {"name_ngrams": "иван петров"}}
        ]
      }
    }
  }'
```

#### 3. Monitoring Optimization
```bash
# Check slow query log
curl -X GET "localhost:9200/_nodes/stats/indices/search?pretty"

# Check thread pool stats
curl -X GET "localhost:9200/_nodes/stats/thread_pool?pretty"
```

---

## Emergency Procedures

### 1. Complete System Restart

```bash
# Stop all services
docker-compose -f monitoring/docker-compose.monitoring.yml down

# Clean up volumes (CAUTION: This will delete all data)
docker volume prune -f

# Restart services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Wait for services to be ready
sleep 30

# Reapply templates and load data
# (Follow steps from "Local Development Setup" section)
```

### 2. Fallback to Local Index

```bash
# Disable Elasticsearch search
export ELASTICSEARCH_ENABLED=false

# Restart search service
docker restart search-service

# Verify fallback is working
curl -X GET "localhost:8080/health"
```

### 3. Data Recovery

```bash
# Check for snapshots
curl -X GET "localhost:9200/_snapshot?pretty"

# Restore from snapshot if available
curl -X POST "localhost:9200/_snapshot/backup_repo/snapshot_1/_restore?pretty" \
  -H "Content-Type: application/json" \
  -d '{
    "indices": "watchlist_*",
    "ignore_unavailable": true,
    "include_global_state": false
  }'
```

### 4. Emergency Rollback

```bash
# Rollback to previous index version
curl -X POST "localhost:9200/_aliases" \
  -H "Content-Type: application/json" \
  -d '{
    "actions": [
      {"remove": {"index": "watchlist_persons_v1_002", "alias": "watchlist_persons_current"}},
      {"add": {"index": "watchlist_persons_v1_001", "alias": "watchlist_persons_current"}}
    ]
  }'
```

---

## Quick Reference

### Essential Commands

```bash
# Check system health
curl -X GET "localhost:9200/_cluster/health?pretty"

# Check indices
curl -X GET "localhost:9200/_cat/indices?v"

# Check templates
curl -X GET "localhost:9200/_index_template?pretty"

# Test search
curl -X GET "localhost:9200/watchlist_persons_current/_search?pretty" \
  -H "Content-Type: application/json" \
  -d '{"query": {"match_all": {}}, "size": 1}'

# Check metrics
curl -X GET "localhost:9090/api/v1/query?query=up
```

### Environment Variables

```bash
# Elasticsearch configuration
export ES_URL="http://localhost:9200"
export ES_USER=""
export ES_PASS=""
export ES_VERIFY_SSL="false"
export ES_TIMEOUT="30"

# Search configuration
export DISABLE_VECTOR_SEARCH="false"
export ELASTICSEARCH_FALLBACK="false"
export ELASTICSEARCH_ENABLED="true"

# Monitoring configuration
export PROMETHEUS_ENABLED="true"
export PROMETHEUS_PORT="8080"
```

### Log Locations

```bash
# Elasticsearch logs
docker logs search-elasticsearch

# Search service logs
docker logs search-service

# Prometheus logs
docker logs search-prometheus

# Grafana logs
docker logs search-grafana
```

