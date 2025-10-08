# 📚 AI Service API Documentation

## Overview

AI Service provides RESTful API endpoints for text normalization, structured data extraction, and hybrid search capabilities with multilingual support (English, Russian, Ukrainian).

## Base URL

```
Development: http://localhost:8000
Production:  https://your-domain.com
```

## Authentication

Most endpoints are public. Administrative endpoints require Bearer token authentication:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -X POST http://localhost:8000/admin/clear-cache
```

## Core Endpoints

### 1. Text Processing

#### `POST /process`

Complete text processing through all 9 layers of the AI pipeline.

**Request:**
```json
{
  "text": "Иван Иванович Иванов 15.05.1985",
  "options": {
    "include_variants": true,
    "include_embeddings": false,
    "language": "auto"
  }
}
```

**Response:**
```json
{
  "processed_text": "иван иванович иванов 15.05.1985",
  "language": "ru",
  "signals": {
    "persons": [
      {
        "name": "Иван Иванович Иванов",
        "confidence": 0.95,
        "position": {"start": 0, "end": 21}
      }
    ],
    "dates": [
      {
        "value": "15.05.1985",
        "normalized": "1985-05-15",
        "confidence": 0.98
      }
    ]
  },
  "variants": ["иван иванов", "ivan ivanov"],
  "processing_time_ms": 45
}
```

#### `POST /normalize`

Text normalization only (layers 1-5).

**Request:**
```json
{
  "text": "Петров Пётр Петрович",
  "language": "ru"
}
```

**Response:**
```json
{
  "normalized_text": "петров пётр петрович",
  "language": "ru",
  "tokens": [
    {"original": "Петров", "normalized": "петров", "type": "surname"},
    {"original": "Пётр", "normalized": "пётр", "type": "given_name"},
    {"original": "Петрович", "normalized": "петрович", "type": "patronymic"}
  ]
}
```

### 2. Batch Processing

#### `POST /process-batch`

Process multiple texts efficiently.

**Request:**
```json
{
  "texts": [
    "Иван Иванов",
    "Anna Smith",
    "Петро Петренко"
  ],
  "options": {
    "include_variants": false,
    "include_embeddings": false
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "text": "Иван Иванов",
      "processed_text": "иван иванов",
      "language": "ru",
      "signals": {...}
    },
    {
      "text": "Anna Smith", 
      "processed_text": "anna smith",
      "language": "en",
      "signals": {...}
    }
  ],
  "total_processing_time_ms": 120
}
```

### 3. Search Endpoints

#### `POST /search`

Hybrid search combining AC (Aho-Corasick) and vector search.

**Request:**
```json
{
  "query": "Иван Петров",
  "search_type": "hybrid",
  "options": {
    "limit": 10,
    "threshold": 0.7,
    "include_ac": true,
    "include_vector": true
  }
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "person_123",
      "name": "Иван Петрович Петров",
      "score": 0.92,
      "match_type": "hybrid",
      "highlights": ["<mark>Иван</mark> <mark>Петров</mark>ич Петров"]
    }
  ],
  "total_found": 1,
  "search_time_ms": 25
}
```

#### `POST /search/ac`

AC-only search for exact and fuzzy matching.

**Request:**
```json
{
  "query": "ООО Ромашка",
  "match_types": ["exact", "phrase", "ngram"],
  "fuzzy": true,
  "limit": 20
}
```

#### `POST /search/vector`

Vector-only semantic search.

**Request:**
```json
{
  "query": "John Smith",
  "similarity_threshold": 0.8,
  "limit": 15
}
```

### 4. Embeddings

#### `POST /embeddings/generate`

Generate vector embeddings for text.

**Request:**
```json
{
  "texts": ["Иван Иванов", "Anna Smith"],
  "model": "paraphrase-multilingual-MiniLM-L12-v2"
}
```

**Response:**
```json
{
  "embeddings": [
    {
      "text": "Иван Иванов",
      "vector": [0.1234, -0.5678, ...], // 384 dimensions
      "dimension": 384
    }
  ],
  "model_used": "paraphrase-multilingual-MiniLM-L12-v2",
  "generation_time_ms": 15
}
```

### 5. Administrative Endpoints 🔒

#### `POST /admin/clear-cache`

Clear all caches.

**Response:**
```json
{
  "message": "Cache cleared successfully",
  "cleared_entries": 1250
}
```

#### `POST /admin/reset-stats`

Reset processing statistics.

**Response:**
```json
{
  "message": "Statistics reset successfully",
  "reset_timestamp": "2024-01-15T10:30:00Z"
}
```

### 6. Information Endpoints

#### `GET /health`

Service health check.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "memory_usage_mb": 256,
  "cache_stats": {
    "hit_rate": 0.78,
    "total_entries": 5000
  }
}
```

