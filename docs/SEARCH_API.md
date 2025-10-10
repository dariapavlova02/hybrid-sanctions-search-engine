# Search API Documentation

## Overview

The Search API provides comprehensive search capabilities for the AI Service, including AC (Autocomplete) search, vector search, and hybrid search modes. The API supports both exact matches and fuzzy matching with fallback mechanisms.

## Base URL

```
GET /api/v1/search
```

## Authentication

The Search API supports multiple authentication methods:

- **API Key**: Include `X-API-Key` header
- **Basic Auth**: Username/password authentication
- **JWT Token**: Bearer token authentication

## Request Parameters

### Required Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `query` | string | Search query text | "John Smith" |
| `search_mode` | string | Search mode: `ac`, `vector`, or `hybrid` | "hybrid" |

### Optional Parameters

| Parameter | Type | Default | Description | Example |
|-----------|------|---------|-------------|---------|
| `top_k` | integer | 10 | Maximum number of results to return | 20 |
| `threshold` | float | 0.5 | Minimum score threshold for results | 0.7 |
| `language` | string | "auto" | Language for search (auto, en, ru, uk) | "en" |
| `entity_types` | array | [] | Filter by entity types | ["person", "organization"] |
| `client_id` | string | "default" | Client identifier for rate limiting | "web_app" |

### Advanced Parameters

| Parameter | Type | Default | Description | Example |
|-----------|------|---------|-------------|---------|
| `ac_boost` | float | 1.0 | Boost factor for AC search | 1.5 |
| `vector_boost` | float | 1.0 | Boost factor for vector search | 1.2 |
| `bm25_boost` | float | 1.0 | Boost factor for BM25 search | 1.1 |
| `enable_fallback` | boolean | true | Enable fallback search | false |
| `max_results` | integer | 100 | Maximum results from each search mode | 50 |

## Request Examples

### Basic Search Request

```json
{
  "query": "John Smith",
  "search_mode": "hybrid",
  "top_k": 10,
  "threshold": 0.7
}
```

### Advanced Search Request

```json
{
  "query": "Petr Petrovich Ivanov",
  "search_mode": "hybrid",
  "top_k": 20,
  "threshold": 0.6,
  "language": "ru",
  "entity_types": ["person"],
  "ac_boost": 1.5,
  "vector_boost": 1.2,
  "enable_fallback": true
}
```

### AC Search Only

```json
{
  "query": "Petr",
  "search_mode": "ac",
  "top_k": 15,
  "threshold": 0.8
}
```

### Vector Search Only

```json
{
  "query": "John Smith",
  "search_mode": "vector",
  "top_k": 10,
  "threshold": 0.5
}
```

## Response Format

### Success Response

