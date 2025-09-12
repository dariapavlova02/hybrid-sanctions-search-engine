# API Usage Examples

This document provides comprehensive examples of using the AI Service API for sanctions screening and text processing.

## 🚀 Getting Started

### Service Health Check
```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "AI Service", 
  "version": "1.0.0",
  "implementation": "legacy_orchestrator",
  "orchestrator": {
    "initialized": true,
    "processed_total": 0,
    "success_rate": 0,
    "cache_hit_rate": 0.0,
    "services": {
      "unicode": "active",
      "language": "active", 
      "normalization": "active",
      "variants": "active",
      "patterns": "active",
      "templates": "active",
      "embeddings": "active"
    }
  },
  "screening": true
}
```

## 📝 Text Processing Examples

### Basic Text Normalization
```bash
curl -X POST "http://localhost:8000/normalize" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Владимир Владимирович Путин",
    "language": "ru"
  }'
```

**Response:**
```json
{
  "original_text": "Владимир Владимирович Путин",
  "normalized_text": "владимир владимирович путин",
  "language": "ru",
  "processing_time": 0.045,
  "success": true
}
```

### Complete Text Processing with Variants
```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Александр Петрович Иванов",
    "generate_variants": true,
    "generate_embeddings": false,
    "cache_result": true
  }'
```

**Response:**
```json
{
  "success": true,
  "original_text": "Александр Петрович Иванов",
  "normalized_text": "александр петрович иванов",
  "language": "ru",
  "language_confidence": 0.7,
  "variants": [
    "aleksandr petrovich ivanov",
    "alexander petrovic ivanov", 
    "aleksander petrovych ivanov",
    "александр петрович іванов",
    "олександр петрович іванов",
    // ... more variants
  ],
  "processing_time": 0.286,
  "has_embeddings": false,
  "errors": null
}
```

### Batch Processing
```bash
curl -X POST "http://localhost:8000/process-batch" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "Иван Петрович Сидоров",
      "АО Роснефть", 
      "Volodymyr Zelenskyy"
    ],
    "generate_variants": true,
    "generate_embeddings": false,
    "max_concurrent": 3
  }'
```

**Response:**
```json
{
  "results": [
    {
      "success": true,
      "original_text": "Иван Петрович Сидоров",
      "normalized_text": "иван петрович сидоров",
      "language": "ru",
      "variants_count": 26,
      "processing_time": 0.561,
      "errors": null
    },
    // ... more results
  ],
  "total_texts": 3,
  "successful": 3,
  "total_processing_time": 1.234
}
```

## 🎯 Sanctions Screening Examples

### Basic Entity Screening
```bash
curl -X POST "http://localhost:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "text_purpose": "Владимир Владимирович Путин",
    "request_id": "screening_001",
    "metadata": {
      "entity_type": "person",
      "country": "RU",
      "source": "transaction"
    }
  }'
```

**Response:**
```json
{
  "decision": "REVIEW",
  "latency_ms": 1245.67,
  "snapshot": {"watchlist": "dev", "index": "dev"},
  "matches": [
    {
      "core_id": "AC_NAME_SIGNAL",
      "entity_type": "person|company",
      "score": 0.9,
      "thresholds": {
        "auto_hit": 0.86,
        "review": 0.74,
        "clear": 0.60
      },
      "evidence": {
        "name_observed": "Владимир Владимирович Путин",
        "name_canonical": "High-recall name/company signal",
        "features": {
          "cos_fastText": 0.0,
          "cos_tfidf": 0.0,
          "jaro": 0.0,
          "rule_boost": 0.0
        },
        "metadata_match": {}
      },
      "reason_codes": ["RC_EXACT", "RC_ALIAS"]
    }
  ],
  "tiers_executed": ["ac_exact", "blocking", "knn_vector", "reranking"],
  "early_stopped": true
}
```

### Company Screening
```bash
curl -X POST "http://localhost:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{
    "text_purpose": "ООО Газпром Экспорт",
    "request_id": "company_001", 
    "metadata": {
      "entity_type": "company",
      "country": "RU",
      "registration_number": "1234567890"
    }
  }'
```

### Screening Decision Explanation
```bash
curl -X POST "http://localhost:8000/explain" \
  -H "Content-Type: application/json" \
  -d '{
    "request_id": "screening_001"
  }'
```