#### `GET /stats`

Processing statistics.

**Response:**
```json
{
  "total_requests": 10000,
  "avg_processing_time_ms": 35,
  "cache_hit_rate": 0.78,
  "language_distribution": {
    "ru": 0.45,
    "en": 0.35,
    "uk": 0.20
  },
  "error_rate": 0.01
}
```

#### `GET /languages`

Supported languages.

**Response:**
```json
{
  "supported_languages": ["ru", "en", "uk"],
  "default_language": "auto",
  "detection_confidence_threshold": 0.8
}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input text",
    "details": {
      "field": "text",
      "issue": "Text cannot be empty"
    }
  },
  "request_id": "req_123456789"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request parameters |
| `PROCESSING_ERROR` | 500 | Text processing failed |
| `LANGUAGE_NOT_SUPPORTED` | 400 | Unsupported language |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `UNAUTHORIZED` | 401 | Invalid API key |
| `SEARCH_UNAVAILABLE` | 503 | Search service down |

## Rate Limiting

- **Public endpoints**: 1000 requests/minute per IP
- **Authenticated endpoints**: 5000 requests/minute per API key
- **Batch processing**: 100 requests/minute

## Performance

### Expected Latencies

| Operation | P50 | P95 | P99 |
|-----------|-----|-----|-----|
| Single text processing | 15ms | 45ms | 80ms |
| Batch processing (10 items) | 80ms | 150ms | 250ms |
| Hybrid search | 20ms | 50ms | 100ms |
| Embedding generation | 10ms | 25ms | 45ms |

### Throughput

- **Single instance**: ~1000 requests/second
- **Batch processing**: ~100 batches/second
- **Search queries**: ~500 queries/second

## SDK Examples

### Python

```python
import httpx

client = httpx.Client(base_url="http://localhost:8000")

# Process text
response = client.post("/process", json={
    "text": "Иван Иванов",
    "options": {"include_variants": True}
})
result = response.json()

# Search
response = client.post("/search", json={
    "query": "Иван Петров",
    "search_type": "hybrid"
})
results = response.json()["results"]
```

### JavaScript

```javascript
const response = await fetch('http://localhost:8000/process', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: 'Иван Иванов',
    options: { include_variants: true }
  })
});

const result = await response.json();
console.log(result.processed_text);
```

## Configuration

### Environment Variables

```bash
# Service Configuration
APP_ENV=production
WORKERS=4
DEBUG=false

# Security
ADMIN_API_KEY=your-secure-key

# Search Configuration
ELASTICSEARCH_URL=http://localhost:9200
ENABLE_VECTOR_SEARCH=true

# Performance
CACHE_TTL=3600
MAX_BATCH_SIZE=100
```

### Feature Flags

```python
# config/settings.py
FEATURE_FLAGS = {
    "use_factory_normalizer": True,
    "enable_search_optimizations": True,
    "enhanced_accuracy_mode": False
}
```

## Monitoring

### Metrics Endpoints

- `GET /metrics` - Prometheus metrics
- `GET /health/detailed` - Detailed health information

### Key Metrics

- `ai_service_requests_total` - Total requests
- `ai_service_processing_duration_seconds` - Processing latency
- `ai_service_cache_hit_rate` - Cache effectiveness
- `ai_service_errors_total` - Error count

## Support

For API support and questions:
- Documentation: [docs/](./)
- Issues: GitHub Issues
- Status: `/health` endpoint