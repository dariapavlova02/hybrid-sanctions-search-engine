# Search Configuration Guide

## Overview

This guide covers all configuration options for the Search layer in the AI Service, including Elasticsearch settings, search parameters, caching, security, and performance tuning.

## Configuration Structure

The search configuration is organized into several sections:

```yaml
search:
  # Basic search settings
  enable_search: true
  default_search_mode: "hybrid"
  default_top_k: 10
  default_threshold: 0.5
  
  # Elasticsearch configuration
  elasticsearch:
    hosts: ["localhost:9200"]
    timeout: 30
    max_retries: 3
    retry_on_timeout: true
    verify_certs: true
    
  # Caching settings
  enable_search_cache: true
  search_cache_size: 500
  search_cache_ttl_seconds: 1800
  
  # Security settings
  enable_elasticsearch_auth: false
  es_auth_type: "basic"
  enable_rate_limiting: false
  rate_limit_requests_per_minute: 100
```

## Basic Search Settings

### Core Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_search` | boolean | `true` | Enable/disable search functionality |
| `default_search_mode` | string | `"hybrid"` | Default search mode (ac, vector, hybrid) |
| `default_top_k` | integer | `10` | Default number of results to return |
| `default_threshold` | float | `0.5` | Default score threshold for results |

### Search Mode Configuration

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `ac_search.enabled` | boolean | `true` | Enable AC (autocomplete) search |
| `ac_search.boost` | float | `1.0` | Boost factor for AC search results |
| `vector_search.enabled` | boolean | `true` | Enable vector search |
| `vector_search.boost` | float | `1.0` | Boost factor for vector search results |
| `hybrid_search.enabled` | boolean | `true` | Enable hybrid search mode |

## Elasticsearch Configuration

### Connection Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `hosts` | array | `["localhost:9200"]` | Elasticsearch cluster hosts |
| `timeout` | integer | `30` | Connection timeout in seconds |
| `max_retries` | integer | `3` | Maximum retry attempts |
| `retry_on_timeout` | boolean | `true` | Retry on timeout errors |
| `verify_certs` | boolean | `true` | Verify SSL certificates |

### Authentication Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_elasticsearch_auth` | boolean | `false` | Enable Elasticsearch authentication |
| `es_auth_type` | string | `"basic"` | Authentication type (basic, api_key, ssl) |
| `es_username` | string | `null` | Elasticsearch username |
| `es_password` | string | `null` | Elasticsearch password |
| `es_api_key` | string | `null` | Elasticsearch API key |
| `es_ca_certs` | string | `null` | Path to CA certificates |

### Connection Pooling

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `maxsize` | integer | `25` | Maximum connections in pool |
| `http_compress` | boolean | `true` | Enable HTTP compression |
| `sniff_on_start` | boolean | `true` | Sniff cluster nodes on startup |
| `sniff_on_connection_fail` | boolean | `true` | Sniff on connection failure |
| `sniff_timeout` | integer | `10` | Timeout for sniffing operations |
| `sniff_interval` | integer | `60` | Interval between sniffing attempts |

## Caching Configuration

### Search Result Caching

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_search_cache` | boolean | `true` | Enable search result caching |
| `search_cache_size` | integer | `500` | Maximum cached results |
| `search_cache_ttl_seconds` | integer | `1800` | Cache TTL in seconds |

### Query Caching

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_query_caching` | boolean | `true` | Enable query result caching |
| `query_cache_size` | integer | `1000` | Maximum cached queries |
| `query_cache_ttl_seconds` | integer | `3600` | Query cache TTL in seconds |

### Embedding Caching

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_embedding_cache` | boolean | `true` | Enable embedding caching |
| `embedding_cache_size` | integer | `1000` | Maximum cached embeddings |
| `embedding_cache_ttl_seconds` | integer | `3600` | Embedding cache TTL in seconds |

## Security Configuration

### Authentication

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_elasticsearch_auth` | boolean | `false` | Enable Elasticsearch authentication |
| `es_auth_type` | string | `"basic"` | Authentication type |
| `es_username` | string | `null` | Elasticsearch username |
| `es_password` | string | `null` | Elasticsearch password |
| `es_api_key` | string | `null` | Elasticsearch API key |