**Response:**
```json
{
  "request": {
    "text_purpose": "Владимир Владимирович Путин",
    "request_id": "screening_001",
    "metadata": {"entity_type": "person", "country": "RU"}
  },
  "result": {
    "decision": "REVIEW",
    "matches": [/* match details */],
    "tiers_executed": ["ac_exact", "blocking", "knn_vector", "reranking"]
  },
  "audit_trail": {
    "tier_results": {
      "ac_exact": {"matches": 2, "processing_time_ms": 45.2},
      "blocking": {"candidates": 150, "processing_time_ms": 123.4},
      "knn_vector": {"top_matches": 50, "processing_time_ms": 456.7},
      "reranking": {"final_candidates": 5, "processing_time_ms": 234.1}
    },
    "decision_logic": {
      "threshold_applied": "review",
      "confidence_score": 0.78,
      "rule_matches": ["exact_name", "phonetic_match"]
    }
  }
}
```

## 🔍 Similarity Search Examples

### Find Similar Names
```bash
curl -X POST "http://localhost:8000/search-similar" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Владимир Путин",
    "candidates": [
      "Владимир Владимирович Путин",
      "Александр Иванов", 
      "Vladimir Putin",
      "Влад Путін"
    ],
    "threshold": 0.7,
    "top_k": 3,
    "use_embeddings": false
  }'
```

**Response:**
```json
{
  "method": "variants",
  "query": "Владимир Путин",
  "results": [
    {
      "text": "Владимир Владимирович Путин",
      "score": 0.846,
      "query": "Владимир Путин"
    },
    {
      "text": "Vladimir Putin", 
      "score": 0.782,
      "query": "Владимир Путин"
    }
  ],
  "total_candidates": 4,
  "threshold": 0.7
}
```

## 📊 Monitoring & Statistics

### Service Statistics
```bash
curl http://localhost:8000/stats
```

**Response:**
```json
{
  "processing": {
    "total_processed": 1247,
    "successful": 1235,
    "failed": 12,
    "success_rate": 0.99,
    "average_processing_time": 0.234
  },
  "cache": {
    "hits": 456,
    "misses": 791,
    "hit_rate": 0.365,
    "current_size": 1247,
    "max_size": 10000,
    "memory_usage_mb": 15.7
  },
  "services": {
    "unicode": "active",
    "language": "active",
    "normalization": "active", 
    "variants": "active",
    "patterns": "active",
    "templates": "active",
    "embeddings": "active"
  },
  "implementation": "legacy_orchestrator"
}
```

### Prometheus Metrics
```bash
curl http://localhost:8000/metrics
```

**Response** (Prometheus format):
```
# HELP orchestrator_processed_total Total processed
# TYPE orchestrator_processed_total gauge
orchestrator_processed_total 1247

# HELP orchestrator_successful_total Successful processed  
# TYPE orchestrator_successful_total gauge
orchestrator_successful_total 1235

# HELP orchestrator_cache_hit_rate Cache hit rate
# TYPE orchestrator_cache_hit_rate gauge
orchestrator_cache_hit_rate 0.365
```

## 🔒 Administrative Operations

### Clear Cache (Requires API Key)
```bash
curl -X POST "http://localhost:8000/clear-cache" \
  -H "Authorization: Bearer your-admin-api-key"
```

### Reset Statistics (Requires API Key)
```bash
curl -X POST "http://localhost:8000/reset-stats" \
  -H "Authorization: Bearer your-admin-api-key"
```

### Reload Watchlist Index (Requires API Key)
```bash
curl -X GET "http://localhost:8000/reload?snapshot=v2.1&overlay=false" \
  -H "Authorization: Bearer your-admin-api-key"
```

## 🌍 Language-Specific Examples

### Russian Text Processing
```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Министерство иностранных дел Российской Федерации"
  }'
```

### Ukrainian Text Processing  
```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Володимир Олександрович Зеленський"
  }'
```

### English Text Processing
```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "United States Department of Treasury"
  }'
```

## ⚡ Performance Optimization Examples

### High-Performance Batch Processing
```bash
curl -X POST "http://localhost:8000/process-batch" \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [/* 100 entities */],
    "generate_variants": true,
    "generate_embeddings": false,
    "max_concurrent": 10
  }'
```

### Cached vs Non-Cached Performance
```bash
# First request (cache miss)
time curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test Entity", "cache_result": true}'

# Second request (cache hit) 
time curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{"text": "Test Entity", "cache_result": true}'
```

## 🚨 Error Handling Examples

### Input Validation Error
```bash
curl -X POST "http://localhost:8000/process" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Very long text that exceeds maximum length limit..."
  }'
```

**Response:**
```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "text"],
      "msg": "Text length 50000 exceeds maximum allowed length 10000"
    }
  ]
}
```

### Service Unavailable Error
```bash
curl -X POST "http://localhost:8000/screen" \
  -H "Content-Type: application/json" \
  -d '{"text_purpose": "Test"}'
```

**Response (if service not initialized):**
```json
{
  "detail": "Services not initialized"
}
```

These examples demonstrate the full range of API capabilities for production sanctions screening workflows.