```json
{
  "status": "success",
  "data": {
    "candidates": [
      {
        "doc_id": "person_12345",
        "score": 0.95,
        "text": "John Smith",
        "entity_type": "person",
        "metadata": {
          "first_name": "John",
          "last_name": "Smith",
          "aliases": ["J. Smith", "Johnny"]
        },
        "search_mode": "ac",
        "match_fields": ["normalized_text"],
        "confidence": 0.95
      }
    ],
    "total_results": 1,
    "processing_time_ms": 45.2,
    "search_modes_used": ["ac", "vector"],
    "cache_hit": false,
    "fallback_used": false
  },
  "metadata": {
    "query": "John Smith",
    "normalized_query": "john smith",
    "language": "en",
    "confidence": 0.95,
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### Error Response

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Maximum 100 requests per minute.",
    "details": {
      "limit": 100,
      "window": "1 minute",
      "retry_after": 30
    }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

## Search Modes

### AC Search (Autocomplete)

- **Purpose**: Fast prefix matching for autocomplete functionality
- **Best for**: Real-time suggestions, exact name matching
- **Performance**: Very fast (< 10ms typical)
- **Use cases**: User input suggestions, exact name lookups

### Vector Search

- **Purpose**: Semantic similarity search using embeddings
- **Best for**: Fuzzy matching, similar names, typos
- **Performance**: Fast (10-50ms typical)
- **Use cases**: Finding similar names, handling typos, cross-language search

### Hybrid Search

- **Purpose**: Combines AC and vector search for best results
- **Best for**: Comprehensive search with high recall
- **Performance**: Medium (20-100ms typical)
- **Use cases**: General search, complex queries, production systems

## Error Codes

| Code | HTTP Status | Description | Solution |
|------|-------------|-------------|----------|
| `INVALID_QUERY` | 400 | Query parameter is missing or invalid | Provide valid query string |
| `INVALID_SEARCH_MODE` | 400 | Invalid search mode specified | Use 'ac', 'vector', or 'hybrid' |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests | Wait and retry after specified time |
| `AUTHENTICATION_FAILED` | 401 | Invalid or missing authentication | Provide valid API key or credentials |
| `AUTHORIZATION_FAILED` | 403 | Insufficient permissions | Contact administrator for access |
| `QUERY_TOO_LONG` | 400 | Query exceeds maximum length | Shorten query to under 1000 characters |
| `INVALID_THRESHOLD` | 400 | Threshold value is invalid | Use value between 0.0 and 1.0 |
| `SEARCH_SERVICE_UNAVAILABLE` | 503 | Search service is temporarily unavailable | Retry after some time |
| `ELASTICSEARCH_ERROR` | 500 | Elasticsearch connection error | Contact support if persistent |
| `FALLBACK_ERROR` | 500 | Fallback search failed | Contact support |

## Rate Limiting

The Search API implements rate limiting to ensure fair usage:

- **Default limit**: 100 requests per minute per client
- **Burst limit**: 10 requests per second
- **Headers**: Rate limit information is included in response headers:
  - `X-RateLimit-Limit`: Maximum requests per window
  - `X-RateLimit-Remaining`: Remaining requests in current window
  - `X-RateLimit-Reset`: Time when the rate limit resets

## Caching

The Search API implements multiple levels of caching:

- **Query cache**: Caches search results for 30 minutes
- **Vector cache**: Caches generated embeddings for 1 hour
- **Configuration cache**: Caches search configuration for 5 minutes

Cache headers are included in responses:
- `X-Cache-Status`: `HIT`, `MISS`, or `BYPASS`
- `X-Cache-TTL`: Time to live for cached result

## Performance Tips

1. **Use appropriate search mode**: AC for exact matches, vector for fuzzy search
2. **Set reasonable thresholds**: Lower thresholds (0.3-0.5) for more results
3. **Limit result count**: Use `top_k` to control response size
4. **Enable caching**: Cached results are much faster
5. **Use fallback**: Enable fallback for better reliability

## Examples

### cURL Examples

```bash
# Basic search
curl -X GET "https://api.example.com/api/v1/search?query=John%20Smith&search_mode=hybrid" \
  -H "X-API-Key: your-api-key"

# Advanced search with JSON body
curl -X POST "https://api.example.com/api/v1/search" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "Petr Petrovich Ivanov",
    "search_mode": "hybrid",
    "top_k": 20,
    "threshold": 0.6,
    "language": "ru"
  }'
```

### Python Examples

```python
import requests

# Basic search
response = requests.get(
    "https://api.example.com/api/v1/search",
    params={
        "query": "John Smith",
        "search_mode": "hybrid",
        "top_k": 10
    },
    headers={"X-API-Key": "your-api-key"}
)

# Advanced search
search_data = {
    "query": "Petr Petrovich Ivanov",
    "search_mode": "hybrid",
    "top_k": 20,
    "threshold": 0.6,
    "language": "ru",
    "entity_types": ["person"]
}

response = requests.post(
    "https://api.example.com/api/v1/search",
    json=search_data,
    headers={"X-API-Key": "your-api-key"}
)
```

### JavaScript Examples

```javascript
// Basic search
const response = await fetch('/api/v1/search?query=John%20Smith&search_mode=hybrid', {
  headers: {
    'X-API-Key': 'your-api-key'
  }
});

// Advanced search
const searchData = {
  query: 'Petr Petrovich Ivanov',
  search_mode: 'hybrid',
  top_k: 20,
  threshold: 0.6,
  language: 'ru'
};

const response = await fetch('/api/v1/search', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': 'your-api-key'
  },
  body: JSON.stringify(searchData)
});
```

## Monitoring and Health

### Health Check

```bash
curl -X GET "https://api.example.com/api/v1/search/health"
```

Response:
```json
{
  "status": "healthy",
  "elasticsearch": {
    "status": "connected",
    "cluster_health": "green"
  },
  "fallback_services": {
    "watchlist_index": "available",
    "vector_index": "available"
  },
  "cache": {
    "search_cache": {
      "size": 150,
      "hit_rate": 0.85
    },
    "query_cache": {
      "size": 200,
      "hit_rate": 0.92
    }
  },
  "performance": {
    "avg_response_time_ms": 45.2,
    "total_requests": 1250,
    "error_rate": 0.02
  }
}
```

### Metrics

The Search API exposes Prometheus metrics at `/metrics`:

- `search_requests_total`: Total number of search requests
- `search_request_duration_seconds`: Request duration histogram
- `search_cache_hits_total`: Cache hit counter
- `search_errors_total`: Error counter by type
- `elasticsearch_connection_errors_total`: Elasticsearch connection errors