### Rate Limiting

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_rate_limiting` | boolean | `false` | Enable rate limiting |
| `rate_limit_requests_per_minute` | integer | `100` | Requests per minute limit |

### Data Security

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_query_validation` | boolean | `true` | Enable query validation |
| `enable_sensitive_data_filtering` | boolean | `true` | Filter sensitive data from results |
| `enable_audit_logging` | boolean | `false` | Enable audit logging |

## Performance Configuration

### Query Optimization

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enable_query_optimization` | boolean | `true` | Enable query optimization |
| `ac_query_boost_factor` | float | `1.0` | AC query boost factor |
| `vector_query_boost_factor` | float | `1.0` | Vector query boost factor |
| `bm25_query_boost_factor` | float | `1.0` | BM25 query boost factor |

### Vector Search Settings

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `vector_dimension` | integer | `384` | Vector dimension size |
| `vector_cos_threshold` | float | `0.45` | Cosine similarity threshold |
| `vector_fallback_max_results` | integer | `50` | Maximum results for vector fallback |

## Environment-Specific Configuration

### Development Environment

```yaml
search:
  enable_search: true
  elasticsearch:
    hosts: ["localhost:9200"]
    verify_certs: false
  enable_elasticsearch_auth: false
  enable_rate_limiting: false
  enable_audit_logging: false
  search_cache_size: 100
  query_cache_size: 200
```

### Staging Environment

```yaml
search:
  enable_search: true
  elasticsearch:
    hosts: ["es-staging:9200"]
    verify_certs: true
  enable_elasticsearch_auth: true
  es_auth_type: "basic"
  es_username: "search_user"
  enable_rate_limiting: true
  rate_limit_requests_per_minute: 500
  enable_audit_logging: true
  search_cache_size: 500
  query_cache_size: 1000
```

### Production Environment

```yaml
search:
  enable_search: true
  elasticsearch:
    hosts: ["es-node1:9200", "es-node2:9200", "es-node3:9200"]
    verify_certs: true
    maxsize: 50
    sniff_on_start: true
    sniff_on_connection_fail: true
  enable_elasticsearch_auth: true
  es_auth_type: "api_key"
  es_api_key: "${ES_API_KEY}"
  enable_rate_limiting: true
  rate_limit_requests_per_minute: 1000
  enable_audit_logging: true
  search_cache_size: 2000
  query_cache_size: 5000
  enable_query_optimization: true
  ac_query_boost_factor: 1.2
  vector_query_boost_factor: 1.1
  bm25_query_boost_factor: 1.0
```

## Configuration Examples

### Basic Setup

```yaml
# config.yaml
search:
  enable_search: true
  default_search_mode: "hybrid"
  elasticsearch:
    hosts: ["localhost:9200"]
    timeout: 30
  enable_search_cache: true
  search_cache_size: 500
```

### High-Performance Setup

```yaml
# config.yaml
search:
  enable_search: true
  default_search_mode: "hybrid"
  elasticsearch:
    hosts: ["es1:9200", "es2:9200", "es3:9200"]
    timeout: 60
    maxsize: 100
    sniff_on_start: true
    sniff_on_connection_fail: true
  enable_search_cache: true
  search_cache_size: 5000
  enable_query_caching: true
  query_cache_size: 10000
  enable_query_optimization: true
  ac_query_boost_factor: 1.5
  vector_query_boost_factor: 1.2
  bm25_query_boost_factor: 1.1
```

### Secure Setup

```yaml
# config.yaml
search:
  enable_search: true
  elasticsearch:
    hosts: ["es-secure:9200"]
    verify_certs: true
    es_ca_certs: "/path/to/ca-bundle.crt"
  enable_elasticsearch_auth: true
  es_auth_type: "api_key"
  es_api_key: "${ES_API_KEY}"
  enable_rate_limiting: true
  rate_limit_requests_per_minute: 100
  enable_query_validation: true
  enable_sensitive_data_filtering: true
  enable_audit_logging: true
```

## Performance Tuning

### Memory Optimization

```yaml
search:
  # Reduce cache sizes for memory-constrained environments
  search_cache_size: 100
  query_cache_size: 200
  embedding_cache_size: 500
  
  # Optimize connection pooling
  elasticsearch:
    maxsize: 10
    sniff_interval: 120
```

### Latency Optimization

```yaml
search:
  # Increase cache sizes for better hit rates
  search_cache_size: 2000
  query_cache_size: 5000
  
  # Optimize connection settings
  elasticsearch:
    timeout: 10
    max_retries: 1
    maxsize: 50
    http_compress: true
```

### Throughput Optimization

```yaml
search:
  # Enable all optimizations
  enable_query_optimization: true
  enable_query_caching: true
  enable_embedding_cache: true
  
  # Optimize boost factors
  ac_query_boost_factor: 1.2
  vector_query_boost_factor: 1.1
  bm25_query_boost_factor: 1.0
  
  # Increase connection pool
  elasticsearch:
    maxsize: 100
    sniff_on_start: true
    sniff_on_connection_fail: true
```

## Troubleshooting

### Common Issues

#### Elasticsearch Connection Errors

**Problem**: `Elasticsearch connection failed`

**Solutions**:
1. Check Elasticsearch is running: `curl http://localhost:9200`
2. Verify hosts configuration
3. Check network connectivity
4. Verify authentication credentials

**Configuration**:
```yaml
elasticsearch:
  hosts: ["localhost:9200"]
  timeout: 30
  max_retries: 3
  retry_on_timeout: true
```

#### High Memory Usage

**Problem**: High memory consumption

**Solutions**:
1. Reduce cache sizes
2. Enable cache eviction
3. Optimize connection pooling

**Configuration**:
```yaml
search_cache_size: 100
query_cache_size: 200
embedding_cache_size: 500
elasticsearch:
  maxsize: 10
```

#### Slow Search Performance

**Problem**: Slow search response times

**Solutions**:
1. Enable query optimization
2. Increase cache sizes
3. Optimize boost factors
4. Check Elasticsearch performance

**Configuration**:
```yaml
enable_query_optimization: true
search_cache_size: 2000
query_cache_size: 5000
ac_query_boost_factor: 1.2
vector_query_boost_factor: 1.1
```

#### Rate Limiting Issues

**Problem**: `Rate limit exceeded` errors

**Solutions**:
1. Increase rate limit
2. Implement client-side throttling
3. Use caching to reduce requests

**Configuration**:
```yaml
enable_rate_limiting: true
rate_limit_requests_per_minute: 1000
```

### Monitoring and Debugging

#### Enable Debug Logging

```yaml
logging:
  level: DEBUG
  search:
    level: DEBUG
    elasticsearch: DEBUG
    cache: DEBUG
```

#### Health Check Endpoints

```bash
# Check search service health
curl http://localhost:8000/api/v1/search/health

# Check Elasticsearch health
curl http://localhost:8000/api/v1/search/health/elasticsearch

# Check cache statistics
curl http://localhost:8000/api/v1/search/health/cache
```

#### Performance Metrics

```bash
# Get search metrics
curl http://localhost:8000/metrics | grep search_

# Get cache statistics
curl http://localhost:8000/api/v1/search/stats/cache

# Get query performance
curl http://localhost:8000/api/v1/search/stats/performance
```

## Migration Guide

### Upgrading from v1.0 to v2.0

1. **Update configuration structure**:
   ```yaml
   # Old format
   search_layer:
     elasticsearch_host: "localhost:9200"
   
   # New format
   search:
     elasticsearch:
       hosts: ["localhost:9200"]
   ```

2. **Update authentication settings**:
   ```yaml
   # Old format
   es_username: "user"
   es_password: "pass"
   
   # New format
   enable_elasticsearch_auth: true
   es_auth_type: "basic"
   es_username: "user"
   es_password: "pass"
   ```

3. **Update cache settings**:
   ```yaml
   # Old format
   cache_size: 500
   
   # New format
   search_cache_size: 500
   query_cache_size: 1000
   ```

### Configuration Validation

The system validates configuration on startup:

```bash
# Check configuration validity
python -m ai_service.config.validate

# Test Elasticsearch connection
python -m ai_service.config.test_elasticsearch
```

## Best Practices

1. **Start with defaults**: Begin with default configuration and tune as needed
2. **Monitor performance**: Use metrics to identify bottlenecks
3. **Test thoroughly**: Validate configuration in staging before production
4. **Use environment variables**: Store sensitive data in environment variables
5. **Enable caching**: Always enable caching for better performance
6. **Configure monitoring**: Set up health checks and metrics collection
7. **Plan for scaling**: Configure connection pooling and clustering
8. **Security first**: Enable authentication and rate limiting in production
